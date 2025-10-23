# Claude Skills MCP Server

[![Tests](https://github.com/K-Dense-AI/claude-skills-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/K-Dense-AI/claude-skills-mcp/actions/workflows/test.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![PyPI version](https://badge.fury.io/py/claude-skills-mcp.svg?icon=si%3Apython)](https://badge.fury.io/py/claude-skills-mcp)

> **Use [Claude's powerful new Skills system](https://www.anthropic.com/news/skills) with ANY AI model or coding assistant** - including Cursor, Codex, GPT-5, Gemini, and more. This MCP server brings Anthropic's Agent Skills framework to the entire AI ecosystem through the Model Context Protocol.

A Model Context Protocol (MCP) server that provides intelligent search capabilities for discovering relevant Claude Agent Skills using vector embeddings and semantic similarity. This server implements the same progressive disclosure architecture that Anthropic describes in their [Agent Skills engineering blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), making specialized skills available to any MCP-compatible AI application.

**An open-source project by [K-Dense AI](https://k-dense.ai)** - creators of autonomous AI scientists for scientific research.

This MCP server enables any MCP-compatible AI assistant to intelligently search and retrieve skills from our curated [Claude Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) repository and other skill sources like the [Official Claude Skills](https://github.com/anthropics/skills).

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en-US/install-mcp?name=claude-skills-mcp&config=eyJjb21tYW5kIjoidXZ4IGNsYXVkZS1za2lsbHMtbWNwIn0%3D)

## Demo

![Claude Skills MCP in Action](docs/demo.gif)

*Semantic search and progressive loading of Claude Agent Skills in Cursor*

## Highlights

- **Two-Package Architecture**: Lightweight frontend (~15 MB) starts instantly; backend (~250 MB) downloads in background
- **No Cursor Timeout**: Frontend responds in <5 seconds, solving the timeout issue
- **Semantic Search**: Vector embeddings for intelligent skill discovery
- **Progressive Disclosure**: Multi-level skill loading (metadata → full content → files)
- **Zero Configuration**: Works out of the box with curated skills
- **Multi-Source**: Load from GitHub repositories and local directories
- **Fast & Local**: No API keys needed, with automatic GitHub caching
- **Configurable**: Customize sources, models, and content limits

## Quick Start

### For Cursor Users

Add through the [Cursor Directory](https://cursor.directory/mcp/claude-skills-mcp), or add to your Cursor config (`~/.cursor/mcp.json`):

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

The frontend starts instantly and displays tools, automatically downloading and starting the backend in the background (~60-120s due to RAG dependencies, one-time). Subsequent uses are instant.

### Using uvx (Standalone)

Run the server with default configuration:

```bash
uvx claude-skills-mcp
```

This starts the lightweight frontend which auto-downloads the backend and loads ~90 skills from Anthropic's official skills repository and K-Dense AI's scientific skills collection.

### With Custom Configuration

```bash
# 1. Print the default configuration
uvx claude-skills-mcp --example-config > config.json

# 2. Edit config.json to your needs

# 3. Run with your custom configuration
uvx claude-skills-mcp --config config.json
```

## Documentation

- **[Getting Started](docs/getting-started.md)** - Installation, Cursor setup, CLI usage, and troubleshooting
- **[Architecture Guide](docs/architecture.md)** - Two-package design, data flow, and components
- **[API Documentation](docs/api.md)** - Tool parameters, examples, and best practices
- **[Usage Examples](docs/usage.md)** - Advanced configuration, real-world use cases, and custom skill creation
- **[Testing Guide](docs/testing.md)** - Complete testing instructions, CI/CD, and coverage analysis

## MCP Tools

The server provides three tools for working with Claude Agent Skills:

1. **`search_skills`** - Semantic search for relevant skills based on task description
2. **`read_skill_document`** - Retrieve specific files (scripts, data, references) from skills  
3. **`list_skills`** - View complete inventory of all loaded skills (for exploration/debugging)

See [API Documentation](docs/api.md) for detailed parameters, examples, and best practices.

## Architecture (v1.0.0)

The system uses a **two-package architecture** for optimal performance:

- **Frontend** ([`claude-skills-mcp`](https://pypi.org/project/claude-skills-mcp/)): Lightweight proxy (~15 MB)
  - Starts instantly (<5 seconds) ✅ **No Cursor timeout!**
  - Auto-downloads backend on first use
  - MCP server (stdio) for Cursor
  
- **Backend** ([`claude-skills-mcp-backend`](https://pypi.org/project/claude-skills-mcp-backend/)): Heavy server (~250 MB)
  - Vector search with PyTorch & sentence-transformers
  - MCP server (streamable HTTP)
  - Auto-installed by frontend OR deployable standalone

**Benefits:**
- ✅ Solves Cursor timeout issue (frontend starts instantly)
- ✅ Same simple user experience (`uvx claude-skills-mcp`)
- ✅ Backend downloads in background (doesn't block Cursor)
- ✅ Can connect to remote hosted backend (no local install needed)

See [Architecture Guide](docs/architecture.md) for detailed design and data flow.

## Skill Sources

Load skills from **GitHub repositories** (direct skills or Claude Code plugins) or **local directories**. 

By default, loads from:
- [Official Anthropic Skills](https://github.com/anthropics/skills) - 15 diverse skills for documents, presentations, web artifacts, and more
- [K-Dense AI Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) - 78+ specialized skills for bioinformatics, cheminformatics, and scientific analysis
- Local directory `~/.claude/skills` (if it exists)

## Contributing

Contributions are welcome! To contribute:

1. **Report issues**: [Open an issue](https://github.com/K-Dense-AI/claude-skills-mcp/issues) for bugs or feature requests
2. **Submit PRs**: Fork, create a feature branch, ensure tests pass (`uv run pytest tests/`), then submit
3. **Code style**: Run `uvx ruff check src/` before committing
4. **Add tests**: New features should include tests

### Development

**Version Management**: This monorepo uses a centralized version system:
- Edit the `VERSION` file at the repo root to bump the version
- Run `python3 scripts/sync-version.py` to sync all references (or use `--check` to verify)
- The `scripts/build-all.sh` script automatically syncs versions before building

For questions, email [orion.li@k-dense.ai](mailto:orion.li@k-dense.ai)

## Learn More

- [Agent Skills Documentation](https://docs.claude.com/en/docs/claude-code/skills) - Official Anthropic documentation on the Skills format
- [Agent Skills Blog Post](https://www.anthropic.com/news/skills) - Announcement and overview
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol that makes cross-platform Skills possible
- [Engineering Blog: Equipping Agents for the Real World](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) - Technical deep-dive on the Skills architecture

## License

This project is licensed under the [Apache License 2.0](LICENSE).

Copyright 2025 K-Dense AI (https://k-dense.ai)
