"""State persistence for tracking skill updates."""

import hashlib
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_state_cache_dir() -> Path:
    """Get state cache directory.

    Returns
    -------
    Path
        Path to state cache directory.
    """
    cache_dir = Path(tempfile.gettempdir()) / "claude_skills_mcp_cache" / "state"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_state_file_path(key: str) -> Path:
    """Get state file path for a given key.

    Parameters
    ----------
    key : str
        State key (e.g., 'github_tracker', 'local_tracker').

    Returns
    -------
    Path
        Path to state file.
    """
    cache_dir = _get_state_cache_dir()
    # Create hash-based filename to avoid path issues
    hash_key = hashlib.md5(key.encode()).hexdigest()
    return cache_dir / f"{hash_key}.json"


class StateManager:
    """Manages persistent state for skill update tracking.

    Attributes
    ----------
    state_key : str
        Unique key for this state manager.
    state_file : Path
        Path to the state file.
    state : dict[str, Any]
        Current state dictionary.
    """

    def __init__(self, state_key: str):
        """Initialize state manager.

        Parameters
        ----------
        state_key : str
            Unique key for this state (e.g., 'github_tracker').
        """
        self.state_key = state_key
        self.state_file = _get_state_file_path(state_key)
        self.state: dict[str, Any] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load state from disk cache."""
        if not self.state_file.exists():
            logger.debug(f"No existing state found for {self.state_key}")
            self.state = {}
            return

        try:
            with open(self.state_file, "r") as f:
                self.state = json.load(f)
            logger.debug(f"Loaded state for {self.state_key} from {self.state_file}")
        except Exception as e:
            logger.warning(f"Failed to load state from {self.state_file}: {e}")
            self.state = {}

    def save_state(self) -> None:
        """Save current state to disk cache."""
        try:
            # Add timestamp
            self.state["_last_saved"] = datetime.now().isoformat()

            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"Saved state for {self.state_key} to {self.state_file}")
        except Exception as e:
            logger.warning(f"Failed to save state to {self.state_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from state.

        Parameters
        ----------
        key : str
            State key.
        default : Any, optional
            Default value if key not found, by default None.

        Returns
        -------
        Any
            Value from state or default.
        """
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in state.

        Parameters
        ----------
        key : str
            State key.
        value : Any
            Value to set.
        """
        self.state[key] = value

    def update(self, updates: dict[str, Any]) -> None:
        """Update multiple state values.

        Parameters
        ----------
        updates : dict[str, Any]
            Dictionary of updates.
        """
        self.state.update(updates)

    def clear(self) -> None:
        """Clear all state."""
        self.state = {}
        self.save_state()
