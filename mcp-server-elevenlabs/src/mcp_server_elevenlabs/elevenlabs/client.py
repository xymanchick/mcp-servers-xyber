import datetime
import logging
import os

from elevenlabs.client import ElevenLabs

from mcp_server_elevenlabs.config import ElevenLabsSettings

logger = logging.getLogger(__name__)


def generate_voice(
    text: str,
    api_config: ElevenLabsSettings,
    file_path: str,
    voice_id: str = None,
    model_id: str = None,
) -> str:
    # Create generated_audio folder when actually needed
    generated_audio_dir = file_path
    # The path is now absolute in container (/app/media/voice/generated_audio)
    os.makedirs(generated_audio_dir, exist_ok=True)
    api_key = api_config.ELEVENLABS_API_KEY

    # Use provided ID or fallback to config
    voice_id = voice_id or api_config.ELEVENLABS_VOICE_ID
    model_id = model_id or api_config.ELEVENLABS_MODEL_ID

    if not api_key:
        logger.error("ELEVENLABS_API_KEY is not set.")
        raise ValueError("ELEVENLABS_API_KEY is not set.")

    client = ElevenLabs(api_key=api_key)

    # Generate audio
    try:
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise

    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audio_{timestamp}.mp3"
    filepath = os.path.join(generated_audio_dir, filename)  # file path inside docker

    # Save audio data to file
    with open(filepath, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    logger.info(f"Audio saved to: {filepath}")

    return filename
