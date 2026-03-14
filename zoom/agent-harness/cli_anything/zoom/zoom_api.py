#!/usr/bin/env python3
"""Zoom API — REST API server for the Zoom CLI harness.

Start: python -m cli_anything.zoom.zoom_api
Or:    api-anything-zoom --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.zoom.zoom_cli import cli
from cli_anything.zoom.core.session import Session
from cli_anything.zoom.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="zoom",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-zoom."""
    ApiSkin.cli_main("zoom", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
