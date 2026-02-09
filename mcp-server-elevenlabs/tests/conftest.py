import pytest


@pytest.fixture(autouse=True)
def _isolate_voice_dir(tmp_path, monkeypatch):
    """
    Force the server to write generated audio into a temp directory during tests.

    Notes:
    - `mcp_server_elevenlabs.config` uses a module-level `settings` instance, so
      we patch the instance directly (rather than relying on env reloads).
    """
    from mcp_server_elevenlabs.config import get_app_settings

    settings = get_app_settings()
    settings.media.MEDIA_HOST_DIR = tmp_path / "media"
    settings.media.MEDIA_HOST_DIR.mkdir(parents=True, exist_ok=True)
    settings.media.voice_output_dir.mkdir(parents=True, exist_ok=True)
    yield
