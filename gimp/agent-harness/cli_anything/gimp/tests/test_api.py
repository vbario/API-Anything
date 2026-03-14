"""API tests for api-anything-gimp.

Tests the REST API layer using FastAPI's TestClient (no server required).
"""

import pytest
import sys
import os

# Ensure imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi.testclient import TestClient
from cli_anything.gimp.gimp_api import create_app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the GIMP API."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def session_id(client):
    """Create a fresh session and return its ID."""
    resp = client.post("/sessions")
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    yield sid
    # Cleanup
    client.delete(f"/sessions/{sid}")


@pytest.fixture
def session_with_project(client, session_id):
    """Create a session with a project already loaded."""
    resp = client.post(
        "/project/new",
        headers={"X-Session-Id": session_id},
        json={"width": 800, "height": 600, "name": "test_project"},
    )
    assert resp.status_code == 200
    return session_id


# ── Meta Endpoints ───────────────────────────────────────────────


class TestMeta:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["software"] == "gimp"
        assert "docs" in data

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["software"] == "gimp"


# ── Session Management ──────────────────────────────────────────


class TestSessions:
    def test_create_session(self, client):
        resp = client.post("/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        # Cleanup
        client.delete(f"/sessions/{data['session_id']}")

    def test_list_sessions(self, client, session_id):
        resp = client.get("/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert session_id in data

    def test_get_session(self, client, session_id):
        resp = client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id

    def test_delete_session(self, client):
        # Create
        sid = client.post("/sessions").json()["session_id"]
        # Delete
        resp = client.delete(f"/sessions/{sid}")
        assert resp.status_code == 200
        # Verify gone
        resp = client.get(f"/sessions/{sid}")
        assert resp.status_code == 404

    def test_invalid_session_returns_404(self, client):
        resp = client.get("/sessions/nonexistent-id")
        assert resp.status_code == 404

    def test_cleanup_expired(self, client):
        resp = client.post("/sessions/cleanup")
        assert resp.status_code == 200
        assert "removed" in resp.json()


# ── Project Commands ────────────────────────────────────────────


class TestProject:
    def test_project_new(self, client, session_id):
        resp = client.post(
            "/project/new",
            headers={"X-Session-Id": session_id},
            json={"width": 1920, "height": 1080, "name": "my_image"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my_image"
        assert data["canvas"]["width"] == 1920
        assert data["canvas"]["height"] == 1080

    def test_project_new_with_profile(self, client, session_id):
        resp = client.post(
            "/project/new",
            headers={"X-Session-Id": session_id},
            json={"profile": "hd720p", "name": "hd_project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["canvas"]["width"] == 1280
        assert data["canvas"]["height"] == 720

    def test_project_info(self, client, session_with_project):
        resp = client.get(
            "/project/info",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test_project"

    def test_project_profiles(self, client, session_with_project):
        resp = client.get(
            "/project/profiles",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_project_requires_session(self, client):
        resp = client.post("/project/new", json={"width": 100, "height": 100})
        assert resp.status_code == 422  # Missing X-Session-Id header


# ── Layer Commands ──────────────────────────────────────────────


class TestLayers:
    def test_layer_new(self, client, session_with_project):
        resp = client.post(
            "/layer/new",
            headers={"X-Session-Id": session_with_project},
            json={"name": "Background", "fill": "white"},
        )
        assert resp.status_code == 200

    def test_layer_list(self, client, session_with_project):
        # Add a layer first
        client.post(
            "/layer/new",
            headers={"X-Session-Id": session_with_project},
            json={"name": "Layer 1"},
        )
        resp = client.get(
            "/layer/list",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200

    def test_layer_duplicate(self, client, session_with_project):
        client.post(
            "/layer/new",
            headers={"X-Session-Id": session_with_project},
            json={"name": "Original"},
        )
        resp = client.post(
            "/layer/duplicate",
            headers={"X-Session-Id": session_with_project},
            json={"index": 0},
        )
        assert resp.status_code == 200

    def test_layer_remove(self, client, session_with_project):
        client.post(
            "/layer/new",
            headers={"X-Session-Id": session_with_project},
            json={"name": "To Remove"},
        )
        resp = client.request(
            "DELETE",
            "/layer/remove",
            headers={"X-Session-Id": session_with_project},
            json={"index": 0},
        )
        assert resp.status_code == 200


# ── Canvas Commands ─────────────────────────────────────────────


class TestCanvas:
    def test_canvas_info(self, client, session_with_project):
        resp = client.get(
            "/canvas/info",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200

    def test_canvas_resize(self, client, session_with_project):
        resp = client.post(
            "/canvas/resize",
            headers={"X-Session-Id": session_with_project},
            json={"width": 1024, "height": 768},
        )
        assert resp.status_code == 200

    def test_canvas_scale(self, client, session_with_project):
        resp = client.post(
            "/canvas/scale",
            headers={"X-Session-Id": session_with_project},
            json={"width": 640, "height": 480},
        )
        assert resp.status_code == 200


# ── Filter Commands ─────────────────────────────────────────────


class TestFilters:
    def test_filter_list_available(self, client, session_with_project):
        resp = client.get(
            "/filter/list-available",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200

    def test_filter_add(self, client, session_with_project):
        # Need a layer first
        client.post(
            "/layer/new",
            headers={"X-Session-Id": session_with_project},
            json={"name": "Filter Target"},
        )
        resp = client.post(
            "/filter/add",
            headers={"X-Session-Id": session_with_project},
            json={"name": "brightness", "layer_index": 0},
        )
        assert resp.status_code == 200


# ── Session Commands (undo/redo) ────────────────────────────────


class TestSessionCommands:
    def test_session_status(self, client, session_with_project):
        resp = client.get(
            "/session/status",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200

    def test_undo_redo(self, client, session_with_project):
        # Add a layer (creates undo point)
        client.post(
            "/layer/new",
            headers={"X-Session-Id": session_with_project},
            json={"name": "Undo Test"},
        )
        # Undo
        resp = client.post(
            "/session/undo",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200

        # Redo
        resp = client.post(
            "/session/redo",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200

    def test_session_history(self, client, session_with_project):
        resp = client.get(
            "/session/history",
            headers={"X-Session-Id": session_with_project},
        )
        assert resp.status_code == 200


# ── Workflow Tests ──────────────────────────────────────────────


class TestWorkflows:
    def test_full_workflow(self, client):
        """Test complete workflow: create session -> project -> layers -> info."""
        # Create session
        sid = client.post("/sessions").json()["session_id"]
        headers = {"X-Session-Id": sid}

        # Create project
        resp = client.post(
            "/project/new",
            headers=headers,
            json={"width": 1920, "height": 1080, "name": "workflow_test"},
        )
        assert resp.status_code == 200

        # Add layers
        client.post("/layer/new", headers=headers,
                     json={"name": "Background", "fill": "white"})
        client.post("/layer/new", headers=headers,
                     json={"name": "Foreground", "fill": "transparent"})

        # Check project info
        resp = client.get("/project/info", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["layer_count"] == 2

        # Undo last layer
        client.post("/session/undo", headers=headers)

        # Verify layer count decreased
        resp = client.get("/project/info", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["layer_count"] == 1

        # Cleanup
        client.delete(f"/sessions/{sid}")

    def test_session_isolation(self, client):
        """Verify two sessions don't interfere with each other."""
        s1 = client.post("/sessions").json()["session_id"]
        s2 = client.post("/sessions").json()["session_id"]

        # Create different projects
        client.post("/project/new",
                     headers={"X-Session-Id": s1},
                     json={"name": "session_one", "width": 100, "height": 100})
        client.post("/project/new",
                     headers={"X-Session-Id": s2},
                     json={"name": "session_two", "width": 200, "height": 200})

        # Verify isolation
        info1 = client.get("/project/info", headers={"X-Session-Id": s1}).json()
        info2 = client.get("/project/info", headers={"X-Session-Id": s2}).json()
        assert info1["name"] == "session_one"
        assert info2["name"] == "session_two"
        assert info1["canvas"]["width"] == 100
        assert info2["canvas"]["width"] == 200

        # Cleanup
        client.delete(f"/sessions/{s1}")
        client.delete(f"/sessions/{s2}")
