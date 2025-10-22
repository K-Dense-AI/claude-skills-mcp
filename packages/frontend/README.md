# Claude Skills MCP Frontend

Lightweight MCP proxy for Claude Skills that auto-downloads the heavy backend on demand.

## Overview

This is the frontend component of the Claude Skills MCP system. It's a lightweight proxy (~15 MB) that:
- Starts instantly (<5 seconds)
- Auto-downloads the backend when first needed
- Acts as MCP server (stdio) for Cursor
- Acts as MCP client (HTTP) for the backend
- Returns tool schemas immediately (no backend wait needed)

## Installation

```bash
# Via uvx (recommended for Cursor)
uvx claude-skills-mcp

# Via uv tool (persistent install)
uv tool install claude-skills-mcp

# Via pip
pip install claude-skills-mcp
```

## Usage with Cursor

Add to your Cursor MCP settings (`~/.cursor/mcp.json`):

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

Restart Cursor and the skills will be available!

### First Run Behavior

On first run, the frontend will:
1. Start immediately (~5 seconds) ✅ **Cursor timeout satisfied!**
2. Return tool schemas to Cursor (instant)
3. Download backend in background (~250 MB, 60-120 seconds)
4. When you first use a tool, you'll see "Loading backend..."
5. Once backend ready, all tools work normally

**Subsequent runs**: Fast! Backend is already installed.

## Configuration

The frontend forwards all arguments to the backend:

```bash
# Custom configuration
uvx claude-skills-mcp --config my-config.json

# Verbose logging
uvx claude-skills-mcp --verbose

# Custom backend port (advanced)
uvx claude-skills-mcp --port 9000
```

## Remote Backend (Future)

```bash
# Connect to hosted backend instead of local
uvx claude-skills-mcp --remote https://skills.k-dense.ai/mcp
```

**Note**: Remote backend support coming in v1.1.0

## How It Works

```
Cursor → Frontend (stdio, ~15 MB)
           ↓
         list_tools() → Returns hardcoded schemas INSTANTLY ✅
           ↓
         [Backend downloads in background...]
           ↓
         call_tool() → Proxies to Backend (HTTP)
           ↓
         Backend (HTTP, ~250 MB) → Performs actual search
```

This architecture solves the Cursor timeout problem by separating:
- **Fast startup** (frontend, minimal dependencies)
- **Heavy processing** (backend, downloads async)

## Dependencies

Frontend only requires:
- `mcp>=1.0.0` (~5 MB)
- `httpx>=0.24.0` (~5 MB)

**Total**: ~15 MB (downloads in <10 seconds)

The backend (`claude-skills-mcp-backend`) is auto-installed on first use.

## Troubleshooting

### "Backend not ready" message

On first run, you'll see this message for 30-120 seconds while the backend downloads. This is normal and only happens once.

### Backend installation fails

Check:
1. Internet connection
2. Disk space (~500 MB free needed)
3. Python 3.12 installed

### Tools not working

Run with verbose logging:
```bash
uvx claude-skills-mcp --verbose
```

Check logs in stderr for backend status.

## Development

```bash
# Clone the monorepo
git clone https://github.com/K-Dense-AI/claude-skills-mcp.git
cd claude-skills-mcp/packages/frontend

# Install in development mode
uv pip install -e ".[test]"

# Run tests
uv run pytest tests/
```

## Related Packages

- **claude-skills-mcp-backend** (Backend): Heavy server with vector search
- **Main Repository**: https://github.com/K-Dense-AI/claude-skills-mcp

## License

Apache License 2.0

Copyright 2025 K-Dense AI (https://k-dense.ai)

