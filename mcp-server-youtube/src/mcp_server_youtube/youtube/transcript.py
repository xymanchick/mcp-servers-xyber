"""Modern transcript fetcher with user-friendly error messages."""
from __future__ import annotations

import logging
from mcp_server_youtube.youtube.models import TranscriptResult
from mcp_server_youtube.youtube.models import TranscriptStatus
from youtube_transcript_api import NoTranscriptFound
from youtube_transcript_api import TranscriptsDisabled
from youtube_transcript_api import VideoUnavailable
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


class TranscriptFetcher:
    """Handles transcript retrieval with proper error handling and user-friendly messages."""

    def __init__(self, video_id: str) -> None:
        self.video_id = video_id
        self.transcript_list = None
        self.max_transcript_preview = 500
        logger.debug(f'Initialized TranscriptFetcher for video {video_id}')

    def fetch(self, preferred_language: str) -> TranscriptResult:
        """Fetch transcript with preferred language."""
        logger.debug(f'Fetching transcript for video {self.video_id} in language {preferred_language}')
        
        try:
            self.transcript_list = YouTubeTranscriptApi.list_transcripts(self.video_id)
            logger.debug(f'Successfully retrieved transcript list for video {self.video_id}')
            return self._get_preferred_transcript(preferred_language)
        except TranscriptsDisabled:
            logger.info(f'Transcripts disabled by creator for video {self.video_id}')
            return TranscriptResult(
                status=TranscriptStatus.DISABLED,
                error_message='Transcripts disabled by video creator'
            )
        except VideoUnavailable:
            logger.warning(f'Video {self.video_id} is unavailable')
            return TranscriptResult(
                status=TranscriptStatus.UNAVAILABLE,
                error_message='Video unavailable'
            )
        except Exception as e:
            logger.error(f'Unexpected error fetching transcript list for video {self.video_id}: {str(e)}', exc_info=True)
            return TranscriptResult(
                status=TranscriptStatus.ERROR,
                error_message='Transcript service temporarily unavailable'
            )

    def _get_preferred_transcript(self, preferred_language: str) -> TranscriptResult:
        """Try to get the preferred language transcript."""
        logger.debug(f'Attempting to find transcript in preferred language: {preferred_language}')
        
        try:
            transcript = self.transcript_list.find_transcript([preferred_language])
            logger.debug(f'Found transcript in preferred language {preferred_language}')
            return self._handle_transcript(transcript, preferred_language)
        except NoTranscriptFound:
            logger.debug(f'No transcript found in preferred language {preferred_language}, trying fallback')
            return self._get_fallback_transcript()
        except Exception as e:
            logger.warning(f'Error finding preferred transcript for video {self.video_id}: {str(e)}')
            return self._get_fallback_transcript()

    def _get_fallback_transcript(self) -> TranscriptResult:
        """Get any available transcript as fallback."""
        logger.debug(f'Getting fallback transcript for video {self.video_id}')
        
        try:
            # Get all available transcripts
            transcripts = list(self.transcript_list)
            if not transcripts:
                logger.info(f'No transcripts available for video {self.video_id}')
                return TranscriptResult(
                    status=TranscriptStatus.NO_TRANSCRIPT,
                    error_message='No transcripts available for this video'
                )

            # Get available languages (clean format)
            available_languages = [
                str(t.language_code).replace('LanguageCode.', '')
                for t in transcripts
            ]
            logger.debug(f'Available transcript languages for video {self.video_id}: {available_languages}')

            # Try transcripts in priority order: manual → English → any available
            prioritized_transcripts = self._prioritize_transcripts(transcripts)
            logger.debug(f'Trying {len(prioritized_transcripts)} transcripts in priority order')

            # Actually try to fetch each transcript
            for i, transcript in enumerate(prioritized_transcripts):
                lang_code = str(transcript.language_code).replace('LanguageCode.', '')
                logger.debug(f'Attempting transcript {i+1}/{len(prioritized_transcripts)}: {lang_code}')
                
                result = self._handle_transcript(transcript, transcript.language_code)
                if result.status == TranscriptStatus.SUCCESS:
                    logger.info(f'Successfully fetched transcript for video {self.video_id} in language {lang_code}')
                    return result
                else:
                    logger.debug(f'Failed to fetch transcript in {lang_code}: {result.error_message}')
                # If this transcript failed, try the next one

            # All attempts failed - return user-friendly message with available languages
            langs_str = ', '.join(available_languages)
            if len(available_languages) == 1:
                message = f'Transcript available in {langs_str} but currently inaccessible (YouTube blocking)'
            else:
                message = f'Transcripts available in {langs_str} but currently inaccessible (YouTube blocking)'

            logger.warning(f'All transcript attempts failed for video {self.video_id}. Available languages: {langs_str}')
            return TranscriptResult(
                status=TranscriptStatus.BLOCKED,
                error_message=message,
                available_languages=available_languages
            )

        except Exception as e:
            logger.error(f'Unexpected error in fallback transcript fetch for video {self.video_id}: {str(e)}', exc_info=True)
            return TranscriptResult(
                status=TranscriptStatus.ERROR,
                error_message='Transcript service temporarily unavailable'
            )

    def _prioritize_transcripts(self, transcripts: list) -> list:
        """Sort transcripts by preference: manual → English → others."""
        manual_transcripts = []
        english_transcripts = []
        other_transcripts = []

        logger.debug(f'Prioritizing {len(transcripts)} available transcripts')

        for transcript in transcripts:
            try:
                # Check if manually created (safely)
                is_manual = hasattr(transcript, 'is_manually_created') and transcript.is_manually_created
                lang_code = str(transcript.language_code).replace('LanguageCode.', '')

                if is_manual:
                    manual_transcripts.append(transcript)
                    logger.debug(f'Found manual transcript in {lang_code}')
                elif lang_code.startswith('en'):
                    english_transcripts.append(transcript)
                    logger.debug(f'Found English transcript in {lang_code}')
                else:
                    other_transcripts.append(transcript)
                    logger.debug(f'Found other transcript in {lang_code}')
            except Exception as e:
                # If there's any issue checking attributes, put in other_transcripts
                logger.debug(f'Error checking transcript attributes, adding to others: {str(e)}')
                other_transcripts.append(transcript)

        priority_order = manual_transcripts + english_transcripts + other_transcripts
        logger.debug(f'Transcript priority: {len(manual_transcripts)} manual, {len(english_transcripts)} English, {len(other_transcripts)} others')
        return priority_order

    def _extract_text_from_entries(self, transcript_data: list) -> list[str]:
        """Extract text from transcript entries safely."""
        text_parts = []
        logger.debug(f'Extracting text from {len(transcript_data)} transcript entries')
        
        for i, entry in enumerate(transcript_data):
            try:
                # Handle different entry formats
                if hasattr(entry, 'text'):
                    text = entry.text
                elif isinstance(entry, dict) and 'text' in entry:
                    text = entry['text']
                else:
                    text = str(entry)

                if text and text.strip():
                    text_parts.append(text.strip())
                elif i < 5:  # Only log first few empty entries to avoid spam
                    logger.debug(f'Empty text entry at index {i}')
            except Exception as e:
                if i < 5:  # Only log first few errors to avoid spam
                    logger.debug(f'Error processing transcript entry {i}: {str(e)}')
                continue
                
        logger.debug(f'Successfully extracted {len(text_parts)} text parts from transcript entries')
        return text_parts

    def _format_transcript_text(self, text_parts: list[str]) -> str:
        """Format transcript text with length limits."""
        formatted_transcript = ' '.join(text_parts)
        original_length = len(formatted_transcript)

        # Truncate if too long
        if len(formatted_transcript) > self.max_transcript_preview:
            formatted_transcript = formatted_transcript[:self.max_transcript_preview] + '...'
            logger.debug(f'Transcript truncated from {original_length} to {len(formatted_transcript)} characters')
        else:
            logger.debug(f'Transcript formatted: {original_length} characters')

        return formatted_transcript

    def _get_available_languages(self) -> list[str]:
        """Get clean list of available language codes."""
        available_languages = [
            str(t.language_code).replace('LanguageCode.', '')
            for t in self.transcript_list
        ]
        logger.debug(f'Available languages: {available_languages}')
        return available_languages

    def _handle_transcript(self, transcript, language: str) -> TranscriptResult:
        """Fetch and format the transcript safely."""
        lang_code = str(language).replace('LanguageCode.', '')
        logger.debug(f'Handling transcript fetch for language {lang_code}')
        
        try:
            transcript_data = transcript.fetch()
            logger.debug(f'Successfully fetched transcript data for {lang_code}: {len(transcript_data) if transcript_data else 0} entries')

            if not transcript_data:
                logger.warning(f'Empty transcript data received for video {self.video_id} in {lang_code}')
                return TranscriptResult(
                    status=TranscriptStatus.ERROR,
                    error_message='Empty transcript data'
                )

            # Extract text parts
            text_parts = self._extract_text_from_entries(transcript_data)
            if not text_parts:
                logger.warning(f'No valid text found in transcript for video {self.video_id} in {lang_code}')
                return TranscriptResult(
                    status=TranscriptStatus.ERROR,
                    error_message='No valid text found in transcript'
                )

            # Format transcript
            formatted_transcript = self._format_transcript_text(text_parts)
            logger.info(f'Successfully processed transcript for video {self.video_id} in {lang_code}: {len(text_parts)} segments, {len(formatted_transcript)} chars')

            return TranscriptResult(
                status=TranscriptStatus.SUCCESS,
                transcript=formatted_transcript,
                language=lang_code,
                available_languages=self._get_available_languages()
            )

        except Exception as e:
            # Return user-friendly error instead of technical details
            logger.warning(f'Failed to fetch transcript for video {self.video_id} in {lang_code}: {str(e)}')
            return TranscriptResult(
                status=TranscriptStatus.BLOCKED,
                error_message=f'Transcript in {lang_code} currently inaccessible (YouTube blocking)'
            )
