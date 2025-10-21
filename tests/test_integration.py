"""Integration tests including local demo."""

import tempfile
from pathlib import Path

import pytest

from src.claude_skills_mcp.config import load_config
from src.claude_skills_mcp.skill_loader import load_all_skills
from src.claude_skills_mcp.search_engine import SkillSearchEngine


@pytest.mark.integration
def test_local_demo():
    """
    Local demo test showing end-to-end functionality with local skills.

    This test demonstrates:
    1. Creating local skills in a temporary directory
    2. Configuring the system to use these local skills
    3. Indexing the skills with vector embeddings
    4. Performing semantic search
    5. Validating search results

    Run standalone with:
        pytest tests/test_integration.py::test_local_demo -v
    """
    print("\n" + "=" * 80)
    print("CLAUDE SKILLS MCP SERVER - LOCAL DEMO")
    print("=" * 80)

    # Step 1: Create temporary directory with test skills
    print("\n[1] Creating temporary local skills...")
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # Create bioinformatics skill
        bio_skill_dir = temp_path / "bioinformatics"
        bio_skill_dir.mkdir()
        (bio_skill_dir / "SKILL.md").write_text("""---
name: Bioinformatics Analysis
description: Analyze genomic sequences, perform alignment, and identify variants
---

# Bioinformatics Analysis

This skill provides tools and methods for comprehensive bioinformatics analysis.

## Capabilities

- DNA/RNA sequence analysis
- Multiple sequence alignment
- Variant calling and annotation
- Gene expression analysis
- Phylogenetic tree construction

## Example Usage

```python
from Bio import SeqIO
# Analyze sequences
```
""")

        # Create machine learning skill
        ml_skill_dir = temp_path / "machine-learning"
        ml_skill_dir.mkdir()
        (ml_skill_dir / "SKILL.md").write_text("""---
name: Machine Learning Models
description: Build and train machine learning models for predictive analytics
---

# Machine Learning Models

This skill covers various machine learning techniques and frameworks.

## Capabilities

- Supervised learning (classification, regression)
- Unsupervised learning (clustering, dimensionality reduction)
- Model evaluation and validation
- Feature engineering
- Hyperparameter tuning

## Example Usage

```python
from sklearn.ensemble import RandomForestClassifier
# Train model
```
""")

        # Create data visualization skill
        viz_skill_dir = temp_path / "data-visualization"
        viz_skill_dir.mkdir()
        (viz_skill_dir / "SKILL.md").write_text("""---
name: Data Visualization
description: Create interactive and publication-quality visualizations
---

# Data Visualization

This skill provides tools for creating stunning data visualizations.

## Capabilities

- Statistical plots
- Interactive dashboards
- Heatmaps and clustering visualizations
- Time series plots
- Network graphs

## Example Usage

```python
import matplotlib.pyplot as plt
import seaborn as sns
# Create plots
```
""")

        print(f"   Created 3 test skills in {temp_path}")

        # Step 2: Configure to use local skills
        print("\n[2] Configuring skill sources...")
        config = {
            "skill_sources": [{"type": "local", "path": str(temp_path)}],
            "embedding_model": "all-MiniLM-L6-v2",
            "default_top_k": 3,
        }
        print(f"   Using local path: {temp_path}")

        # Step 3: Load skills
        print("\n[3] Loading skills from local directory...")
        skills = load_all_skills(config["skill_sources"])
        print(f"   Loaded {len(skills)} skills:")
        for skill in skills:
            print(f"      - {skill.name}: {skill.description}")

        assert len(skills) == 3
        skill_names = {skill.name for skill in skills}
        assert "Bioinformatics Analysis" in skill_names
        assert "Machine Learning Models" in skill_names
        assert "Data Visualization" in skill_names

        # Step 4: Initialize search engine and index skills
        print("\n[4] Indexing skills with vector embeddings...")
        search_engine = SkillSearchEngine(config["embedding_model"])
        search_engine.index_skills(skills)
        print(f"   Indexed {len(skills)} skills")

        # Step 5: Perform searches
        print("\n[5] Performing semantic searches...")

        test_queries = [
            (
                "I need to analyze DNA sequences and find mutations",
                "Bioinformatics Analysis",
            ),
            (
                "Build a classification model to predict outcomes",
                "Machine Learning Models",
            ),
            ("Create interactive plots for my data", "Data Visualization"),
        ]

        for query, expected_top in test_queries:
            print(f"\n   Query: '{query}'")
            results = search_engine.search(query, top_k=2)

            assert len(results) > 0
            print(
                f"   Top result: {results[0]['name']} (score: {results[0]['relevance_score']:.4f})"
            )

            # Validate top result
            assert results[0]["name"] == expected_top, (
                f"Expected '{expected_top}' but got '{results[0]['name']}'"
            )

            # Validate structure
            assert "description" in results[0]
            assert "content" in results[0]
            assert "source" in results[0]
            assert "relevance_score" in results[0]
            assert 0 <= results[0]["relevance_score"] <= 1

            print(f"   ✓ Correctly identified '{expected_top}'")

        print("\n" + "=" * 80)
        print("LOCAL DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nDemonstration summary:")
        print(f"  • Created {len(skills)} local skills")
        print("  • Indexed skills with vector embeddings")
        print(f"  • Performed {len(test_queries)} semantic searches")
        print("  • All searches returned correct top results")
        print("\nThis demonstrates the core MCP server functionality:")
        print("  1. Loading skills from local directories")
        print("  2. Vector embedding generation")
        print("  3. Semantic similarity search")
        print("  4. Returning relevant skills with scores")
        print("=" * 80 + "\n")


