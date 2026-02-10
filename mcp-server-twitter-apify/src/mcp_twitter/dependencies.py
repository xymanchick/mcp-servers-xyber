import logging

from mcp_twitter.twitter import QueryRegistry, TwitterScraper, build_default_registry

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        DependencyContainer.initialize()

    Yield:
        await DependencyContainer.shutdown()

        # In route handlers via Depends():
        @router.post("/endpoint")
        async def endpoint(
            registry: QueryRegistry = Depends(get_registry),
            scraper: TwitterScraper = Depends(get_scraper),
        ):
            ...

    """

    _registry: QueryRegistry | None = None
    _scraper: TwitterScraper | None = None

    @classmethod
    def initialize(cls, apify_token: str, actor_name: str) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).

        Args:
            apify_token: Apify API token
            actor_name: Name of the Apify actor to use

        """
        logger.info("Initializing dependencies...")

        cls._registry = build_default_registry()
        cls._scraper = TwitterScraper(
            apify_token=apify_token,
            results_dir=None,  # Disable file-based storage, use DB cache only
            actor_name=actor_name,
            output_format="min",
            use_cache=True,  # Enable database cache
        )

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._scraper = None
        cls._registry = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_registry(cls) -> QueryRegistry:
        """
        Get the QueryRegistry instance.

        Usage as FastAPI dependency:
            @router.get("/queries")
            async def get_queries(registry: QueryRegistry = Depends(get_registry)):
                ...
        """
        if cls._registry is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._registry

    @classmethod
    def get_scraper(cls) -> TwitterScraper:
        """
        Get the TwitterScraper instance.

        Usage as FastAPI dependency:
            @router.post("/search")
            async def search(scraper: TwitterScraper = Depends(get_scraper)):
                ...
        """
        if cls._scraper is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._scraper


# Alias the class methods for use as FastAPI dependencies
get_registry = DependencyContainer.get_registry
get_scraper = DependencyContainer.get_scraper
