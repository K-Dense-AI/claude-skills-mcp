# Testing Guide

This guide provides comprehensive testing instructions beyond the Quick Start in the main README.

## Test Suite Overview

The test suite covers unit tests, integration tests, and end-to-end workflows across both frontend and backend packages.

## Running Tests

### Quick Commands

```bash
# Backend tests
cd packages/backend
uv run pytest tests/

# Frontend tests  
cd packages/frontend
uv run pytest tests/

# Integration tests (from repo root)
uv run pytest tests/integration/

# Unit tests only (fast)
cd packages/backend
uv run pytest tests/ -m "not integration"

# Specific test file
uv run pytest tests/test_search_engine.py -v
```

## Integration Test Demos

### Local Demo Test

Demonstrates creating temporary local skills and performing semantic search:

```bash
cd packages/backend
uv run pytest tests/test_integration.py::test_local_demo -v -s
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
cd packages/backend
uv run pytest tests/test_integration.py::test_repo_demo -v -s
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

You should see Claude invoke the `find_helpful_skills` tool in its chain of thought.

### Option 2: MCP Inspector (Debugging)

Interactive web-based testing:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/claude-skills-mcp run claude-skills-mcp
```

This opens a web UI where you can:
- See available tools
- Call `find_helpful_skills` with custom queries
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

Coverage reporting is enabled by default for backend tests.

**Backend module coverage:**
- `search_engine.py`: High coverage
- `config.py`: High coverage
- `skill_loader.py`: Good coverage (GitHub loading in integration tests)
- `mcp_handlers.py`: Tested end-to-end
- `http_server.py`: Tested via integration tests

### Generate Coverage Reports

**Terminal report** (default):
```bash
cd packages/backend
uv run pytest tests/
# Shows coverage automatically
```

**HTML report** (interactive):
```bash
cd packages/backend
uv run pytest tests/ --cov-report=html
open htmlcov/index.html
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
- Separate jobs for backend and frontend testing
- Integration tests
- Build verification

View CI results at: [GitHub Actions](https://github.com/K-Dense-AI/claude-skills-mcp/actions)

## Writing New Tests

### Adding a Unit Test

```python
# packages/backend/tests/test_mymodule.py
import pytest
from claude_skills_mcp_backend.mymodule import my_function

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

