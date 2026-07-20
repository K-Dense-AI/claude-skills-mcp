"""Tests for the MCP proxy."""

import pytest

from claude_skills_mcp.mcp_proxy import MCPProxy


@pytest.mark.asyncio
async def test_remote_url_skips_local_backend(monkeypatch):
    """With remote_url set, no local backend is spawned - the proxy connects
    directly to the given URL."""
    proxy = MCPProxy(backend_args=[], remote_url="https://example.com/mcp")
    connected = []

    async def fake_connect(url):
        connected.append(url)

    monkeypatch.setattr(proxy, "_connect_to_backend", fake_connect)

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("local backend must not be spawned in remote mode")

    monkeypatch.setattr(
        proxy.backend_manager, "ensure_backend_running", fail_if_called
    )

    await proxy._start_backend_async()

    assert connected == ["https://example.com/mcp"]
    assert proxy.backend_ready is True
    assert proxy.backend_manager.backend_process is None


@pytest.mark.asyncio
async def test_connect_with_retry_recovers_from_transient_failure(monkeypatch):
    """Transient connection failures are retried before giving up."""
    proxy = MCPProxy(backend_args=[], remote_url="https://example.com/mcp")
    attempts = []

    async def flaky_connect(url):
        attempts.append(url)
        if len(attempts) < 3:
            raise ConnectionError("transient")

    monkeypatch.setattr(proxy, "_connect_to_backend", flaky_connect)

    await proxy._connect_with_retry("https://example.com/mcp", attempts=3, delay=0)

    assert len(attempts) == 3


@pytest.mark.asyncio
async def test_connect_with_retry_raises_after_exhaustion(monkeypatch):
    """The last error propagates when all attempts fail."""
    proxy = MCPProxy(backend_args=[], remote_url="https://example.com/mcp")

    async def always_fail(url):
        raise ConnectionError("permanent")

    monkeypatch.setattr(proxy, "_connect_to_backend", always_fail)

    with pytest.raises(ConnectionError, match="permanent"):
        await proxy._connect_with_retry("https://example.com/mcp", attempts=2, delay=0)
