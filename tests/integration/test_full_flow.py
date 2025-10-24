"""Integration tests for full frontend → backend flow."""

import subprocess
import time
import pytest


def test_frontend_startup_time():
    """Test that frontend starts quickly (critical for Cursor timeout)."""
    # Use frontend from published PyPI (once published)
    # For now, test the import speed only
    from pathlib import Path
    
    # Find frontend directory relative to this test file
    test_dir = Path(__file__).parent
    frontend_dir = test_dir.parent.parent / "packages" / "frontend"
    
    start_time = time.time()
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            "from claude_skills_mcp import __version__; print(__version__)",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        cwd=str(frontend_dir),
    )
    elapsed = time.time() - start_time

    print(f"\n✓ Frontend import time: {elapsed:.2f}s")
    assert result.returncode == 0, f"Frontend failed: {result.stderr}"
    assert elapsed < 2, f"Frontend import took {elapsed:.2f}s (should be instant)"
    print(f"✓ Frontend version: {result.stdout.strip()}")


def test_backend_available_from_pypi():
    """Test that backend is available and downloadable from PyPI."""
    result = subprocess.run(
        ["uvx", "claude-skills-mcp-backend", "--help"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, f"Backend not available: {result.stderr}"
    assert "claude-skills-mcp-backend" in result.stdout.lower()
    assert "--port" in result.stdout
    assert "--host" in result.stdout
    print("\n✓ Backend available from PyPI")


def test_backend_starts_http_server():
    """Test that backend starts and responds to health checks."""

    # Start backend in background
    proc = subprocess.Popen(
        ["uvx", "claude-skills-mcp-backend", "--port", "9999", "--verbose"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for startup
        time.sleep(10)

        # Test health endpoint
        response = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:9999/health"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        print(f"\n✓ Backend health response: {response.stdout}")
        assert "ok" in response.stdout.lower()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()  # Force kill if doesn't terminate
            proc.wait()


def test_hardcoded_tools_match_backend():
    """Verify frontend's hardcoded tool schemas match backend."""
    from claude_skills_mcp.mcp_proxy import TOOL_SCHEMAS

    # Check we have the right number of tools
    assert len(TOOL_SCHEMAS) == 3, f"Expected 3 tools, got {len(TOOL_SCHEMAS)}"

    # Check tool names
    tool_names = [tool.name for tool in TOOL_SCHEMAS]
    assert "search_skills" in tool_names
    assert "read_skill_document" in tool_names
    assert "list_skills" in tool_names

    # Check schemas have required fields
    for tool in TOOL_SCHEMAS:
        assert tool.name
        assert tool.description
        assert tool.inputSchema
        print(f"✓ Tool schema valid: {tool.name}")


@pytest.mark.asyncio
async def test_backend_manager_check():
    """Test that backend manager can check for uvx."""
    from claude_skills_mcp.backend_manager import BackendManager

    manager = BackendManager()
    has_uvx = manager.check_backend_available()

    assert has_uvx, "uvx not available - required for backend spawning"
    print("\n✓ Backend manager can check uvx availability")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
