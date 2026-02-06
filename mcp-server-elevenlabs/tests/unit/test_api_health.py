from fastapi.testclient import TestClient


def test_api_health_ok():
    from mcp_server_elevenlabs.app import create_app

    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_api_generate_voice_file_download(monkeypatch):
    from mcp_server_elevenlabs.app import create_app
    from mcp_server_elevenlabs.config import get_app_settings

    settings = get_app_settings()
    payload = b"ID3" + b"\x03" * 20

    def _fake_generate_voice(*_args, **_kwargs) -> str:
        filename = "api_direct.mp3"
        (settings.media.voice_output_dir / filename).write_bytes(payload)
        return filename

    monkeypatch.setattr(
        "mcp_server_elevenlabs.api_routers.tts_file.generate_voice",
        _fake_generate_voice,
    )

    app = create_app()
    client = TestClient(app)

    resp = client.post("/api/generate-voice-file", json={"text": "hi"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/mpeg")
    assert resp.content == payload

