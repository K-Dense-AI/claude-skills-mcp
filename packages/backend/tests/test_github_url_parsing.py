"""Live smoke tests for GitHub loading.

URL parsing and subpath filtering semantics are unit-tested without network
in test_tarball_loading.py. These tests verify the loader works against real
GitHub, asserting invariants rather than specific repository content (which
changes over time).
"""

import pytest

from claude_skills_mcp_backend.skill_loader import load_from_github


@pytest.mark.network
@pytest.mark.integration
def test_load_live_base_repo():
    """A real repository loads with well-formed skills."""
    skills = load_from_github("https://github.com/K-Dense-AI/claude-scientific-skills")

    if len(skills) == 0:
        pytest.skip("GitHub unreachable - skipping live test")

    for skill in skills:
        assert skill.name, f"Skill without name from {skill.source}"
        assert skill.description, f"Skill '{skill.name}' has no description"
        # A description of '>' or '|' would mean broken YAML multiline parsing
        assert skill.description not in {">", "|"}, (
            f"Skill '{skill.name}' has unparsed YAML scalar as description"
        )
        assert "github.com" in skill.source


@pytest.mark.network
@pytest.mark.integration
def test_load_live_subpath_restricts_results():
    """A subpath (discovered from the repo itself) restricts what loads."""
    all_skills = load_from_github("https://github.com/anthropics/skills")

    if len(all_skills) == 0:
        pytest.skip("GitHub unreachable - skipping live test")

    # Derive a real subpath from a loaded skill's source instead of
    # hardcoding repository structure: .../tree/{ref}/{subpath}/SKILL.md
    sample_source = all_skills[0].source
    repo_rel = sample_source.split("/tree/", 1)[1].split("/", 1)[1]
    subpath = repo_rel.rsplit("/SKILL.md", 1)[0]

    subset = load_from_github("https://github.com/anthropics/skills", subpath=subpath)

    assert 1 <= len(subset) < len(all_skills) or len(all_skills) == 1
    for skill in subset:
        assert f"/{subpath}/" in skill.source
