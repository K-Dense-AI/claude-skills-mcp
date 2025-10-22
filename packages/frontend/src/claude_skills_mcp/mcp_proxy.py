"""MCP Proxy - Acts as both MCP Server (stdio) and MCP Client (HTTP)."""

import asyncio
import logging
from typing import Any, Optional

from mcp.server import Server
from mcp import ClientSession
from mcp.server.stdio import stdio_server
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool, TextContent

from .backend_manager import BackendManager

logger = logging.getLogger(__name__)


# HARDCODED tool schemas (must match backend exactly!)
# This allows instant list_tools response without waiting for backend
TOOL_SCHEMAS = [
    Tool(
        name="search_skills",
        title="Claude Agent Skills Search",
        description=(
            "Search and discover proven Claude Agent Skills that provide expert guidance for your tasks. "
            "Use this tool whenever you're starting a new task, facing a coding challenge, or need specialized "
            "techniques. Returns highly relevant skills with complete implementation guides, code examples, and "
            "best practices ranked by relevance. Each result includes detailed step-by-step instructions you can "
            "follow immediately. Essential for leveraging battle-tested patterns, avoiding common pitfalls, and "
            "accelerating development with proven solutions. Perfect for finding reusable workflows, debugging "
            "strategies, API integration patterns, data processing techniques, and domain-specific methodologies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": (
                        "Description of the task you want to accomplish. Be specific about your goal, "
                        "context, or problem domain for better results (e.g., 'debug Python API errors', "
                        "'process genomic data', 'build React dashboard')"
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of skills to return (default: 3). Higher values provide more options but may include less relevant results.",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 20,
                },
                "list_documents": {
                    "type": "boolean",
                    "description": "Include a list of available documents (scripts, references, assets) for each skill (default: True)",
                    "default": True,
                },
            },
            "required": ["task_description"],
        },
    ),
    Tool(
        name="read_skill_document",
        title="Read Skill Document",
        description=(
            "Retrieve specific documents (scripts, references, assets) from a skill. "
            "Use this after searching for skills to access additional resources like Python scripts, "
            "example data files, reference materials, or images. Supports pattern matching to retrieve "
            "multiple files at once (e.g., 'scripts/*.py' for all Python scripts)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill (as returned by search_skills)",
                },
                "document_path": {
                    "type": "string",
                    "description": (
                        "Path or pattern to match documents. Examples: 'scripts/example.py', "
                        "'scripts/*.py', 'references/*', 'assets/diagram.png'. "
                        "If not provided, returns a list of all available documents."
                    ),
                },
                "include_base64": {
                    "type": "boolean",
                    "description": (
                        "For images: if True, return base64-encoded content; if False, return only URL. "
                        "Default: False (URL only for efficiency)"
                    ),
                    "default": False,
                },
            },
            "required": ["skill_name"],
        },
    ),
    Tool(
        name="list_skills",
        title="List All Loaded Skills",
        description=(
            "Returns a complete inventory of all loaded skills with their names, descriptions, "
            "sources, and document counts. Use this for exploration or debugging to see what "
            "skills are available. NOTE: For finding relevant skills for a specific task, use "
            "the 'search_skills' tool instead - it performs semantic search to find the most "
            "appropriate skills for your needs."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
]


class MCPProxy:
    """MCP Proxy that acts as stdio server and HTTP client.

    This lightweight proxy:
    1. Starts instantly (<5s) with minimal dependencies
    2. Returns hardcoded tools immediately (no backend needed)
    3. Spawns backend in background (non-blocking)
    4. Proxies tool calls to backend once ready

    Attributes
    ----------
    server : Server
        MCP server instance (stdio transport).
    backend_manager : BackendManager
        Manages backend installation and spawning.
    backend_client : ClientSession | None
        MCP client connected to backend.
    backend_ready : bool
        Whether backend is ready to handle requests.
    backend_args : list[str]
        CLI arguments to forward to backend.
    """

    def __init__(self, backend_args: list[str]):
        """Initialize the proxy.

        Parameters
        ----------
        backend_args : list[str]
            CLI arguments to forward to backend when spawning.
        """
        self.server = Server("claude-skills-mcp-proxy")
        self.backend_manager = BackendManager()
        self.backend_client: Optional[ClientSession] = None
        self.backend_ready = False
        self.backend_args = backend_args
        self._backend_task: Optional[asyncio.Task] = None

        logger.info("MCP Proxy initialized")

    async def start(self) -> None:
        """Start the proxy server.

        This method:
        1. Registers MCP handlers (with hardcoded tools)
        2. Spawns backend in background
        3. Runs stdio MCP server (connects to Cursor)
        """
        # Register handlers before starting
        self._register_handlers()

        # Start backend in background (NON-BLOCKING!)
        self._backend_task = asyncio.create_task(self._start_backend_async())

        # Run stdio MCP server (this blocks until Cursor disconnects)
        logger.info("Starting MCP proxy server with stdio transport")
        async with stdio_server() as (read_stream, write_stream):
            try:
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
            finally:
                # Cleanup on exit
                await self._cleanup()

    def _register_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools - returns hardcoded schemas INSTANTLY."""
            logger.debug("list_tools called - returning hardcoded tools")
            return TOOL_SCHEMAS

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls - proxy to backend."""
            logger.info(f"call_tool: {name}")

            # Check if backend is ready
            if not self.backend_ready:
                # Backend still loading - show progress
                logger.info("Backend not ready yet, returning loading message")
                return [
                    TextContent(
                        type="text",
                        text=(
                            "[BACKEND LOADING]\n\n"
                            "The backend server is starting up and downloading models.\n"
                            "This happens only on first run and takes 30-120 seconds.\n\n"
                            "Please wait a moment and try again.\n\n"
                            "Future requests will be instant once the backend is ready!"
                        ),
                    )
                ]

            # Backend ready - forward the request
            logger.info(f"Forwarding {name} to backend")
            try:
                result = await self.backend_client.call_tool(name, arguments)
                logger.debug(f"Backend returned {len(result.content)} content items")
                return result.content
            except Exception as e:
                logger.error(f"Error calling backend tool: {e}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error communicating with backend: {e}\n\nPlease try again.",
                    )
                ]

    async def _start_backend_async(self) -> None:
        """Start backend in background (non-blocking).

        This method:
        1. Checks if backend is installed
        2. Installs if needed (uv pip install)
        3. Spawns backend process (uvx)
        4. Waits for health check
        5. Connects MCP client
        """
        try:
            logger.info("Starting backend initialization...")

            # Ensure backend is running
            backend_url = await self.backend_manager.ensure_backend_running(
                self.backend_args
            )

            # Connect to backend via streamable HTTP
            logger.info(f"Connecting to backend at {backend_url}")
            await self._connect_to_backend(backend_url)

            self.backend_ready = True
            logger.info("Backend ready and connected!")

        except Exception as e:
            logger.error(f"Failed to start backend: {e}", exc_info=True)
            # Backend failed but proxy still runs
            # Users will see error message when they try to use tools

    async def _connect_to_backend(self, url: str) -> None:
        """Connect to backend via MCP streamable HTTP client.

        Parameters
        ----------
        url : str
            Backend URL (e.g., http://localhost:8765/mcp).
        """
        try:
            # Create streamable HTTP client
            async with streamablehttp_client(url) as (read, write):
                self.backend_client = ClientSession(read, write)

                # Initialize the client session
                result = await self.backend_client.initialize()
                logger.info(f"Backend client initialized: {result}")

        except Exception as e:
            logger.error(f"Failed to connect to backend: {e}")
            raise

    async def _cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        logger.info("Cleaning up proxy...")

        # Close backend client
        if self.backend_client:
            try:
                # Note: ClientSession doesn't have explicit close method
                # It's managed by the context manager
                pass
            except Exception as e:
                logger.warning(f"Error closing backend client: {e}")

        # Terminate backend process
        self.backend_manager.cleanup()

        # Cancel backend task
        if self._backend_task and not self._backend_task.done():
            self._backend_task.cancel()
            try:
                await self._backend_task
            except asyncio.CancelledError:
                pass

        logger.info("Cleanup complete")
