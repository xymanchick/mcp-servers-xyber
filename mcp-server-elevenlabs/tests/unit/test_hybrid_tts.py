import base64

from fastapi.testclient import TestClient


def test_hybrid_generate_voice_returns_json_and_writes_file(monkeypatch):
    from mcp_server_elevenlabs.app import create_app
    from mcp_server_elevenlabs.config import get_app_settings

    settings = get_app_settings()

    def _fake_generate_voice(*_args, **_kwargs) -> str:
        filename = "test_audio.mp3"
        out = settings.media.voice_output_dir / filename
        out.write_bytes(b"ID3" + b"\x00" * 100)  # minimal-ish mp3 header bytes
        return filename

    monkeypatch.setattr(
        "mcp_server_elevenlabs.hybrid_routers.tts.generate_voice",
        _fake_generate_voice,
    )

    app = create_app()
    client = TestClient(app)

    resp = client.post("/hybrid/generate-voice", json={"text": "hello"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["filename"].endswith(".mp3")
    assert data["media_type"] == "audio/mpeg"
    assert data["download_url"].endswith(f"/hybrid/audio/{data['filename']}")
    assert data["audio_bytes"] > 0
    assert data["audio_base64"] is None

    assert (settings.media.voice_output_dir / data["filename"]).exists()


def test_hybrid_generate_voice_can_embed_base64(monkeypatch):
    from mcp_server_elevenlabs.app import create_app
    from mcp_server_elevenlabs.config import get_app_settings

    settings = get_app_settings()
    payload = b"ID3" + b"\x01" * 50

    def _fake_generate_voice(*_args, **_kwargs) -> str:
        filename = "test_audio_base64.mp3"
        (settings.media.voice_output_dir / filename).write_bytes(payload)
        return filename

    monkeypatch.setattr(
        "mcp_server_elevenlabs.hybrid_routers.tts.generate_voice",
        _fake_generate_voice,
    )

    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/hybrid/generate-voice",
        json={"text": "hello", "return_audio_base64": True, "max_audio_bytes": 10_000},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["audio_base64"]
    decoded = base64.b64decode(data["audio_base64"])
    assert decoded == payload


def test_hybrid_generate_voice_base64_rejects_large_payload(monkeypatch):
    from mcp_server_elevenlabs.app import create_app
    from mcp_server_elevenlabs.config import get_app_settings

    settings = get_app_settings()

    def _fake_generate_voice(*_args, **_kwargs) -> str:
        filename = "test_audio_large.mp3"
        (settings.media.voice_output_dir / filename).write_bytes(b"ID3" + b"\x00" * 500)
        return filename

    monkeypatch.setattr(
        "mcp_server_elevenlabs.hybrid_routers.tts.generate_voice",
        _fake_generate_voice,
    )

    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/hybrid/generate-voice",
        json={"text": "hello", "return_audio_base64": True, "max_audio_bytes": 10},
    )
    assert resp.status_code == 413


def test_hybrid_audio_download(monkeypatch):
    from mcp_server_elevenlabs.app import create_app
    from mcp_server_elevenlabs.config import get_app_settings

    settings = get_app_settings()
    payload = b"ID3" + b"\x02" * 30

    def _fake_generate_voice(*_args, **_kwargs) -> str:
        filename = "test_audio_download.mp3"
        (settings.media.voice_output_dir / filename).write_bytes(payload)
        return filename

    monkeypatch.setattr(
        "mcp_server_elevenlabs.hybrid_routers.tts.generate_voice",
        _fake_generate_voice,
    )

    app = create_app()
    client = TestClient(app)

    gen = client.post("/hybrid/generate-voice", json={"text": "hello"})
    assert gen.status_code == 200
    filename = gen.json()["filename"]

    dl = client.get(f"/hybrid/audio/{filename}")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("audio/mpeg")
    assert dl.content == payload


def test_hybrid_audio_download_404_for_missing_file():
    from mcp_server_elevenlabs.app import create_app

    app = create_app()
    client = TestClient(app)

    dl = client.get("/hybrid/audio/does_not_exist.mp3")
    assert dl.status_code == 404


def test_hybrid_audio_download_rejects_path_traversal():
    from mcp_server_elevenlabs.app import create_app

    app = create_app()
    client = TestClient(app)

    # `{filename}` does not accept slashes, but ".." itself would escape the base dir without checks.
    # Use URL-encoded dots to avoid client-side path normalization.
    dl = client.get("/hybrid/audio/%2e%2e")
    assert dl.status_code == 400

