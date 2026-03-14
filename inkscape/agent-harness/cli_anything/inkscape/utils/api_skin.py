"""api-anything API Skin — Universal REST API wrapper for cli-anything CLIs.

Copy this file into your CLI package at:
    cli_anything/<software>/utils/api_skin.py

Usage (auto-wrap existing CLI — 3 lines):

    from cli_anything.gimp.gimp_cli import cli
    from cli_anything.gimp.core.session import Session
    from cli_anything.gimp.utils.api_skin import ApiSkin

    api = ApiSkin.from_click("gimp", cli, Session)
    api.run()

Usage (manual routes for full control):

    from cli_anything.gimp.utils.api_skin import ApiSkin
    from cli_anything.gimp.core.session import Session
    from cli_anything.gimp.core import project as proj_mod

    api = ApiSkin("gimp", session_factory=Session)

    @api.app.post("/project/new", tags=["project"])
    def project_new(width: int = 1920, height: int = 1080,
                    x_session_id: str = Header(alias="X-Session-Id")):
        sess = api.get_session(x_session_id)
        proj = proj_mod.create_project(width=width, height=height)
        sess.set_project(proj)
        return proj_mod.get_project_info(proj)

    api.run()
"""

import uuid
import time
import json
import threading
import io
import re
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Optional, Callable, Dict, List, Type

try:
    import click
    from click.testing import CliRunner
except ImportError:
    click = None

try:
    from fastapi import FastAPI, HTTPException, Header, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field, create_model
    import uvicorn
except ImportError as e:
    raise ImportError(
        "api-anything requires FastAPI and uvicorn. Install with:\n"
        "  pip install fastapi uvicorn python-multipart"
    ) from e


# ── Brand colors (for terminal logging) ─────────────────────────
_CYAN = "\033[38;5;80m"
_BOLD = "\033[1m"
_RESET = "\033[0m"
_DIM = "\033[2m"
_GREEN = "\033[38;5;78m"
_YELLOW = "\033[38;5;220m"

_ACCENT_COLORS = {
    "gimp":        "\033[38;5;214m",
    "blender":     "\033[38;5;208m",
    "inkscape":    "\033[38;5;39m",
    "audacity":    "\033[38;5;33m",
    "libreoffice": "\033[38;5;40m",
    "obs_studio":  "\033[38;5;55m",
    "kdenlive":    "\033[38;5;69m",
    "shotcut":     "\033[38;5;35m",
}
_DEFAULT_ACCENT = "\033[38;5;75m"


# ── Session Store ────────────────────────────────────────────────

