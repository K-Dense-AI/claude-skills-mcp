"""HTTP server with MCP Streamable HTTP transport."""

import logging
import threading
from typing import Any

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent

from .search_engine import SkillSearchEngine
from .skill_loader import load_skills_in_batches, load_all_skills
from .config import load_config
from .update_checker import UpdateChecker
from .scheduler import HourlyScheduler

logger = logging.getLogger(__name__)

# Global state
mcp_server = Server("claude-skills-mcp-backend")
session_manager: StreamableHTTPSessionManager | None = None
search_engine: SkillSearchEngine | None = None
loading_state_global = None
update_checker_global: UpdateChecker | None = None
scheduler_global: HourlyScheduler | None = None
config_global: dict[str, Any] | None = None


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
        from .mcp_handlers import (
            handle_search_skills,
            handle_read_skill_document,
            handle_list_skills,
        )

        if name == "search_skills":
            return await handle_search_skills(
                arguments,
                search_engine,
                loading_state_global,
                default_top_k,
                max_content_chars,
            )
        elif name == "read_skill_document":
            return await handle_read_skill_document(arguments, search_engine)
        elif name == "list_skills":
            return await handle_list_skills(
                arguments, search_engine, loading_state_global
            )
        else:
            raise ValueError(f"Unknown tool: {name}")


async def health_check(request):
    """Health check endpoint."""
    skills_loaded = len(search_engine.skills) if search_engine else 0
    models_loaded = search_engine.model is not None if search_engine else False

    response = {
        "status": "ok",
        "version": "1.0.0",
        "skills_loaded": skills_loaded,
        "models_loaded": models_loaded,
        "loading_complete": loading_state_global.is_complete
        if loading_state_global
        else False,
    }

    # Add auto-update information
    if config_global:
        response["auto_update_enabled"] = config_global.get(
            "auto_update_enabled", False
        )

    if scheduler_global:
        scheduler_status = scheduler_global.get_status()
        response.update(
            {
                "next_update_check": scheduler_status.get("next_run_time"),
                "last_update_check": scheduler_status.get("last_run_time"),
            }
        )

    if update_checker_global:
        api_usage = update_checker_global.get_api_usage()
        response.update(
            {
                "github_api_calls_this_hour": api_usage.get("calls_this_hour", 0),
                "github_api_limit": api_usage.get("limit_per_hour", 60),
                "github_authenticated": api_usage.get("authenticated", False),
            }
        )

    if loading_state_global:
        with loading_state_global._lock:
            if loading_state_global.errors:
                response["update_errors"] = loading_state_global.errors[
                    -5:
                ]  # Last 5 errors

    return JSONResponse(response)


# Create Starlette app
routes = [
    Route("/health", health_check, methods=["GET"]),
]

app = Starlette(routes=routes)


async def initialize_backend(config_path: str | None = None, verbose: bool = False):
    """Initialize search engine and load skills."""
    global \
        search_engine, \
        loading_state_global, \
        update_checker_global, \
        scheduler_global, \
        config_global

    # Setup logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Initializing Claude Skills MCP Backend")

    # Load configuration
    config = load_config(config_path)
    config_global = config

    # Initialize search engine
    logger.info("Initializing search engine...")
    search_engine = SkillSearchEngine(config["embedding_model"])

    # Initialize loading state
    loading_state_global = LoadingState()

    # Initialize update checker
    github_token = config.get("github_api_token")
    update_checker_global = UpdateChecker(github_token)
    logger.info(
        f"Update checker initialized (GitHub token: {'provided' if github_token else 'not provided'})"
    )

    # Register MCP handlers
    register_mcp_handlers(
        default_top_k=config["default_top_k"],
        max_content_chars=config.get("max_skill_content_chars"),
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

    # Setup auto-update scheduler if enabled
    if config.get("auto_update_enabled", False):
        interval_minutes = config.get("auto_update_interval_minutes", 60)

        async def update_callback():
            """Callback for scheduled updates."""
            try:
                logger.info("Running scheduled update check...")

                # Check for updates
                result = update_checker_global.check_for_updates(
                    config["skill_sources"]
                )

                logger.info(
                    f"Update check complete: {len(result.changed_sources)} sources changed, "
                    f"{result.api_calls_made} API calls made"
                )

                if result.errors:
                    for error in result.errors:
                        logger.warning(f"Update check error: {error}")
                        loading_state_global.add_error(error)

                # Reload skills if updates detected
                if result.has_updates:
                    logger.info(
                        f"Reloading {len(result.changed_sources)} changed sources..."
                    )

                    # For simplicity, reload all skills if any changed
                    # This clears the index and reloads everything
                    logger.info("Reloading all skills...")
                    new_skills = load_all_skills(
                        skill_sources=config["skill_sources"], config=config
                    )

                    # Re-index all skills
                    search_engine.index_skills(new_skills)
                    logger.info(f"Re-indexed {len(new_skills)} skills after update")
                else:
                    logger.info("No updates detected")

                # Warn if approaching API limit (only for non-authenticated)
                api_usage = update_checker_global.get_api_usage()
                if (
                    not api_usage["authenticated"]
                    and api_usage["calls_this_hour"] >= 50
                ):
                    logger.warning(
                        f"Approaching GitHub API rate limit: {api_usage['calls_this_hour']}/60 calls this hour"
                    )

            except Exception as e:
                error_msg = f"Error during scheduled update: {e}"
                logger.error(error_msg, exc_info=True)
                loading_state_global.add_error(error_msg)

        # Create and start scheduler
        scheduler_global = HourlyScheduler(interval_minutes, update_callback)
        scheduler_global.start()
        logger.info(
            f"Auto-update scheduler started (interval: {interval_minutes} minutes)"
        )
    else:
        logger.info("Auto-update disabled in configuration")


async def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    config_path: str | None = None,
    verbose: bool = False,
):
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
        app, host=host, port=port, log_level="debug" if verbose else "info"
    )
    server = uvicorn.Server(config)
    await server.serve()
