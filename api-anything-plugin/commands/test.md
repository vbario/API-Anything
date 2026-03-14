# api-anything:test Command

Run API tests for a cli-anything harness and update TEST.md.

## Usage

```bash
/api-anything:test <software-path>
```

## Arguments

- `<software-path>` - **Required.** Path to the cli-anything harness directory.

## What This Command Does

1. Locates `tests/test_api.py` in the harness
2. Runs `pytest tests/test_api.py -v --tb=short`
3. Appends API test results to `TEST.md`

If `test_api.py` doesn't exist, it generates one first using the test patterns from HARNESS.md.

## Test Categories

### Health & Meta
- `GET /` returns API info
- `GET /health` returns ok status

### Session Management
- `POST /sessions` creates session, returns session_id
- `GET /sessions` lists all sessions
- `GET /sessions/{id}` returns session details
- `DELETE /sessions/{id}` removes session
- Invalid session_id returns 404

### Command Endpoints
- Each CLI command group has corresponding endpoints
- Endpoints return JSON (matching `--json` output)
- Missing required params return 422
- Operations require valid session

### Workflows
- Create session -> create project -> add layers -> export
- Undo/redo flow
- Multiple concurrent sessions
