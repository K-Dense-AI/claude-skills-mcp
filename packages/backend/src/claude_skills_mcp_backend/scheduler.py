"""Hourly scheduler for automatic skill updates."""

import asyncio
import logging
from collections.abc import Callable, Awaitable
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class HourlyScheduler:
    """Scheduler that runs tasks on exact clockface hours.

    Attributes
    ----------
    interval_minutes : int
        Interval between checks in minutes.
    update_callback : Callable[[], Awaitable[None]]
        Async callback to execute on each scheduled run.
    _task : asyncio.Task | None
        Background task running the scheduler.
    _running : bool
        Whether the scheduler is running.
    next_run_time : datetime | None
        Next scheduled run time.
    last_run_time : datetime | None
        Last run time.
    """

    def __init__(
        self,
        interval_minutes: int,
        update_callback: Callable[[], Awaitable[None]],
    ):
        """Initialize hourly scheduler.

        Parameters
        ----------
        interval_minutes : int
            Interval between checks in minutes (typically 60 for hourly).
        update_callback : Callable[[], Awaitable[None]]
            Async callback to execute on schedule.
        """
        self.interval_minutes = interval_minutes
        self.update_callback = update_callback
        self._task: asyncio.Task | None = None
        self._running = False
        self.next_run_time: datetime | None = None
        self.last_run_time: datetime | None = None

    def _calculate_next_hour(self) -> datetime:
        """Calculate the next exact clockface hour.

        Returns
        -------
        datetime
            Next hour boundary (:00:00).
        """
        now = datetime.now()
        # Round up to next hour
        next_hour = (now + timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
        return next_hour

    def _calculate_seconds_until(self, target_time: datetime) -> float:
        """Calculate seconds until target time.

        Parameters
        ----------
        target_time : datetime
            Target datetime.

        Returns
        -------
        float
            Seconds until target (minimum 0).
        """
        now = datetime.now()
        delta = (target_time - now).total_seconds()
        return max(0, delta)

    async def _schedule_loop(self) -> None:
        """Main scheduling loop."""
        logger.info("Hourly scheduler started")

        # Calculate time until next exact hour for first run
        self.next_run_time = self._calculate_next_hour()
        seconds_until_first = self._calculate_seconds_until(self.next_run_time)

        logger.info(
            f"First update check scheduled at {self.next_run_time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(in {seconds_until_first / 60:.1f} minutes)"
        )

        # Wait until first exact hour
        await asyncio.sleep(seconds_until_first)

        # Main loop
        while self._running:
            try:
                # Run the update check
                logger.info(
                    f"Running scheduled update check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                self.last_run_time = datetime.now()

                await self.update_callback()

                # Calculate next run time
                self.next_run_time = datetime.now() + timedelta(
                    minutes=self.interval_minutes
                )
                # Align to exact hour if interval is 60 minutes
                if self.interval_minutes == 60:
                    self.next_run_time = self.next_run_time.replace(
                        minute=0, second=0, microsecond=0
                    )

                seconds_until_next = self._calculate_seconds_until(self.next_run_time)

                logger.info(
                    f"Next update check scheduled at {self.next_run_time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(in {seconds_until_next / 60:.1f} minutes)"
                )

                # Wait for next interval
                await asyncio.sleep(seconds_until_next)

            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Wait a bit before retrying to avoid tight error loops
                await asyncio.sleep(60)

        logger.info("Hourly scheduler stopped")

    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._schedule_loop())
        logger.info("Scheduler task created")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            return

        logger.info("Stopping scheduler...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Scheduler stopped")

    def get_status(self) -> dict[str, Any]:
        """Get scheduler status.

        Returns
        -------
        dict[str, Any]
            Status information.
        """
        return {
            "running": self._running,
            "interval_minutes": self.interval_minutes,
            "next_run_time": self.next_run_time.isoformat()
            if self.next_run_time
            else None,
            "last_run_time": self.last_run_time.isoformat()
            if self.last_run_time
            else None,
        }
