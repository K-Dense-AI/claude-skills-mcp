# Migration Guide: v0.1.x → v1.0.0

## Overview

Version 1.0.0 introduces a major architectural change: the monolithic package has been split into two packages for better performance and deployment flexibility.

## What Changed

### Package Architecture

**Before (v0.1.x)**:
- Single package: `claude-skills-mcp` (~280 MB with all dependencies)
- stdio MCP server only
- All dependencies downloaded on first `uvx` run (could timeout in Cursor)

**After (v1.0.0)**:
- **Frontend**: `claude-skills-mcp` (~15 MB, lightweight proxy)
- **Backend**: `claude-skills-mcp-backend` (~250 MB, heavy server)
- Frontend auto-downloads backend on first use
- No more Cursor timeout issues!

### User Impact

#### For Cursor Users

**✅ No configuration changes needed!**

Your existing Cursor config still works:
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

**What's different:**
- First run: Frontend starts instantly, backend downloads in background
- You'll see "Loading backend..." on first tool use
- Once backend ready (~60-120s), everything works normally
- Subsequent runs: Fast! Backend is already installed

#### For Developers

**Import changes:**

```python
# Before (v0.1.x)
from src.claude_skills_mcp.search_engine import SkillSearchEngine
from src.claude_skills_mcp.skill_loader import load_skills_from_github

# After (v1.0.0)
from claude_skills_mcp_backend.search_engine import SkillSearchEngine
from claude_skills_mcp_backend.skill_loader import load_skills_from_github
```

**Installation:**

```python
# Before
pip install claude-skills-mcp

# After - install both if using programmatically
pip install claude-skills-mcp claude-skills-mcp-backend
# Or just backend if you don't need the proxy
pip install claude-skills-mcp-backend
```

## New Features

### Remote Backend Support (Coming in v1.1.0)

Connect to K-Dense AI's hosted backend instead of running locally:

```json
{
  "mcpServers": {
    "claude-skills": {
      "url": "https://skills.k-dense.ai/mcp"
    }
  }
}
```

Benefits:
- No local downloads needed
- Instant setup
- Curated scientific skills
- Always up-to-date

### Backend Standalone Mode

Run the backend as a standalone HTTP server:

```bash
claude-skills-mcp-backend --host 0.0.0.0 --port 8080
```

This is useful for:
- Deploying your own hosted backend
- Development and testing
- Sharing backend across multiple clients

## Migration Steps

### For End Users

1. Update to v1.0.0:
   ```bash
   uvx --upgrade claude-skills-mcp
   ```

2. Restart Cursor

3. First tool use will download backend (one-time wait)

4. Done!

### For Developers

1. Update imports in your code (see above)

2. Install both packages:
   ```bash
   pip install claude-skills-mcp claude-skills-mcp-backend
   ```

3. Update any direct references to the old package structure

4. Run tests to verify compatibility

## Breaking Changes

### Package Structure

The `claude-skills-mcp` package no longer contains:
- `search_engine.py`
- `skill_loader.py`
- Heavy dependencies (torch, sentence-transformers)

These are now in `claude-skills-mcp-backend`.

### Import Paths

All core functionality imports must change from `claude_skills_mcp` to `claude_skills_mcp_backend`.

### CLI Behavior

The `claude-skills-mcp` command now:
- Acts as a proxy (not a server directly)
- Spawns backend automatically
- Forwards arguments to backend

For stdio MCP server behavior, use `claude-skills-mcp-backend` directly.

## Rollback

If you need to roll back to v0.1.x:

```bash
# Uninstall v1.0.0
uv tool uninstall claude-skills-mcp
uv cache clean claude-skills-mcp
uv cache clean claude-skills-mcp-backend

# Install v0.1.2
uv tool install claude-skills-mcp==0.1.2
```

## FAQ

### Why split the packages?

To solve Cursor's startup timeout issue. The frontend (~15 MB) starts instantly, while the heavy backend (~250 MB) downloads in the background.

### Do I need to change my Cursor config?

No! The same configuration works with both v0.1.x and v1.0.0.

### Will this use more disk space?

No, same total size (~280 MB). It's just split into two packages.

### Can I use the backend without the frontend?

Yes! Install `claude-skills-mcp-backend` and run it standalone for HTTP/SSE access.

### Can I use just the frontend?

No, the frontend requires the backend to function. However, the backend can be remote (hosted).

## Support

For issues or questions:
- GitHub Issues: https://github.com/K-Dense-AI/claude-skills-mcp/issues
- Email: orion.li@k-dense.ai

## Learn More

- [Main Documentation](https://github.com/K-Dense-AI/claude-skills-mcp)
- [Architecture Guide](https://github.com/K-Dense-AI/claude-skills-mcp/blob/main/docs/architecture.md)
- [API Documentation](https://github.com/K-Dense-AI/claude-skills-mcp/blob/main/docs/api.md)

