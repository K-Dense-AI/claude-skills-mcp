"""Main entry point for Claude Skills MCP server."""

import argparse
import asyncio
import logging
import sys

from .config import load_config, get_example_config
from .skill_loader import load_all_skills
from .search_engine import SkillSearchEngine
from .server import SkillsMCPServer


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

        # Load skills from all sources
        logger.info("Loading skills from configured sources...")
        skills = load_all_skills(config["skill_sources"])

        if not skills:
            logger.error("No skills were loaded! Please check your configuration.")
            sys.exit(1)

        logger.info(f"Successfully loaded {len(skills)} skills")

        # Initialize search engine
        search_engine = SkillSearchEngine(config["embedding_model"])
        search_engine.index_skills(skills)

        # Create and run MCP server
        mcp_server = SkillsMCPServer(
            search_engine=search_engine,
            default_top_k=config["default_top_k"],
            max_content_chars=config.get("max_skill_content_chars"),
        )

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
