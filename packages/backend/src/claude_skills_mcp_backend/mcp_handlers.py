"""MCP server implementation for Claude Skills search."""

import fnmatch
import logging
import threading
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .search_engine import SkillSearchEngine

logger = logging.getLogger(__name__)


class LoadingState:
    """Thread-safe state tracker for background skill loading.

    Attributes
    ----------
    total_skills : int
        Total number of skills expected to be loaded.
    loaded_skills : int
        Number of skills loaded so far.
    is_complete : bool
        Whether loading is complete.
    errors : list[str]
        List of error messages encountered during loading.
    _lock : threading.Lock
        Lock for thread-safe access.
    """

    def __init__(self):
        """Initialize loading state."""
        self.total_skills = 0
        self.loaded_skills = 0
        self.is_complete = False
        self.errors: list[str] = []
        self._lock = threading.Lock()

    def update_progress(self, loaded: int, total: int | None = None) -> None:
        """Update loading progress.

        Parameters
        ----------
        loaded : int
            Number of skills loaded.
        total : int | None, optional
            Total skills expected (if known), by default None.
        """
        with self._lock:
            self.loaded_skills = loaded
            if total is not None:
                self.total_skills = total

    def add_error(self, error: str) -> None:
        """Add an error message.

        Parameters
        ----------
        error : str
            Error message to record.
        """
        with self._lock:
            self.errors.append(error)

    def mark_complete(self) -> None:
        """Mark loading as complete."""
        with self._lock:
            self.is_complete = True

    def get_status_message(self) -> str | None:
        """Get current loading status message.

        Returns
        -------
        str | None
            Status message if loading is in progress, None if complete.
        """
        with self._lock:
            if self.is_complete:
                return None

            if self.loaded_skills == 0:
                return "[LOADING: Skills are being loaded in the background, please wait...]\n"

            if self.total_skills > 0:
                return f"[LOADING: {self.loaded_skills}/{self.total_skills} skills loaded, indexing in progress...]\n"
            else:
                return f"[LOADING: {self.loaded_skills} skills loaded so far, indexing in progress...]\n"


