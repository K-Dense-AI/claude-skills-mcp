"""Backend installation and process management."""

import asyncio
import logging
import os
import signal
import socket
import subprocess
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class BackendManager:
    """Manages claude-skills-mcp-backend installation and lifecycle.

    Attributes
    ----------
    backend_port : int | None
        Port for the backend HTTP server. None until a free port is
        auto-selected at startup (or a port was pinned explicitly).
    backend_host : str
        Host for the backend HTTP server.
    backend_process : asyncio.subprocess.Process | None
        Running backend process.
    backend_url : str | None
        Backend HTTP URL once started.
    """

    def __init__(self, port: Optional[int] = None, host: str = "127.0.0.1"):
        """Initialize backend manager.

        Parameters
        ----------
        port : int | None, optional
            Backend port. None (default) auto-selects a free port when the
            backend starts, so multiple frontends can run side by side
            without fighting over a fixed port.
        host : str, optional
            Backend host, by default "127.0.0.1".
        """
        self.backend_port = port
        self.backend_host = host
        self.backend_process: Optional[asyncio.subprocess.Process] = None
        self.backend_url: Optional[str] = None

    def check_backend_available(self) -> bool:
        """Check if backend package is available via uvx.

        Returns
        -------
        bool
            True if backend can be run via uvx, False otherwise.
        """
        try:
            # Check if uvx can find the backend package
            result = subprocess.run(["uvx", "--help"], capture_output=True, timeout=5)
            # If uvx exists, backend will auto-download on first use
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"uvx check failed: {e}")
            return False

    async def start_backend(self, backend_args: list[str]) -> str:
        """Start the backend server process via uvx.

        Parameters
        ----------
        backend_args : list[str]
            CLI arguments to pass to the backend.

        Returns
        -------
        str
            Backend URL (http://host:port/mcp).
        """
        if self.backend_port is None:
            self.backend_port = self._find_free_port()

        logger.info(
            f"Starting backend server on {self.backend_host}:{self.backend_port}"
        )

        # Build shell command with unbuffered output
        # Host/port are always passed explicitly so the health check below
        # polls the same address the backend actually binds
        args_str = " ".join(
            ["--host", self.backend_host, "--port", str(self.backend_port)]
            + backend_args
        )
        cmd = f"PYTHONUNBUFFERED=1 uvx claude-skills-mcp-backend {args_str}"

        logger.debug(f"Backend command: {cmd}")

        try:
            # Use shell for simple reliable execution
            # start_new_session=True ensures process group for proper cleanup
            self.backend_process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )

            # Start background tasks to consume backend output streams
            # This prevents broken pipe errors from pipes filling up
            logger.info("Starting stream consumers for backend stdout/stderr")
            asyncio.create_task(self._consume_stream(self.backend_process.stdout, "backend-stdout"))
            asyncio.create_task(self._consume_stream(self.backend_process.stderr, "backend-stderr"))

            # Wait for backend to be ready
            # Allow extra time for slow connections to download models + skills
            logger.info("Waiting for backend to be ready...")
            self.backend_url = f"http://{self.backend_host}:{self.backend_port}/mcp"
            await self._wait_for_health(timeout=300)  # 5 minutes for slow connections

            logger.info(f"Backend ready at {self.backend_url}")
            return self.backend_url

        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            raise RuntimeError(f"Failed to start backend server: {e}")

    def _find_free_port(self) -> int:
        """Ask the OS for a free port on the backend host.

        Returns
        -------
        int
            An available port number.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.backend_host, 0))
            return sock.getsockname()[1]

    async def _consume_stream(
        self, stream: asyncio.StreamReader, prefix: str
    ) -> None:
        """Consume a stream and relay lines to logger.

        This prevents broken pipe errors by continuously reading from the stream.

        Parameters
        ----------
        stream : asyncio.StreamReader
            Stream to consume.
        prefix : str
            Prefix for log messages.
        """
        logger.info(f"Stream consumer started for {prefix}")
        line_count = 0
        try:
            while True:
                line = await stream.readline()
                if not line:
                    logger.info(f"Stream {prefix} closed after {line_count} lines")
                    break
                # Relay backend logs to frontend logger (visible in Cursor)
                decoded = line.decode("utf-8").rstrip()
                if decoded:
                    line_count += 1
                    logger.info(f"[{prefix}] {decoded}")
        except Exception as e:
            logger.error(f"Stream consumer {prefix} error after {line_count} lines: {e}")

    async def _wait_for_health(self, timeout: int = 300) -> None:
        """Wait for the backend HTTP server to come up.

        Returns as soon as /health responds 200 - skill loading continues in
        the background and the backend's tool handlers report loading
        progress to callers until it completes.

        Parameters
        ----------
        timeout : int, optional
            Maximum time to wait in seconds, by default 300 (5 minutes,
            covers the one-time backend package download on first run).

        Raises
        ------
        TimeoutError
            If backend doesn't become healthy within timeout.
        """
        health_url = f"http://{self.backend_host}:{self.backend_port}/health"
        start_time = asyncio.get_event_loop().time()

        last_error = None
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        health_data = response.json()
                        skills_loaded = health_data.get("skills_loaded", 0)
                        logger.info(
                            f"Backend is up ({skills_loaded} skills loaded so far, "
                            "loading continues in background)"
                        )
                        return
                    last_error = f"Status {response.status_code}"
            except Exception as e:
                last_error = str(e)

            # Check timeout
            if elapsed > timeout:
                raise TimeoutError(
                    f"Backend failed to start within {timeout}s. Last error: {last_error}"
                )

            # Show progress
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                logger.info(f"Waiting for backend... ({int(elapsed)}s elapsed)")

            await asyncio.sleep(1)

    async def ensure_backend_running(self, backend_args: list[str]) -> str:
        """Ensure backend is running via uvx.

        Spawns a fresh backend on this manager's port (auto-selected when not
        pinned), so it never touches processes owned by other sessions.

        Parameters
        ----------
        backend_args : list[str]
            CLI arguments to forward to backend.

        Returns
        -------
        str
            Backend URL.
        """
        logger.info("Starting fresh backend via uvx (auto-downloads if needed)...")
        return await self.start_backend(backend_args)

    def kill_backend_process(self) -> None:
        """Synchronously kill the spawned backend process group, if any.

        Safe to call from atexit handlers. Only targets the process this
        manager spawned — never other processes that happen to share a port.
        """
        if self.backend_process is None:
            return
        try:
            os.killpg(os.getpgid(self.backend_process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    async def cleanup(self) -> None:
        """Cleanup backend process and all child processes."""
        if self.backend_process:
            # Kill backend process group
            try:
                logger.info(f"Terminating backend process group (PID: {self.backend_process.pid})")
                
                try:
                    # Kill the whole process group (negative PID)
                    os.killpg(os.getpgid(self.backend_process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
                
                # Wait for process to terminate (with timeout)
                try:
                    await asyncio.wait_for(self.backend_process.wait(), timeout=5.0)
                    logger.info("Backend process terminated gracefully")
                except asyncio.TimeoutError:
                    # Force kill if it doesn't exit
                    logger.warning("Backend didn't exit gracefully, force killing")
                    try:
                        os.killpg(os.getpgid(self.backend_process.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    
            except Exception as e:
                logger.warning(f"Error during backend cleanup: {e}")
