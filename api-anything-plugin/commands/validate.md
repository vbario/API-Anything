# api-anything:validate Command

Validate an API harness against api-anything standards.

## Usage

```bash
/api-anything:validate <software-path>
```

## Arguments

- `<software-path>` - **Required.** Path to the cli-anything harness directory.

## Validation Checks

1. **api_skin.py** exists in `utils/`
2. **<software>_api.py** exists and imports correctly
3. **setup.py** includes:
   - `api` extras_require with fastapi, uvicorn, python-multipart
   - `api-anything-<software>` console_scripts entry
4. **FastAPI app** creates successfully (import test)
5. **Session routes** exist: POST/GET/DELETE /sessions
6. **Health route** exists: GET /health
7. **Command routes** cover all CLI commands (except repl)
8. **OpenAPI schema** generates without errors
9. **test_api.py** exists in tests/
10. **API tests** pass: `pytest tests/test_api.py -v`

## Output

Reports pass/fail for each check with actionable fix suggestions.
