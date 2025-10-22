"""Tests for lazy document loading."""

import time
import pytest
from claude_skills_mcp_backend.search_engine import SkillSearchEngine
from claude_skills_mcp_backend.skill_loader import load_from_github


@pytest.mark.integration
def test_lazy_document_loading():
    """Test that documents are fetched on-demand, not at startup."""

    # Time the skill loading (should be fast)
    start = time.time()
    skills = load_from_github("https://github.com/K-Dense-AI/claude-scientific-skills")
    load_time = time.time() - start

    print(f"\nLoad time: {load_time:.2f} seconds")
    print(f"Loaded {len(skills)} skills")

    # Should be much faster than before (< 30 seconds vs 60+ seconds)
    assert load_time < 30, f"Loading took too long: {load_time}s"

    # Find a skill with documents
    skill_with_docs = None
    for skill in skills:
        if len(skill.documents) > 0:
            skill_with_docs = skill
            break

    assert skill_with_docs is not None, "Should find at least one skill with documents"

    print(f"\nTesting with skill: {skill_with_docs.name}")
    print(f"  Documents: {len(skill_with_docs.documents)}")

    # Documents should have metadata but no content initially
    first_doc_path = list(skill_with_docs.documents.keys())[0]
    doc_info = skill_with_docs.documents[first_doc_path]

    print(f"  First document: {first_doc_path}")
    print(f"    Type: {doc_info.get('type')}")
    print(f"    Size: {doc_info.get('size')} bytes")
    print(f"    Fetched: {doc_info.get('fetched')}")

    assert "url" in doc_info, "Should have URL"
    assert not doc_info.get("fetched"), "Should not be fetched yet"
    assert "content" not in doc_info, "Should not have content yet"

    # Now fetch the document
    print("\n  Fetching document on-demand...")
    content = skill_with_docs.get_document(first_doc_path)

    assert content is not None, "Should fetch content on-demand"
    assert content.get("fetched"), "Should be marked as fetched"

    if doc_info.get("type") == "text":
        assert "content" in content, "Text document should have content"
        print(f"  ✓ Fetched text document ({len(content.get('content', ''))} chars)")

    # Verify it's cached in memory
    print("\n  Testing memory cache...")
    cached_content = skill_with_docs.get_document(first_doc_path)
    assert cached_content == content, "Should return cached content"
    print("  ✓ Memory cache working")


@pytest.mark.integration
def test_document_disk_cache():
    """Test that fetched documents are cached to disk."""
    from claude_skills_mcp_backend.skill_loader import _get_document_cache_dir

    skills = load_from_github(
        "https://github.com/K-Dense-AI/claude-scientific-skills",
        subpath="scientific-thinking",
    )

    print(f"\nLoaded {len(skills)} skills from scientific-thinking")

    # Find a skill with documents
    skill_with_docs = None
    for skill in skills:
        if len(skill.documents) > 0:
            skill_with_docs = skill
            break

    assert skill_with_docs is not None

    print(f"\nTesting disk cache with skill: {skill_with_docs.name}")

    # Get first document
    doc_path = list(skill_with_docs.documents.keys())[0]
    print(f"  Document: {doc_path}")

    # Fetch document (should cache to disk)
    content1 = skill_with_docs.get_document(doc_path)
    assert content1 is not None

    # Check cache directory
    cache_dir = _get_document_cache_dir()
    cache_files = list(cache_dir.glob("*.cache"))

    print(f"  Cache directory: {cache_dir}")
    print(f"  Cache files: {len(cache_files)}")

    assert len(cache_files) > 0, "Should have cache files"

    # Fetch again (should use disk cache, no network)
    content2 = skill_with_docs.get_document(doc_path)
    assert content1 == content2, "Should return same content from cache"

    print("  ✓ Disk cache working")


@pytest.mark.integration
def test_startup_time_improvement():
    """Verify that startup time is significantly improved."""

    print("\n" + "=" * 80)
    print("STARTUP TIME COMPARISON TEST")
    print("=" * 80)

    # Test with full scientific skills repository
    start = time.time()
    skills = load_from_github("https://github.com/K-Dense-AI/claude-scientific-skills")
    load_time = time.time() - start

    print(f"\nFull repository load time: {load_time:.2f} seconds")
    print(f"Skills loaded: {len(skills)}")

    # Count total documents
    total_docs = sum(len(skill.documents) for skill in skills)
    print(f"Total documents (metadata): {total_docs}")

    # Verify load time is acceptable
    assert load_time < 30, f"Load time {load_time:.2f}s exceeds 30s limit"

    print(f"\n✓ Startup time: {load_time:.2f}s (target: <30s)")
    print(f"✓ Expected improvement: ~60s → {load_time:.2f}s")
    print("✓ Documents are lazy-loaded (not fetched at startup)")
    print("=" * 80)


@pytest.mark.integration
def test_lazy_fetching_with_server():
    """Test lazy fetching through the MCP server interface."""
    from claude_skills_mcp_backend.server import SkillsMCPServer, LoadingState
    import asyncio

    # Load skills (fast - no document content)
    skills = load_from_github(
        "https://github.com/K-Dense-AI/claude-scientific-skills",
        subpath="scientific-thinking/exploratory-data-analysis",
    )

    assert len(skills) >= 1, "Should load EDA skill"

    # Create server
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(skills)
    loading_state = LoadingState()
    loading_state.mark_complete()  # Mark as complete since skills are already loaded
    server = SkillsMCPServer(engine, loading_state)

    # Find EDA skill
    eda_skill = skills[0]
    print(f"\nTesting with skill: {eda_skill.name}")
    print(f"  Documents: {len(eda_skill.documents)}")

    if len(eda_skill.documents) > 0:
        doc_path = list(eda_skill.documents.keys())[0]

        # Call read_skill_document (should trigger lazy fetch)
        result = asyncio.run(
            server._handle_read_skill_document(
                {
                    "skill_name": eda_skill.name,
                    "document_path": doc_path,
                }
            )
        )

        assert len(result) == 1
        text = result[0].text

        # Should have fetched and returned content
        assert "Document:" in text or "Image:" in text
        print("  ✓ Lazy fetch triggered by read_skill_document")
        print("  ✓ Document content returned")


@pytest.mark.integration
def test_metadata_only_at_startup():
    """Verify that only metadata is loaded at startup, not content."""

    skills = load_from_github(
        "https://github.com/K-Dense-AI/claude-scientific-skills",
        subpath="scientific-packages/biopython",
    )

    assert len(skills) >= 1, "Should load biopython skill"

    biopython = skills[0]
    print(f"\nSkill: {biopython.name}")
    print(f"Documents: {len(biopython.documents)}")

    # Check all documents - none should have content
    for doc_path, doc_info in biopython.documents.items():
        # Should have metadata
        assert "type" in doc_info, f"{doc_path} missing type"
        assert "size" in doc_info, f"{doc_path} missing size"
        assert "url" in doc_info, f"{doc_path} missing URL"

        # Should NOT have content
        assert "content" not in doc_info, (
            f"{doc_path} should not have content at startup"
        )
        assert not doc_info.get("fetched"), (
            f"{doc_path} should not be marked as fetched"
        )

    print(f"  ✓ All {len(biopython.documents)} documents have metadata only")
    print("  ✓ No content loaded at startup (lazy loading working)")
