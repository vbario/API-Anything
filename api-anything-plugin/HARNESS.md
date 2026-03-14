# api-anything Harness Methodology

## Overview

api-anything extends the cli-anything methodology by adding a REST API layer to any existing CLI harness. Where cli-anything makes software agent-native via CLI, api-anything makes it **service-native** via HTTP/JSON.

The core principle: **don't reimplement — wrap**. The API layer delegates to the existing CLI harness, reusing all core modules, session management, and business logic.

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         API Clients              │
                    │  (agents, web apps, scripts)     │
                    └──────────────┬──────────────────┘
                                   │ HTTP/JSON
                    ┌──────────────▼──────────────────┐
                    │       api_skin.py (FastAPI)       │
                    │  - Session management (multi-tenant)│
                    │  - Click-to-API bridge            │
                    │  - CORS, error handling           │
                    │  - OpenAPI auto-docs              │
                    └──────────────┬──────────────────┘
                                   │ Python calls
                    ┌──────────────▼──────────────────┐
                    │    Existing CLI Harness           │
                    │  - Click CLI groups               │
                    │  - Core modules (project, etc.)   │
                    │  - Session with undo/redo         │
                    │  - Export/render pipeline          │
                    └──────────────┬──────────────────┘
                                   │ Backend calls
                    ┌──────────────▼──────────────────┐
                    │       Real Software Backend       │
                    │  (Pillow, bpy, ffmpeg, etc.)      │
                    └─────────────────────────────────┘
```

## Key Concepts

### 1. Session Management

The CLI uses a single global session. The API supports **multiple concurrent sessions**, each identified by a UUID:

```
POST /sessions              → {"session_id": "abc-123"}
GET  /sessions              → list all sessions
GET  /sessions/{id}         → session details
DELETE /sessions/{id}       → cleanup
```

All command endpoints require an `X-Session-Id` header:

```bash
curl -X POST http://localhost:8000/project/new \
    -H "X-Session-Id: abc-123" \
    -H "Content-Type: application/json" \
    -d '{"width": 1920, "height": 1080}'
```

Sessions expire after a configurable TTL (default: 1 hour).

### 2. Click-to-API Bridge

The `ApiSkin.from_click()` method automatically converts Click commands to FastAPI routes:

| Click Pattern | API Pattern |
|--------------|-------------|
| `cli project new --width 1920` | `POST /project/new {"width": 1920}` |
| `cli layer list` | `GET /layer/list` |
| `cli filter remove 0 --layer 1` | `DELETE /filter/remove {"filter_index": 0, "layer_index": 1}` |
| `cli session undo` | `POST /session/undo` |
| `cli export render out.png` | `POST /export/render {"output_path": "out.png"}` |

HTTP method is inferred from the command name:
- **GET**: list, info, status, show, check, probe, histogram, presets, profiles, history
- **DELETE**: remove, delete, close
- **POST**: everything else (new, add, set, save, render, undo, redo, etc.)

### 3. API Skin Pattern

The `api_skin.py` file is analogous to `repl_skin.py`:

| repl_skin.py | api_skin.py |
|-------------|-------------|
| Terminal REPL interface | HTTP/JSON interface |
| `ReplSkin("gimp")` | `ApiSkin("gimp")` |
| `skin.print_banner()` | `GET /` (API info) |
| `skin.get_input()` | HTTP request handling |
| Global session | Per-request session via header |
| `--json` flag | Always JSON |
| stdout output | JSON response body |

### 4. Thread Safety

The CLI uses module-level globals (`_session`, `_json_output`). The API serializes command invocations via a global lock to prevent race conditions. Each request:

1. Acquires the invoke lock
2. Binds the session to the CLI module
3. Invokes the Click command via CliRunner
4. Captures JSON output
5. Restores the original state
6. Releases the lock

This serializes requests but ensures correctness. For high-throughput needs, use the manual route pattern which bypasses Click and calls core modules directly.

## Implementation Phases

### Phase 1: Validate Existing Harness
- Confirm CLI harness exists and tests pass
- Identify CLI entry point and Session class

### Phase 2: Copy api_skin.py
- Copy from plugin to `utils/api_skin.py`
- This is the same pattern as copying `repl_skin.py`

### Phase 3: Create <software>_api.py
- Minimal file using `ApiSkin.from_click()`
- Include `create_app()` factory for ASGI deployment
- Include `main()` for console_scripts

### Phase 4: Update setup.py
- Add `api` extras_require
- Add `api-anything-<software>` console_scripts

### Phase 5: Write API Tests
- Use `fastapi.testclient.TestClient`
- Test session lifecycle, command endpoints, error handling
- Test multi-session isolation

### Phase 6: Update Documentation
- Add API section to README.md
- Include curl examples

## File Layout

```
<software>/
└── agent-harness/
    ├── setup.py                         # + api extras + console_scripts
    └── cli_anything/
        └── <software>/
            ├── <software>_cli.py        # Existing CLI (unchanged)
            ├── <software>_api.py        # NEW: API entry point
            ├── core/                    # Existing (unchanged)
            ├── utils/
            │   ├── repl_skin.py         # Existing (unchanged)
            │   └── api_skin.py          # NEW: API skin
            └── tests/
                ├── test_core.py         # Existing (unchanged)
                ├── test_full_e2e.py     # Existing (unchanged)
                └── test_api.py          # NEW: API tests
