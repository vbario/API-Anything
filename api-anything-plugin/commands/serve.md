# api-anything:serve Command

Quickly launch an API server for any existing cli-anything CLI harness.

## Usage

```bash
/api-anything:serve <software-path> [--port PORT] [--host HOST]
```

## Arguments

- `<software-path>` - **Required.** Path to the cli-anything harness directory.
- `--port PORT` - Port to bind (default: 8000).
- `--host HOST` - Host to bind (default: 0.0.0.0).

## What This Command Does

This is a quick-start command that launches an API server without permanently modifying the harness. It:

1. Locates the CLI entry point and Session class in the harness
2. Creates a temporary `api_skin.py` wrapper
3. Starts a uvicorn server with auto-reload

Use `/api-anything` (without `:serve`) to permanently add API support to a harness.

## Example

```bash
# Quick-serve the GIMP CLI as an API
/api-anything:serve /home/user/gimp/agent-harness --port 3000

# Then test it:
curl http://localhost:3000/docs
curl -X POST http://localhost:3000/sessions
```

## Implementation Steps

1. Read the harness directory to find:
   - `cli_anything/<software>/<software>_cli.py` — the Click CLI group
   - `cli_anything/<software>/core/session.py` — the Session class

2. If `api_skin.py` is not already in `utils/`, copy it there temporarily.

3. Create a temporary serve script and run it:
   ```python
   from cli_anything.<software>.<software>_cli import cli
   from cli_anything.<software>.core.session import Session
   from cli_anything.<software>.utils.api_skin import ApiSkin

   api = ApiSkin.from_click("<software>", cli, Session)
   api.run(host="<host>", port=<port>)
   ```

4. The server runs in the foreground. Press Ctrl+C to stop.
