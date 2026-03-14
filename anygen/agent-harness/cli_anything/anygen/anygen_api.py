#!/usr/bin/env python3
"""AnyGen API — REST API server for the AnyGen CLI harness.

Start: python -m cli_anything.anygen.anygen_api
Or:    api-anything-anygen --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.anygen.anygen_cli import cli
from cli_anything.anygen.core.session import Session
from cli_anything.anygen.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="anygen",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-anygen."""
    ApiSkin.cli_main("anygen", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
