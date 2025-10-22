"""Tests for skill loading functionality."""

import pytest

from claude_skills_mcp_backend.skill_loader import parse_skill_md, load_from_local, Skill


def test_parse_skill_md_valid(sample_skill_md):
    """Test parsing a valid SKILL.md file."""
    skill = parse_skill_md(sample_skill_md, "test_source")

    assert skill is not None
    assert skill.name == "Test Skill"
    assert skill.description == "A test skill for validation and testing purposes"
    assert "This is a test skill content" in skill.content
    assert skill.source == "test_source"


def test_parse_skill_md_missing_frontmatter():
    """Test parsing SKILL.md without YAML frontmatter."""
    content = """# Test Skill

Just content without frontmatter.
"""
    skill = parse_skill_md(content, "test_source")

    assert skill is None


def test_parse_skill_md_missing_name():
    """Test parsing SKILL.md with missing name in frontmatter."""
    content = """---
description: A skill without a name
---

# Content
"""
    skill = parse_skill_md(content, "test_source")

    assert skill is None


def test_parse_skill_md_missing_description():
    """Test parsing SKILL.md with missing description in frontmatter."""
    content = """---
name: Test Skill
---

# Content
"""
    skill = parse_skill_md(content, "test_source")

    assert skill is None


def test_parse_skill_md_quoted_values():
    """Test parsing SKILL.md with quoted name and description."""
    content = """---
name: "Quoted Name"
description: 'Single quoted description'
---

# Content
"""
    skill = parse_skill_md(content, "test_source")

    assert skill is not None
    assert skill.name == "Quoted Name"
    assert skill.description == "Single quoted description"


def test_load_from_local_valid_directory(temp_skill_dir):
    """Test loading skills from a valid local directory."""
    skills = load_from_local(str(temp_skill_dir))

    assert len(skills) == 2
    skill_names = {skill.name for skill in skills}
    assert "Local Test Skill 1" in skill_names
    assert "Local Test Skill 2" in skill_names


def test_load_from_local_nonexistent_directory():
    """Test loading skills from a non-existent directory."""
    skills = load_from_local("/nonexistent/directory")

    assert skills == []


def test_load_from_local_empty_directory():
    """Test loading skills from an empty directory."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        skills = load_from_local(tmpdir)
        assert skills == []


def test_skill_to_dict():
    """Test converting Skill object to dictionary."""
    skill = Skill(
        name="Test",
        description="Test description",
        content="Test content",
        source="test_source",
    )

    skill_dict = skill.to_dict()

    assert skill_dict["name"] == "Test"
    assert skill_dict["description"] == "Test description"
    assert skill_dict["content"] == "Test content"
    assert skill_dict["source"] == "test_source"


@pytest.mark.parametrize(
    "path_variation",
    [
        "~/test-skills",
        "~/.claude/skills",
    ],
)
def test_load_from_local_with_home_expansion(path_variation):
    """Test that ~ is properly expanded in paths."""
    # This will return empty list since paths don't exist,
    # but it shouldn't crash
    skills = load_from_local(path_variation)
    assert isinstance(skills, list)
