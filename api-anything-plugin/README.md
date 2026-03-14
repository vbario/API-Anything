# api-anything Plugin for Claude Code

Turn any cli-anything CLI harness into a REST API with one command.

## Overview

The api-anything plugin extends cli-anything by adding an HTTP/JSON API layer. Where cli-anything makes software agent-native via CLI, api-anything makes it **service-native** via REST API.

Any existing cli-anything CLI (GIMP, Blender, Inkscape, etc.) can be exposed as a REST API with auto-generated OpenAPI documentation, multi-tenant sessions, and zero code changes to the existing harness.

## What It Does

```
cli-anything-gimp project new --width 1920    # CLI (agent-native)
         ↓ api-anything wraps this ↓
POST /project/new {"width": 1920}              # API (service-native)
```

- Auto-generates REST endpoints from Click commands
- Multi-tenant session management (multiple clients, isolated state)
- OpenAPI/Swagger docs at `/docs`
- CORS enabled for browser clients
- Thread-safe command execution

## Installation

### From Claude Code

```bash
/plugin install api-anything@your-registry
```

### Manual

```bash
cd ~/.claude/plugins
git clone https://github.com/yourusername/api-anything-plugin.git
```

## Commands

### `/api-anything <software-path>`

Build a permanent API layer for an existing cli-anything harness.

```bash
/api-anything /home/user/gimp/agent-harness
```

This:
1. Copies `api_skin.py` into the harness
2. Creates `<software>_api.py` with auto-wrapping
3. Updates `setup.py` with API dependencies
4. Writes API tests
5. Installs the API command to PATH

### `/api-anything:serve <software-path> [--port PORT]`

Quick-start an API server for any existing CLI harness (no permanent changes).

```bash
/api-anything:serve /home/user/gimp/agent-harness --port 3000
```

### `/api-anything:test <software-path>`

Run API tests and update TEST.md.

```bash
/api-anything:test /home/user/gimp/agent-harness
```

### `/api-anything:validate <software-path>`

Validate API harness against standards.

```bash
/api-anything:validate /home/user/gimp/agent-harness
```

### `/api-anything:list [--path DIR] [--json]`

List all cli-anything harnesses with their API status.

```bash
/api-anything:list --path /root/cli-anything
```

## Quick Start

### 1. Build the API

```bash
# If you have an existing CLI harness:
/api-anything /home/user/gimp/agent-harness

# Install with API dependencies:
cd /home/user/gimp/agent-harness
pip install -e ".[api]"
```

### 2. Start the Server

```bash
api-anything-gimp --port 8000
# Server starts at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 3. Use the API

```bash
# Create a session
SESSION=$(curl -s -X POST http://localhost:8000/sessions | jq -r .session_id)

# Create a project
curl -X POST http://localhost:8000/project/new \
    -H "X-Session-Id: $SESSION" \
    -H "Content-Type: application/json" \
    -d '{"width": 1920, "height": 1080, "name": "my_image"}'

# Add a layer
curl -X POST http://localhost:8000/layer/new \
    -H "X-Session-Id: $SESSION" \
    -H "Content-Type: application/json" \
    -d '{"name": "Background", "fill": "white"}'

# List layers
curl -H "X-Session-Id: $SESSION" http://localhost:8000/layer/list

# Undo
curl -X POST http://localhost:8000/session/undo \
    -H "X-Session-Id: $SESSION"

# Export
curl -X POST http://localhost:8000/export/render \
    -H "X-Session-Id: $SESSION" \
    -H "Content-Type: application/json" \
    -d '{"output_path": "/tmp/output.png"}'

# Cleanup
curl -X DELETE http://localhost:8000/sessions/$SESSION
```

## API Architecture

### Session Model

Every API interaction requires a session. Sessions hold project state, undo/redo history, and are isolated from each other.

```
POST /sessions                    → Create session
GET  /sessions                    → List all sessions
GET  /sessions/{session_id}       → Session details
DELETE /sessions/{session_id}     → Delete session
POST /sessions/cleanup            → Remove expired sessions
```

### Command Endpoints

CLI commands map to REST endpoints:

| CLI Command | HTTP Method | Endpoint |
|------------|-------------|----------|
| `project new --width 1920` | POST | `/project/new` |
| `project info` | GET | `/project/info` |
| `layer list` | GET | `/layer/list` |
| `layer new --name Bg` | POST | `/layer/new` |
| `filter add blur` | POST | `/filter/add` |
| `filter remove 0` | DELETE | `/filter/remove` |
| `session undo` | POST | `/session/undo` |
| `export render out.png` | POST | `/export/render` |

### Authentication

Sessions act as lightweight authentication. For production, add API key middleware or OAuth2 via FastAPI's dependency injection.

## How It Works

The `api_skin.py` module (analogous to `repl_skin.py`) provides:

1. **`ApiSkin.from_click()`** — Introspects a Click CLI group and auto-generates FastAPI routes
2. **`SessionStore`** — Thread-safe session management with TTL
3. **Click-to-API bridge** — Converts HTTP requests to Click CLI invocations, captures JSON output
4. **OpenAPI generation** — Swagger docs from Click parameter metadata

The auto-wrapper uses Click's `CliRunner` for reliable command execution:

```python
# What happens inside api_skin.py:
runner = CliRunner()
result = runner.invoke(cli, ["--json", "project", "new", "--width", "1920"])
return json.loads(result.output)  # → FastAPI JSON response
```

## Output Structure

```
<software>/
└── agent-harness/
    ├── setup.py                     # Updated: api extras + console_scripts
    └── cli_anything/
        └── <software>/
            ├── <software>_cli.py    # Existing CLI (unchanged)
            ├── <software>_api.py    # NEW: 3-line API entry point
            ├── utils/
            │   ├── repl_skin.py     # Existing (unchanged)
            │   └── api_skin.py      # NEW: API skin
            └── tests/
                └── test_api.py      # NEW: API tests
```

## Prerequisites

- Python 3.10+
- An existing cli-anything CLI harness
- FastAPI + uvicorn (installed automatically via `pip install -e ".[api]"`)

## Key Differences: CLI vs API

| Feature | CLI (cli-anything) | API (api-anything) |
|---------|-------------------|-------------------|
| Interface | Terminal | HTTP/JSON |
| Sessions | Single global | Multi-tenant |
| Output | Text or `--json` | Always JSON |
| Discovery | `--help`, `which` | `/docs`, OpenAPI |
| State | Process-local | Server-side + session ID |
| Concurrency | Single user | Multiple clients |
| Deployment | pip install | pip install + uvicorn |

## Version History

### 1.0.0 (2026-03-14)
- Initial release
- Auto-wrapping Click CLIs via `ApiSkin.from_click()`
- Multi-tenant session management
- 5 commands: api-anything, serve, test, validate, list
- GIMP reference implementation
- HARNESS.md API methodology
