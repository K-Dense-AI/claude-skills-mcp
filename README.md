# Claude Skills MCP Server

> **Use [Claude's powerful new Skills system](https://www.anthropic.com/news/skills) with ANY AI model or coding assistant** - including Cursor, Codex, GPT-4, Gemini, and more. This MCP server brings Anthropic's Agent Skills framework to the entire AI ecosystem through the Model Context Protocol.

A Model Context Protocol (MCP) server that provides intelligent search capabilities for discovering relevant Claude Agent Skills using vector embeddings and semantic similarity. This server implements the same progressive disclosure architecture that Anthropic describes in their [Agent Skills engineering blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), making specialized skills available to any MCP-compatible AI application.

**An open-source project by [K-Dense AI](https://k-dense.ai)** - creators of autonomous AI scientists for scientific research.

This MCP server enables any MCP-compatible AI assistant to intelligently search and retrieve skills from our curated [Claude Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) repository and other skill sources. If you want substantially more advanced capabilities, compute infrastructure, and enterprise-ready AI scientist offerings, check out [K-Dense AI's commercial platform](https://k-dense.ai/).

## Features

- 🔍 **Semantic Search**: Find the most relevant Claude Agent Skills using vector embeddings
- 📚 **Progressive Disclosure**: Implements Anthropic's multi-level skill loading architecture - loads only necessary context when needed
- 🎯 **Optimized Tool Descriptions**: Enhanced MCP tool definitions following best practices for better AI model integration
- 🚀 **Zero Configuration**: Works out of the box with curated scientific skills
- 🌐 **GitHub Integration**: Load skills directly from GitHub repositories
- 📁 **Local Skills**: Support for local skill directories
- ⚡ **Fast**: Local embeddings with sentence-transformers (no API keys needed)
- 🔧 **Configurable**: Customize skill sources, embedding models, search parameters, and content limits
- 🎚️ **Content Limiting**: Optional character limits for skill content to manage context window usage

## Quick Start

### Using uvx (Recommended)

Run the server with default configuration (no installation required):

```bash
uvx claude-skills-mcp
```

This automatically loads skills from the [official Anthropic Skills repository](https://github.com/anthropics/skills) - featuring diverse, production-ready examples including document creation, web development, testing, and creative applications with Python scripts, images, and rich media content.

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
- Standard MCP protocol implementation following specification best practices
- One tool: `search_skills` with optimized, action-oriented descriptions
- Progressive disclosure of skill content with configurable truncation
- Stdio transport for easy integration
- Formatted output with relevance scores and source links

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
      "url": "https://github.com/anthropics/skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 3,
  "max_skill_content_chars": null
}
```

### Example Custom Configuration

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/anthropics/skills"
    },
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills"
    },
    {
      "type": "local",
      "path": "~/.claude/skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 3,
  "max_skill_content_chars": 5000
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
- **max_skill_content_chars**: Maximum characters for skill content (default: `null` for unlimited)
  - When set, truncates skill content to this limit with a note and source link
  - Useful for managing context window size with large skills
  - Only truncates the content field; metadata (name, score, source) is always included
- **load_skill_documents**: Load additional files from skill directories (default: `true`)
- **max_image_size_bytes**: Maximum size for base64-encoding images (default: `5242880` = 5MB)
- **allowed_image_extensions**: Supported image file types (default: `[".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]`)
- **text_file_extensions**: Supported text file types (default: `[".md", ".py", ".txt", ".json", ".yaml", ".yml", ".sh", ".r", ".ipynb", ".xml"]`)

## MCP Tools

The server exposes two MCP tools for working with skills, following [MCP specification best practices](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) with optimized descriptions designed to improve AI model integration and invocation accuracy.

### Tool 1: `search_skills`

Search and discover relevant Claude Agent Skills.

#### Input Parameters

- **task_description** (required): Description of the task you want to accomplish
- **top_k** (optional): Number of skills to return (default: 3, max: 20)
- **list_documents** (optional): Include list of available documents for each skill (default: false)

#### Output

Returns the most relevant skills with:
- Skill name and description
- Full SKILL.md content (or truncated with source link if `max_skill_content_chars` is set)
- Source URL or path
- Relevance score (0-1, higher is better)
- Document count and optional document listing

### Tool 2: `read_skill_document`

Retrieve specific documents (scripts, references, assets) from a skill.

#### Input Parameters

- **skill_name** (required): Name of the skill (as returned by search_skills)
- **document_path** (optional): Path or pattern to match documents (e.g., "scripts/*.py", "assets/diagram.png")
  - If not provided, lists all available documents
  - Supports glob patterns for matching multiple files
- **include_base64** (optional): For images, return base64-encoded content (default: false, returns URL only)

#### Output

Returns:
- Single document: Full content (text) or URL/base64 (images)
- Multiple documents: List with paths, types, and content
- No path specified: List of all available documents with metadata

The tool uses action-oriented language and clear examples to help AI models understand when and how to invoke it effectively.

### Example Usage

When this MCP server is connected to any AI assistant (Claude, GPT-4, Gemini, Cursor, etc.), the AI can:

**Search for skills:**
```
I need help analyzing RNA sequencing data
```
The AI assistant will invoke `search_skills` with this task description and receive the most relevant skills from the indexed sources.

**Access skill documents:**
```
Show me the Python scripts from the "Exploratory Data Analysis" skill
```
The AI assistant will invoke `read_skill_document` with pattern matching to retrieve the scripts.

**View available documents:**
```
What additional files are available for this skill?
```
The AI assistant will invoke `read_skill_document` without a path to list all documents.

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

This server implements the same **progressive disclosure** architecture that Anthropic describes in their [engineering blog on Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills):

1. **Startup**: Loads skills from configured GitHub repos and local directories
2. **Indexing**: Generates vector embeddings for all skill descriptions using sentence-transformers
3. **Search & Progressive Loading**: When a task description is received:
   - Generates embedding for the query
   - Computes cosine similarity with all indexed skills
   - Returns top-K most similar skills with their full content
   - Skills are structured to enable multi-level context loading (name/description → full SKILL.md → referenced files)
   - Optional content truncation helps manage context window usage while preserving access to full skill sources

This architecture mirrors how Anthropic designed the Skills system to work: minimal metadata is always available, with full context loaded only when relevant to the current task. Any MCP-compatible AI assistant can leverage this same progressive disclosure pattern.

## Supported Skill Sources

### GitHub Repositories

The server can load skills from:
- Direct skill folders (containing SKILL.md)
- Claude Code plugin repositories (with .claude-plugin/marketplace.json)

Examples:
- [Official Anthropic Skills](https://github.com/anthropics/skills) - Production-ready skills with Python scripts, images, and diverse content (default)
- [K-Dense AI Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills) - 70+ specialized scientific skills for bioinformatics, cheminformatics, and research

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

- [Usage Examples](docs/usage.md) - Advanced configuration, real-world use cases, and custom skill creation
- [Testing Guide](docs/testing.md) - Complete testing instructions, CI/CD, and coverage analysis
- [Roadmap](docs/roadmap.md) - Future features and planned enhancements

## Roadmap

We're working on exciting new capabilities to make skill discovery even more powerful:

- **🎯 MCP Sampling**: Replace RAG with intelligent, context-aware skill selection using LLM reasoning
- **🐍 Sandboxed Execution**: Run Python code from skills in secure, isolated environments
- **⚙️ Binary Support**: Execute compiled tools and scientific software (BLAST, RDKit, etc.)
- **🔄 Skill Workflows**: Compose multiple skills into automated pipelines

See our [detailed roadmap](docs/roadmap.md) for technical specifications and implementation plans.

## Learn More

- [Agent Skills Documentation](https://docs.claude.com/en/docs/claude-code/skills) - Official Anthropic documentation on the Skills format
- [Agent Skills Blog Post](https://www.anthropic.com/news/skills) - Announcement and overview
- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol that makes cross-platform Skills possible
- [Engineering Blog: Equipping Agents for the Real World](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) - Technical deep-dive on the Skills architecture

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE.md).

**Required Notice:** Copyright K-Dense AI (https://k-dense.ai)

For commercial use or licensing inquiries, please contact K-Dense AI at [orion.li@k-dense.ai](mailto:orion.li@k-dense.ai).
