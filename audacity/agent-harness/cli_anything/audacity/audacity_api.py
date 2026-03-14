#!/usr/bin/env python3
"""Audacity API — REST API server for the Audacity CLI harness.

Start: python -m cli_anything.audacity.audacity_api
Or:    api-anything-audacity --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.audacity.audacity_cli import cli
from cli_anything.audacity.core.session import Session
from cli_anything.audacity.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="audacity",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-audacity."""
    ApiSkin.cli_main("audacity", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
