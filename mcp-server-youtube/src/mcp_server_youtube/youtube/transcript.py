"""Modern transcript fetcher with user-friendly error messages."""

from __future__ import annotations

from mcp_server_youtube.youtube.models import TranscriptResult, TranscriptStatus
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)


class TranscriptFetcher:
    """Handles transcript retrieval with proper error handling and user-friendly messages."""

    def __init__(self, video_id: str) -> None:
        self.video_id = video_id
        self.transcript_list = None
        self.max_transcript_preview = 500

    def fetch(self, preferred_language: str) -> TranscriptResult:
        """Fetch transcript with preferred language."""
        try:
            self.transcript_list = YouTubeTranscriptApi.list_transcripts(self.video_id)
            return self._get_preferred_transcript(preferred_language)
        except TranscriptsDisabled:
            return TranscriptResult(
                status=TranscriptStatus.DISABLED,
                error_message="Transcripts disabled by video creator",
            )
        except VideoUnavailable:
            return TranscriptResult(
                status=TranscriptStatus.UNAVAILABLE, error_message="Video unavailable"
            )
        except Exception:
            return TranscriptResult(
                status=TranscriptStatus.ERROR,
                error_message="Transcript service temporarily unavailable",
            )

    def _get_preferred_transcript(self, preferred_language: str) -> TranscriptResult:
        """Try to get the preferred language transcript."""
        try:
            transcript = self.transcript_list.find_transcript([preferred_language])
            return self._handle_transcript(transcript, preferred_language)
        except NoTranscriptFound:
            return self._get_fallback_transcript()
        except Exception:
            return self._get_fallback_transcript()

    def _get_fallback_transcript(self) -> TranscriptResult:
        """Get any available transcript as fallback."""
        try:
            # Get all available transcripts
            transcripts = list(self.transcript_list)
            if not transcripts:
                return TranscriptResult(
                    status=TranscriptStatus.NO_TRANSCRIPT,
                    error_message="No transcripts available for this video",
                )

            # Get available languages (clean format)
            available_languages = [
                str(t.language_code).replace("LanguageCode.", "") for t in transcripts
            ]

            # Try transcripts in priority order: manual → English → any available
            prioritized_transcripts = self._prioritize_transcripts(transcripts)

            # Actually try to fetch each transcript
            for transcript in prioritized_transcripts:
                result = self._handle_transcript(transcript, transcript.language_code)
                if result.status == TranscriptStatus.SUCCESS:
                    return result
                # If this transcript failed, try the next one

            # All attempts failed - return user-friendly message with available languages
            langs_str = ", ".join(available_languages)
            if len(available_languages) == 1:
                message = f"Transcript available in {langs_str} but currently inaccessible (YouTube blocking)"
            else:
                message = f"Transcripts available in {langs_str} but currently inaccessible (YouTube blocking)"

            return TranscriptResult(
                status=TranscriptStatus.BLOCKED,
                error_message=message,
                available_languages=available_languages,
            )

        except Exception:
            return TranscriptResult(
                status=TranscriptStatus.ERROR,
                error_message="Transcript service temporarily unavailable",
            )

    def _prioritize_transcripts(self, transcripts: list) -> list:
        """Sort transcripts by preference: manual → English → others."""
        manual_transcripts = []
        english_transcripts = []
        other_transcripts = []

        for transcript in transcripts:
            try:
                # Check if manually created (safely)
                is_manual = (
                    hasattr(transcript, "is_manually_created")
                    and transcript.is_manually_created
                )
                lang_code = str(transcript.language_code).replace("LanguageCode.", "")

                if is_manual:
                    manual_transcripts.append(transcript)
                elif lang_code.startswith("en"):
                    english_transcripts.append(transcript)
                else:
                    other_transcripts.append(transcript)
            except Exception:
                # If there's any issue checking attributes, put in other_transcripts
                other_transcripts.append(transcript)

        return manual_transcripts + english_transcripts + other_transcripts

    def _extract_text_from_entries(self, transcript_data: list) -> list[str]:
        """Extract text from transcript entries safely."""
        text_parts = []
        for entry in transcript_data:
            try:
                # Handle different entry formats
                if hasattr(entry, "text"):
                    text = entry.text
                elif isinstance(entry, dict) and "text" in entry:
                    text = entry["text"]
                else:
                    text = str(entry)

                if text and text.strip():
                    text_parts.append(text.strip())
            except Exception:
                continue
        return text_parts

    def _format_transcript_text(self, text_parts: list[str]) -> str:
        """Format transcript text with length limits."""
        formatted_transcript = " ".join(text_parts)

        # Truncate if too long
        if len(formatted_transcript) > self.max_transcript_preview:
            formatted_transcript = (
                formatted_transcript[: self.max_transcript_preview] + "..."
            )

        return formatted_transcript

    def _get_available_languages(self) -> list[str]:
        """Get clean list of available language codes."""
        return [
            str(t.language_code).replace("LanguageCode.", "")
            for t in self.transcript_list
        ]

    def _handle_transcript(self, transcript, language: str) -> TranscriptResult:
        """Fetch and format the transcript safely."""
        try:
            transcript_data = transcript.fetch()

            if not transcript_data:
                return TranscriptResult(
                    status=TranscriptStatus.ERROR, error_message="Empty transcript data"
                )

            # Extract text parts
            text_parts = self._extract_text_from_entries(transcript_data)
            if not text_parts:
                return TranscriptResult(
                    status=TranscriptStatus.ERROR,
                    error_message="No valid text found in transcript",
                )

            # Format transcript
            formatted_transcript = self._format_transcript_text(text_parts)

            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript=formatted_transcript,
                language=str(language).replace("LanguageCode.", ""),
                available_languages=self._get_available_languages(),
            )

        except Exception:
            # Return user-friendly error instead of technical details
            lang_code = str(language).replace("LanguageCode.", "")
            return TranscriptResult(
                status=TranscriptStatus.BLOCKED,
                error_message=f"Transcript in {lang_code} currently inaccessible (YouTube blocking)",
            )
