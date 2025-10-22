# Claude Skills MCP Backend

Heavy backend server for Claude Skills MCP system with vector search capabilities.

## Overview

This is the backend component of the Claude Skills MCP system. It provides:
- Vector-based semantic search using sentence-transformers
- Skill indexing and retrieval
- MCP protocol via Streamable HTTP transport
- Background skill loading from GitHub and local sources

**Note**: This package is typically auto-installed by the frontend (`claude-skills-mcp`). You only need to install it manually for:
- Remote deployment (hosting your own backend)
- Development and testing
- Standalone usage without the frontend proxy

## Installation

```bash
# Via uv (recommended)
uv tool install claude-skills-mcp-backend

# Via uvx (one-time use)
uvx claude-skills-mcp-backend

# Via pip
pip install claude-skills-mcp-backend
```

## Usage

### Run Standalone Server

```bash
# Default (localhost:8765)
claude-skills-mcp-backend

# Custom port
claude-skills-mcp-backend --port 8080

# For remote access
claude-skills-mcp-backend --host 0.0.0.0 --port 8080

# With custom configuration
claude-skills-mcp-backend --config my-config.json

# Verbose logging
claude-skills-mcp-backend --verbose
```

### Configuration

```bash
# Print example configuration
claude-skills-mcp-backend --example-config > config.json

# Edit config.json to customize skill sources, embedding model, etc.

# Run with custom config
claude-skills-mcp-backend --config config.json
```

## Endpoints

When running, the backend exposes:

- **Streamable HTTP MCP**: `http://localhost:8765/mcp`
- **Health Check**: `http://localhost:8765/health`

## Docker Deployment

### Build Image

```bash
docker build -t claude-skills-mcp-backend .
```

### Run Container

```bash
# For local access
docker run -p 8765:8765 claude-skills-mcp-backend

# For remote access
docker run -p 8080:8765 \
  -e HOST=0.0.0.0 \
  claude-skills-mcp-backend --host 0.0.0.0 --port 8765
```

## Dependencies

This package includes heavy dependencies (~250 MB):
- PyTorch (CPU-only on Linux): ~150-200 MB
- sentence-transformers: ~50 MB
- numpy, httpx, fastapi, uvicorn: ~30 MB

**First download may take 60-180 seconds** depending on your internet connection.

## Performance

- **Startup time**: 2-5 seconds (with cached dependencies)
- **First search**: +2-5 seconds (embedding model download, one-time)
- **Query time**: <1 second after models loaded
- **Memory usage**: ~500 MB

## Development

```bash
# Clone the monorepo
git clone https://github.com/K-Dense-AI/claude-skills-mcp.git
cd claude-skills-mcp/packages/backend

# Install in development mode
uv pip install -e ".[test]"

# Run tests
uv run pytest tests/
```

## Related Packages

- **claude-skills-mcp** (Frontend): Lightweight proxy that auto-installs this backend
- **Main Repository**: https://github.com/K-Dense-AI/claude-skills-mcp

## License

Apache License 2.0

Copyright 2025 K-Dense AI (https://k-dense.ai)

