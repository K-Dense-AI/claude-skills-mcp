# Claude Skills MCP Server

> **Use [Claude's powerful new Skills system](https://www.anthropic.com/news/skills) with ANY AI model or coding assistant** - including Cursor, Codex, GPT-5, Gemini, and more. This MCP server brings Anthropic's Agent Skills framework to the entire AI ecosystem through the Model Context Protocol.

A Model Context Protocol (MCP) server that provides intelligent search capabilities for discovering relevant Claude Agent Skills using vector embeddings and semantic similarity. This server implements the same progressive disclosure architecture that Anthropic describes in their [Agent Skills engineering blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), making specialized skills available to any MCP-compatible AI application.

**An open-source project by [K-Dense AI](https://k-dense.ai)** - creators of autonomous AI scientists for scientific research.

This MCP server enables any MCP-compatible AI assistant to intelligently search and retrieve skills from our curated [Claude Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) repository and other skill sources like the [Official Claude Skills](https://github.com/anthropics/skills). If you want substantially more advanced capabilities, compute infrastructure, and enterprise-ready AI scientist offerings, check out [K-Dense AI's commercial platform](https://k-dense.ai/).

## Features

- 🔍 **Semantic Search**: Vector embeddings for intelligent skill discovery
- 📚 **Progressive Disclosure**: Multi-level skill loading (metadata → full content → files)
- 🚀 **Zero Configuration**: Works out of the box with curated skills
- 🌐 **Multi-Source**: Load from GitHub repositories and local directories
- ⚡ **Fast & Local**: No API keys needed, with automatic GitHub caching
- 🔧 **Configurable**: Customize sources, models, and content limits

## Quick Start

### Using uvx (Recommended)

Run the server with default configuration (no installation required):

```bash
uvx claude-skills-mcp
```

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

Built on five core components: Configuration (JSON-based config loading), Skill Loader (GitHub + local with automatic caching), Search Engine (sentence-transformers vector search), MCP Server (three tools with stdio transport), and CLI Entry Point (argument parsing and lifecycle management).

See [Architecture Guide](docs/architecture.md) for detailed design, data flow, and extension points.

## Configuration

The server uses a JSON configuration file to specify skill sources and search parameters.

### Default Configuration

If no config file is specified, the server uses these defaults:

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/anthropics/skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 3,
  "max_skill_content_chars": null
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `skill_sources` | Array | Anthropic repo | GitHub repos or local paths |
| `embedding_model` | String | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `default_top_k` | Integer | `3` | Number of results to return |
| `max_skill_content_chars` | Integer/null | `null` | Content truncation limit |
| `load_skill_documents` | Boolean | `true` | Load additional skill files |
| `max_image_size_bytes` | Integer | `5242880` | Max image size (5MB) |

See [config.example.json](config.example.json) for complete options and [Usage Guide](docs/usage.md) for advanced configuration patterns.

## MCP Tools

The server provides three tools for working with Claude Agent Skills:

1. **`search_skills`** - Semantic search for relevant skills based on task description
2. **`read_skill_document`** - Retrieve specific files (scripts, data, references) from skills  
3. **`list_skills`** - View complete inventory of all loaded skills (for exploration/debugging)

See [API Documentation](docs/api.md) for detailed parameters, examples, and best practices.

### Quick Examples

**Find skills:** "I need to analyze RNA sequencing data"  
**Access files:** "Show me Python scripts from the scanpy skill"  
**List all:** "What skills are available?"

For task-oriented queries, prefer `search_skills` over `list_skills`.

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

This server implements Anthropic's **progressive disclosure** architecture:

1. **Startup**: Load skills from GitHub/local sources, generate vector embeddings
2. **Search**: Match task queries against skill descriptions using cosine similarity  
3. **Progressive Loading**: Return metadata → full content → referenced files as needed
4. **Caching**: Automatic 24-hour caching of GitHub API responses

This enables any MCP-compatible AI assistant to intelligently discover and load relevant skills with minimal context overhead. See [Architecture Guide](docs/architecture.md) for details.

## Skill Sources

Load skills from **GitHub repositories** (direct skills or Claude Code plugins) or **local directories**. Defaults to [Official Anthropic Skills](https://github.com/anthropics/skills). See [K-Dense AI Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) for 70+ specialized scientific skills.

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

- [Usage Examples](docs/usage.md) - Advanced configuration, real-world use cases, and custom skill creation
- [Testing Guide](docs/testing.md) - Complete testing instructions, CI/CD, and coverage analysis
- [Roadmap](docs/roadmap.md) - Future features and planned enhancements

## Roadmap

We're working on MCP Sampling, sandboxed execution, binary support, and skill workflows. See our [detailed roadmap](docs/roadmap.md) for technical specifications.

## Learn More

- [Agent Skills Documentation](https://docs.claude.com/en/docs/claude-code/skills) - Official Anthropic documentation on the Skills format
- [Agent Skills Blog Post](https://www.anthropic.com/news/skills) - Announcement and overview
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol that makes cross-platform Skills possible
- [Engineering Blog: Equipping Agents for the Real World](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) - Technical deep-dive on the Skills architecture

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE.md).

**Required Notice:** Copyright K-Dense AI (https://k-dense.ai)

For commercial use or licensing inquiries, please contact K-Dense AI at [orion.li@k-dense.ai](mailto:orion.li@k-dense.ai).
