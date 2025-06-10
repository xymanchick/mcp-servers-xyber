import asyncio
import logging
import os
import tempfile
from functools import lru_cache
from typing import List, Optional, Any

import arxiv  # Official arxiv library
import fitz  # PyMuPDF

from mcp_server_arxiv.arxiv.config import ArxivConfig, ArxivServiceError, ArxivApiError, ArxivConfigError
from mcp_server_arxiv.arxiv.models import ArxivSearchResult

from .exceptions import ( 
    ServiceUnavailableError,
    InvalidResponseError,
    InputValidationError,
    UnknownMCPError
)

from .decorators import retry_on_exception

logger = logging.getLogger(__name__)


async def _async_download_and_extract_pdf_text(
    paper_details: dict, # Contains arxiv.Result object and other info
    temp_dir: str,
    max_text_length: Optional[int]
) -> ArxivSearchResult:
    """
    Asynchronously downloads a PDF, extracts its text, and returns an ArxivSearchResult.
    `paper_details` should contain `{'paper_obj': arxiv.Result, 'arxiv_id': str, ...}`
    """
    paper: arxiv.Result = paper_details['paper_obj']
    arxiv_id = paper_details['arxiv_id']
    pdf_url = paper_details['pdf_url']

    full_text_content = None
    processing_error_message = None
    temp_pdf_path = None

    try:
        # Define a safe filename
        safe_filename = f"{arxiv_id.replace('/', '_')}.pdf"
        temp_pdf_path = os.path.join(temp_dir, safe_filename)
        logger.info(f"  Downloading PDF for {arxiv_id} to: {temp_pdf_path}")

        loop = asyncio.get_running_loop()
        # Run blocking download in executor
        await loop.run_in_executor(
            None,
            lambda: paper.download_pdf(dirpath=temp_dir, filename=safe_filename)
        )
        logger.info(f"  Download successful for {arxiv_id}.")

        logger.info(f"  Parsing PDF: {temp_pdf_path}")
        # PDF parsing is CPU-bound, run in executor

        def parse_pdf_sync():
            doc = fitz.open(temp_pdf_path)
            extracted_pages = [page.get_text("text", sort=True) for page in doc]
            doc.close()
            return "\n".join(extracted_pages).strip()

        full_text_content = await loop.run_in_executor(None, parse_pdf_sync)

        if not full_text_content:
            full_text_content = "[Could not extract text content from PDF]"
            # processing_error_message = "Could not extract text content from PDF" # Not necessarily an error, could be image-based
        elif max_text_length is not None and len(full_text_content) > max_text_length:
            full_text_content = full_text_content[:max_text_length] + f"... (truncated to {max_text_length} chars)"

        logger.info(f"  Successfully extracted text for {arxiv_id} (length: {len(full_text_content)} chars).")

    except FileNotFoundError:
        processing_error_message = "[Download failed or file not found after download attempt]"
        logger.error(f"  Error for {arxiv_id}: {processing_error_message}")
    except arxiv.arxiv.DownloadError as e:
        processing_error_message = f"[Failed to download PDF: {e}]"
        logger.error(f"  Error for {arxiv_id}: {processing_error_message}")
    except fitz.fitz.FitzError as e: # Specific exception for PyMuPDF errors
        processing_error_message = f"[Failed to parse PDF: {e}]"
        logger.error(f"  Error for {arxiv_id}: {processing_error_message}")
    except Exception as e:
        processing_error_message = f"[Unexpected error processing PDF {arxiv_id}: {type(e).__name__} - {e}]"
        logger.error(f"  Error for {arxiv_id}: {processing_error_message}", exc_info=True)
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                logger.debug(f"  Deleted temporary PDF: {temp_pdf_path}")
            except Exception as e:
                logger.warning(f"  Failed to delete temporary PDF {temp_pdf_path}: {e}")

    return ArxivSearchResult(
        title=paper.title,
        authors=[author.name for author in paper.authors],
        published_date=paper.published.strftime('%Y-%m-%d') if paper.published else "N/A",
        summary=paper.summary,
        arxiv_id=arxiv_id,
        pdf_url=pdf_url,
        full_text=full_text_content,
        processing_error=processing_error_message
    )


