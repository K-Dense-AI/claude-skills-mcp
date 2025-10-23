#!/usr/bin/env python3
"""Sync version from VERSION file to all package files.

This script reads the version from the root VERSION file and updates
all version references across the monorepo including:
- pyproject.toml files
- __init__.py files
- Runtime code (http_server.py)
- Test files
- Documentation

Usage:
    python scripts/sync-version.py [--check]

Arguments:
    --check: Only check if versions are synced, don't modify files
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def read_version() -> str:
    """Read version from VERSION file.

    Returns
    -------
    str
        Version string (e.g., "1.0.1")
    """
    version_file = Path(__file__).parent.parent / "VERSION"
    return version_file.read_text().strip()


def update_file(
    file_path: Path, pattern: str, replacement: str, check_only: bool = False
) -> Tuple[bool, int]:
    """Update version in a file using regex pattern.

    Parameters
    ----------
    file_path : Path
        Path to file to update
    pattern : str
        Regex pattern to match (should have one capture group for version)
    replacement : str
        Replacement string (use {version} placeholder)
    check_only : bool, optional
        If True, only check if update needed without modifying, by default False

    Returns
    -------
    Tuple[bool, int]
        (changed, num_replacements) - whether file would change and how many replacements
    """
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return False, 0

    content = file_path.read_text()
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)

    if count == 0:
        print(f"⚠️  Pattern not found in {file_path}")
        return False, 0

    changed = content != new_content

    if changed and not check_only:
        file_path.write_text(new_content)

    return changed, count


def sync_versions(check_only: bool = False) -> bool:
    """Sync all version references to VERSION file.

    Parameters
    ----------
    check_only : bool, optional
        If True, only check without modifying files, by default False

    Returns
    -------
    bool
        True if all versions are synced (or were successfully synced), False otherwise
    """
    version = read_version()
    print(f"📌 Version from VERSION file: {version}")
    print()

    repo_root = Path(__file__).parent.parent
    updates: List[Tuple[str, Path, str, str]] = [
        # (description, file_path, pattern, replacement)
        (
            "Backend pyproject.toml",
            repo_root / "packages/backend/pyproject.toml",
            r'^version = "[^"]+"',
            f'version = "{version}"',
        ),
        (
            "Frontend pyproject.toml",
            repo_root / "packages/frontend/pyproject.toml",
            r'^version = "[^"]+"',
            f'version = "{version}"',
        ),
        (
            "Backend __init__.py",
            repo_root / "packages/backend/src/claude_skills_mcp_backend/__init__.py",
            r'^__version__ = "[^"]+"',
            f'__version__ = "{version}"',
        ),
        (
            "Frontend __init__.py",
            repo_root / "packages/frontend/src/claude_skills_mcp/__init__.py",
            r'^__version__ = "[^"]+"',
            f'__version__ = "{version}"',
        ),
        (
            "HTTP server health endpoint",
            repo_root / "packages/backend/src/claude_skills_mcp_backend/http_server.py",
            r'"version": "[^"]+"',
            f'"version": "{version}"',
        ),
        (
            "Integration test (frontend wheel)",
            repo_root / "tests/integration/test_timing.py",
            r'frontend_wheel = "packages/frontend/dist/claude_skills_mcp-[0-9]+\.[0-9]+\.[0-9]+-py3-none-any\.whl"',
            f'frontend_wheel = "packages/frontend/dist/claude_skills_mcp-{version}-py3-none-any.whl"',
        ),
        (
            "Integration test (backend wheel)",
            repo_root / "tests/integration/test_timing.py",
            r'"packages/backend/dist/claude_skills_mcp_backend-[0-9]+\.[0-9]+\.[0-9]+-py3-none-any\.whl"',
            f'"packages/backend/dist/claude_skills_mcp_backend-{version}-py3-none-any.whl"',
        ),
        (
            "GitHub workflow (backend wheel)",
            repo_root / ".github/workflows/test.yml",
            r'claude_skills_mcp_backend-[0-9]+\.[0-9]+\.[0-9]+-py3-none-any\.whl',
            f'claude_skills_mcp_backend-{version}-py3-none-any.whl',
        ),
        (
            "GitHub workflow (frontend wheel)",
            repo_root / ".github/workflows/test.yml",
            r'claude_skills_mcp-[0-9]+\.[0-9]+\.[0-9]+-py3-none-any\.whl',
            f'claude_skills_mcp-{version}-py3-none-any.whl',
        ),
    ]

    all_synced = True
    changes_made = []

    for description, file_path, pattern, replacement in updates:
        changed, count = update_file(file_path, pattern, replacement, check_only)

        if changed:
            all_synced = False
            status = "❌ OUT OF SYNC" if check_only else "✅ UPDATED"
            changes_made.append(description)
        else:
            status = "✓ OK"

        print(f"{status:20} {description} ({count} replacement{'s' if count != 1 else ''})")

    print()

    if check_only:
        if all_synced:
            print("✅ All versions are synced!")
            return True
        else:
            print("❌ Some versions are out of sync:")
            for change in changes_made:
                print(f"   - {change}")
            print()
            print("Run 'python scripts/sync-version.py' to sync all versions.")
            return False
    else:
        if changes_made:
            print(f"✅ Updated {len(changes_made)} file(s) to version {version}")
        else:
            print(f"✅ All versions already at {version}")
        return True


def update_lock_files(check_only: bool = False) -> bool:
    """Update uv.lock files by running uv lock in each package.

    Parameters
    ----------
    check_only : bool, optional
        If True, only check if lock files need updating, by default False

    Returns
    -------
    bool
        True if successful or no update needed, False otherwise
    """
    repo_root = Path(__file__).parent.parent
    packages = [
        ("Backend", repo_root / "packages/backend"),
        ("Frontend", repo_root / "packages/frontend"),
    ]

    if check_only:
        # Just check if lock files contain the right version
        version = read_version()
        all_ok = True
        
        for name, package_dir in packages:
            lock_file = package_dir / "uv.lock"
            if lock_file.exists():
                content = lock_file.read_text()
                # Look for the package's own version in lock file
                if name == "Backend":
                    pattern = r'name = "claude-skills-mcp-backend"\nversion = "([^"]+)"'
                else:
                    pattern = r'name = "claude-skills-mcp"\nversion = "([^"]+)"'
                
                match = re.search(pattern, content)
                if match and match.group(1) != version:
                    print(f"❌ OUT OF SYNC        {name} uv.lock (version {match.group(1)} != {version})")
                    all_ok = False
                elif match:
                    print(f"✓ OK                 {name} uv.lock")
                else:
                    print(f"⚠️  Could not verify {name} uv.lock")
        
        return all_ok
    else:
        # Update lock files
        for name, package_dir in packages:
            try:
                print(f"Updating {name} lock file...", end=" ")
                result = subprocess.run(
                    ["uv", "lock"],
                    cwd=package_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    print("✓")
                else:
                    print(f"✗ (exit code {result.returncode})")
                    print(f"  Error: {result.stderr}")
                    return False
            except Exception as e:
                print(f"✗ ({e})")
                return False

        return True


def main() -> int:
    """Main entry point.

    Returns
    -------
    int
        Exit code (0 for success, 1 for failure)
    """
    check_only = "--check" in sys.argv

    if check_only:
        print("🔍 Checking version sync...\n")
    else:
        print("🔄 Syncing versions...\n")

    success = sync_versions(check_only)
    
    if not success:
        return 1
    
    # Also update/check lock files
    print()
    lock_success = update_lock_files(check_only)
    
    if not lock_success:
        if check_only:
            print("\nRun 'python scripts/sync-version.py' to update lock files.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

