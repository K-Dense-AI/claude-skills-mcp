"""Tests for tarball-based GitHub loading (no network required)."""

import io
import tarfile

import httpx
import pytest

from claude_skills_mcp_backend.skill_loader import (
    load_from_github,
    parse_github_source_url,
)

SKILL_MD_SIMPLE = """---
name: rna-analysis
description: Analyze RNA sequencing data and identify differentially expressed genes
---

# RNA Analysis

Use this skill for RNA-seq work.
"""

SKILL_MD_MULTILINE = """---
name: protein-folding
description: >
  Predict protein structure using deep learning models
  and validate against known structures.
---

# Protein Folding
"""


def _build_repo_tarball(root_name: str) -> bytes:
    """Build an in-memory tar.gz mimicking a GitHub codeload tarball."""
    files = {
        f"{root_name}/skills/rna-analysis/SKILL.md": SKILL_MD_SIMPLE,
        f"{root_name}/skills/rna-analysis/scripts/analyze.py": "print('analysis')\n",
        f"{root_name}/skills/rna-analysis/references/notes.md": "# Notes\n",
        f"{root_name}/skills/protein-folding/SKILL.md": SKILL_MD_MULTILINE,
        f"{root_name}/README.md": "# Repo readme (not a skill doc)\n",
    }
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.fixture
def fake_github(monkeypatch, tmp_path):
    """Patch tarball download and snapshot cache dir; returns call recorder."""
    calls = []

    def fake_fetch(owner: str, repo: str, ref: str) -> bytes:
        calls.append((owner, repo, ref))
        if ref == "main":
            return _build_repo_tarball(f"{repo}-main")
        raise httpx.HTTPStatusError(
            "404",
            request=httpx.Request("GET", "https://codeload.github.com/x"),
            response=httpx.Response(
                404, request=httpx.Request("GET", "https://codeload.github.com/x")
            ),
        )

    monkeypatch.setattr(
        "claude_skills_mcp_backend.skill_loader._fetch_tarball_bytes", fake_fetch
    )
    monkeypatch.setattr(
        "claude_skills_mcp_backend.skill_loader._get_repo_cache_dir",
        lambda: tmp_path / "repos",
    )
    return calls


def test_load_from_github_via_tarball(fake_github):
    """Skills load from a single tarball download."""
    skills = load_from_github("https://github.com/acme/skills-repo")

    assert len(skills) == 2
    assert fake_github == [("acme", "skills-repo", "main")]  # exactly one download

    by_name = {s.name: s for s in skills}
    assert "rna-analysis" in by_name
    assert "protein-folding" in by_name

    # Multiline YAML description parsed fully
    assert "deep learning models" in by_name["protein-folding"].description
    assert by_name["protein-folding"].description != ">"

    # Source points at the canonical GitHub URL
    assert by_name["rna-analysis"].source == (
        "https://github.com/acme/skills-repo/tree/main/skills/rna-analysis/SKILL.md"
    )


def test_documents_lazy_loaded_from_snapshot(fake_github):
    """Document metadata is listed upfront; content read lazily from disk."""
    skills = load_from_github("https://github.com/acme/skills-repo")
    skill = next(s for s in skills if s.name == "rna-analysis")

    assert set(skill.documents) == {"scripts/analyze.py", "references/notes.md"}
    meta = skill.documents["scripts/analyze.py"]
    assert meta["fetched"] is False
    assert "content" not in meta
    assert meta["url"] == (
        "https://raw.githubusercontent.com/acme/skills-repo/main/"
        "skills/rna-analysis/scripts/analyze.py"
    )

    doc = skill.get_document("scripts/analyze.py")
    assert doc is not None
    assert doc["content"] == "print('analysis')\n"
    assert doc["fetched"] is True

    assert skill.get_document("does/not/exist.py") is None


def test_snapshot_cache_reused(fake_github):
    """A second load reuses the extracted snapshot without downloading."""
    load_from_github("https://github.com/acme/skills-repo")
    load_from_github("https://github.com/acme/skills-repo")

    assert len(fake_github) == 1


def test_force_refresh_redownloads(fake_github):
    """force_refresh bypasses the snapshot cache."""
    load_from_github("https://github.com/acme/skills-repo")
    load_from_github("https://github.com/acme/skills-repo", force_refresh=True)

    assert len(fake_github) == 2


def test_master_branch_fallback(monkeypatch, tmp_path):
    """Repos without a 'main' branch fall back to 'master'."""
    calls = []

    def fake_fetch(owner: str, repo: str, ref: str) -> bytes:
        calls.append(ref)
        if ref == "master":
            return _build_repo_tarball(f"{repo}-master")
        raise httpx.HTTPStatusError(
            "404",
            request=httpx.Request("GET", "https://codeload.github.com/x"),
            response=httpx.Response(
                404, request=httpx.Request("GET", "https://codeload.github.com/x")
            ),
        )

    monkeypatch.setattr(
        "claude_skills_mcp_backend.skill_loader._fetch_tarball_bytes", fake_fetch
    )
    monkeypatch.setattr(
        "claude_skills_mcp_backend.skill_loader._get_repo_cache_dir",
        lambda: tmp_path / "repos",
    )

    skills = load_from_github("https://github.com/acme/old-repo")

    assert calls == ["main", "master"]
    assert len(skills) == 2
    assert "tree/master/" in skills[0].source


def test_subpath_filter(fake_github):
    """Subpath (from URL or parameter) restricts which skills load."""
    skills = load_from_github(
        "https://github.com/acme/skills-repo/tree/main/skills/rna-analysis"
    )
    assert [s.name for s in skills] == ["rna-analysis"]

    skills = load_from_github(
        "https://github.com/acme/skills-repo", subpath="skills/protein-folding"
    )
    assert [s.name for s in skills] == ["protein-folding"]

    skills = load_from_github(
        "https://github.com/acme/skills-repo", subpath="no/such/dir"
    )
    assert skills == []


def test_parse_github_source_url():
    """URL parsing extracts owner, repo, branch, and subpath."""
    assert parse_github_source_url("https://github.com/owner/repo") == (
        "owner",
        "repo",
        None,
        "",
    )
    assert parse_github_source_url(
        "https://github.com/owner/repo/tree/dev/some/sub/dir"
    ) == ("owner", "repo", "dev", "some/sub/dir")
    # Explicit subpath parameter wins over URL subpath
    assert parse_github_source_url(
        "https://github.com/owner/repo/tree/dev/some/dir", subpath="explicit"
    ) == ("owner", "repo", "dev", "explicit")
    assert parse_github_source_url("https://github.com/onlyowner") is None
