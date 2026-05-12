"""Tests for skill loading functionality."""

import pytest

from claude_skills_mcp_backend.skill_loader import (
    parse_skill_md,
    load_from_local,
    Skill,
)


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


def test_load_from_local_excludes_node_modules(tmp_path):
    """SKILL.md files under node_modules/ must be excluded by default."""
    # Real skill at the root
    (tmp_path / "real-skill").mkdir()
    (tmp_path / "real-skill" / "SKILL.md").write_text(
        "---\nname: Real Skill\ndescription: A real user skill\n---\n# Real\n"
    )

    # Noise: SKILL.md bundled inside node_modules (e.g. dotenv's example skill)
    nested = tmp_path / "some-project" / "node_modules" / "dotenv" / "skills" / "dotenv"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text(
        "---\nname: dotenv\ndescription: third-party noise\n---\n# noise\n"
    )

    skills = load_from_local(str(tmp_path))
    names = {s.name for s in skills}

    assert "Real Skill" in names
    assert "dotenv" not in names, "node_modules SKILL.md must be excluded"


def test_load_from_local_excludes_venv(tmp_path):
    """SKILL.md files under venv/site-packages must be excluded by default."""
    (tmp_path / "real-skill").mkdir()
    (tmp_path / "real-skill" / "SKILL.md").write_text(
        "---\nname: Real Skill\ndescription: A real skill\n---\n# Real\n"
    )

    # Noise: SKILL.md inside venv/site-packages (e.g. typer's bundled skill)
    nested = (
        tmp_path / "some-project" / "venv" / "lib" / "python3.12"
        / "site-packages" / "typer" / ".agents" / "skills" / "typer"
    )
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text(
        "---\nname: typer\ndescription: bundled noise\n---\n# noise\n"
    )

    skills = load_from_local(str(tmp_path))
    names = {s.name for s in skills}

    assert "Real Skill" in names
    assert "typer" not in names, "venv/site-packages SKILL.md must be excluded"


def test_load_from_local_custom_exclude_patterns(tmp_path):
    """Custom exclude_patterns override the defaults."""
    (tmp_path / "good").mkdir()
    (tmp_path / "good" / "SKILL.md").write_text(
        "---\nname: Good\ndescription: keep me\n---\n# Good\n"
    )
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "SKILL.md").write_text(
        "---\nname: Bad\ndescription: drop me\n---\n# Bad\n"
    )

    skills = load_from_local(str(tmp_path), config={"exclude_patterns": ["**/bad/**"]})
    names = {s.name for s in skills}

    assert names == {"Good"}


def test_load_from_local_empty_exclude_patterns_disables_filter(tmp_path):
    """An empty exclude_patterns list disables filtering (opt-out)."""
    (tmp_path / "real-skill").mkdir()
    (tmp_path / "real-skill" / "SKILL.md").write_text(
        "---\nname: Real Skill\ndescription: A real skill\n---\n# Real\n"
    )
    nested = tmp_path / "some-project" / "node_modules" / "dotenv" / "skills" / "dotenv"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text(
        "---\nname: dotenv\ndescription: would normally be excluded\n---\n# noise\n"
    )

    skills = load_from_local(str(tmp_path), config={"exclude_patterns": []})
    names = {s.name for s in skills}

    # With no exclude_patterns, both must be loaded (legacy behavior)
    assert "Real Skill" in names
    assert "dotenv" in names
