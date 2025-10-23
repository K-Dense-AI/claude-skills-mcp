"""Timing tests to verify Cursor timeout requirements are met."""

import subprocess
import time
import pytest


def test_frontend_cold_start_under_cursor_timeout():
    """CRITICAL: Frontend must start under Cursor's ~60s timeout."""
    # Clear cache to simulate first-time user
    subprocess.run(["uv", "cache", "clean", "claude-skills-mcp"], capture_output=True)

    print("\nTesting frontend cold start (cache cleared)...")
    start_time = time.time()

    result = subprocess.run(
        ["uvx", "claude-skills-mcp", "--help"],
        capture_output=True,
        text=True,
        timeout=60,  # Cursor's timeout
    )

    elapsed = time.time() - start_time

    print(f"Frontend startup time: {elapsed:.2f}s")
    print("Cursor timeout limit: 60s")
    print(f"Margin: {60 - elapsed:.2f}s")

    assert result.returncode == 0, f"Frontend failed: {result.stderr}"
    assert elapsed < 60, (
        f"Frontend startup ({elapsed:.2f}s) exceeds Cursor timeout (60s)"
    )
    assert elapsed < 10, (
        f"Frontend startup ({elapsed:.2f}s) should be < 10s for good UX"
    )

    print(f"✅ PASS: Frontend starts in {elapsed:.2f}s (well under 60s limit)")


def test_frontend_warm_start_very_fast():
    """Frontend warm start should be very fast (<5s)."""
    # Run once to ensure cached
    subprocess.run(
        ["uvx", "claude-skills-mcp", "--help"], capture_output=True, timeout=30
    )

    # Now test warm start
    print("\nTesting frontend warm start (cached)...")
    start_time = time.time()

    result = subprocess.run(
        ["uvx", "claude-skills-mcp", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    elapsed = time.time() - start_time

    print(f"Frontend warm startup time: {elapsed:.2f}s")

    assert result.returncode == 0
    assert elapsed < 5, f"Frontend warm start ({elapsed:.2f}s) should be < 5s"

    print(f"✅ PASS: Frontend warm start is {elapsed:.2f}s")


def test_backend_cold_start_time():
    """Measure backend download time (happens in background, doesn't block Cursor)."""
    # Clear backend cache
    subprocess.run(
        ["uv", "cache", "clean", "claude-skills-mcp-backend"], capture_output=True
    )

    print("\nTesting backend cold start (cache cleared)...")
    print("Note: This happens in BACKGROUND, doesn't block Cursor startup")

    start_time = time.time()

    result = subprocess.run(
        ["uvx", "claude-skills-mcp-backend", "--help"],
        capture_output=True,
        text=True,
        timeout=180,  # Give plenty of time for download
    )

    elapsed = time.time() - start_time

    print(f"Backend download + start time: {elapsed:.2f}s")

    assert result.returncode == 0, f"Backend failed: {result.stderr}"

    # Backend can be slow - it downloads in background
    print(
        f"✅ Backend downloads in {elapsed:.2f}s (in background, doesn't affect Cursor)"
    )


def test_backend_warm_start():
    """Backend warm start should be faster."""
    # Ensure cached
    subprocess.run(
        ["uvx", "claude-skills-mcp-backend", "--help"], capture_output=True, timeout=60
    )

    print("\nTesting backend warm start (cached)...")
    start_time = time.time()

    result = subprocess.run(
        ["uvx", "claude-skills-mcp-backend", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    elapsed = time.time() - start_time

    print(f"Backend warm startup time: {elapsed:.2f}s")

    assert result.returncode == 0
    assert elapsed < 20, f"Backend warm start ({elapsed:.2f}s) should be reasonable"

    print(f"✅ PASS: Backend warm start is {elapsed:.2f}s")


def test_package_sizes():
    """Verify package sizes are as expected."""
    import os

    # Check frontend wheel size
    frontend_wheel = "packages/frontend/dist/claude_skills_mcp-1.0.3-py3-none-any.whl"
    if os.path.exists(frontend_wheel):
        size_kb = os.path.getsize(frontend_wheel) / 1024
        print(f"\nFrontend wheel size: {size_kb:.1f} KB")
        assert size_kb < 50, f"Frontend wheel ({size_kb:.1f} KB) should be < 50 KB"
        print(f"✅ Frontend is lightweight: {size_kb:.1f} KB")

    # Check backend wheel size
    backend_wheel = (
        "packages/backend/dist/claude_skills_mcp_backend-1.0.3-py3-none-any.whl"
    )
    if os.path.exists(backend_wheel):
        size_kb = os.path.getsize(backend_wheel) / 1024
        print(
            f"Backend wheel size: {size_kb:.1f} KB (source only, dependencies separate)"
        )
        assert size_kb < 100, f"Backend wheel ({size_kb:.1f} KB) should be < 100 KB"
        print(f"✅ Backend source is {size_kb:.1f} KB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
