# api-anything:list Command

List all available API-Anything tools.

## Usage

```bash
/api-anything:list [--path <directory>] [--depth <n>] [--json]
```

## Options

- `--path <directory>` - Directory to search (default: current directory)
- `--depth <n>` - Maximum recursion depth (default: unlimited)
- `--json` - Output in JSON format

## What This Command Does

Scans for cli-anything harnesses that have API support enabled. Checks for:

1. Installed `api-anything-*` commands in PATH
2. Harness directories containing `*_api.py` files
3. `setup.py` files with `api-anything-*` console_scripts entries

## Output

| Tool | CLI Status | API Status | Port | Version | Path |
|------|-----------|------------|------|---------|------|
| gimp | installed | installed | - | 1.0.0 | /root/cli-anything/gimp |
| blender | installed | generated | - | 1.0.0 | /root/cli-anything/blender |
| inkscape | installed | not built | - | 1.0.0 | /root/cli-anything/inkscape |