class SessionStore:
    """Thread-safe session store with TTL-based expiration."""

    def __init__(self, ttl: int = 3600):
        """
        Args:
            ttl: Session time-to-live in seconds (default: 1 hour).
        """
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._store_lock = threading.Lock()
        self.ttl = ttl

    def create(self, factory: Callable) -> str:
        """Create a new session. Returns the session ID."""
        sid = str(uuid.uuid4())
        with self._store_lock:
            self._sessions[sid] = {
                "session": factory(),
                "created_at": time.time(),
                "last_access": time.time(),
            }
            self._locks[sid] = threading.Lock()
        return sid

    def get(self, sid: str) -> Any:
        """Get the session object for a given ID. Raises KeyError if not found."""
        with self._store_lock:
            if sid not in self._sessions:
                raise KeyError(sid)
            self._sessions[sid]["last_access"] = time.time()
            return self._sessions[sid]["session"]

    def get_lock(self, sid: str) -> Optional[threading.Lock]:
        """Get the per-session lock for thread-safe command execution."""
        with self._store_lock:
            return self._locks.get(sid)

    def delete(self, sid: str) -> None:
        """Delete a session."""
        with self._store_lock:
            self._sessions.pop(sid, None)
            self._locks.pop(sid, None)

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions (metadata only)."""
        with self._store_lock:
            return {
                sid: {
                    "created_at": entry["created_at"],
                    "last_access": entry["last_access"],
                    "has_project": (
                        entry["session"].has_project()
                        if hasattr(entry["session"], "has_project")
                        else None
                    ),
                }
                for sid, entry in self._sessions.items()
            }

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        now = time.time()
        with self._store_lock:
            expired = [
                sid for sid, entry in self._sessions.items()
                if now - entry["last_access"] > self.ttl
            ]
            for sid in expired:
                del self._sessions[sid]
                self._locks.pop(sid, None)
            return len(expired)


# ── Click-to-API Bridge ─────────────────────────────────────────

# Commands whose names imply read-only (safe for GET)
_READ_VERBS = frozenset({
    "list", "info", "status", "show", "get", "check", "probe",
    "histogram", "presets", "preset-info", "profiles", "json",
    "history", "list-available",
})

# Commands whose names imply deletion
_DELETE_VERBS = frozenset({"remove", "delete", "close"})


def _infer_method(name: str) -> str:
    """Infer HTTP method from Click command name."""
    if name in _READ_VERBS:
        return "GET"
    if name in _DELETE_VERBS:
        return "DELETE"
    return "POST"


def _click_type_to_python(param_type) -> type:
    """Map a Click parameter type to a Python type."""
    if click is None:
        return str
    if isinstance(param_type, click.types.IntParamType):
        return int
    if isinstance(param_type, click.types.FloatParamType):
        return float
    if isinstance(param_type, click.types.BoolParamType):
        return bool
    return str


def _param_name_to_option(name: str) -> str:
    """Convert Python param name to Click option flag."""
    return f"--{name.replace('_', '-')}"


def _extract_click_params(cmd) -> List[Dict[str, Any]]:
    """Extract parameter info from a Click command."""
    params = []
    for p in cmd.params:
        # Skip the --json flag (API always returns JSON)
        if p.name in ("use_json",):
            continue

        # Get the actual Click option string (e.g., "--type" not "--layer-type")
        cli_option = None
        if hasattr(p, "opts") and p.opts:
            # Use the longest option string (prefer --long-form over -s)
            cli_option = max(p.opts, key=len)

        info: Dict[str, Any] = {
            "name": p.name,
            "cli_option": cli_option,
            "required": p.required,
            "default": p.default,
            "help": getattr(p, "help", "") or "",
            "is_flag": getattr(p, "is_flag", False),
            "multiple": getattr(p, "multiple", False),
            "is_argument": isinstance(p, click.Argument),
        }

        if info["is_flag"]:
            info["python_type"] = bool
            info["default"] = info["default"] if info["default"] is not None else False
        elif info["multiple"]:
            info["python_type"] = str  # Will become List[str]
            info["default"] = None
        else:
            info["python_type"] = _click_type_to_python(p.type)

        # Extract choices
        if hasattr(p, "type") and isinstance(p.type, click.Choice):
            info["choices"] = list(p.type.choices)

        params.append(info)
    return params


def _build_click_args(params_info: List[Dict], values: Dict[str, Any]) -> List[str]:
    """Build Click command-line args from parameter values."""
    args = []
    for p in params_info:
        val = values.get(p["name"])
        if val is None:
            continue

        # Use the actual Click option string if available, otherwise derive it
        opt_flag = p.get("cli_option") or _param_name_to_option(p["name"])

        if p["is_argument"]:
            args.append(str(val))
        elif p["is_flag"]:
            if val:
                args.append(opt_flag)
        elif p["multiple"]:
            if isinstance(val, list):
                for v in val:
                    args.append(opt_flag)
                    args.append(str(v))
            elif isinstance(val, str):
                args.append(opt_flag)
                args.append(val)
        else:
            args.append(opt_flag)
            args.append(str(val))
    return args


def _parse_cli_output(output: str) -> Any:
    """Parse CLI output, trying JSON first, then returning raw text."""
    output = output.strip()
    if not output:
        return {"status": "ok"}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"output": output}


# ── ApiSkin ──────────────────────────────────────────────────────

class ApiSkin:
    """Universal API skin for cli-anything CLIs.

    Creates a FastAPI application with:
    - Multi-tenant session management
    - Auto-generated REST endpoints from Click command trees
    - OpenAPI/Swagger documentation at /docs
    - CORS support for browser clients
    - Thread-safe command execution
    """

    def __init__(
        self,
        software: str,
        version: str = "1.0.0",
        session_factory: Optional[Callable] = None,
        session_ttl: int = 3600,
        cors_origins: Optional[List[str]] = None,
    ):
        """
        Args:
            software: Software name (e.g., "gimp", "blender").
            version: API version string.
            session_factory: Callable that creates a new Session instance.
            session_ttl: Session time-to-live in seconds.
            cors_origins: Allowed CORS origins (default: ["*"]).
        """
        self.software = software.lower().replace("-", "_")
        self.display_name = software.replace("_", " ").title()
        self.version = version
        self.session_factory = session_factory
        self.store = SessionStore(ttl=session_ttl)
        self._invoke_lock = threading.Lock()
        self._cli_module = None

        accent = _ACCENT_COLORS.get(self.software, _DEFAULT_ACCENT)

        self.app = FastAPI(
            title=f"api-anything \u00b7 {self.display_name}",
            version=version,
            description=(
                f"REST API for **{self.display_name}**, "
                f"auto-generated by [api-anything](https://github.com/HKUDS/CLI-Anything).\n\n"
                f"All stateful commands require an `X-Session-Id` header. "
                f"Create a session first via `POST /sessions`."
            ),
        )

        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins or ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Error handler
        @self.app.exception_handler(Exception)
        async def global_error_handler(request: Request, exc: Exception):
            return JSONResponse(
                status_code=500,
                content={"error": str(exc), "type": type(exc).__name__},
            )

        self._register_health_routes()
        self._register_session_routes()

    # ── Health ────────────────────────────────────────────────────

    def _register_health_routes(self):
        @self.app.get("/", tags=["meta"], summary="API info")
        def root():
            return {
                "software": self.software,
                "display_name": self.display_name,
                "version": self.version,
                "docs": "/docs",
                "openapi": "/openapi.json",
            }

        @self.app.get("/health", tags=["meta"], summary="Health check")
        def health():
            return {
                "status": "ok",
                "software": self.software,
                "version": self.version,
            }

    # ── Sessions ──────────────────────────────────────────────────

    def _register_session_routes(self):
        store = self.store
        factory = self.session_factory

        @self.app.post(
            "/sessions",
            tags=["sessions"],
            summary="Create a new session",
            response_description="Returns a session_id to use in X-Session-Id header",
        )
        def create_session():
            if factory is None:
                raise HTTPException(500, "No session factory configured")
            sid = store.create(factory)
            return {"session_id": sid}

        @self.app.get("/sessions", tags=["sessions"], summary="List active sessions")
        def list_sessions():
            return store.list_all()

        @self.app.get(
            "/sessions/{session_id}",
            tags=["sessions"],
            summary="Get session details",
        )
        def get_session_info(session_id: str):
            try:
                sess = store.get(session_id)
            except KeyError:
                raise HTTPException(404, f"Session {session_id} not found")
            if hasattr(sess, "status"):
                return {"session_id": session_id, **sess.status()}
            return {"session_id": session_id, "status": "active"}

        @self.app.delete(
            "/sessions/{session_id}",
            tags=["sessions"],
            summary="Delete a session",
        )
        def delete_session(session_id: str):
            store.delete(session_id)
            return {"deleted": session_id}

        @self.app.post(
            "/sessions/cleanup",
            tags=["sessions"],
            summary="Remove expired sessions",
        )
        def cleanup_sessions():
            count = store.cleanup_expired()
            return {"removed": count}

    # ── Session helper ────────────────────────────────────────────

    def get_session(self, session_id: str) -> Any:
        """Retrieve a session by ID. Raises HTTPException 404 if not found."""
        try:
            return self.store.get(session_id)
        except KeyError:
            raise HTTPException(404, f"Session {session_id} not found")

    # ── Click auto-wrapper ────────────────────────────────────────

    @classmethod
    def from_click(
        cls,
        software: str,
        cli_group,
        session_factory: Callable,
        cli_module=None,
        version: str = "1.0.0",
        session_ttl: int = 3600,
    ) -> "ApiSkin":
        """Create an ApiSkin by auto-wrapping a Click CLI group.

        This introspects the Click command tree and generates FastAPI
        routes for every command. Commands are invoked via Click's
        CliRunner with --json flag for structured output.

        Args:
            software: Software name.
            cli_group: The Click group (e.g., from gimp_cli.py).
            session_factory: Callable that returns a new Session.
            cli_module: The module containing the CLI (for session binding).
                        If None, auto-detected from cli_group.
            version: API version.
            session_ttl: Session TTL in seconds.
        """
        api = cls(
            software=software,
            version=version,
            session_factory=session_factory,
            session_ttl=session_ttl,
        )
        api._cli_group = cli_group

        # Auto-detect CLI module for session binding
        if cli_module is None and hasattr(cli_group, "callback"):
            import inspect
            mod = inspect.getmodule(cli_group.callback)
            api._cli_module = mod
        else:
            api._cli_module = cli_module

        api._register_click_routes(cli_group, prefix="")
        return api

    def _register_click_routes(self, group, prefix: str):
        """Recursively walk a Click group and register routes."""
        if not hasattr(group, "commands"):
            return

        for name, cmd in group.commands.items():
            # Skip REPL command — interactive only
            if name == "repl":
                continue

            path = f"{prefix}/{name}"

            if isinstance(cmd, click.Group):
                self._register_click_routes(cmd, path)
            elif isinstance(cmd, click.Command):
                self._register_click_command(cmd, path, name, prefix)

    def _register_click_command(self, cmd, path: str, name: str, group_prefix: str):
        """Register a single Click command as a FastAPI route."""
        method = _infer_method(name)
        tag = group_prefix.strip("/") or self.software
        params_info = _extract_click_params(cmd)

        # Build Pydantic model for POST/DELETE body
        model_fields = {}
        for p in params_info:
            py_type = p["python_type"]
            if p["multiple"]:
                # Multiple values -> Optional[List[str]]
                model_fields[p["name"]] = (
                    Optional[List[str]],
                    Field(None, description=p["help"]),
                )
            elif p["required"] and p["default"] is None:
                model_fields[p["name"]] = (
                    py_type,
                    Field(..., description=p["help"]),
                )
            else:
                model_fields[p["name"]] = (
                    Optional[py_type],
                    Field(p["default"], description=p["help"]),
                )

        # Create dynamic model
        model_name = "".join(
            part.capitalize() for part in path.strip("/").split("/")
        ) + "Request"
        RequestModel = create_model(model_name, **model_fields) if model_fields else None

        # Build the command path for CliRunner
        cmd_path = [seg for seg in path.strip("/").split("/") if seg]

        # Capture references for closure
        api = self
        p_info = params_info

        summary = cmd.help.split("\n")[0] if cmd.help else name

        if method == "GET":
            # GET: use query parameters
            if RequestModel:
                @self.app.get(
                    path, tags=[tag], summary=summary,
                    response_model=None, name=f"get_{path.strip('/').replace('/', '_')}",
                )
                def get_handler(
                    request: Request,
                    x_session_id: str = Header(..., alias="X-Session-Id"),
                    _cmd_path=cmd_path, _p_info=p_info, _model=RequestModel,
                ):
                    values = dict(request.query_params)
                    # Cast types
                    for p in _p_info:
                        if p["name"] in values:
                            try:
                                values[p["name"]] = p["python_type"](values[p["name"]])
                            except (ValueError, TypeError):
                                pass
                    return api._invoke_click(x_session_id, _cmd_path, _p_info, values)
            else:
                @self.app.get(
                    path, tags=[tag], summary=summary,
                    response_model=None, name=f"get_{path.strip('/').replace('/', '_')}",
                )
                def get_handler_no_params(
                    x_session_id: str = Header(..., alias="X-Session-Id"),
                    _cmd_path=cmd_path,
                ):
                    return api._invoke_click(x_session_id, _cmd_path, [], {})

        elif method == "POST":
            if RequestModel:
                @self.app.post(
                    path, tags=[tag], summary=summary,
                    response_model=None, name=f"post_{path.strip('/').replace('/', '_')}",
                )
                def post_handler(
                    body: RequestModel,  # type: ignore[valid-type]
                    x_session_id: str = Header(..., alias="X-Session-Id"),
                    _cmd_path=cmd_path, _p_info=p_info,
                ):
                    values = body.model_dump(exclude_none=False)
                    return api._invoke_click(x_session_id, _cmd_path, _p_info, values)
            else:
                @self.app.post(
                    path, tags=[tag], summary=summary,
                    response_model=None, name=f"post_{path.strip('/').replace('/', '_')}",
                )
                def post_handler_no_params(
                    x_session_id: str = Header(..., alias="X-Session-Id"),
                    _cmd_path=cmd_path,
                ):
                    return api._invoke_click(x_session_id, _cmd_path, [], {})

        elif method == "DELETE":
            if RequestModel:
                @self.app.delete(
                    path, tags=[tag], summary=summary,
                    response_model=None, name=f"delete_{path.strip('/').replace('/', '_')}",
                )
                def delete_handler(
                    body: RequestModel,  # type: ignore[valid-type]
                    x_session_id: str = Header(..., alias="X-Session-Id"),
                    _cmd_path=cmd_path, _p_info=p_info,
                ):
                    values = body.model_dump(exclude_none=False)
                    return api._invoke_click(x_session_id, _cmd_path, _p_info, values)
            else:
                @self.app.delete(
                    path, tags=[tag], summary=summary,
                    response_model=None, name=f"delete_{path.strip('/').replace('/', '_')}",
                )
                def delete_handler_no_params(
                    x_session_id: str = Header(..., alias="X-Session-Id"),
                    _cmd_path=cmd_path,
                ):
                    return api._invoke_click(x_session_id, _cmd_path, [], {})

    def _invoke_click(
        self,
        session_id: str,
        cmd_path: List[str],
        params_info: List[Dict],
        values: Dict[str, Any],
    ) -> Any:
        """Invoke a Click command with session binding and output capture."""
        # Validate session
        try:
            session = self.store.get(session_id)
        except KeyError:
            raise HTTPException(404, f"Session {session_id} not found")

        # Build CLI args
        cli_args = ["--json"] + cmd_path + _build_click_args(params_info, values)

        # Thread-safe invocation: the CLI uses module-level globals for session
        # state, so we must serialize all invocations to avoid races.
        with self._invoke_lock:
            # Bind the session to the CLI module
            if self._cli_module is not None:
                original_session = getattr(self._cli_module, "_session", None)
                setattr(self._cli_module, "_session", session)

            try:
                runner = CliRunner(mix_stderr=False)
                result = runner.invoke(self._cli_group, cli_args, catch_exceptions=True)

                # Check for errors: non-zero exit code or uncaught exceptions
                if result.exception and not isinstance(result.exception, SystemExit):
                    raise HTTPException(
                        400,
                        {
                            "error": str(result.exception),
                            "type": type(result.exception).__name__,
                        },
                    )

                if result.exit_code != 0:
                    # Click caught an error (UsageError, etc.) and called sys.exit
                    error_output = result.output.strip()
                    if hasattr(result, "stderr") and result.stderr:
                        error_output = result.stderr.strip()
                    raise HTTPException(
                        400,
                        {
                            "error": error_output or f"Command failed with exit code {result.exit_code}",
                            "exit_code": result.exit_code,
                        },
                    )

                return _parse_cli_output(result.output)

            finally:
                # Restore original session
                if self._cli_module is not None:
                    setattr(self._cli_module, "_session", original_session)

    # ── Server ────────────────────────────────────────────────────

    def run(self, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        """Start the API server.

        Args:
            host: Bind address.
            port: Bind port.
            **kwargs: Additional args passed to uvicorn.run().
        """
        accent = _ACCENT_COLORS.get(self.software, _DEFAULT_ACCENT)
        print(
            f"\n  {_CYAN}{_BOLD}\u25c6{_RESET}  "
            f"{_CYAN}{_BOLD}api-anything{_RESET} "
            f"{_DIM}\u00b7{_RESET} "
            f"{accent}{_BOLD}{self.display_name}{_RESET}"
        )
        print(
            f"     {_DIM}v{self.version} \u00b7 "
            f"http://{host}:{port} \u00b7 "
            f"docs at /docs{_RESET}\n"
        )
        uvicorn.run(self.app, host=host, port=port, **kwargs)

    # ── CLI entry point helper ────────────────────────────────────

    @staticmethod
    def cli_main(software: str, cli_group, session_class, version: str = "1.0.0"):
        """Convenience entry point for __main__.py or console_scripts.

        Parses --host, --port, --reload from sys.argv and starts the server.

        Usage in setup.py:
            entry_points={
                "console_scripts": [
                    "api-anything-gimp=cli_anything.gimp.gimp_api:main",
                ],
            }
        """
        import argparse

        parser = argparse.ArgumentParser(
            description=f"api-anything REST API server for {software}",
        )
        parser.add_argument("--host", default="0.0.0.0", help="Bind address")
        parser.add_argument("--port", type=int, default=8000, help="Bind port")
        parser.add_argument("--reload", action="store_true", help="Auto-reload on changes")
        parser.add_argument("--ttl", type=int, default=3600, help="Session TTL in seconds")
        args = parser.parse_args()

        import inspect
        cli_module = inspect.getmodule(cli_group.callback)

        api = ApiSkin.from_click(
            software=software,
            cli_group=cli_group,
            session_factory=session_class,
            cli_module=cli_module,
            version=version,
            session_ttl=args.ttl,
        )
        api.run(host=args.host, port=args.port, reload=args.reload)
