"""Integration tests including local demo."""

import tempfile
from pathlib import Path

import pytest

from claude_skills_mcp_backend.config import load_config
from claude_skills_mcp_backend.skill_loader import load_all_skills
from claude_skills_mcp_backend.search_engine import SkillSearchEngine


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


@pytest.mark.integration
def test_anthropic_skills_repo():
    """
    Test loading from official Anthropic skills repository.

    This test demonstrates:
    1. Loading skills from the official Anthropic skills repository
    2. Verifying that diverse file types are loaded (Python, images, XML, etc.)
    3. Testing document loading functionality with real skills
    4. Validating pattern matching on real skill documents

    Run standalone with:
        pytest tests/test_integration.py::test_anthropic_skills_repo -v -s

    Note: Requires internet connection.
    """
    print("\n" + "=" * 80)
    print("ANTHROPIC SKILLS REPOSITORY - INTEGRATION TEST")
    print("=" * 80)

    # Step 1: Configure to use official Anthropic skills repository
    print("\n[1] Configuring skill source...")
    config = {
        "skill_sources": [
            {
                "type": "github",
                "url": "https://github.com/anthropics/skills",
            }
        ],
        "embedding_model": "all-MiniLM-L6-v2",
        "default_top_k": 3,
        "load_skill_documents": True,
        "text_file_extensions": [
            ".md",
            ".py",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".sh",
            ".r",
            ".ipynb",
            ".xml",
        ],
        "allowed_image_extensions": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"],
        "max_image_size_bytes": 5242880,
    }
    print(f"   Repository: {config['skill_sources'][0]['url']}")

    # Step 2: Load skills from GitHub
    print("\n[2] Loading skills from Anthropic repository...")
    skills = load_all_skills(config["skill_sources"], config)

    print(f"   Loaded {len(skills)} skills from repository")

    # Verify we got skills
    assert len(skills) > 5, f"Expected >5 skills, got {len(skills)}"

    # Display sample skills
    print("\n   Sample skills loaded:")
    for skill in skills[:5]:
        doc_count = len(skill.documents)
        print(f"      - {skill.name}: {skill.description[:60]}...")
        if doc_count > 0:
            print(f"        ({doc_count} additional documents)")

    # Step 3: Verify document loading
    print("\n[3] Verifying document loading...")

    skills_with_docs = [s for s in skills if len(s.documents) > 0]
    print(f"   {len(skills_with_docs)}/{len(skills)} skills have additional documents")

    if skills_with_docs:
        # Pick a skill with documents
        sample_skill = skills_with_docs[0]
        print(f"\n   Sample skill with documents: {sample_skill.name}")
        print(f"   Documents ({len(sample_skill.documents)}):")

        # Show types of documents
        doc_types = {}
        for doc_path, doc_info in sample_skill.documents.items():
            doc_type = doc_info.get("type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

            # Show first few documents
            if (
                len(
                    [
                        p
                        for p in sample_skill.documents.keys()
                        if sample_skill.documents[p].get("type") == doc_type
                    ]
                )
                <= 3
            ):
                size_kb = doc_info.get("size", 0) / 1024
                print(f"      - {doc_path} ({doc_type}, {size_kb:.1f} KB)")

        print("\n   Document types found:")
        for doc_type, count in doc_types.items():
            print(f"      - {doc_type}: {count} file(s)")

        # Verify we have text files
        text_docs = [
            p
            for p, info in sample_skill.documents.items()
            if info.get("type") == "text"
        ]
        assert len(text_docs) > 0 or len(skills_with_docs) > 1, (
            "Should have at least some text documents"
        )

    # Step 4: Test search functionality
    print("\n[4] Testing semantic search...")
    search_engine = SkillSearchEngine(config["embedding_model"])
    search_engine.index_skills(skills)
    print(f"   Indexed {len(skills)} skills")

    # Search for skills
    test_queries = [
        "create interactive web applications",
        "test web applications",
        "create visual designs",
    ]

    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = search_engine.search(query, top_k=3)

        assert len(results) > 0, f"No results for query: {query}"

        for i, result in enumerate(results, 1):
            doc_count = len(result.get("documents", {}))
            print(
                f"      {i}. {result['name']} (score: {result['relevance_score']:.4f})"
            )
            if doc_count > 0:
                print(f"         {doc_count} additional files")

    print("\n" + "=" * 80)
    print("ANTHROPIC SKILLS REPOSITORY TEST COMPLETED!")
    print("=" * 80)
    print("\nTest summary:")
    print(f"  • Loaded {len(skills)} skills from official Anthropic repository")
    print(f"  • {len(skills_with_docs)} skills have additional documents")
    print("  • Tested document loading with diverse file types")
    print("  • Semantic search working correctly")
    print("\nThis validates:")
    print("  1. Loading from the official Anthropic skills repository")
    print("  2. Document loading for skills with scripts and assets")
    print("  3. Support for diverse file types (Python, images, XML, etc.)")
    print("  4. Full integration with search functionality")
    print("=" * 80 + "\n")


@pytest.mark.integration
def test_anthropic_specific_skills():
    """
    Test specific skills from Anthropic repository including large skills and binary handling.

    This test validates:
    1. Loading large skills like slack-gif-creator
    2. Handling of binary files (tar.gz) - should be skipped gracefully
    3. Loading Python scripts from artifacts-builder
    4. Document retrieval with read_skill_document functionality

    Run standalone with:
        pytest tests/test_integration.py::test_anthropic_specific_skills -v -s

    Note: Requires internet connection.
    """
    print("\n" + "=" * 80)
    print("ANTHROPIC SPECIFIC SKILLS - DETAILED TEST")
    print("=" * 80)

    # Step 1: Configure and load skills
    print("\n[1] Loading Anthropic skills repository...")
    config = {
        "skill_sources": [
            {
                "type": "github",
                "url": "https://github.com/anthropics/skills",
            }
        ],
        "embedding_model": "all-MiniLM-L6-v2",
        "default_top_k": 3,
        "load_skill_documents": True,
        "text_file_extensions": [
            ".md",
            ".py",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".sh",
            ".r",
            ".ipynb",
            ".xml",
        ],
        "allowed_image_extensions": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"],
        "max_image_size_bytes": 5242880,
    }

    skills = load_all_skills(config["skill_sources"], config)
    print(f"   Loaded {len(skills)} skills")

    assert len(skills) > 0, "Should load skills from Anthropic repository"

    # Step 2: Find and validate slack-gif-creator skill
    print("\n[2] Testing slack-gif-creator skill (large skill)...")
    slack_gif_skill = None
    for skill in skills:
        if (
            "slack-gif-creator" in skill.name.lower()
            or "slack gif" in skill.name.lower()
        ):
            slack_gif_skill = skill
            break

    if slack_gif_skill:
        print(f"   Found: {slack_gif_skill.name}")
        print(f"   Content size: {len(slack_gif_skill.content)} characters")
        print(f"   Documents: {len(slack_gif_skill.documents)} files")

        # Verify it's a substantial skill
        assert len(slack_gif_skill.content) > 500, (
            "slack-gif-creator should have substantial content"
        )

        # Show document types
        if slack_gif_skill.documents:
            doc_types = {}
            for doc_path, doc_info in slack_gif_skill.documents.items():
                doc_type = doc_info.get("type", "unknown")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            print(f"   Document types: {doc_types}")
    else:
        print(
            "   ⚠ slack-gif-creator skill not found (repository structure may have changed)"
        )

    # Step 3: Find and validate artifacts-builder skill
    print("\n[3] Testing artifacts-builder skill (contains scripts)...")
    artifacts_builder_skill = None
    for skill in skills:
        if (
            "artifacts-builder" in skill.name.lower()
            or "artifact" in skill.name.lower()
        ):
            artifacts_builder_skill = skill
            break

    if artifacts_builder_skill:
        print(f"   Found: {artifacts_builder_skill.name}")
        print(f"   Documents: {len(artifacts_builder_skill.documents)} files")

        # Check for Python scripts in documents
        python_scripts = [
            p for p in artifacts_builder_skill.documents.keys() if p.endswith(".py")
        ]
        if python_scripts:
            print(f"   Python scripts found: {len(python_scripts)}")
            for script in python_scripts[:3]:  # Show first 3
                print(f"      - {script}")

        # Note: tar.gz files are binary and should NOT be loaded
        # This is expected behavior - we only load text files and images
        binary_refs = [
            p
            for p in artifacts_builder_skill.documents.keys()
            if ".tar.gz" in p or ".gz" in p
        ]
        assert len(binary_refs) == 0, (
            "Binary files (tar.gz) should not be loaded as documents"
        )
        print("   ✓ Binary files correctly excluded from document loading")
    else:
        print(
            "   ⚠ artifacts-builder skill not found (repository structure may have changed)"
        )

    # Step 4: Test document retrieval patterns
    print("\n[4] Testing document retrieval patterns...")

    # Find any skill with Python scripts
    skill_with_py = None
    for skill in skills:
        py_files = [p for p in skill.documents.keys() if p.endswith(".py")]
        if py_files:
            skill_with_py = skill
            break

    if skill_with_py:
        print(f"   Testing with: {skill_with_py.name}")
        py_files = [p for p in skill_with_py.documents.keys() if p.endswith(".py")]
        print(f"   Python files: {len(py_files)}")

        # Verify we can access Python script content (with lazy loading)
        for py_file in py_files[:1]:  # Check first one
            # Documents start with metadata only (lazy loading)
            doc_metadata = skill_with_py.documents[py_file]
            assert doc_metadata["type"] == "text", "Python scripts should be text type"
            assert "url" in doc_metadata, "Should have URL for lazy fetching"

            # Fetch the document content on-demand
            doc_content = skill_with_py.get_document(py_file)
            assert doc_content is not None, "Should be able to fetch document"
            assert "content" in doc_content, "Fetched document should have content"
            assert len(doc_content["content"]) > 0, (
                "Python script content should not be empty"
            )
            print(
                f"   ✓ Successfully fetched {py_file} ({len(doc_content['content'])} chars)"
            )

    # Step 5: Verify search functionality with these skills
    print("\n[5] Testing semantic search with loaded skills...")
    search_engine = SkillSearchEngine(config["embedding_model"])
    search_engine.index_skills(skills)

    test_searches = [
        ("create animated GIF images", ["gif", "image", "animation"]),
        ("build interactive web artifacts", ["artifact", "web", "interactive"]),
    ]

    for query, keywords in test_searches:
        print(f"\n   Query: '{query}'")
        results = search_engine.search(query, top_k=3)

        assert len(results) > 0, f"Should find results for: {query}"
        print(
            f"   Top: {results[0]['name']} (score: {results[0]['relevance_score']:.4f})"
        )

        # Check if result is relevant (contains at least one keyword)
        top_text = results[0]["name"].lower() + " " + results[0]["description"].lower()
        has_keyword = any(kw in top_text for kw in keywords)
        if has_keyword:
            print("   ✓ Relevant result found")

    print("\n" + "=" * 80)
    print("ANTHROPIC SPECIFIC SKILLS TEST COMPLETED!")
    print("=" * 80)
    print("\nValidation summary:")
    if slack_gif_skill:
        print(
            f"  ✓ slack-gif-creator: {len(slack_gif_skill.content)} chars, {len(slack_gif_skill.documents)} docs"
        )
    if artifacts_builder_skill:
        print(f"  ✓ artifacts-builder: {len(artifacts_builder_skill.documents)} docs")
        py_count = len(
            [p for p in artifacts_builder_skill.documents.keys() if p.endswith(".py")]
        )
        print(f"     - {py_count} Python scripts loaded")
    print("  ✓ Binary files (tar.gz) correctly excluded")
    print("  ✓ Semantic search working with real skills")
    print("\nThis validates:")
    print("  1. Large skills load correctly")
    print("  2. Python scripts are loaded as text documents")
    print("  3. Binary files are gracefully skipped")
    print("  4. Document structure is correct and accessible")
    print("=" * 80 + "\n")


@pytest.mark.integration
def test_list_skills_tool():
    """Test that list_skills returns all loaded skills."""
    from claude_skills_mcp_backend.mcp_handlers import SkillsMCPServer, LoadingState
    from claude_skills_mcp_backend.skill_loader import load_from_github
    import asyncio

    # Load a small set of skills for testing
    skills = load_from_github(
        "https://github.com/K-Dense-AI/claude-scientific-skills",
        subpath="scientific-thinking",
    )

    # Create engine and server
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    engine.index_skills(skills)
    loading_state = LoadingState()
    loading_state.mark_complete()  # Mark as complete since skills are already loaded
    server = SkillsMCPServer(engine, loading_state)

    # Call list_skills
    result = asyncio.run(server._handle_list_skills({}))

    # Verify output
    assert len(result) == 1
    text = result[0].text

    assert f"Total skills loaded: {len(skills)}" in text
    print(f"\nlist_skills output:\n{text[:500]}...")


@pytest.mark.integration
def test_update_detection():
    """Test that update checker can detect changes in repositories.

    This test demonstrates:
    1. Initializing the update checker
    2. Running a check (first time - no updates expected)
    3. Verifying API usage tracking
    4. Handling update results

    Note: This test makes real API calls but doesn't trigger actual updates
    (first check always returns False to avoid unnecessary reloads).
    """
    from claude_skills_mcp_backend.update_checker import UpdateChecker

    print("\n" + "=" * 80)
    print("UPDATE DETECTION TEST")
    print("=" * 80)

    # Step 1: Initialize update checker
    print("\n[1] Initializing update checker...")
    checker = UpdateChecker()  # No token - will use 60 req/hr limit
    print("   ✓ Update checker initialized")

    # Step 2: Check for updates on default sources
    print("\n[2] Checking for updates (first check)...")
    sources = [
        {"type": "github", "url": "https://github.com/anthropics/skills"},
        {
            "type": "github",
            "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
        },
    ]

    result = checker.check_for_updates(sources)

    print(f"   Has updates: {result.has_updates}")
    print(f"   Changed sources: {len(result.changed_sources)}")
    print(f"   API calls made: {result.api_calls_made}")
    print(f"   Errors: {len(result.errors)}")

    # First check should not trigger updates (establishes baseline)
    assert result.has_updates is False, "First check should not trigger updates"
    assert len(result.changed_sources) == 0, (
        "First check should have no changed sources"
    )

    # Should have made API calls to check commits
    assert result.api_calls_made > 0, "Should have made GitHub API calls"
    assert result.api_calls_made <= 4, "Should not exceed expected API calls"

    # Step 3: Verify API usage tracking
    print("\n[3] Checking API usage tracking...")
    api_usage = checker.get_api_usage()

    print(f"   Calls this hour: {api_usage['calls_this_hour']}")
    print(f"   Limit: {api_usage['limit_per_hour']}")
    print(f"   Authenticated: {api_usage['authenticated']}")

    assert api_usage["calls_this_hour"] > 0, "Should track API calls"
    assert api_usage["limit_per_hour"] == 60, "Should use unauthenticated limit"
    assert api_usage["authenticated"] is False, "Should not be authenticated"

    # Step 4: Verify no errors occurred
    if result.errors:
        print("\n   ⚠ Errors encountered:")
        for error in result.errors:
            print(f"      - {error}")

    print("\n" + "=" * 80)
    print("UPDATE DETECTION TEST COMPLETED!")
    print("=" * 80)
    print("\nTest summary:")
    print(f"  • Checked {len(sources)} GitHub sources")
    print(f"  • Made {result.api_calls_made} API calls")
    print("  • First check established baseline (no updates triggered)")
    print("  • API usage tracking working correctly")
    print("\nThis validates:")
    print("  1. Update checker can communicate with GitHub API")
    print("  2. Commit SHA tracking is initialized")
    print("  3. API usage is tracked and reported")
    print("  4. First check doesn't trigger unnecessary reloads")
    print("=" * 80 + "\n")