```

## API Test Patterns

### Using TestClient (no server required)

```python
import pytest
from fastapi.testclient import TestClient
from cli_anything.<software>.<software>_api import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def session_id(client):
    resp = client.post("/sessions")
    assert resp.status_code == 200
    return resp.json()["session_id"]

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_project_new(client, session_id):
    resp = client.post(
        "/project/new",
        headers={"X-Session-Id": session_id},
        json={"width": 800, "height": 600, "name": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test"
    assert data["canvas"]["width"] == 800
```

### Testing Session Isolation

```python
def test_sessions_isolated(client):
    # Create two sessions
    s1 = client.post("/sessions").json()["session_id"]
    s2 = client.post("/sessions").json()["session_id"]

    # Create different projects
    client.post("/project/new",
        headers={"X-Session-Id": s1},
        json={"name": "project_one"})
    client.post("/project/new",
        headers={"X-Session-Id": s2},
        json={"name": "project_two"})

    # Verify isolation
    info1 = client.get("/project/info", headers={"X-Session-Id": s1}).json()
    info2 = client.get("/project/info", headers={"X-Session-Id": s2}).json()
    assert info1["name"] == "project_one"
    assert info2["name"] == "project_two"
```

## Deployment

### Development

```bash
api-anything-<software> --port 8000 --reload
```

### Production (uvicorn)

```bash
uvicorn cli_anything.<software>.<software>_api:create_app \
    --factory --host 0.0.0.0 --port 8000 --workers 4
```

Note: With `--workers > 1`, each worker has its own session store. Use a shared store (Redis) for multi-worker deployments, or stick to `--workers 1` for simplicity.

### Docker

```dockerfile
FROM python:3.12-slim
RUN pip install cli-anything-<software>[api]
EXPOSE 8000
CMD ["api-anything-<software>", "--port", "8000"]
```

## Lessons Learned

### 1. Don't Fight Click
The auto-wrapper uses Click's CliRunner rather than trying to call callbacks directly. This ensures all Click middleware (parameter validation, type conversion, error handling) runs correctly.

### 2. Global Lock is Fine for v1
The CLI's global state requires serialized access. A global lock is simple and correct. Profile before optimizing — most API operations complete in milliseconds.

### 3. Always Return JSON
The API always passes `--json` to the CLI. Never return raw text from an API endpoint.

### 4. Session TTL Prevents Leaks
Default 1-hour TTL prevents session accumulation. Clients should explicitly delete sessions when done, but the TTL is a safety net.

### 5. OpenAPI Docs are Free
FastAPI auto-generates OpenAPI/Swagger docs at `/docs`. This makes the API self-documenting and explorable — agents and developers can discover endpoints without reading source code.
