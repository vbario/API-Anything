#!/usr/bin/env python3
"""Blender API — REST API server for the Blender CLI harness.

Start: python -m cli_anything.blender.blender_api
Or:    api-anything-blender --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.blender.blender_cli import cli
from cli_anything.blender.core.session import Session
from cli_anything.blender.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="blender",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-blender."""
    ApiSkin.cli_main("blender", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
