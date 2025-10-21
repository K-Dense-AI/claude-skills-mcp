"""Configuration management for Claude Skills MCP server."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "skill_sources": [
        {
            "type": "github",
            "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
        }
    ],
    "embedding_model": "all-MiniLM-L6-v2",
    "default_top_k": 3,
}


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from file or use defaults.

    Parameters
    ----------
    config_path : str | None
        Path to configuration JSON file. If None, uses DEFAULT_CONFIG.

    Returns
    -------
    dict[str, Any]
        Configuration dictionary.
    """
    if config_path is None:
        logger.info("No config file specified, using default configuration")
        return DEFAULT_CONFIG.copy()

    try:
        config_file = Path(config_path).expanduser().resolve()
        if not config_file.exists():
            logger.warning(f"Config file {config_path} not found, using defaults")
            return DEFAULT_CONFIG.copy()

        with open(config_file, "r") as f:
            config = json.load(f)

        # Merge with defaults for any missing keys
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)

        logger.info(f"Loaded configuration from {config_path}")
        return merged_config

    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        logger.info("Falling back to default configuration")
        return DEFAULT_CONFIG.copy()


def get_example_config() -> str:
    """Get an example configuration as JSON string.

    Returns
    -------
    str
        Example configuration in JSON format.
    """
    example = {
        "skill_sources": [
            {
                "type": "github",
                "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
            },
            {
                "type": "github",
                "url": "https://github.com/anthropics/claude-cookbooks",
                "subpath": "skills/custom_skills",
            },
            {"type": "local", "path": "~/.claude/skills"},
        ],
        "embedding_model": "all-MiniLM-L6-v2",
        "default_top_k": 3,
    }
    return json.dumps(example, indent=2)
