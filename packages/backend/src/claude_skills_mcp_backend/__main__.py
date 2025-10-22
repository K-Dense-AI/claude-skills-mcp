"""Main entry point for Claude Skills MCP Backend (HTTP/Streamable HTTP server)."""

import argparse
import asyncio
import sys

from .http_server import run_server
from .config import get_example_config


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Claude Skills MCP Backend - Streamable HTTP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration
  claude-skills-mcp-backend

  # Run on custom port
  claude-skills-mcp-backend --port 8080

  # Run with custom configuration
  claude-skills-mcp-backend --config my-config.json

  # Generate example configuration
  claude-skills-mcp-backend --example-config > config.json

  # Run with verbose logging
  claude-skills-mcp-backend --verbose
        """,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to expose the HTTP server on (default: 8765)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the HTTP server to (default: 127.0.0.1, use 0.0.0.0 for remote access)",
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

    # Run the HTTP server
    await run_server(
        host=args.host,
        port=args.port,
        config_path=args.config,
        verbose=args.verbose
    )


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

