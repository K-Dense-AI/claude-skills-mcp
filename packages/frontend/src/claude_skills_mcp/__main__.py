"""Main entry point for Claude Skills MCP Frontend (Proxy)."""

import argparse
import asyncio
import logging
import sys

from .mcp_proxy import MCPProxy


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


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    """Parse command line arguments.

    Frontend accepts SUPERSET of backend args and forwards them.

    Returns
    -------
    tuple[argparse.Namespace, list[str]]
        Parsed frontend args and list of args to forward to backend.
    """
    parser = argparse.ArgumentParser(
        description="Claude Skills MCP Frontend - Lightweight Proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with defaults (auto-downloads backend)
  uvx claude-skills-mcp

  # Run with custom configuration (forwarded to backend)
  uvx claude-skills-mcp --config my-config.json

  # Run with verbose logging (both frontend and backend)
  uvx claude-skills-mcp --verbose

  # Connect to remote backend instead of local
  uvx claude-skills-mcp --remote https://skills.k-dense.ai/mcp

  # All backend args are supported and forwarded:
  uvx claude-skills-mcp --config custom.json --verbose
        """,
    )

    # Frontend-specific arguments
    parser.add_argument(
        "--remote",
        type=str,
        help="Connect to remote backend URL instead of spawning local backend (e.g., https://skills.k-dense.ai/mcp)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (frontend and backend)",
    )

    # Backend arguments (forwarded when spawning backend)
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Backend port (default: 8765, forwarded to backend)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Backend host (default: 127.0.0.1, forwarded to backend)",
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration JSON file (forwarded to backend)",
    )

    parser.add_argument(
        "--example-config",
        action="store_true",
        help="Print example configuration and exit (forwarded to backend)",
    )

    args = parser.parse_args()

    # Build backend args list
    backend_args = []

    if args.port != 8765:
        backend_args.extend(["--port", str(args.port)])

    if args.host != "127.0.0.1":
        backend_args.extend(["--host", args.host])

    if args.config:
        backend_args.extend(["--config", args.config])

    if args.verbose:
        backend_args.append("--verbose")

    if args.example_config:
        backend_args.append("--example-config")

    return args, backend_args


async def main_async() -> None:
    """Main async function."""
    args, backend_args = parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Starting Claude Skills MCP Frontend (Proxy)")

    # Handle example config - just forward to backend
    if args.example_config:
        import subprocess

        try:
            # Try to call backend directly if installed
            result = subprocess.run(
                ["claude-skills-mcp-backend", "--example-config"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print(result.stdout)
                return
        except Exception:
            pass

        # Fallback: show message
        print(
            "# Backend not installed yet. Run without --example-config first to install.",
            file=sys.stderr,
        )
        print("# Default configuration will be used by the backend.", file=sys.stderr)
        sys.exit(1)

    try:
        # Check if remote backend specified
        if args.remote:
            logger.info(f"Using remote backend: {args.remote}")
            # TODO: Implement remote backend connection
            # For now, this would require a different proxy implementation
            print("Remote backend not yet implemented in v1.0.0", file=sys.stderr)
            print("Please use local backend for now", file=sys.stderr)
            sys.exit(1)

        # Create and start proxy with backend args
        proxy = MCPProxy(backend_args=backend_args)
        await proxy.start()

    except KeyboardInterrupt:
        logger.info("Proxy stopped by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
