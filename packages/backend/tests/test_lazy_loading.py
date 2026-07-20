"""Live smoke tests for lazy document loading.

Lazy-loading semantics (metadata-only at startup, on-demand reads, snapshot
caching) are unit-tested without network in test_tarball_loading.py. These
tests verify the behavior against a real repository, using invariants rather
than hardcoded repository content.
"""

import asyncio
import time

import pytest

from claude_skills_mcp_backend.search_engine import SkillSearchEngine
from claude_skills_mcp_backend.skill_loader import load_from_github

REPO_URL = "https://github.com/anthropics/skills"


def _load_live_skills():
    skills = load_from_github(REPO_URL)
    if len(skills) == 0:
        pytest.skip("GitHub unreachable - skipping live test")
    return skills


@pytest.mark.network
@pytest.mark.integration
def test_metadata_only_at_startup_then_lazy_fetch():
    """Documents expose metadata at load time; content is read on demand."""
    skills = _load_live_skills()

    skill_with_docs = next((s for s in skills if s.documents), None)
    if skill_with_docs is None:
        pytest.skip("No skill with documents in repository")

    # All documents: metadata only, no content
    for doc_path, doc_info in skill_with_docs.documents.items():
        assert "type" in doc_info, f"{doc_path} missing type"
        assert "size" in doc_info, f"{doc_path} missing size"
        assert "url" in doc_info, f"{doc_path} missing URL"
        assert "content" not in doc_info, f"{doc_path} has content at startup"
        assert not doc_info.get("fetched"), f"{doc_path} marked fetched at startup"

    # On-demand fetch returns content and caches it
    doc_path = next(iter(skill_with_docs.documents))
    content = skill_with_docs.get_document(doc_path)

    assert content is not None, "Should fetch content on-demand"
    assert content.get("fetched"), "Should be marked as fetched"
    if content.get("type") == "text":
        assert "content" in content, "Text document should have content"

    cached = skill_with_docs.get_document(doc_path)
    assert cached == content, "Second read should return cached content"


@pytest.mark.network
@pytest.mark.integration
def test_startup_time_is_fast():
    """Loading a repository stays fast (single tarball download)."""
    start = time.time()
    skills = _load_live_skills()
    load_time = time.time() - start

    total_docs = sum(len(skill.documents) for skill in skills)
    print(f"\nLoaded {len(skills)} skills ({total_docs} document entries) "
          f"in {load_time:.2f}s")

    assert load_time < 30, f"Load time {load_time:.2f}s exceeds 30s limit"


@pytest.mark.network
@pytest.mark.integration
def test_lazy_fetching_through_server():
    """read_skill_document triggers the lazy fetch through the MCP server."""
    from claude_skills_mcp_backend.mcp_handlers import LoadingState, SkillsMCPServer

    skills = _load_live_skills()
    skill_with_docs = next((s for s in skills if s.documents), None)
    if skill_with_docs is None:
        pytest.skip("No skill with documents in repository")

    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(skills)
    loading_state = LoadingState()
    loading_state.mark_complete()
    server = SkillsMCPServer(engine, loading_state)

    doc_path = next(iter(skill_with_docs.documents))
    result = asyncio.run(
        server._handle_read_skill_document(
            {"skill_name": skill_with_docs.name, "document_path": doc_path}
        )
    )

    assert len(result) == 1
    assert "Document:" in result[0].text or "Image:" in result[0].text
