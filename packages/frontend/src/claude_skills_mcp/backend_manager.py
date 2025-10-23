"""Backend installation and process management."""

import asyncio
import logging
import os
import signal
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

        # Build shell command with unbuffered output
        args_str = " ".join(backend_args)
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
        """Wait for backend health check to pass AND skills to be loaded.

        Parameters
        ----------
        timeout : int, optional
            Maximum time to wait in seconds, by default 300 (5 minutes).

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
                        # Check if skills are loaded
                        health_data = response.json()
                        skills_loaded = health_data.get("skills_loaded", 0)
                        loading_complete = health_data.get("loading_complete", False)
                        
                        if loading_complete and skills_loaded > 0:
                            logger.info(f"Backend health check passed ({skills_loaded} skills loaded)")
                            return
                        elif loading_complete and skills_loaded == 0:
                            # Still no skills after loading complete - might be config issue
                            last_error = "Backend loaded but no skills found (check config/network)"
                        else:
                            # Show progress
                            last_error = f"Loading: {skills_loaded} skills so far..."
                            if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                                logger.info(f"Still loading skills... ({skills_loaded} loaded so far)")

                    else:
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

        Checks if backend is already running on the port. If yes and healthy,
        reuses it. Otherwise spawns a new one. This prevents port conflicts
        when Cursor spawns multiple MCP instances.

        Parameters
        ----------
        backend_args : list[str]
            CLI arguments to forward to backend.

        Returns
        -------
        str
            Backend URL.
        """
        backend_url = f"http://{self.backend_host}:{self.backend_port}/mcp"
        health_url = f"http://{self.backend_host}:{self.backend_port}/health"
        
        # Check if backend is already running
        logger.info("Checking if backend is already running...")
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    health_data = response.json()
                    skills_loaded = health_data.get("skills_loaded", 0)
                    logger.info(
                        f"Backend already running on port {self.backend_port} "
                        f"with {skills_loaded} skills - reusing it"
                    )
                    self.backend_url = backend_url
                    return backend_url
        except Exception:
            # Backend not running, we'll start it
            logger.info("No backend found, starting new instance...")
            pass

        # Start new backend
        logger.info("Starting backend via uvx (auto-downloads if needed)...")
        return await self.start_backend(backend_args)

    async def cleanup(self) -> None:
        """Cleanup backend process and all child processes."""
        if self.backend_process:
            try:
                # For shell=True, we need to kill the entire process group
                # Send SIGTERM to the process group to kill backend + uvx + python
                logger.info(f"Terminating backend process group (PID: {self.backend_process.pid})")
                
                try:
                    # Kill the whole process group (negative PID)
                    os.killpg(os.getpgid(self.backend_process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    # Process already dead
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