@pytest.mark.integration
def test_end_to_end_with_default_config():
    """Test end-to-end functionality with default configuration.

    This test verifies the full workflow using the default GitHub source.
    Note: Requires internet connection.
    """
    # Load default configuration
    config = load_config()

    assert "skill_sources" in config
    assert len(config["skill_sources"]) > 0

    # Load skills from GitHub (default source)
    skills = load_all_skills(config["skill_sources"])

    # Should load at least some skills
    assert len(skills) > 0
    print(f"\nLoaded {len(skills)} skills from default source")

    # Index skills
    search_engine = SkillSearchEngine(config["embedding_model"])
    search_engine.index_skills(skills)

    # Perform a search
    results = search_engine.search("analyze RNA sequencing data", top_k=3)

    assert len(results) > 0
    assert results[0]["relevance_score"] > 0

    print(f"Top result: {results[0]['name']}")


@pytest.mark.integration
def test_mixed_sources():
    """Test loading skills from multiple sources simultaneously."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # Create one local skill
        local_skill_dir = temp_path / "local-skill"
        local_skill_dir.mkdir()
        (local_skill_dir / "SKILL.md").write_text("""---
name: Local Skill
description: A skill from local filesystem
---

# Local Skill
""")

        # Configure mixed sources (local + potentially GitHub)
        config = {
            "skill_sources": [
                {"type": "local", "path": str(temp_path)}
                # Could add GitHub source here for real mixed test
            ],
            "embedding_model": "all-MiniLM-L6-v2",
            "default_top_k": 3,
        }

        skills = load_all_skills(config["skill_sources"])

        # Should have at least the local skill
        assert len(skills) >= 1
        skill_names = {skill.name for skill in skills}
        assert "Local Skill" in skill_names


@pytest.mark.integration
def test_repo_demo():
    """
    Repository demo test using K-Dense-AI claude-scientific-skills.

    This test demonstrates:
    1. Loading skills from a real GitHub repository
    2. Verifying skills are loaded correctly with proper metadata
    3. Testing semantic search with domain-specific queries
    4. Validating that relevant scientific skills are found

    Run standalone with:
        pytest tests/test_integration.py::test_repo_demo -v

    Note: Requires internet connection.
    """
    print("\n" + "=" * 80)
    print("CLAUDE SKILLS MCP SERVER - GITHUB REPOSITORY DEMO")
    print("=" * 80)

    # Step 1: Configure to use K-Dense-AI scientific skills repository
    print("\n[1] Configuring skill source...")
    config = {
        "skill_sources": [
            {
                "type": "github",
                "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
            }
        ],
        "embedding_model": "all-MiniLM-L6-v2",
        "default_top_k": 5,
    }
    print(f"   Repository: {config['skill_sources'][0]['url']}")

    # Step 2: Load skills from GitHub
    print("\n[2] Loading skills from GitHub repository...")
    skills = load_all_skills(config["skill_sources"])

    print(f"   Loaded {len(skills)} skills from repository")

    # Verify we got a reasonable number of skills
    assert len(skills) > 50, f"Expected >50 skills, got {len(skills)}"

    # Display sample skills
    print("\n   Sample skills loaded:")
    for skill in skills[:5]:
        print(f"      - {skill.name}: {skill.description[:60]}...")

    # Verify expected skills exist
    skill_names = {skill.name for skill in skills}

    # Check for some well-known skills from the repository
    expected_skills = [
        "biopython",
        "rdkit",
        "scanpy",
        "pubmed-database",
        "alphafold-database",
    ]

    found_expected = [name for name in expected_skills if name in skill_names]
    print(f"\n   Found {len(found_expected)}/{len(expected_skills)} expected skills")

    # At least some expected skills should be present
    assert len(found_expected) >= 3, (
        f"Expected to find at least 3 key skills, found {found_expected}"
    )

    # Step 3: Index skills with search engine
    print("\n[3] Indexing skills with vector embeddings...")
    search_engine = SkillSearchEngine(config["embedding_model"])
    search_engine.index_skills(skills)
    print(f"   Successfully indexed {len(skills)} skills")

    # Step 4: Test domain-specific searches
    print("\n[4] Testing domain-specific semantic searches...")

    test_queries = [
        {
            "query": "I need to analyze RNA sequencing data and identify differentially expressed genes",
            "expected_domains": ["rna", "sequencing", "gene", "expression", "analysis"],
        },
        {
            "query": "Find protein structures and predict folding",
            "expected_domains": ["protein", "structure", "alphafold", "pdb"],
        },
        {
            "query": "Screen chemical compounds for drug discovery",
            "expected_domains": ["drug", "compound", "chemical", "molecule", "chembl"],
        },
        {
            "query": "Access genomic variant data and clinical significance",
            "expected_domains": ["variant", "genomic", "clinical", "mutation"],
        },
    ]

    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        expected_domains = test_case["expected_domains"]

        print(f"\n   Query {i}: '{query}'")
        results = search_engine.search(query, top_k=3)

        assert len(results) > 0, f"No results for query: {query}"

        # Display top results
        for j, result in enumerate(results, 1):
            print(
                f"      {j}. {result['name']} (score: {result['relevance_score']:.4f})"
            )
            print(f"         {result['description'][:80]}...")

        # Validate result quality
        top_result = results[0]
        assert top_result["relevance_score"] > 0.2, (
            f"Top result relevance too low: {top_result['relevance_score']}"
        )

        # Check that at least one expected domain keyword appears in top results
        top_3_text = " ".join(
            [r["name"].lower() + " " + r["description"].lower() for r in results[:3]]
        )

        domain_found = any(domain in top_3_text for domain in expected_domains)
        assert domain_found, (
            f"None of {expected_domains} found in top results for query: {query}"
        )

        print("      ✓ Relevant results found for scientific domain")

    # Step 5: Verify skill content quality
    print("\n[5] Validating skill content quality...")

    # Check a random skill has proper structure
    sample_skill = skills[len(skills) // 2]  # Pick middle skill

    assert sample_skill.name, "Skill must have a name"
    assert sample_skill.description, "Skill must have a description"
    assert len(sample_skill.description) > 20, "Description should be meaningful"
    assert sample_skill.content, "Skill must have content"
    assert len(sample_skill.content) > 100, "Content should be substantial"
    assert sample_skill.source, "Skill must have source URL"
    assert "github.com" in sample_skill.source, "Source should point to GitHub"

    print(f"   ✓ Validated skill structure for: {sample_skill.name}")

    print("\n" + "=" * 80)
    print("GITHUB REPOSITORY DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print("\nDemonstration summary:")
    print(f"  • Loaded {len(skills)} skills from K-Dense-AI repository")
    print(f"  • Found expected scientific skills: {', '.join(found_expected)}")
    print(f"  • Tested {len(test_queries)} domain-specific queries")
    print("  • All queries returned relevant scientific skills")
    print("  • Validated skill metadata and content quality")
    print("\nThis demonstrates real-world MCP server functionality:")
    print("  1. Loading skills from public GitHub repositories")
    print("  2. Parsing SKILL.md files with scientific content")
    print("  3. Vector search across diverse scientific domains")
    print("  4. Returning domain-relevant skills with high accuracy")
    print("=" * 80 + "\n")
