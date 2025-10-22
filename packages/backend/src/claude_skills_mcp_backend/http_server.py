"""HTTP server with MCP Streamable HTTP transport."""

import asyncio
import logging
import sys
import threading
from typing import Any

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
import uvicorn
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent

from .search_engine import SkillSearchEngine
from .skill_loader import load_skills_in_batches
from .config import load_config

logger = logging.getLogger(__name__)

# Global state
mcp_server = Server("claude-skills-mcp-backend")
session_manager: StreamableHTTPSessionManager | None = None
search_engine: SkillSearchEngine | None = None
loading_state_global = None


class LoadingState:
    """Thread-safe state tracker for background skill loading."""
    
    def __init__(self):
        self.total_skills = 0
        self.loaded_skills = 0
        self.is_complete = False
        self.errors: list[str] = []
        self._lock = threading.Lock()
    
    def update_progress(self, loaded: int, total: int | None = None) -> None:
        with self._lock:
            self.loaded_skills = loaded
            if total is not None:
                self.total_skills = total
    
    def add_error(self, error: str) -> None:
        with self._lock:
            self.errors.append(error)
    
    def mark_complete(self) -> None:
        with self._lock:
            self.is_complete = True
    
    def get_status_message(self) -> str | None:
        with self._lock:
            if self.is_complete:
                return None
            if self.loaded_skills == 0:
                return "[LOADING: Skills are being loaded in the background, please wait...]\n"
            if self.total_skills > 0:
                return f"[LOADING: {self.loaded_skills}/{self.total_skills} skills loaded, indexing in progress...]\n"
            return f"[LOADING: {self.loaded_skills} skills loaded so far, indexing in progress...]\n"


def register_mcp_handlers(default_top_k: int = 3, max_content_chars: int | None = None):
    """Register MCP tool handlers."""
    
    @mcp_server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available MCP tools."""
        return [
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
                            "description": f"Number of skills to return (default: {default_top_k}). Higher values provide more options but may include less relevant results.",
                            "default": default_top_k,
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
    
    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls - import handlers from mcp_handlers."""
        # Import handle functions from mcp_handlers
        from .mcp_handlers import handle_search_skills, handle_read_skill_document, handle_list_skills
        
        if name == "search_skills":
            return await handle_search_skills(
                arguments, search_engine, loading_state_global, default_top_k, max_content_chars
            )
        elif name == "read_skill_document":
            return await handle_read_skill_document(arguments, search_engine)
        elif name == "list_skills":
            return await handle_list_skills(arguments, search_engine, loading_state_global)
        else:
            raise ValueError(f"Unknown tool: {name}")


async def health_check(request):
    """Health check endpoint."""
    skills_loaded = len(search_engine.skills) if search_engine else 0
    models_loaded = search_engine.model is not None if search_engine else False
    
    return JSONResponse({
        "status": "ok",
        "version": "1.0.0",
        "skills_loaded": skills_loaded,
        "models_loaded": models_loaded,
        "loading_complete": loading_state_global.is_complete if loading_state_global else False
    })


# Create Starlette app
routes = [
    Route("/health", health_check, methods=["GET"]),
]

app = Starlette(routes=routes)


async def initialize_backend(config_path: str | None = None, verbose: bool = False):
    """Initialize search engine and load skills."""
    global search_engine, loading_state_global
    
    # Setup logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger.info("Initializing Claude Skills MCP Backend")
    
    # Load configuration
    config = load_config(config_path)
    
    # Initialize search engine
    logger.info("Initializing search engine...")
    search_engine = SkillSearchEngine(config["embedding_model"])
    
    # Initialize loading state
    loading_state_global = LoadingState()
    
    # Register MCP handlers
    register_mcp_handlers(
        default_top_k=config["default_top_k"],
        max_content_chars=config.get("max_skill_content_chars")
    )
    
    # Define batch callback for incremental loading
    def on_batch_loaded(batch_skills: list, total_loaded: int) -> None:
        logger.info(f"Batch loaded: {len(batch_skills)} skills (total: {total_loaded})")
        search_engine.add_skills(batch_skills)
        loading_state_global.update_progress(total_loaded)
    
    # Start background thread to load skills
    def background_loader() -> None:
        try:
            logger.info("Starting background skill loading...")
            load_skills_in_batches(
                skill_sources=config["skill_sources"],
                config=config,
                batch_callback=on_batch_loaded,
                batch_size=config.get("batch_size", 10),
            )
            loading_state_global.mark_complete()
            logger.info("Background skill loading complete")
        except Exception as e:
            logger.error(f"Error in background loading: {e}", exc_info=True)
            loading_state_global.add_error(str(e))
            loading_state_global.mark_complete()
    
    # Start the background loading thread
    loader_thread = threading.Thread(target=background_loader, daemon=True)
    loader_thread.start()
    logger.info("Background loading thread started, server is ready")


async def run_server(host: str = "127.0.0.1", port: int = 8765, config_path: str | None = None, verbose: bool = False):
    """Run the HTTP server."""
    global session_manager
    
    # Initialize backend (search engine, skills, etc.)
    await initialize_backend(config_path, verbose)
    
    # Create session manager for MCP protocol
    session_manager = StreamableHTTPSessionManager(mcp_server)
    
    # Mount MCP endpoint - session manager is an ASGI app
    app.mount("/mcp", session_manager)
    
    # Run server
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="debug" if verbose else "info"
    )
    server = uvicorn.Server(config)
    await server.serve()

