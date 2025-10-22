"""Backend installation and process management."""

import asyncio
import logging
import subprocess
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class BackendManager:
    """Manages claude-skills-mcp-backend installation and lifecycle.

    Attributes
    ----------
    backend_port : int
        Port for the backend HTTP server.
    backend_host : str
        Host for the backend HTTP server.
    backend_process : asyncio.subprocess.Process | None
        Running backend process.
    backend_url : str | None
        Backend HTTP URL once started.
    """

    def __init__(self, port: int = 8765, host: str = "127.0.0.1"):
        """Initialize backend manager.

        Parameters
        ----------
        port : int, optional
            Backend port, by default 8765.
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
        logger.info(
            f"Starting backend server on {self.backend_host}:{self.backend_port}"
        )

        # Build command: uvx claude-skills-mcp-backend [args]
        cmd = ["uvx", "claude-skills-mcp-backend"] + backend_args

        logger.debug(f"Backend command: {' '.join(cmd)}")

        try:
            self.backend_process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Wait for backend to be ready
            logger.info("Waiting for backend to be ready...")
            self.backend_url = f"http://{self.backend_host}:{self.backend_port}/mcp"
            await self._wait_for_health(timeout=120)

            logger.info(f"Backend ready at {self.backend_url}")
            return self.backend_url

        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            raise RuntimeError(f"Failed to start backend server: {e}")

    async def _wait_for_health(self, timeout: int = 120) -> None:
        """Wait for backend health check to pass.

        Parameters
        ----------
        timeout : int, optional
            Maximum time to wait in seconds, by default 120.

        Raises
        ------
        TimeoutError
            If backend doesn't become healthy within timeout.
        """
        health_url = f"http://{self.backend_host}:{self.backend_port}/health"
        start_time = asyncio.get_event_loop().time()

        last_error = None
        while True:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        logger.info("Backend health check passed")
                        return
                    last_error = f"Status {response.status_code}"
            except Exception as e:
                last_error = str(e)

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
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

        uvx handles downloading and installing the backend automatically
        in its own isolated environment. No need for manual installation!

        Parameters
        ----------
        backend_args : list[str]
            CLI arguments to forward to backend.

        Returns
        -------
        str
            Backend URL.
        """
        logger.info("Starting backend via uvx (auto-downloads if needed)...")

        # uvx handles everything - no manual installation needed!
        return await self.start_backend(backend_args)

    def cleanup(self) -> None:
        """Cleanup backend process."""
        if self.backend_process:
            try:
                self.backend_process.terminate()
                logger.info("Backend process terminated")
            except Exception as e:
                logger.warning(f"Failed to terminate backend: {e}")
