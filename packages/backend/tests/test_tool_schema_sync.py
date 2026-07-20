"""Guard against drift between frontend hardcoded schemas and backend tools.

The frontend proxy hardcodes tool schemas (mcp_proxy.TOOL_SCHEMAS) so it can
answer list_tools instantly, with a comment saying they "must match backend
exactly". This test enforces that.
"""

import sys
from pathlib import Path

import pytest

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


@pytest.fixture
def frontend_schemas():
    """Import the frontend's hardcoded TOOL_SCHEMAS by path."""
    sys.path.insert(0, str(FRONTEND_SRC))
    try:
        from claude_skills_mcp.mcp_proxy import TOOL_SCHEMAS

        yield TOOL_SCHEMAS
    finally:
        sys.path.remove(str(FRONTEND_SRC))


@pytest.mark.asyncio
async def test_frontend_schemas_match_backend_tools(frontend_schemas):
    """Frontend TOOL_SCHEMAS and backend FastMCP tools must not drift."""
    from claude_skills_mcp_backend.http_server import mcp, register_mcp_tools

    backend_tools = {t.name: t for t in await mcp.list_tools()}
    if not backend_tools:
        register_mcp_tools()
        backend_tools = {t.name: t for t in await mcp.list_tools()}

    frontend_tools = {t.name: t for t in frontend_schemas}

    assert set(frontend_tools) == set(backend_tools), (
        f"Tool name drift: frontend={sorted(frontend_tools)} "
        f"backend={sorted(backend_tools)}"
    )

    for name, f_tool in frontend_tools.items():
        b_tool = backend_tools[name]

        assert f_tool.description == b_tool.description, (
            f"Description drift in '{name}':\n"
            f"frontend: {f_tool.description!r}\n"
            f"backend:  {b_tool.description!r}"
        )

        f_props = f_tool.inputSchema.get("properties", {})
        b_props = b_tool.inputSchema.get("properties", {})
        assert set(f_props) == set(b_props), (
            f"Parameter drift in '{name}': "
            f"frontend={sorted(f_props)} backend={sorted(b_props)}"
        )

        f_required = set(f_tool.inputSchema.get("required", []))
        b_required = set(b_tool.inputSchema.get("required", []))
        assert f_required == b_required, (
            f"Required-parameter drift in '{name}': "
            f"frontend={sorted(f_required)} backend={sorted(b_required)}"
        )

        # Defaults for optional parameters must agree where both declare them
        for prop, f_schema in f_props.items():
            b_schema = b_props[prop]
            if "default" in f_schema and "default" in b_schema:
                assert f_schema["default"] == b_schema["default"], (
                    f"Default drift in '{name}.{prop}': "
                    f"frontend={f_schema['default']!r} backend={b_schema['default']!r}"
                )
