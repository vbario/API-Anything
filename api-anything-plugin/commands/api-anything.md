# api-anything Command

Build a REST API harness for any existing cli-anything CLI.

## CRITICAL: Read HARNESS.md First

**Before doing anything else, you MUST read `./HARNESS.md`.** It defines the API methodology, architecture standards, and implementation patterns. Do not improvise — follow the harness specification.

## Usage

```bash
/api-anything <software-path>
```

## Arguments

- `<software-path>` - **Required.** Path to an existing cli-anything harness directory (e.g., `/home/user/gimp/agent-harness`). The directory must contain a working CLI harness built with `/cli-anything`.

## What This Command Does

This command takes an existing cli-anything CLI harness and generates a REST API layer on top of it, making the software accessible via HTTP/JSON.

### Phase 1: Existing Harness Validation
- Verify the CLI harness exists and is functional
- Locate the CLI entry point (`<software>_cli.py`)
- Locate the Session class (`core/session.py`)
- Identify all command groups and commands
- Run existing tests to confirm CLI works

### Phase 2: API Skin Setup
- Copy `api_skin.py` from the api-anything plugin to `utils/api_skin.py`
- This provides `ApiSkin`, `SessionStore`, and the Click-to-API bridge

### Phase 3: API Implementation
- Create `<software>_api.py` at `cli_anything/<software>/gimp_api.py`
- Use `ApiSkin.from_click()` for auto-wrapping the Click CLI
- The generated file should be minimal (3-line `from_click` pattern)
- Add `create_app()` factory for ASGI deployment
- Add `main()` entry point for console_scripts

### Phase 4: Setup.py Update
- Add `api` extras_require: `fastapi>=0.100.0`, `uvicorn[standard]>=0.20.0`, `python-multipart>=0.0.5`
- Add console_scripts entry: `api-anything-<software>=cli_anything.<software>.<software>_api:main`

### Phase 5: API Testing
- Create `tests/test_api.py` with:
  - Health check endpoint test
  - Session CRUD tests (create, get, list, delete)
  - Command endpoint tests (project new, layer operations, etc.)
  - Error handling tests (invalid session, missing params)
  - Use `fastapi.testclient.TestClient` (no server needed)
- Run tests with `pytest tests/test_api.py -v`

### Phase 6: Documentation
- Update the harness README.md with API usage section
- Document available endpoints
- Include curl examples for common workflows

## Output Structure

```
<software>/
└── agent-harness/
    ├── setup.py                      # Updated with API deps + entry point
    └── cli_anything/
        └── <software>/
            ├── <software>_api.py     # NEW: API entry point
            ├── utils/
            │   ├── api_skin.py       # NEW: API skin (copied from plugin)
            │   └── repl_skin.py      # Existing REPL skin
            └── tests/
                └── test_api.py       # NEW: API tests
```

## Example

```bash
# Build API for existing GIMP CLI harness
/api-anything /home/user/gimp/agent-harness

# Then start the server:
api-anything-gimp --port 8000

# Or use uvicorn directly:
uvicorn cli_anything.gimp.gimp_api:create_app --factory --reload
```

## Success Criteria

1. `api_skin.py` is present in `utils/`
2. `<software>_api.py` exists and imports correctly
3. `setup.py` includes API extras and console_scripts entry
4. `api-anything-<software>` command works: `api-anything-<software> --help`
5. All API tests pass
6. OpenAPI docs are accessible at `/docs`
7. Session CRUD works (create, use, delete)
8. All existing CLI commands are accessible via HTTP endpoints
