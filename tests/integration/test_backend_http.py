"""Integration test for backend HTTP server."""

import asyncio
import httpx
import pytest


@pytest.mark.asyncio
async def test_backend_http_server_health():
    """Test that backend HTTP server starts and responds to health checks."""
    from claude_skills_mcp_backend.http_server import run_server

    # Start server in background
    server_task = asyncio.create_task(
        run_server(host="127.0.0.1", port=9876, config_path=None, verbose=False)
    )

    # Give it time to start
    await asyncio.sleep(3)

    try:
        # Test health endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:9876/health", timeout=5.0)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "version" in data
            print(f"\n✓ Backend health check passed: {data}")
    finally:
        # Cleanup
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