class SkillsMCPServer:
    """MCP Server for searching Claude Agent Skills.

    Attributes
    ----------
    search_engine : SkillSearchEngine
        The search engine instance.
    default_top_k : int
        Default number of results to return.
    max_content_chars : int | None
        Maximum characters for skill content (None for unlimited).
    loading_state : LoadingState
        State tracker for background skill loading.
    """

    def __init__(
        self,
        search_engine: SkillSearchEngine,
        loading_state: LoadingState,
        default_top_k: int = 3,
        max_content_chars: int | None = None,
    ):
        """Initialize the MCP server.

        Parameters
        ----------
        search_engine : SkillSearchEngine
            Initialized search engine with indexed skills.
        loading_state : LoadingState
            State tracker for background skill loading.
        default_top_k : int, optional
            Default number of results to return, by default 3.
        max_content_chars : int | None, optional
            Maximum characters for skill content. None for unlimited, by default None.
        """
        self.search_engine = search_engine
        self.loading_state = loading_state
        self.default_top_k = default_top_k
        self.max_content_chars = max_content_chars
        self.server = Server("claude-skills-mcp")

        # Register handlers
        self._register_handlers()

        logger.info("MCP server initialized")

    def _register_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
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
                                "description": f"Number of skills to return (default: {self.default_top_k}). Higher values provide more options but may include less relevant results.",
                                "default": self.default_top_k,
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

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            if name == "search_skills":
                return await self._handle_search_skills(arguments)
            elif name == "read_skill_document":
                return await self._handle_read_skill_document(arguments)
            elif name == "list_skills":
                return await self._handle_list_skills(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _handle_search_skills(
        self, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle search_skills tool calls.

        Parameters
        ----------
        arguments : dict[str, Any]
            Tool arguments.

        Returns
        -------
        list[TextContent]
            Formatted search results.
        """
        task_description = arguments.get("task_description")
        if not task_description:
            raise ValueError("task_description is required")

        top_k = arguments.get("top_k", self.default_top_k)
        list_documents = arguments.get("list_documents", True)

        # Build formatted response
        response_parts = []

        # Add loading status if skills are still being loaded
        status_msg = self.loading_state.get_status_message()
        if status_msg:
            response_parts.append(status_msg)

        # Perform search
        results = self.search_engine.search(task_description, top_k)

        # Format results as text
        if not results:
            # Check if we have no results because skills are still loading
            if (
                not self.loading_state.is_complete
                and self.loading_state.loaded_skills == 0
            ):
                return [
                    TextContent(
                        type="text",
                        text=status_msg
                        or ""
                        + "No skills loaded yet. Please wait for skills to load and try again.",
                    )
                ]
            return [
                TextContent(
                    type="text",
                    text="No relevant skills found for the given task description.",
                )
            ]

        response_parts.append(
            f"Found {len(results)} relevant skill(s) for: '{task_description}'\n"
        )

        for i, result in enumerate(results, 1):
            response_parts.append(f"\n{'=' * 80}")
            response_parts.append(f"\nSkill {i}: {result['name']}")
            response_parts.append(f"\nRelevance Score: {result['relevance_score']:.4f}")
            response_parts.append(f"\nSource: {result['source']}")
            response_parts.append(f"\nDescription: {result['description']}")

            # Include document count if available
            documents = result.get("documents", {})
            if documents:
                response_parts.append(
                    f"\nAdditional Documents: {len(documents)} file(s)"
                )

                # List documents if requested
                if list_documents:
                    response_parts.append("\nAvailable Documents:")
                    for doc_path in sorted(documents.keys()):
                        doc_info = documents[doc_path]
                        doc_type = doc_info.get("type", "unknown")
                        doc_size = doc_info.get("size", 0)
                        size_kb = doc_size / 1024
                        response_parts.append(
                            f"  - {doc_path} ({doc_type}, {size_kb:.1f} KB)"
                        )

            response_parts.append(f"\n{'-' * 80}")
            response_parts.append("\nFull Content:\n")

            # Apply character limit truncation if configured
            content = result["content"]
            if (
                self.max_content_chars is not None
                and len(content) > self.max_content_chars
            ):
                truncated_content = content[: self.max_content_chars] + "..."
                response_parts.append(truncated_content)
                response_parts.append(
                    f"\n\n[Content truncated at {self.max_content_chars} characters. "
                    f"View full skill at: {result['source']}]"
                )
            else:
                response_parts.append(content)

            response_parts.append(f"\n{'=' * 80}\n")

        return [TextContent(type="text", text="\n".join(response_parts))]

    async def _handle_read_skill_document(
        self, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle read_skill_document tool calls.

        Parameters
        ----------
        arguments : dict[str, Any]
            Tool arguments.

        Returns
        -------
        list[TextContent]
            Document content or list of documents.
        """
        skill_name = arguments.get("skill_name")
        if not skill_name:
            raise ValueError("skill_name is required")

        document_path = arguments.get("document_path")
        include_base64 = arguments.get("include_base64", False)

        # Find the skill by name
        skill = None
        for s in self.search_engine.skills:
            if s.name == skill_name:
                skill = s
                break

        if not skill:
            return [
                TextContent(
                    type="text",
                    text=f"Skill '{skill_name}' not found. Please use search_skills to find valid skill names.",
                )
            ]

        # If no document_path provided, list all available documents
        if not document_path:
            if not skill.documents:
                return [
                    TextContent(
                        type="text",
                        text=f"Skill '{skill_name}' has no additional documents.",
                    )
                ]

            response_parts = [f"Available documents for skill '{skill_name}':\n"]
            for doc_path, doc_info in sorted(skill.documents.items()):
                doc_type = doc_info.get("type", "unknown")
                doc_size = doc_info.get("size", 0)
                size_kb = doc_size / 1024
                response_parts.append(f"  - {doc_path} ({doc_type}, {size_kb:.1f} KB)")

            return [TextContent(type="text", text="\n".join(response_parts))]

        # Match documents by pattern
        matching_docs = {}
        for doc_path, doc_info in skill.documents.items():
            if fnmatch.fnmatch(doc_path, document_path) or doc_path == document_path:
                matching_docs[doc_path] = doc_info

        if not matching_docs:
            return [
                TextContent(
                    type="text",
                    text=f"No documents matching '{document_path}' found in skill '{skill_name}'.",
                )
            ]

        # Lazy fetch: Load content for matched documents if not already loaded
        for doc_path in matching_docs:
            doc_info = matching_docs[doc_path]
            # Check if content needs to be fetched
            if not doc_info.get("fetched") and "content" not in doc_info:
                # Fetch on-demand
                content = skill.get_document(doc_path)
                if content:
                    # Update the matched doc with fetched content
                    matching_docs[doc_path] = content

        # Format response based on number of matches
        response_parts = []

        if len(matching_docs) == 1:
            # Single document - return its content
            doc_path, doc_info = list(matching_docs.items())[0]
            doc_type = doc_info.get("type")

            if doc_type == "text":
                response_parts.append(f"Document: {doc_path}\n")
                response_parts.append("=" * 80)
                response_parts.append(f"\n{doc_info.get('content', '')}")

            elif doc_type == "image":
                response_parts.append(f"Image: {doc_path}\n")
                if doc_info.get("size_exceeded"):
                    response_parts.append(
                        f"Size: {doc_info.get('size', 0) / 1024:.1f} KB (exceeds limit)"
                    )
                    response_parts.append(f"\nURL: {doc_info.get('url', 'N/A')}")
                elif include_base64:
                    response_parts.append(
                        f"Base64 Content:\n{doc_info.get('content', '')}"
                    )
                    if "url" in doc_info:
                        response_parts.append(
                            f"\n\nAlternatively, access via URL: {doc_info['url']}"
                        )
                else:
                    response_parts.append(f"URL: {doc_info.get('url', 'N/A')}")
                    if "content" in doc_info:
                        response_parts.append(
                            "\n(Set include_base64=true to get base64-encoded content)"
                        )

        else:
            # Multiple documents - list them with content
            response_parts.append(
                f"Found {len(matching_docs)} documents matching '{document_path}':\n"
            )

            for doc_path, doc_info in sorted(matching_docs.items()):
                doc_type = doc_info.get("type")
                response_parts.append(f"\n{'=' * 80}")
                response_parts.append(f"\nDocument: {doc_path}")
                response_parts.append(f"\nType: {doc_type}")
                response_parts.append(
                    f"\nSize: {doc_info.get('size', 0) / 1024:.1f} KB"
                )

                if doc_type == "text":
                    response_parts.append("\nContent:")
                    response_parts.append("-" * 80)
                    response_parts.append(f"\n{doc_info.get('content', '')}")

                elif doc_type == "image":
                    if doc_info.get("size_exceeded"):
                        response_parts.append("\n(Size exceeds limit)")
                        response_parts.append(f"\nURL: {doc_info.get('url', 'N/A')}")
                    elif include_base64:
                        response_parts.append(
                            f"\nBase64 Content: {doc_info.get('content', '')}"
                        )
                        if "url" in doc_info:
                            response_parts.append(f"\nURL: {doc_info['url']}")
                    else:
                        response_parts.append(f"\nURL: {doc_info.get('url', 'N/A')}")

                response_parts.append(f"\n{'=' * 80}")

        return [TextContent(type="text", text="\n".join(response_parts))]

    async def _handle_list_skills(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle list_skills tool calls.

        Parameters
        ----------
        arguments : dict[str, Any]
            Tool arguments (empty for list_skills).

        Returns
        -------
        list[TextContent]
            Complete list of all skills with metadata.
        """
        response_parts = []

        # Add loading status if skills are still being loaded
        status_msg = self.loading_state.get_status_message()
        if status_msg:
            response_parts.append(status_msg)

        if not self.search_engine.skills:
            if not self.loading_state.is_complete:
                return [
                    TextContent(
                        type="text",
                        text=status_msg
                        or "" + "No skills loaded yet. Please wait for skills to load.",
                    )
                ]
            return [TextContent(type="text", text="No skills currently loaded.")]

        response_parts.extend(
            [
                f"Total skills loaded: {len(self.search_engine.skills)}\n",
                "=" * 80,
                "\n",
            ]
        )

        for i, skill in enumerate(self.search_engine.skills, 1):
            # Format source as owner/repo for GitHub URLs
            import re

            source = skill.source
            if "github.com" in source:
                # Extract owner/repo from GitHub URL
                match = re.search(r"github\.com/([^/]+/[^/]+)", source)
                if match:
                    source = match.group(1)

            doc_count = len(skill.documents)

            response_parts.append(f"{i}. {skill.name}")
            response_parts.append(f"   Description: {skill.description}")
            response_parts.append(f"   Source: {source}")
            response_parts.append(f"   Documents: {doc_count} file(s)")
            response_parts.append("")

        return [TextContent(type="text", text="\n".join(response_parts))]

    async def run(self) -> None:
        """Run the MCP server using stdio transport."""
        logger.info("Starting MCP server with stdio transport")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )


# Standalone handler functions for HTTP server
async def handle_search_skills(
    arguments: dict[str, Any],
    search_engine,
    loading_state,
    default_top_k: int = 3,
    max_content_chars: int | None = None
) -> list[TextContent]:
    """Handle search_skills tool calls (standalone version for HTTP server)."""
    import fnmatch
    
    task_description = arguments.get("task_description")
    if not task_description:
        raise ValueError("task_description is required")

    top_k = arguments.get("top_k", default_top_k)
    list_documents = arguments.get("list_documents", True)

    response_parts = []

    # Add loading status if skills are still being loaded
    status_msg = loading_state.get_status_message() if loading_state else None
    if status_msg:
        response_parts.append(status_msg)

    # Perform search
    results = search_engine.search(task_description, top_k)

    if not results:
        if loading_state and not loading_state.is_complete and loading_state.loaded_skills == 0:
            return [
                TextContent(
                    type="text",
                    text=(status_msg or "") + "No skills loaded yet. Please wait for skills to load and try again.",
                )
            ]
        return [
            TextContent(
                type="text",
                text="No relevant skills found for the given task description.",
            )
        ]

    response_parts.append(
        f"Found {len(results)} relevant skill(s) for: '{task_description}'\n"
    )

    for i, result in enumerate(results, 1):
        response_parts.append(f"\n{'=' * 80}")
        response_parts.append(f"\nSkill {i}: {result['name']}")
        response_parts.append(f"\nRelevance Score: {result['relevance_score']:.4f}")
        response_parts.append(f"\nSource: {result['source']}")
        response_parts.append(f"\nDescription: {result['description']}")

        documents = result.get("documents", {})
        if documents:
            response_parts.append(
                f"\nAdditional Documents: {len(documents)} file(s)"
            )

            if list_documents:
                response_parts.append("\nAvailable Documents:")
                for doc_path in sorted(documents.keys()):
                    doc_info = documents[doc_path]
                    doc_type = doc_info.get("type", "unknown")
                    doc_size = doc_info.get("size", 0)
                    size_kb = doc_size / 1024
                    response_parts.append(
                        f"  - {doc_path} ({doc_type}, {size_kb:.1f} KB)"
                    )

        response_parts.append(f"\n{'-' * 80}")
        response_parts.append("\nFull Content:\n")

        content = result["content"]
        if max_content_chars is not None and len(content) > max_content_chars:
            truncated_content = content[:max_content_chars] + "..."
            response_parts.append(truncated_content)
            response_parts.append(
                f"\n\n[Content truncated at {max_content_chars} characters. "
                f"View full skill at: {result['source']}]"
            )
        else:
            response_parts.append(content)

        response_parts.append(f"\n{'=' * 80}\n")

    return [TextContent(type="text", text="\n".join(response_parts))]


async def handle_read_skill_document(arguments: dict[str, Any], search_engine) -> list[TextContent]:
    """Handle read_skill_document tool calls (standalone version for HTTP server)."""
    import fnmatch
    
    skill_name = arguments.get("skill_name")
    if not skill_name:
        raise ValueError("skill_name is required")

    document_path = arguments.get("document_path")
    include_base64 = arguments.get("include_base64", False)

    # Find the skill by name
    skill = None
    for s in search_engine.skills:
        if s.name == skill_name:
            skill = s
            break

    if not skill:
        return [
            TextContent(
                type="text",
                text=f"Skill '{skill_name}' not found. Please use search_skills to find valid skill names.",
            )
        ]

    # If no document_path provided, list all available documents
    if not document_path:
        if not skill.documents:
            return [
                TextContent(
                    type="text",
                    text=f"Skill '{skill_name}' has no additional documents.",
                )
            ]

        response_parts = [f"Available documents for skill '{skill_name}':\n"]
        for doc_path, doc_info in sorted(skill.documents.items()):
            doc_type = doc_info.get("type", "unknown")
            doc_size = doc_info.get("size", 0)
            size_kb = doc_size / 1024
            response_parts.append(f"  - {doc_path} ({doc_type}, {size_kb:.1f} KB)")

        return [TextContent(type="text", text="\n".join(response_parts))]

    # Match documents by pattern
    matching_docs = {}
    for doc_path, doc_info in skill.documents.items():
        if fnmatch.fnmatch(doc_path, document_path) or doc_path == document_path:
            matching_docs[doc_path] = doc_info

    if not matching_docs:
        return [
            TextContent(
                type="text",
                text=f"No documents matching '{document_path}' found in skill '{skill_name}'.",
            )
        ]

    # Lazy fetch
    for doc_path in matching_docs:
        doc_info = matching_docs[doc_path]
        if not doc_info.get("fetched") and "content" not in doc_info:
            content = skill.get_document(doc_path)
            if content:
                matching_docs[doc_path] = content

    # Format response
    response_parts = []

    if len(matching_docs) == 1:
        doc_path, doc_info = list(matching_docs.items())[0]
        doc_type = doc_info.get("type")

        if doc_type == "text":
            response_parts.append(f"Document: {doc_path}\n")
            response_parts.append("=" * 80)
            response_parts.append(f"\n{doc_info.get('content', '')}")

        elif doc_type == "image":
            response_parts.append(f"Image: {doc_path}\n")
            if doc_info.get("size_exceeded"):
                response_parts.append(
                    f"Size: {doc_info.get('size', 0) / 1024:.1f} KB (exceeds limit)"
                )
                response_parts.append(f"\nURL: {doc_info.get('url', 'N/A')}")
            elif include_base64:
                response_parts.append(
                    f"Base64 Content:\n{doc_info.get('content', '')}"
                )
                if "url" in doc_info:
                    response_parts.append(
                        f"\n\nAlternatively, access via URL: {doc_info['url']}"
                    )
            else:
                response_parts.append(f"URL: {doc_info.get('url', 'N/A')}")
                if "content" in doc_info:
                    response_parts.append(
                        "\n(Set include_base64=true to get base64-encoded content)"
                    )

    else:
        response_parts.append(
            f"Found {len(matching_docs)} documents matching '{document_path}':\n"
        )

        for doc_path, doc_info in sorted(matching_docs.items()):
            doc_type = doc_info.get("type")
            response_parts.append(f"\n{'=' * 80}")
            response_parts.append(f"\nDocument: {doc_path}")
            response_parts.append(f"\nType: {doc_type}")
            response_parts.append(
                f"\nSize: {doc_info.get('size', 0) / 1024:.1f} KB"
            )

            if doc_type == "text":
                response_parts.append("\nContent:")
                response_parts.append("-" * 80)
                response_parts.append(f"\n{doc_info.get('content', '')}")

            elif doc_type == "image":
                if doc_info.get("size_exceeded"):
                    response_parts.append("\n(Size exceeds limit)")
                    response_parts.append(f"\nURL: {doc_info.get('url', 'N/A')}")
                elif include_base64:
                    response_parts.append(
                        f"\nBase64 Content: {doc_info.get('content', '')}"
                    )
                    if "url" in doc_info:
                        response_parts.append(f"\nURL: {doc_info['url']}")
                else:
                    response_parts.append(f"\nURL: {doc_info.get('url', 'N/A')}")

            response_parts.append(f"\n{'=' * 80}")

    return [TextContent(type="text", text="\n".join(response_parts))]


async def handle_list_skills(arguments: dict[str, Any], search_engine, loading_state) -> list[TextContent]:
    """Handle list_skills tool calls (standalone version for HTTP server)."""
    import re
    
    response_parts = []

    # Add loading status if skills are still being loaded
    status_msg = loading_state.get_status_message() if loading_state else None
    if status_msg:
        response_parts.append(status_msg)

    if not search_engine.skills:
        if loading_state and not loading_state.is_complete:
            return [
                TextContent(
                    type="text",
                    text=(status_msg or "") + "No skills loaded yet. Please wait for skills to load.",
                )
            ]
        return [TextContent(type="text", text="No skills currently loaded.")]

    response_parts.extend(
        [
            f"Total skills loaded: {len(search_engine.skills)}\n",
            "=" * 80,
            "\n",
        ]
    )

    for i, skill in enumerate(search_engine.skills, 1):
        # Format source as owner/repo for GitHub URLs
        source = skill.source
        if "github.com" in source:
            # Extract owner/repo from GitHub URL
            match = re.search(r"github\.com/([^/]+/[^/]+)", source)
            if match:
                source = match.group(1)

        doc_count = len(skill.documents)

        response_parts.append(f"{i}. {skill.name}")
        response_parts.append(f"   Description: {skill.description}")
        response_parts.append(f"   Source: {source}")
        response_parts.append(f"   Documents: {doc_count} file(s)")
        response_parts.append("")

    return [TextContent(type="text", text="\n".join(response_parts))]
