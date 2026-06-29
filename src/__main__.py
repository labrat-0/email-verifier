"""
Entry point for the email-verifier actor.
Sets up logging and runs the main actor loop.
"""

import asyncio
import logging


def setup_logging() -> None:
    """Configure logging for the actor."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Suppress noisy library loggers
    logging.getLogger("apify").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    """Entry point. Sets up logging and runs the actor."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Email Verifier actor starting...")

    from .main import run_actor
    asyncio.run(run_actor())


if __name__ == "__main__":
    main()
