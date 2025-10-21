# Claude Skills MCP Server

A Model Context Protocol (MCP) server that provides intelligent search capabilities for discovering relevant Claude Agent Skills using vector embeddings and semantic similarity.

**An open-source project by [K-Dense AI](https://k-dense.ai)** - creators of autonomous AI scientists for scientific research.

This MCP server enables Claude to intelligently search and retrieve skills from our curated [Claude Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) repository and other skill sources. If you want substantially more advanced capabilities, compute infrastructure, and enterprise-ready AI scientist offerings, check out [K-Dense AI's commercial platform](https://k-dense.ai/).

## Features

- 🔍 **Semantic Search**: Find the most relevant Claude Agent Skills using vector embeddings
- 🚀 **Zero Configuration**: Works out of the box with curated scientific skills
- 🌐 **GitHub Integration**: Load skills directly from GitHub repositories
- 📁 **Local Skills**: Support for local skill directories
- ⚡ **Fast**: Local embeddings with sentence-transformers (no API keys needed)
- 🔧 **Configurable**: Customize skill sources, embedding models, and search parameters

## Quick Start

### Using uvx (Recommended)

Run the server with default configuration (no installation required):

```bash
uvx claude-skills-mcp
```

This automatically loads skills from the [K-Dense AI Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) repository - a curated collection of 70+ scientific skills for bioinformatics, cheminformatics, and scientific analysis.

### With Custom Configuration

1. Generate an example configuration file:

```bash
uvx claude-skills-mcp --example-config > config.json
```

2. Edit `config.json` to customize your skill sources

3. Run with your configuration:

```bash
uvx claude-skills-mcp --config config.json
```

## Architecture

The server consists of five core components:

### 1. Configuration System (`config.py`)
- Default configuration with K-Dense-AI scientific skills
- JSON-based config loading
- Fallback to defaults if config unavailable
- Example config generator

### 2. Skill Loader (`skill_loader.py`)
- GitHub repository loading via API (no authentication required)
- Local directory scanning  
- YAML frontmatter parsing
- Support for both direct skills and Claude Code plugin repositories
- Robust error handling (network issues, missing files, etc.)

### 3. Search Engine (`search_engine.py`)
- Sentence-transformers for local embeddings (`all-MiniLM-L6-v2`)
- Vector indexing at startup for fast queries
- Cosine similarity search
- Configurable top-K results

### 4. MCP Server (`server.py`)
- Standard MCP protocol implementation
- One tool: `search_skills`
- Stdio transport for easy integration
- Formatted output with relevance scores

### 5. Entry Point (`__main__.py`)
- CLI argument parsing
- Async server lifecycle
- Comprehensive error handling
- Logging configuration

## Configuration

The server uses a JSON configuration file to specify skill sources and search parameters.

### Default Configuration

If no config file is specified, the server uses these defaults:

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 3
}
```

### Example Custom Configuration

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills"
    },
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/scientific-thinking"
    },
    {
      "type": "github",
      "url": "https://github.com/anthropics/claude-cookbooks",
      "subpath": "skills/custom_skills"
    },
    {
      "type": "local",
      "path": "~/.claude/skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 3
}
```

### Configuration Options

- **skill_sources**: Array of skill source configurations
  - **type**: Either `"github"` or `"local"`
  - **url**: GitHub repository URL (for github type). Supports:
    - Base repo: `https://github.com/owner/repo`
    - With subpath: `https://github.com/owner/repo/tree/branch/subpath`
  - **subpath**: Optional subdirectory within the repo (alternative to URL-based subpath)
  - **path**: Local directory path (for local type)
- **embedding_model**: Name of the sentence-transformers model (default: `"all-MiniLM-L6-v2"`)
- **default_top_k**: Default number of skills to return (default: `3`)

## MCP Tool: `search_skills`

The server exposes one MCP tool for searching skills.

### Input Parameters

- **task_description** (required): Description of the task you want to accomplish
- **top_k** (optional): Number of skills to return (default: 3, max: 20)

### Output

Returns the most relevant skills with:
- Skill name and description
- Full SKILL.md content
- Source URL or path
- Relevance score (0-1, higher is better)

### Example Usage in Claude

When this MCP server is connected, Claude can use:

```
I need help analyzing RNA sequencing data
```

Claude will invoke `search_skills` with this task description and receive the most relevant skills from the indexed sources.

## Skill Format

The server searches for `SKILL.md` files with the following format:

```markdown
---
name: Skill Name
description: Brief description of what this skill does
---

# Skill Name

[Full skill content in Markdown...]
```

## Technical Details

### Dependencies

- `mcp>=1.0.0` - Model Context Protocol
- `sentence-transformers>=2.2.0` - Vector embeddings
- `numpy>=1.24.0` - Numerical operations
- `httpx>=0.24.0` - HTTP client for GitHub API

### Python Version

- Requires: **Python 3.12** (not 3.13)
- Dependencies are automatically managed by uv/uvx

### Performance

- **Startup time**: ~5-10 seconds (loads model and indexes skills)
- **Query time**: <1 second for vector search
- **Memory usage**: ~500MB (embedding model + indexed skills)
- **First run**: Downloads ~100MB embedding model (cached thereafter)

## How It Works

1. **Startup**: Loads skills from configured GitHub repos and local directories
2. **Indexing**: Generates vector embeddings for all skill descriptions using sentence-transformers
3. **Search**: When a task description is received:
   - Generates embedding for the query
   - Computes cosine similarity with all indexed skills
   - Returns top-K most similar skills with full content

## Supported Skill Sources

### GitHub Repositories

The server can load skills from:
- Direct skill folders (containing SKILL.md)
- Claude Code plugin repositories (with .claude-plugin/marketplace.json)

Examples:
- [K-Dense AI Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) - 70+ scientific skills (default)
- [Anthropic Custom Skills](https://github.com/anthropics/claude-cookbooks/tree/main/skills/custom_skills)
- [Jeffallan's Claude Skills](https://github.com/Jeffallan/claude-skills)

### Local Directories

Any local directory containing SKILL.md files in subdirectories.

## Error Handling

The server is designed to be resilient:
- If a local folder is inaccessible, it logs a warning and continues
- If a GitHub repo fails to load, it tries alternate branches and continues
- If no skills are loaded, the server exits with an error message

## Development

### Installation from Source

```bash
git clone https://github.com/your-org/claude-skills-mcp.git
cd claude-skills-mcp
uv sync
```

### Running in Development

```bash
uv run claude-skills-mcp
```

### Running with Verbose Logging

```bash
uvx claude-skills-mcp --verbose
```

### Running Tests

```bash
# Run all tests (with coverage - runs automatically)
uv run pytest tests/

# Run only unit tests (fast)
uv run pytest tests/ -m "not integration"

# Run local demo (creates temporary skills)
uv run pytest tests/test_integration.py::test_local_demo -v -s

# Run repository demo (loads from K-Dense-AI scientific skills)
uv run pytest tests/test_integration.py::test_repo_demo -v -s

# Generate HTML coverage report
uv run pytest tests/ --cov-report=html
open htmlcov/index.html
```

**Note**: Coverage reporting is enabled by default. All test runs show coverage statistics.

See [Testing Guide](docs/testing.md) for more details.

## Command Line Options

```
uvx claude-skills-mcp [OPTIONS]

Options:
  --config PATH         Path to configuration JSON file
  --example-config      Print example configuration and exit
  --verbose, -v         Enable verbose logging
  --help               Show help message
```

## How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest tests/ -v`
5. Submit a pull request

All contributions are welcome! Please ensure tests pass before submitting.

## Documentation

- [Usage Examples](docs/usage.md) - Detailed usage scenarios and configuration examples
- [Testing Guide](docs/testing.md) - Comprehensive testing instructions
- [Publishing Guide](docs/publishing.md) - How to publish to PyPI

## Learn More

- [Claude Agent Skills Documentation](https://docs.claude.com/en/docs/claude-code/skills)
- [Agent Skills Blog Post](https://www.anthropic.com/news/skills)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Engineering Blog: Equipping Agents for the Real World](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE.md).

**Required Notice:** Copyright K-Dense AI (https://k-dense.ai)

For commercial use or licensing inquiries, please contact K-Dense AI at [contact@k-dense.ai](mailto:contact@k-dense.ai).

---

**Status**: Ready for testing and distribution  
**Version**: 0.1.0
