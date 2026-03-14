#!/usr/bin/env python3
"""LibreOffice API — REST API server for the LibreOffice CLI harness.

Start: python -m cli_anything.libreoffice.libreoffice_api
Or:    api-anything-libreoffice --port 8000
Docs:  http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.libreoffice.libreoffice_cli import cli
from cli_anything.libreoffice.core.session import Session
from cli_anything.libreoffice.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    return ApiSkin.from_click(
        software="libreoffice",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    ).app


def main():
    """CLI entry point for api-anything-libreoffice."""
    ApiSkin.cli_main("libreoffice", cli, Session, version="1.0.0")


if __name__ == "__main__":
    main()
