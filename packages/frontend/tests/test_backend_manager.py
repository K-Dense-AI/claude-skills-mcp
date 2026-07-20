"""Tests for backend process management."""

import socket

import pytest

from claude_skills_mcp.backend_manager import BackendManager


def test_default_port_is_auto():
    """By default no port is pinned; one is auto-selected at spawn."""
    manager = BackendManager()
    assert manager.backend_port is None


def test_explicit_port_is_kept():
    """A pinned port is used as-is."""
    manager = BackendManager(port=9123)
    assert manager.backend_port == 9123


def test_find_free_port_returns_bindable_port():
    """The auto-selected port can actually be bound."""
    manager = BackendManager()
    port = manager._find_free_port()

    assert 1024 <= port <= 65535
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_kill_backend_process_without_process_is_noop():
    """Emergency cleanup must be safe when no backend was spawned."""
    manager = BackendManager()
    manager.kill_backend_process()  # Must not raise


@pytest.mark.asyncio
async def test_start_backend_resolves_port_and_passes_args(monkeypatch):
    """start_backend picks a free port and passes host/port to the backend."""
    manager = BackendManager()
    captured = {}

    class FakeProcess:
        pid = 99999
        stdout = None
        stderr = None

    async def fake_subprocess_shell(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeProcess()

    async def fake_wait_for_health(timeout=300):
        return None

    def fake_consume(stream, prefix):
        async def noop():
            return None

        return noop()

    monkeypatch.setattr(
        "asyncio.create_subprocess_shell", fake_subprocess_shell
    )
    monkeypatch.setattr(manager, "_wait_for_health", fake_wait_for_health)
    monkeypatch.setattr(manager, "_consume_stream", fake_consume)

    url = await manager.start_backend(["--verbose"])

    assert manager.backend_port is not None
    assert f"--port {manager.backend_port}" in captured["cmd"]
    assert "--host 127.0.0.1" in captured["cmd"]
    assert "--verbose" in captured["cmd"]
    assert url == f"http://127.0.0.1:{manager.backend_port}/mcp"


def _fake_client_class(response_factory):
    """Build a fake httpx.AsyncClient whose get() uses response_factory."""

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            return response_factory()

    return FakeClient


@pytest.mark.asyncio
async def test_wait_for_health_returns_while_still_loading(monkeypatch):
    """The proxy connects as soon as the backend is up, before skills finish
    loading - tool calls report loading progress from the backend itself."""
    manager = BackendManager(port=9124)

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"skills_loaded": 5, "loading_complete": False}

    monkeypatch.setattr("httpx.AsyncClient", _fake_client_class(FakeResponse))

    await manager._wait_for_health(timeout=5)  # Must not raise or block


@pytest.mark.asyncio
async def test_wait_for_health_times_out_with_last_error(monkeypatch):
    """When the backend never comes up, the timeout error carries the cause.

    Also a regression test for 'elapsed' being referenced before assignment
    inside the loop (previously swallowed by the broad except).
    """
    manager = BackendManager(port=9124)

    def raise_connect_error():
        raise ConnectionError("connection refused by test")

    monkeypatch.setattr(
        "httpx.AsyncClient", _fake_client_class(raise_connect_error)
    )

    with pytest.raises(TimeoutError) as exc_info:
        await manager._wait_for_health(timeout=0)

    assert "connection refused by test" in str(exc_info.value)
    assert "elapsed" not in str(exc_info.value)
