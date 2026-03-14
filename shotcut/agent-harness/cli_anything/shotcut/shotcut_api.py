#!/usr/bin/env python3
"""Shotcut API — REST API server for the Shotcut CLI harness.

Start: python -m cli_anything.shotcut.shotcut_api
Or:    api-anything-shotcut --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.shotcut.shotcut_cli import cli
from cli_anything.shotcut.core.session import Session
from cli_anything.shotcut.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="shotcut",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-shotcut."""
    ApiSkin.cli_main("shotcut", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
