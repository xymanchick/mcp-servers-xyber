from starlette.routing import Mount


def test_api_routers_only_health():
    from mcp_server_elevenlabs.api_routers import routers

    # Health + REST-only direct download
    assert len(routers) == 2
    all_paths = {route.path for r in routers for route in r.routes}
    assert "/health" in all_paths
    assert "/generate-voice-file" in all_paths


def test_app_mounts_expected_routes():
    from mcp_server_elevenlabs.app import create_app

    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}

    assert "/api/health" in paths
    assert "/hybrid/generate-voice" in paths
    assert "/hybrid/audio/{filename}" in paths

    # No legacy, unprefixed endpoints
    assert "/generate-voice" not in paths
    assert "/audio/{filename}" not in paths

    # MCP is mounted as a sub-app
    assert any(isinstance(r, Mount) and r.path == "/mcp" for r in app.routes)

