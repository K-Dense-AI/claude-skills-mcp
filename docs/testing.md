# Testing Guide

## Quick Test

Run the test suite with pytest (coverage enabled by default):

```bash
uv run pytest tests/
```

Run only unit tests (fast):

```bash
uv run pytest tests/ -m "not integration"
```

Run the local demo integration test:

```bash
uv run pytest tests/test_integration.py::test_local_demo -v -s
```

Run the repository demo (tests with real GitHub skills):

```bash
uv run pytest tests/test_integration.py::test_repo_demo -v -s
```

Expected output:
- ✓ All configuration tests pass
- ✓ Skill loading tests pass
- ✓ Search engine tests pass
- ✓ Integration tests demonstrate full workflow
- ✓ Coverage report showing tested lines

## Manual Server Testing

### 1. Run the Server

```bash
uv run claude-skills-mcp --verbose
```

The server will:
1. Load the default K-Dense-AI scientific skills from GitHub
2. Download and cache the embedding model (first run only)
3. Index all skills
4. Start the MCP server on stdio

### 2. Test with MCP Client

You can test the server with any MCP client. The server communicates via stdio using the Model Context Protocol.

#### Example MCP Request (JSON-RPC over stdio)

**List Tools:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Call search_skills:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_skills",
    "arguments": {
      "task_description": "I need to analyze RNA sequencing data",
      "top_k": 3
    }
  }
}
```

## Integration Testing with Claude Desktop

### 1. Add to Claude Desktop Config

macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "claude-skills": {
      "command": "uvx",
      "args": ["claude-skills-mcp"]
    }
  }
}
```

### 2. Restart Claude Desktop

The skills server will now be available as an MCP tool.

### 3. Test in Claude

Ask Claude something like:
- "Search for skills to help me analyze gene expression data"
- "Find skills for protein structure prediction"
- "What skills are available for drug discovery?"

Claude should invoke the `search_skills` tool and return relevant skills.

## Testing Custom Configuration

### 1. Create Test Config

```bash
cat > test-config.json << 'EOF'
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 5
}
EOF
```

### 2. Run with Custom Config

```bash
uv run claude-skills-mcp --config test-config.json --verbose
```

## Performance Testing

### Startup Time

```bash
time uv run claude-skills-mcp &
# First run: ~10-15 seconds (downloads embedding model)
# Subsequent runs: ~5-7 seconds (uses cached model)
```

### Search Performance

The search engine should return results in <1 second after indexing.

## Debugging

### Enable Verbose Logging

```bash
uv run claude-skills-mcp --verbose
```

This shows:
- Configuration loading
- Skill discovery and loading
- Embedding generation
- Search queries and results
- MCP protocol messages

### Common Issues

**Issue: No skills loaded**
- Check internet connection
- Verify GitHub URL is correct
- Check GitHub API rate limit (60 req/hour for unauthenticated)

**Issue: Model download fails**
- Check internet connection
- Ensure enough disk space (~100MB for model)
- Check Hugging Face access

**Issue: Import errors**
- Run `uv sync` to install dependencies
- Verify Python 3.12 is being used

## Testing Local Skills

### 1. Create Test Skill

```bash
mkdir -p /tmp/test-skills/my-skill
cat > /tmp/test-skills/my-skill/SKILL.md << 'EOF'
---
name: Test Skill
description: A test skill for validation purposes
---

# Test Skill

This is a test skill to verify local skill loading works correctly.

## Usage

Just a test!
EOF
```

### 2. Create Config with Local Path

```bash
cat > local-test-config.json << 'EOF'
{
  "skill_sources": [
    {
      "type": "local",
      "path": "/tmp/test-skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 3
}
EOF
```

### 3. Run Server

```bash
uv run claude-skills-mcp --config local-test-config.json --verbose
```

Should see:
```
INFO:src.claude_skills_mcp.skill_loader:Loaded skill: Test Skill from /tmp/test-skills/my-skill/SKILL.md
```

## Automated Testing

### Unit Tests

Run all unit tests:

```bash
pytest tests/ -v -m "not integration"
```

Run specific test files:

```bash
pytest tests/test_config.py -v
pytest tests/test_skill_loader.py -v  
pytest tests/test_search_engine.py -v
```

### Integration Tests

Run all integration tests:

```bash
pytest tests/ -v -m "integration"
```

Run the local demo:

```bash
pytest tests/test_integration.py::test_local_demo -v -s
```

Run the repository demo (tests real GitHub skills):

```bash
pytest tests/test_integration.py::test_repo_demo -v -s
```

### Coverage Reports

**Coverage is enabled by default** in the pytest configuration. Every test run shows coverage statistics.

Generate interactive HTML coverage report:

```bash
uv run pytest tests/ --cov-report=html
open htmlcov/index.html
```

Run tests without coverage (faster):

```bash
uv run pytest tests/ --no-cov
```

Current coverage targets:
- Core modules (`config.py`, `search_engine.py`, `skill_loader.py`): >80%
- Integration points tested via integration tests
- CLI and server endpoints tested end-to-end

## Continuous Integration

When ready for CI/CD, consider:

- GitHub Actions workflow
- Automated testing on push
- Build verification
- Package publishing to PyPI

## Test Coverage Goals

- [ ] Unit tests for all modules
- [ ] Integration tests with MCP client
- [ ] Performance benchmarks
- [ ] Error handling scenarios
- [ ] Edge cases (malformed skills, network failures, etc.)

