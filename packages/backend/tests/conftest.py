"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from claude_skills_mcp_backend.skill_loader import Skill


@pytest.fixture
def sample_skill_md() -> str:
    """Sample SKILL.md content with YAML frontmatter."""
    return """---
name: Test Skill
description: A test skill for validation and testing purposes
---

# Test Skill

This is a test skill content.

## Features

- Feature 1
- Feature 2

## Usage

```python
# Example code
import test
```
"""


@pytest.fixture
def mock_skills() -> list[Skill]:
    """Create a list of mock skills for testing."""
    return [
        Skill(
            name="RNA Analysis",
            description="Analyze RNA sequencing data and identify differentially expressed genes",
            content="Full content for RNA analysis skill...",
            source="test://rna-analysis",
        ),
        Skill(
            name="Protein Folding",
            description="Predict protein structure using deep learning models",
            content="Full content for protein folding skill...",
            source="test://protein-folding",
        ),
        Skill(
            name="Drug Discovery",
            description="Screen chemical compounds for potential drug targets",
            content="Full content for drug discovery skill...",
            source="test://drug-discovery",
        ),
    ]


@pytest.fixture
def temp_skill_dir() -> Generator[Path, None, None]:
    """Create a temporary directory with test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # Create first skill
        skill1_dir = temp_path / "skill-1"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text("""---
name: Local Test Skill 1
description: First local test skill for validation
---

# Local Test Skill 1

This is the first local test skill.
""")

        # Create second skill
        skill2_dir = temp_path / "skill-2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text("""---
name: Local Test Skill 2
description: Second local test skill for validation
---

# Local Test Skill 2

This is the second local test skill.
""")

        yield temp_path


@pytest.fixture
def sample_config() -> dict[str, any]:
    """Sample configuration for testing."""
    return {
        "skill_sources": [
            {
                "type": "github",
                "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
            }
        ],
        "embedding_model": "all-MiniLM-L6-v2",
        "default_top_k": 3,
    }
