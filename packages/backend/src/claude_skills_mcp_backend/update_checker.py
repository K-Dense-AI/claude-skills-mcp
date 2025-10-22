"""Update detection for GitHub and local skill sources."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from .state_manager import StateManager

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Result of checking for updates.

    Attributes
    ----------
    has_updates : bool
        Whether any updates were detected.
    changed_sources : list[dict[str, Any]]
        List of source configs that have changes.
    api_calls_made : int
        Number of GitHub API calls made.
    errors : list[str]
        Any errors encountered during checking.
    """

    has_updates: bool = False
    changed_sources: list[dict[str, Any]] = field(default_factory=list)
    api_calls_made: int = 0
    errors: list[str] = field(default_factory=list)


class GitHubSourceTracker:
    """Track GitHub repository commit SHAs to detect changes.

    Attributes
    ----------
    state_manager : StateManager
        State persistence manager.
    github_token : str | None
        Optional GitHub personal access token.
    api_calls_this_hour : int
        Counter for API calls made in current hour.
    last_api_reset : datetime
        When the API call counter was last reset.
    """

    def __init__(self, github_token: str | None = None):
        """Initialize GitHub source tracker.

        Parameters
        ----------
        github_token : str | None, optional
            GitHub personal access token, by default None.
        """
        self.state_manager = StateManager("github_tracker")
        self.github_token = github_token
        self.api_calls_this_hour = 0
        self.last_api_reset = datetime.now().replace(minute=0, second=0, microsecond=0)

    def _parse_github_url(self, url: str) -> tuple[str, str, str] | None:
        """Parse GitHub URL to extract owner, repo, and branch.

        Parameters
        ----------
        url : str
            GitHub repository URL.

        Returns
        -------
        tuple[str, str, str] | None
            (owner, repo, branch) or None if invalid.
        """
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")

            if len(path_parts) < 2:
                return None

            owner = path_parts[0]
            repo = path_parts[1]
            branch = "main"  # Default

            # Check for /tree/{branch}/ format
            if len(path_parts) > 3 and path_parts[2] == "tree":
                branch = path_parts[3]

            return owner, repo, branch
        except Exception as e:
            logger.error(f"Failed to parse GitHub URL {url}: {e}")
            return None

    def _get_state_key(self, owner: str, repo: str, branch: str) -> str:
        """Get state key for a repository.

        Parameters
        ----------
        owner : str
            Repository owner.
        repo : str
            Repository name.
        branch : str
            Branch name.

        Returns
        -------
        str
            State key.
        """
        return f"{owner}/{repo}/{branch}"

    def _update_api_counter(self) -> None:
        """Update API call counter and reset if hour has passed."""
        now = datetime.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        if current_hour > self.last_api_reset:
            # New hour, reset counter
            self.api_calls_this_hour = 0
            self.last_api_reset = current_hour

    def _make_api_request(self, url: str) -> dict[str, Any] | None:
        """Make GitHub API request with authentication.

        Parameters
        ----------
        url : str
            API URL.

        Returns
        -------
        dict[str, Any] | None
            Response JSON or None on error.
        """
        self._update_api_counter()
        self.api_calls_this_hour += 1

        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"GitHub API request failed for {url}: {e}")
            return None

    def check_for_updates(self, source_config: dict[str, Any]) -> bool:
        """Check if a GitHub source has updates.

        Parameters
        ----------
        source_config : dict[str, Any]
            Source configuration with 'url' field.

        Returns
        -------
        bool
            True if updates detected, False otherwise.
        """
        url = source_config.get("url")
        if not url:
            return False

        parsed = self._parse_github_url(url)
        if not parsed:
            logger.warning(f"Invalid GitHub URL: {url}")
            return False

        owner, repo, branch = parsed
        state_key = self._get_state_key(owner, repo, branch)

        # Get last known commit SHA
        last_sha = self.state_manager.get(state_key)

        # Fetch current HEAD commit
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
        commit_data = self._make_api_request(api_url)

        if not commit_data:
            logger.warning(f"Failed to fetch commit info for {owner}/{repo}@{branch}")
            return False

        current_sha = commit_data.get("sha")
        if not current_sha:
            logger.warning(f"No SHA in commit data for {owner}/{repo}@{branch}")
            return False

        # Check if SHA changed
        if last_sha is None:
            # First time checking, save SHA but don't trigger update
            logger.info(
                f"First check for {owner}/{repo}@{branch}, SHA: {current_sha[:7]}"
            )
            self.state_manager.set(state_key, current_sha)
            self.state_manager.save_state()
            return False

        if current_sha != last_sha:
            logger.info(
                f"Update detected for {owner}/{repo}@{branch}: "
                f"{last_sha[:7]} -> {current_sha[:7]}"
            )
            # Update the SHA
            self.state_manager.set(state_key, current_sha)
            self.state_manager.save_state()
            return True

        logger.debug(f"No updates for {owner}/{repo}@{branch}")
        return False

    def get_api_usage(self) -> dict[str, Any]:
        """Get current API usage statistics.

        Returns
        -------
        dict[str, Any]
            API usage info including calls made and limit.
        """
        self._update_api_counter()
        limit = 5000 if self.github_token else 60

        return {
            "calls_this_hour": self.api_calls_this_hour,
            "limit_per_hour": limit,
            "authenticated": self.github_token is not None,
            "last_reset": self.last_api_reset.isoformat(),
        }


