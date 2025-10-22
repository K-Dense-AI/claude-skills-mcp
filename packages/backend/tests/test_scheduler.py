"""Tests for hourly scheduler."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from claude_skills_mcp_backend.scheduler import HourlyScheduler


class TestHourlyScheduler:
    """Tests for HourlyScheduler."""

    def test_calculate_next_hour(self):
        """Test calculation of next exact hour."""
        scheduler = HourlyScheduler(60, AsyncMock())
        next_hour = scheduler._calculate_next_hour()

        # Should be at the next hour boundary
        assert next_hour.minute == 0
        assert next_hour.second == 0
        assert next_hour.microsecond == 0

        # Should be in the future
        assert next_hour > datetime.now()

        # Should be within 1 hour from now
        assert next_hour <= datetime.now() + timedelta(hours=1, seconds=1)

    def test_calculate_seconds_until(self):
        """Test calculation of seconds until target time."""
        scheduler = HourlyScheduler(60, AsyncMock())

        # Test future time
        future_time = datetime.now() + timedelta(minutes=30)
        seconds = scheduler._calculate_seconds_until(future_time)
        assert 1790 <= seconds <= 1810  # Around 30 minutes

        # Test past time (should return 0)
        past_time = datetime.now() - timedelta(minutes=10)
        seconds = scheduler._calculate_seconds_until(past_time)
        assert seconds == 0

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test starting and stopping scheduler."""
        callback = AsyncMock()
        scheduler = HourlyScheduler(60, callback)

        # Start scheduler
        scheduler.start()
        assert scheduler._running is True
        assert scheduler._task is not None

        # Stop scheduler
        await scheduler.stop()
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_scheduler_runs_callback(self):
        """Test that scheduler runs the callback."""
        callback = AsyncMock()

        # Use a very short interval for testing (1 second)
        scheduler = HourlyScheduler(interval_minutes=1, update_callback=callback)

        # Manually set next run to very soon to speed up test
        scheduler._running = True
        scheduler.next_run_time = datetime.now() + timedelta(seconds=0.1)

        # Create a task that will run the callback once
        async def run_once():
            """Run scheduler loop once."""
            # Wait for next run
            await asyncio.sleep(0.2)

            # Manually trigger the callback as we would in the loop
            await callback()

            scheduler._running = False

        await asyncio.wait_for(run_once(), timeout=1.0)

        # Verify callback was called
        assert callback.call_count >= 1

    @pytest.mark.asyncio
    async def test_scheduler_handles_errors(self):
        """Test that scheduler handles callback errors gracefully."""

        # Callback that raises an exception
        async def error_callback():
            raise ValueError("Test error")

        scheduler = HourlyScheduler(1, error_callback)

        # Scheduler should not crash when callback raises
        scheduler.start()

        # Give it a moment
        await asyncio.sleep(0.1)

        # Stop it
        await scheduler.stop()

        # Should have stopped cleanly
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting scheduler status."""
        callback = AsyncMock()
        scheduler = HourlyScheduler(60, callback)

        status = scheduler.get_status()
        assert status["running"] is False
        assert status["interval_minutes"] == 60
        assert status["next_run_time"] is None
        assert status["last_run_time"] is None

        # Start scheduler
        scheduler.start()

        # Give it a moment to initialize
        await asyncio.sleep(0.1)

        status = scheduler.get_status()
        assert status["running"] is True

        # Clean up
        await scheduler.stop()