class _ArxivService:
    """Encapsulates ArXiv client logic and configuration."""
    
    def __init__(self, config: ArxivConfig):
        self.config = config
        if arxiv is None or fitz is None:
            logger.error("arxiv or PyMuPDF (fitz) package not installed. Arxiv service unavailable.")
            raise ArxivConfigError("Required package 'arxiv' or 'PyMuPDF' not installed.")
        self.client = arxiv.Client()  # Standard synchronous client
        logger.info("_ArxivService initialized.")

    @retry_on_exception(
        retries=3,
        delay=1.5,
        backoff=2.0,
        exceptions=(ArxivApiError, InvalidResponseError, ArxivServiceError),
        operation="ArXiv API Search Call"
    )
    async def search(
        self,
        query: str,
        max_results_override: Optional[int] = None,
        max_text_length_override: Optional[int] = None
    ) -> List[ArxivSearchResult]:
        """
        Performs an ArXiv search, downloads PDFs, and extracts text asynchronously.

        Args:
            query: The search query string.
            max_results_override: Optional override for the maximum number of results.
            max_text_length_override: Optional override for maximum text length per paper.

        Returns:
            A list of ArxivSearchResult objects.

        Raises:
            ValueError: If query is empty.
            ArxivApiError: For errors during the ArXiv API call or processing.
            ArxivServiceError: For other service-level issues.
        """
        logger.info(f"Performing ArXiv search for query: '{query[:100]}...'")
        if not query:
            logger.warning("Received empty query for ArXiv search.")
            raise InputValidationError("Search query cannot be empty.")

        effective_max_results = max_results_override if max_results_override is not None else self.config.default_max_results
        effective_max_text_length = max_text_length_override if max_text_length_override is not None else self.config.default_max_text_length

        try:
            loop = asyncio.get_running_loop()
            
            # The arxiv.Search and client.results are synchronous, run them in executor
            search_params = arxiv.Search(
                query=query,
                max_results=effective_max_results, # Fetch this many primary results
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            # Get all metadata results first (blocking call)
            try:
                results_iterator = await loop.run_in_executor(
                    None,
                    self.client.results,
                    search_params
                )
                # Convert iterator to list within the executor to avoid StopIteration issues in async context
                papers_metadata = await loop.run_in_executor(None, list, results_iterator)
            except Exception as e: # Catch broad exceptions from arxiv library during initial fetch
                logger.error(f"Error fetching initial results from ArXiv for query '{query}': {e}", exc_info=True)
                raise InvalidResponseError(f"Failed to retrieve search results from ArXiv: {e}") from e

            if not papers_metadata:
                logger.info(f"No papers found on ArXiv for query: '{query}'")
                return []

            tasks = []
            # Use a single temporary directory for all downloads in this search
            with tempfile.TemporaryDirectory(prefix="arxiv_pdf_") as temp_dir:
                logger.info(f"Created temporary directory for downloads: {temp_dir}")

                for paper_obj in papers_metadata: # papers_metadata is now a list of arxiv.Result
                    if not isinstance(paper_obj, arxiv.Result):
                        logger.warning(f"Skipping non-Result item from ArXiv: {type(paper_obj)}")
                        continue

                    paper_initial_details = {
                        'paper_obj': paper_obj,
                        'arxiv_id': paper_obj.get_short_id(),
                        'pdf_url': paper_obj.pdf_url,
                    }
                    # Create a task to download/extract PDF and build ArxivSearchResult
                    task = asyncio.create_task(
                        _async_download_and_extract_pdf_text(
                            paper_initial_details,
                            temp_dir,
                            effective_max_text_length
                        ),
                        name=f"pdf_process_{paper_obj.get_short_id()}"
                    )
                    tasks.append(task)

                if not tasks:
                    logger.info("No valid papers to process after metadata fetch.")
                    return []

                logger.info(f"Waiting for {len(tasks)} PDF processing tasks to complete...")
                # Gather results; asyncio.gather preserves order
                processed_results: List[ArxivSearchResult | Exception] = await asyncio.gather(*tasks, return_exceptions=True)
                logger.info("All PDF processing tasks finished.")

                final_results_list: List[ArxivSearchResult] = []
                for i, res_or_exc in enumerate(processed_results):
                    if isinstance(res_or_exc, ArxivSearchResult):
                        final_results_list.append(res_or_exc)
                    elif isinstance(res_or_exc, Exception):
                        original_paper_obj = papers_metadata[i] # Relies on order preservation
                        logger.error(f"Task for paper {original_paper_obj.get_short_id()} failed: {res_or_exc}", exc_info=res_or_exc)
                        # Create a result indicating the error
                        final_results_list.append(ArxivSearchResult(
                            title=original_paper_obj.title,
                            authors=[author.name for author in original_paper_obj.authors],
                            published_date=original_paper_obj.published.strftime('%Y-%m-%d') if original_paper_obj.published else "N/A",
                            summary=original_paper_obj.summary,
                            arxiv_id=original_paper_obj.get_short_id(),
                            pdf_url=original_paper_obj.pdf_url,
                            processing_error=f"Failed during PDF processing: {type(res_or_exc).__name__} - {str(res_or_exc)}"
                        ))
                    else:
                        # Should not happen with return_exceptions=True
                        logger.warning(f"Unexpected item in gathered results: {type(res_or_exc)}")

            logger.info(f"ArXiv search successful, processed {len(final_results_list)} papers for query '{query}'.")
            return final_results_list
            
#        except ValueError as ve: # E.g. empty query
#            raise ve
#        except ArxivApiError: # Re-raise if already specific
#            raise

        except InputValidationError:
            raise
        except InvalidResponseError:
            raise
        except Exception as e:
            logger.error(f"Error during ArXiv search operation for query '{query}': {e}", exc_info=True)
            # This is a catch-all for unexpected issues in the orchestration
            raise ServiceUnavailableError(f"Unexpected error during ArXiv search: {e}") from e


@lru_cache(maxsize=1)
def get_arxiv_service() -> _ArxivService:
    """
    Factory function to get a singleton instance of the Arxiv service.
    Handles configuration loading and service initialization.

    Returns:
        An initialized _ArxivService instance.

    Raises:
        ArxivConfigError: If configuration loading or validation fails,
                          or if required libraries aren't installed.
    """
    logger.debug("Attempting to get _ArxivService instance...")
    try:
        config = ArxivConfig()  # Load and validate config
        service_instance = _ArxivService(config=config)
        logger.info("_ArxivService instance created successfully via get_arxiv_service.")
        return service_instance
    except ArxivConfigError as e: # Handles errors from ArxivConfig() or _ArxivService() init
        logger.error(f"FATAL: Failed to initialize _ArxivService: {e}", exc_info=True)
        raise # Re-raise specific config error
    except Exception as e:
        # Catch any other unexpected error during initialization
        logger.error(f"FATAL: Unexpected error initializing _ArxivService: {e}", exc_info=True)
        raise ArxivConfigError(f"Unexpected error during _ArxivService initialization: {e}") from e
