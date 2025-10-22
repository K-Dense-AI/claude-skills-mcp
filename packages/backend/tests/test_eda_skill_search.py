"""Tests specifically for the EDA skill search issue."""

import pytest
import numpy as np
from claude_skills_mcp_backend.search_engine import SkillSearchEngine
from claude_skills_mcp_backend.skill_loader import load_from_github


@pytest.mark.integration
def test_eda_skill_exists():
    """Verify that the EDA skill is actually loaded from the repository."""
    skills = load_from_github("https://github.com/K-Dense-AI/claude-scientific-skills")

    # Find EDA skill
    eda_skill = None
    for skill in skills:
        if "exploratory" in skill.name.lower() or "eda" in skill.name.lower():
            eda_skill = skill
            break

    assert eda_skill is not None, "EDA skill not found in loaded skills"

    print("\nFound EDA skill:")
    print(f"  Name: {eda_skill.name}")
    print(f"  Description length: {len(eda_skill.description)} chars")
    print(f"  Description: {eda_skill.description[:200]}...")
    print(f"  Source: {eda_skill.source}")


@pytest.mark.integration
def test_eda_skill_search_ranking():
    """Test if EDA skill appears in search results for relevant queries."""
    skills = load_from_github("https://github.com/K-Dense-AI/claude-scientific-skills")

    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(skills)

    # Test queries that should find EDA skill
    test_queries = [
        "exploratory data analysis",
        "EDA data exploration",
        "explore and visualize dataset",
    ]

    for query in test_queries:
        results = engine.search(query, top_k=10)

        print(f"\nQuery: '{query}'")
        print("Top 10 results:")

        eda_found = False
        eda_rank = None

        for i, result in enumerate(results, 1):
            is_eda = (
                "exploratory" in result["name"].lower()
                or "eda" in result["name"].lower()
            )
            marker = " <- EDA SKILL" if is_eda else ""
            print(
                f"  {i}. {result['name']} (score: {result['relevance_score']:.4f}){marker}"
            )

            if is_eda:
                eda_found = True
                eda_rank = i

        if eda_found:
            print(f"\n  ✓ EDA skill found at rank {eda_rank}")
            # Should be in top 5 for these specific queries
            assert eda_rank <= 5, (
                f"EDA skill ranked too low ({eda_rank}) for query '{query}'"
            )
        else:
            print("\n  ✗ EDA skill NOT in top 10")
            pytest.fail(f"EDA skill not found in top 10 results for query '{query}'")


@pytest.mark.integration
def test_description_length_impact():
    """Test if long descriptions cause embedding issues."""
    skills = load_from_github("https://github.com/K-Dense-AI/claude-scientific-skills")

    # Analyze description lengths
    desc_lengths = [(skill.name, len(skill.description)) for skill in skills]
    desc_lengths.sort(key=lambda x: x[1], reverse=True)

    print("\nTop 10 longest descriptions:")
    for name, length in desc_lengths[:10]:
        print(f"  {name}: {length} chars")

    print("\nTop 10 shortest descriptions:")
    for name, length in desc_lengths[-10:]:
        print(f"  {name}: {length} chars")

    # Test if long-description skills get lower scores
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(skills)

    # Create a mapping of skill name to description length
    length_map = {skill.name: len(skill.description) for skill in skills}

    # Search for a general query
    results = engine.search("data analysis and visualization", top_k=20)

    print("\nCorrelation between description length and search rank:")
    for i, result in enumerate(results[:10], 1):
        desc_len = length_map.get(result["name"], 0)
        print(
            f"  Rank {i}: {result['name'][:40]:40} "
            f"length={desc_len:5} score={result['relevance_score']:.4f}"
        )

    # Calculate correlation between rank and description length
    ranks = list(range(1, len(results) + 1))
    lengths = [length_map.get(r["name"], 0) for r in results]

    correlation = np.corrcoef(ranks, lengths)[0, 1]
    print(f"\nCorrelation between rank and description length: {correlation:.4f}")
    print("(Positive correlation means longer descriptions rank lower)")
