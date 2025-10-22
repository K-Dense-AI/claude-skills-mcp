"""Tests for GitHub URL parsing with branch and subpath."""

from claude_skills_mcp_backend.skill_loader import load_from_github


def test_github_url_with_subpath():
    """Test loading from a GitHub URL with tree/branch/subpath format."""
    # Browser-style URL with subpath
    url = "https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/scientific-thinking"

    skills = load_from_github(url)

    # Should load skills from scientific-thinking subdirectory
    assert len(skills) > 0

    # Check that all skills are from scientific-thinking
    skill_names = {skill.name for skill in skills}

    # These are skills known to be in scientific-thinking
    expected_skills = {
        "docx",
        "pdf",
        "pptx",
        "xlsx",
        "exploratory-data-analysis",
        "hypothesis-generation",
        "peer-review",
        "scientific-brainstorming",
        "scientific-critical-thinking",
        "scientific-visualization",
        "statistical-analysis",
    }

    # All expected skills should be present
    assert expected_skills.issubset(skill_names), (
        f"Missing skills: {expected_skills - skill_names}"
    )

    # Should NOT have skills from other directories (like databases or packages)
    assert "biopython" not in skill_names
    assert "alphafold-database" not in skill_names


def test_github_url_base_repo():
    """Test loading from a base GitHub repo URL."""
    url = "https://github.com/K-Dense-AI/claude-scientific-skills"

    skills = load_from_github(url)

    # Should load all skills from entire repo
    assert len(skills) > 50  # Full repo has 70+ skills

    # Should have skills from multiple directories
    skill_names = {skill.name for skill in skills}
    assert "biopython" in skill_names  # from scientific-packages
    assert "alphafold-database" in skill_names  # from scientific-databases
    assert "peer-review" in skill_names  # from scientific-thinking


def test_github_url_with_deep_subpath():
    """Test loading from a GitHub URL with nested subpath."""
    # Deep nested path
    url = "https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/scientific-thinking/document-skills"

    skills = load_from_github(url)

    # Should only load document skills
    assert len(skills) == 4  # docx, pdf, pptx, xlsx

    skill_names = {skill.name for skill in skills}
    assert skill_names == {"docx", "pdf", "pptx", "xlsx"}


def test_subpath_parameter_override():
    """Test that explicit subpath parameter is used if both URL and parameter provide subpath."""
    # URL has one subpath, parameter has another
    url = "https://github.com/K-Dense-AI/claude-scientific-skills"
    subpath = "scientific-thinking"

    skills = load_from_github(url, subpath=subpath)

    # Should use the subpath parameter
    assert len(skills) > 0

    skill_names = {skill.name for skill in skills}
    assert "peer-review" in skill_names
    assert "biopython" not in skill_names  # from different directory
