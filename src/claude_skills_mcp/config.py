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
            "url": "https://github.com/anthropics/skills",
        },
        {
            "type": "github",
            "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
        },
        {
            "type": "local",
            "path": "~/.claude/skills",
        },
    ],
    "embedding_model": "all-MiniLM-L6-v2",
    "default_top_k": 3,
    "max_skill_content_chars": None,  # None for unlimited, or an integer to limit
    "load_skill_documents": True,  # Load additional files from skill directories
    "max_image_size_bytes": 5242880,  # 5MB limit for image files
    "allowed_image_extensions": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"],
    "text_file_extensions": [
        ".md",
        ".py",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".sh",
        ".r",
        ".ipynb",
        ".xml",
    ],
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
    """Get the default configuration as JSON string.

    Returns
    -------
    str
        Default configuration in JSON format.
    """
    # Add helpful comments for clarity
    config_with_comments = {
        "skill_sources": [
            {
                "type": "github",
                "url": "https://github.com/anthropics/skills",
                "comment": "Official Anthropic skills - diverse examples with Python scripts, images, documents",
            },
            {
                "type": "github",
                "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
                "comment": "70+ scientific skills for bioinformatics, cheminformatics, and analysis",
            },
            {
                "type": "local",
                "path": "~/.claude/skills",
                "comment": "Your custom local skills (optional - directory doesn't need to exist)",
            },
        ],
        "embedding_model": "all-MiniLM-L6-v2",
        "default_top_k": 3,
        "max_skill_content_chars": None,
        "comment_max_chars": "Set to an integer (e.g., 5000) to truncate skill content, or null for unlimited",
        "load_skill_documents": True,
        "max_image_size_bytes": 5242880,
        "allowed_image_extensions": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"],
        "text_file_extensions": [
            ".md",
            ".py",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".sh",
            ".r",
            ".ipynb",
            ".xml",
        ],
    }
    return json.dumps(config_with_comments, indent=2)
