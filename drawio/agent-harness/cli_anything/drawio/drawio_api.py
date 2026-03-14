#!/usr/bin/env python3
"""Draw.io API — REST API server for the Draw.io CLI harness.

Start: python -m cli_anything.drawio.drawio_api
Or:    api-anything-drawio --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.drawio.drawio_cli import cli
from cli_anything.drawio.core.session import Session
from cli_anything.drawio.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="drawio",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-drawio."""
    ApiSkin.cli_main("drawio", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
