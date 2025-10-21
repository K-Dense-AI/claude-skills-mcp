"""MCP server implementation for Claude Skills search."""

import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .search_engine import SkillSearchEngine

logger = logging.getLogger(__name__)


class SkillsMCPServer:
    """MCP Server for searching Claude Agent Skills.

    Attributes
    ----------
    search_engine : SkillSearchEngine
        The search engine instance.
    default_top_k : int
        Default number of results to return.
    """

    def __init__(self, search_engine: SkillSearchEngine, default_top_k: int = 3):
        """Initialize the MCP server.

        Parameters
        ----------
        search_engine : SkillSearchEngine
            Initialized search engine with indexed skills.
        default_top_k : int, optional
            Default number of results to return, by default 3.
        """
        self.search_engine = search_engine
        self.default_top_k = default_top_k
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
                    description=(
                        "Search for relevant Claude Agent Skills based on a task description. "
                        "Returns the most relevant skills with their full content, descriptions, "
                        "and relevance scores. Use this when you need to find skills that can "
                        "help accomplish a specific task or solve a particular problem."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_description": {
                                "type": "string",
                                "description": "Description of the task you want to accomplish",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": f"Number of skills to return (default: {self.default_top_k})",
                                "default": self.default_top_k,
                                "minimum": 1,
                                "maximum": 20,
                            },
                        },
                        "required": ["task_description"],
                    },
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            if name != "search_skills":
                raise ValueError(f"Unknown tool: {name}")

            task_description = arguments.get("task_description")
            if not task_description:
                raise ValueError("task_description is required")

            top_k = arguments.get("top_k", self.default_top_k)

            # Perform search
            results = self.search_engine.search(task_description, top_k)

            # Format results as text
            if not results:
                return [
                    TextContent(
                        type="text",
                        text="No relevant skills found for the given task description.",
                    )
                ]

            # Build formatted response
            response_parts = [
                f"Found {len(results)} relevant skill(s) for: '{task_description}'\n"
            ]

            for i, result in enumerate(results, 1):
                response_parts.append(f"\n{'=' * 80}")
                response_parts.append(f"\nSkill {i}: {result['name']}")
                response_parts.append(
                    f"\nRelevance Score: {result['relevance_score']:.4f}"
                )
                response_parts.append(f"\nSource: {result['source']}")
                response_parts.append(f"\nDescription: {result['description']}")
                response_parts.append(f"\n{'-' * 80}")
                response_parts.append("\nFull Content:\n")
                response_parts.append(result["content"])
                response_parts.append(f"\n{'=' * 80}\n")

            return [TextContent(type="text", text="\n".join(response_parts))]

    async def run(self) -> None:
        """Run the MCP server using stdio transport."""
        logger.info("Starting MCP server with stdio transport")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )
