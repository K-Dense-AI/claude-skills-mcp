# Testing Guide

This guide provides comprehensive testing instructions beyond the Quick Start in the main README.

## Test Suite Overview

**40 tests total:**
- 9 configuration tests
- 12 skill loading tests  
- 11 search engine tests
- 4 GitHub URL parsing tests
- 4 integration tests (includes local + repo demos)

## Running Tests

### Quick Commands

```bash
# All tests (with coverage)
uv run pytest tests/

# Unit tests only (fast, ~20s)
uv run pytest tests/ -m "not integration"

# Integration tests only (requires internet)
uv run pytest tests/ -m "integration"

# Specific test file
uv run pytest tests/test_search_engine.py -v

# Specific test
uv run pytest tests/test_integration.py::test_local_demo -v -s
```

## Integration Test Demos

### Local Demo Test

Demonstrates creating temporary local skills and performing semantic search:

```bash
pytest tests/test_integration.py::test_local_demo -v -s
```

**What it does:**
1. Creates 3 temporary skills (Bioinformatics, ML, Visualization)
2. Indexes them with embeddings
3. Performs 3 semantic searches
4. Validates correct skills are returned with good scores

**Output shows:**
- Skill loading process
- Indexing progress
- Query-by-query results with relevance scores
- Validation that correct skills match queries

### Repository Demo Test

Demonstrates loading real skills from K-Dense AI repository:

```bash
pytest tests/test_integration.py::test_repo_demo -v -s
```

**What it does:**
1. Loads 70+ skills from GitHub
2. Verifies expected skills exist (biopython, rdkit, scanpy, etc.)
3. Tests 4 domain-specific queries
4. Validates search quality across scientific domains

**Output shows:**
- Skills loaded from GitHub
- Domain-specific search results
- Relevance scores for each query
- Validation of skill metadata quality

## Testing with MCP Clients

### Option 1: Claude Desktop (Recommended)

**Setup:**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "claude-skills-local": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/yourusername/path/to/claude-skills-mcp",
        "run",
        "claude-skills-mcp",
        "--verbose"
      ]
    }
  }
}
```

**Test queries in Claude:**
- "What skills can help me analyze RNA sequencing data?"
- "Find skills for protein structure prediction"
- "Search for drug discovery tools"

You should see Claude invoke the `search_skills` tool in its chain of thought.

### Option 2: MCP Inspector (Debugging)

Interactive web-based testing:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/claude-skills-mcp run claude-skills-mcp
```

This opens a web UI where you can:
- See available tools
- Call `search_skills` with custom queries
- View request/response JSON
- Debug protocol issues

## Test Details by Module

### Configuration Tests (`test_config.py`)

Tests configuration loading, validation, and defaults:
- Loading from file vs defaults
- Invalid/missing config files
- Example config generation
- Different `top_k` values

### Skill Loader Tests (`test_skill_loader.py`)

Tests skill parsing and loading:
- YAML frontmatter parsing
- Missing or malformed SKILL.md files
- Local directory scanning
- Home directory expansion (~)
- Error handling for inaccessible paths

### Search Engine Tests (`test_search_engine.py`)

Tests vector search functionality:
- Embedding generation and indexing
- Cosine similarity computation
- Top-K result limiting
- Relevance score ordering
- Empty index handling
- Query-skill matching accuracy

### GitHub URL Tests (`test_github_url_parsing.py`)

Tests URL parsing with branches and subpaths:
- Browser-style URLs: `github.com/owner/repo/tree/branch/subpath`
- Base repository URLs
- Deep nested subpaths
- Subpath parameter override logic

### Integration Tests (`test_integration.py`)

End-to-end workflow tests:
- Local demo (temporary skills)
- Repository demo (K-Dense AI skills)
- Default configuration workflow
- Mixed sources (GitHub + local)

## Coverage Analysis

### Current Coverage: 56%

Coverage is **enabled by default**. Every test run shows statistics.

**Module breakdown:**
- `__init__.py`: 100% ✅
- `search_engine.py`: 100% ✅
- `config.py`: 86% ✅
- `skill_loader.py`: 68% ⚠️ (GitHub loading in integration tests)
- `server.py`: 0% (MCP runtime, tested end-to-end)
- `__main__.py`: 0% (CLI entry, tested end-to-end)

### Generate Coverage Reports

**Terminal report** (default):
```bash
uv run pytest tests/
# Shows coverage automatically
```

**HTML report** (interactive):
```bash
uv run pytest tests/ --cov-report=html
open htmlcov/index.html
```

**Disable coverage** (faster for development):
```bash
uv run pytest tests/ --no-cov
```

### Coverage Tips

Lines marked as missing are often:
- Error handling paths (tested in integration)
- GitHub API fallback logic (tested with live repos)
- MCP server runtime (tested via client connections)

Focus coverage improvements on core business logic in `config.py` and `skill_loader.py`.

## Continuous Integration

GitHub Actions runs automatically on all PRs to `main`:

**Workflow** (`.github/workflows/test.yml`):
- Runs on: Pull requests and pushes to main
- Python version: 3.12 (enforced)
- Unit tests with coverage
- Integration tests
- Build verification

View CI results at: `https://github.com/K-Dense-AI/claude-skills-mcp/actions`

## Writing New Tests

### Adding a Unit Test

```python
# tests/test_mymodule.py
import pytest
from src.claude_skills_mcp.mymodule import my_function

def test_my_function():
    """Test my function with valid input."""
    result = my_function("input")
    assert result == "expected"

@pytest.mark.parametrize("input,expected", [
    ("a", "result_a"),
    ("b", "result_b"),
])
def test_my_function_parametrized(input, expected):
    """Test multiple cases."""
    assert my_function(input) == expected
```

### Adding an Integration Test

```python
# tests/test_integration.py
import pytest

@pytest.mark.integration
def test_my_integration():
    """Integration test requiring external resources."""
    # Your test code
    pass
```

Mark with `@pytest.mark.integration` so it can be excluded with `-m "not integration"`.

