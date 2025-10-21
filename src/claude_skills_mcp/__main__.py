"""Main entry point for Claude Skills MCP server."""

import argparse
import asyncio
import logging
import sys
import threading

from .config import load_config, get_example_config
from .skill_loader import load_skills_in_batches
from .search_engine import SkillSearchEngine
from .server import SkillsMCPServer, LoadingState


def setup_logging(verbose: bool = False) -> None:
    """Configure logging.

    Parameters
    ----------
    verbose : bool, optional
        Enable verbose (DEBUG) logging, by default False.
    """
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Claude Skills MCP Server - Vector search for Claude Agent Skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration (K-Dense-AI scientific skills)
  uvx claude-skills-mcp

  # Run with custom configuration
  uvx claude-skills-mcp --config my-config.json

  # Generate example configuration
  uvx claude-skills-mcp --example-config > config.json

  # Run with verbose logging
  uvx claude-skills-mcp --verbose
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration JSON file (uses defaults if not specified)",
    )

    parser.add_argument(
        "--example-config",
        action="store_true",
        help="Print example configuration and exit",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


async def main_async() -> None:
    """Main async function."""
    args = parse_args()

    # Handle example config request
    if args.example_config:
        print(get_example_config())
        return

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Starting Claude Skills MCP Server")

    try:
        # Load configuration
        config = load_config(args.config)

        # Initialize search engine (empty, will be populated by background loading)
        logger.info("Initializing search engine...")
        search_engine = SkillSearchEngine(config["embedding_model"])

        # Initialize loading state
        loading_state = LoadingState()

        # Create MCP server (starts immediately with empty index)
        mcp_server = SkillsMCPServer(
            search_engine=search_engine,
            loading_state=loading_state,
            default_top_k=config["default_top_k"],
            max_content_chars=config.get("max_skill_content_chars"),
        )

        # Define batch callback for incremental loading
        def on_batch_loaded(batch_skills: list, total_loaded: int) -> None:
            """Callback invoked after each batch of skills is loaded.

            Parameters
            ----------
            batch_skills : list
                Skills in this batch.
            total_loaded : int
                Total number of skills loaded so far.
            """
            logger.info(
                f"Batch loaded: {len(batch_skills)} skills (total: {total_loaded})"
            )
            # Add skills to search engine incrementally
            search_engine.add_skills(batch_skills)
            # Update loading state
            loading_state.update_progress(total_loaded)

        # Start background thread to load skills
        def background_loader() -> None:
            """Background thread function to load skills in batches."""
            try:
                logger.info("Starting background skill loading...")
                load_skills_in_batches(
                    skill_sources=config["skill_sources"],
                    config=config,
                    batch_callback=on_batch_loaded,
                    batch_size=config.get("batch_size", 10),
                )
                loading_state.mark_complete()
                logger.info("Background skill loading complete")
            except Exception as e:
                logger.error(f"Error in background loading: {e}", exc_info=True)
                loading_state.add_error(str(e))
                loading_state.mark_complete()

        # Start the background loading thread
        loader_thread = threading.Thread(target=background_loader, daemon=True)
        loader_thread.start()
        logger.info("Background loading thread started, server is ready")

        # Run the MCP server (non-blocking, skills load in background)
        await mcp_server.run()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
