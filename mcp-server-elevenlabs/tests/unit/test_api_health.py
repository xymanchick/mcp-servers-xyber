from fastapi.testclient import TestClient


def test_api_health_ok():
    from mcp_server_elevenlabs.app import create_app

    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

