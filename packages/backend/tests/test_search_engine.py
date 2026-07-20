"""Tests for search engine functionality."""

import pytest

from claude_skills_mcp_backend.search_engine import SkillSearchEngine


def test_search_engine_initialization():
    """Test search engine initialization with lazy model loading."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")

    # Model should be None initially (lazy loading)
    assert engine.model is None
    assert engine.model_name == "all-MiniLM-L6-v2"
    assert engine.skills == []
    assert engine.embeddings is None

    # Model should be loaded when ensure_model_loaded is called
    model = engine._ensure_model_loaded()
    assert model is not None
    assert engine.model is not None
    assert engine.model == model


def test_index_skills(mock_skills):
    """Test indexing skills."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(mock_skills)

    assert len(engine.skills) == 3
    assert engine.embeddings is not None
    assert engine.embeddings.shape[0] == 3


def test_index_empty_skills():
    """Test indexing with empty skill list."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills([])

    assert engine.skills == []
    assert engine.embeddings is None


def test_search_basic(mock_skills):
    """Test basic search functionality."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(mock_skills)

    results = engine.search("analyze gene expression", top_k=2)

    assert len(results) == 2
    assert results[0]["name"] in ["RNA Analysis", "Protein Folding", "Drug Discovery"]
    assert "relevance_score" in results[0]
    assert 0 <= results[0]["relevance_score"] <= 1


def test_search_top_k_limit(mock_skills):
    """Test that top_k limits results correctly."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(mock_skills)

    results_1 = engine.search("protein analysis", top_k=1)
    results_2 = engine.search("protein analysis", top_k=2)
    results_all = engine.search("protein analysis", top_k=10)

    assert len(results_1) == 1
    assert len(results_2) == 2
    assert len(results_all) == 3  # Max available


def test_search_relevance_ordering(mock_skills):
    """Test that results are ordered by relevance."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(mock_skills)

    results = engine.search("RNA sequencing gene expression", top_k=3)

    # Results should be sorted by relevance score (highest first)
    for i in range(len(results) - 1):
        assert results[i]["relevance_score"] >= results[i + 1]["relevance_score"]


def test_search_empty_index():
    """Test searching with no indexed skills."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")

    results = engine.search("test query", top_k=3)

    assert results == []


def test_search_result_structure(mock_skills):
    """Test that search results have the expected structure."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(mock_skills)

    results = engine.search("test query", top_k=1)

    assert len(results) > 0
    result = results[0]

    assert "name" in result
    assert "description" in result
    assert "content" in result
    assert "source" in result
    assert "relevance_score" in result


@pytest.mark.parametrize(
    "query,expected_top_skill",
    [
        ("RNA sequencing data", "RNA Analysis"),
        ("protein structure prediction", "Protein Folding"),
        ("drug compound screening", "Drug Discovery"),
    ],
)
def test_search_finds_relevant_skills(mock_skills, query, expected_top_skill):
    """Test that search finds the most relevant skill for specific queries."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(mock_skills)

    results = engine.search(query, top_k=1)

    assert len(results) > 0
    # The top result should be the expected skill (with high probability)
    # Note: This is not guaranteed 100% but should work with good embeddings
    assert results[0]["name"] == expected_top_skill


def test_cosine_similarity():
    """Test cosine similarity computation."""
    import numpy as np
    from claude_skills_mcp_backend.search_engine import SkillSearchEngine

    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([1.0, 0.0, 0.0])
    vec3 = np.array([0.0, 1.0, 0.0])

    matrix = np.array([vec2, vec3])

    similarities = SkillSearchEngine._cosine_similarity(vec1, matrix)

    assert len(similarities) == 2
    assert abs(similarities[0] - 1.0) < 0.001  # Same vector
    assert abs(similarities[1] - 0.0) < 0.001  # Orthogonal


def test_embedding_cache_reuse(mock_skills, monkeypatch, tmp_path):
    """A second engine indexing the same skills reuses cached embeddings.

    On a full cache hit the embedding model is never loaded, which is what
    makes warm startups fast.
    """
    import numpy as np

    monkeypatch.setattr(
        "claude_skills_mcp_backend.search_engine._get_embedding_cache_dir",
        lambda: tmp_path,
    )

    engine1 = SkillSearchEngine("all-MiniLM-L6-v2")
    engine1.index_skills(mock_skills)
    assert engine1.model is not None  # Cache miss: model was loaded

    engine2 = SkillSearchEngine("all-MiniLM-L6-v2")
    engine2.index_skills(mock_skills)
    assert engine2.model is None  # Cache hit: model never loaded
    assert np.array_equal(engine1.embeddings, engine2.embeddings)

    # Search still works after a cache hit (model loads lazily for the query)
    results = engine2.search("analyze gene expression", top_k=1)
    assert len(results) == 1


def test_embedding_cache_corrupt_file_reencodes(mock_skills, monkeypatch, tmp_path):
    """A corrupt cache file is ignored and embeddings are recomputed."""
    monkeypatch.setattr(
        "claude_skills_mcp_backend.search_engine._get_embedding_cache_dir",
        lambda: tmp_path,
    )

    engine1 = SkillSearchEngine("all-MiniLM-L6-v2")
    engine1.index_skills(mock_skills)

    for cache_file in tmp_path.glob("*.npy"):
        cache_file.write_bytes(b"not a numpy file")

    engine2 = SkillSearchEngine("all-MiniLM-L6-v2")
    engine2.index_skills(mock_skills)
    assert engine2.model is not None  # Had to re-encode
    assert engine2.embeddings is not None
    assert engine2.embeddings.shape[0] == len(mock_skills)


def test_embedding_cache_distinct_per_model_and_batch(mock_skills, monkeypatch, tmp_path):
    """Different batches produce distinct cache entries."""
    monkeypatch.setattr(
        "claude_skills_mcp_backend.search_engine._get_embedding_cache_dir",
        lambda: tmp_path,
    )

    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(mock_skills)
    assert len(list(tmp_path.glob("*.npy"))) == 1

    engine.index_skills(mock_skills[:2])
    assert len(list(tmp_path.glob("*.npy"))) == 2
