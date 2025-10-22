"""Tests for configuration management."""

import json
import tempfile
from pathlib import Path

import pytest

from claude_skills_mcp_backend.config import load_config, get_example_config, DEFAULT_CONFIG


def test_load_default_config():
    """Test loading default configuration when no file is specified."""
    config = load_config()

    assert config is not None
    assert "skill_sources" in config
    assert "embedding_model" in config
    assert "default_top_k" in config
    assert config["default_top_k"] == 3
    assert config["embedding_model"] == "all-MiniLM-L6-v2"


def test_load_config_from_file():
    """Test loading configuration from a JSON file."""
    test_config = {
        "skill_sources": [{"type": "local", "path": "/tmp/test"}],
        "embedding_model": "test-model",
        "default_top_k": 5,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_config, f)
        config_path = f.name

    try:
        config = load_config(config_path)

        assert config["embedding_model"] == "test-model"
        assert config["default_top_k"] == 5
        assert len(config["skill_sources"]) == 1
        assert config["skill_sources"][0]["type"] == "local"
    finally:
        Path(config_path).unlink()


def test_load_nonexistent_config():
    """Test loading config when file doesn't exist falls back to defaults."""
    config = load_config("/nonexistent/path/config.json")

    # Should fall back to defaults
    assert config == DEFAULT_CONFIG


def test_get_example_config():
    """Test example configuration generation."""
    example = get_example_config()

    assert isinstance(example, str)
    assert "skill_sources" in example
    assert "embedding_model" in example
    assert "default_top_k" in example

    # Should be valid JSON
    parsed = json.loads(example)
    assert isinstance(parsed, dict)


def test_default_config_structure():
    """Test that DEFAULT_CONFIG has the expected structure."""
    assert "skill_sources" in DEFAULT_CONFIG
    assert "embedding_model" in DEFAULT_CONFIG
    assert "default_top_k" in DEFAULT_CONFIG

    assert isinstance(DEFAULT_CONFIG["skill_sources"], list)
    assert len(DEFAULT_CONFIG["skill_sources"]) > 0

    # Check first source is the official Anthropic skills repo
    first_source = DEFAULT_CONFIG["skill_sources"][0]
    assert first_source["type"] == "github"
    assert "anthropics/skills" in first_source["url"]


@pytest.mark.parametrize("top_k", [1, 3, 5, 10])
def test_config_with_different_top_k(top_k):
    """Test configuration with different top_k values."""
    test_config = {
        "skill_sources": DEFAULT_CONFIG["skill_sources"],
        "embedding_model": DEFAULT_CONFIG["embedding_model"],
        "default_top_k": top_k,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_config, f)
        config_path = f.name

    try:
        config = load_config(config_path)
        assert config["default_top_k"] == top_k
    finally:
        Path(config_path).unlink()