class LocalSourceTracker:
    """Track local skill file modification times to detect changes.

    Attributes
    ----------
    state_manager : StateManager
        State persistence manager.
    """

    def __init__(self):
        """Initialize local source tracker."""
        self.state_manager = StateManager("local_tracker")

    def _get_skill_files(self, path: str) -> list[Path]:
        """Get all SKILL.md files in a directory.

        Parameters
        ----------
        path : str
            Directory path to search.

        Returns
        -------
        list[Path]
            List of SKILL.md file paths.
        """
        try:
            local_path = Path(path).expanduser().resolve()
            if not local_path.exists() or not local_path.is_dir():
                return []

            return list(local_path.rglob("SKILL.md"))
        except Exception as e:
            logger.error(f"Error scanning local path {path}: {e}")
            return []

    def check_for_updates(self, source_config: dict[str, Any]) -> bool:
        """Check if a local source has updates.

        Parameters
        ----------
        source_config : dict[str, Any]
            Source configuration with 'path' field.

        Returns
        -------
        bool
            True if updates detected, False otherwise.
        """
        path = source_config.get("path")
        if not path:
            return False

        skill_files = self._get_skill_files(path)

        # Get state key
        state_key = f"local:{path}"
        last_mtimes = self.state_manager.get(state_key, {})

        # Check modification times
        current_mtimes = {}
        has_changes = False

        for skill_file in skill_files:
            try:
                mtime = skill_file.stat().st_mtime
                file_key = str(skill_file)
                current_mtimes[file_key] = mtime

                # Check if file is new or modified
                if file_key not in last_mtimes:
                    logger.info(f"New skill file detected: {skill_file}")
                    has_changes = True
                elif (
                    abs(last_mtimes[file_key] - mtime) > 0.001
                ):  # Allow small float differences
                    logger.info(f"Modified skill file detected: {skill_file}")
                    has_changes = True
            except Exception as e:
                logger.warning(f"Failed to check mtime for {skill_file}: {e}")

        # Check for deleted files
        for file_key in last_mtimes:
            if file_key not in current_mtimes:
                logger.info(f"Deleted skill file detected: {file_key}")
                has_changes = True

        # Update state
        if has_changes or not last_mtimes:
            # First check or changes detected
            self.state_manager.set(state_key, current_mtimes)
            self.state_manager.save_state()

            # Don't trigger update on first check
            if not last_mtimes:
                logger.info(
                    f"First check for local path {path}, tracking {len(skill_files)} files"
                )
                return False

        return has_changes


class UpdateChecker:
    """Orchestrate update checking across all sources.

    Attributes
    ----------
    github_tracker : GitHubSourceTracker
        GitHub source tracker.
    local_tracker : LocalSourceTracker
        Local source tracker.
    """

    def __init__(self, github_token: str | None = None):
        """Initialize update checker.

        Parameters
        ----------
        github_token : str | None, optional
            GitHub personal access token, by default None.
        """
        self.github_tracker = GitHubSourceTracker(github_token)
        self.local_tracker = LocalSourceTracker()

    def check_for_updates(self, skill_sources: list[dict[str, Any]]) -> UpdateResult:
        """Check all sources for updates.

        Parameters
        ----------
        skill_sources : list[dict[str, Any]]
            List of skill source configurations.

        Returns
        -------
        UpdateResult
            Result containing changed sources and metadata.
        """
        result = UpdateResult()

        for source_config in skill_sources:
            source_type = source_config.get("type")

            try:
                if source_type == "github":
                    has_update = self.github_tracker.check_for_updates(source_config)
                    if has_update:
                        result.has_updates = True
                        result.changed_sources.append(source_config)

                elif source_type == "local":
                    has_update = self.local_tracker.check_for_updates(source_config)
                    if has_update:
                        result.has_updates = True
                        result.changed_sources.append(source_config)

            except Exception as e:
                error_msg = f"Error checking {source_type} source: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Get API usage stats
        api_usage = self.github_tracker.get_api_usage()
        result.api_calls_made = api_usage["calls_this_hour"]

        return result

    def get_api_usage(self) -> dict[str, Any]:
        """Get GitHub API usage statistics.

        Returns
        -------
        dict[str, Any]
            API usage info.
        """
        return self.github_tracker.get_api_usage()
