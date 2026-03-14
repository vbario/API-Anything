#!/usr/bin/env python3
"""Inkscape API — REST API server for the Inkscape CLI harness.

Start: python -m cli_anything.inkscape.inkscape_api
Or:    api-anything-inkscape --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.inkscape.inkscape_cli import cli
from cli_anything.inkscape.core.session import Session
from cli_anything.inkscape.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="inkscape",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-inkscape."""
    ApiSkin.cli_main("inkscape", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
