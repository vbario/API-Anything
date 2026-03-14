#!/usr/bin/env python3
"""Kdenlive API — REST API server for the Kdenlive CLI harness.

Start: python -m cli_anything.kdenlive.kdenlive_api
Or:    api-anything-kdenlive --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.kdenlive.kdenlive_cli import cli
from cli_anything.kdenlive.core.session import Session
from cli_anything.kdenlive.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="kdenlive",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-kdenlive."""
    ApiSkin.cli_main("kdenlive", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
