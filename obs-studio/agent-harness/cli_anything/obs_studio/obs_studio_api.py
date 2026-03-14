#!/usr/bin/env python3
"""OBS Studio API — REST API server for the OBS Studio CLI harness.

Start the server:
    python -m cli_anything.obs_studio.obs_studio_api
    # or after pip install:
    api-anything-obs-studio --port 8000

Then use the API:
    curl -X POST http://localhost:8000/sessions
    curl -X POST http://localhost:8000/project/new \
        -H "X-Session-Id: <id>" \
        -H "Content-Type: application/json" \
        -d '{"name": "My Stream", "width": 1920, "height": 1080}'

    open http://localhost:8000/docs
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything.obs_studio.obs_studio_cli import cli
from cli_anything.obs_studio.core.session import Session
from cli_anything.obs_studio.utils.api_skin import ApiSkin


def create_app():
    """Create the FastAPI app."""
    api = ApiSkin.from_click(
        software="obs-studio",
        cli_group=cli,
        session_factory=Session,
        version="1.0.0",
    )
    return api.app


def main():
    """CLI entry point for api-anything-obs-studio."""
    ApiSkin.cli_main(
        software="obs-studio",
        cli_group=cli,
        session_class=Session,
        version="1.0.0",
    )


if __name__ == "__main__":
    main()
