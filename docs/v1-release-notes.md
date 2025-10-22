# v1.0.0 Release Notes

## Major Architecture Change - Two-Package System

Version 1.0.0 introduces a fundamental architectural change to solve the Cursor timeout issue while maintaining the simple `uvx` user experience.

## What Changed

### Package Split

**Before (v0.1.x)**:
- Single monolithic package with all dependencies
- Total size: ~280 MB (including PyTorch, sentence-transformers)
- Cursor timeout on first install (60-180 seconds to download)

**After (v1.0.0)**:
- **Frontend** (`claude-skills-mcp`): Lightweight proxy (~15 MB)
- **Backend** (`claude-skills-mcp-backend`): Heavy server (~250 MB)
- Frontend starts instantly, backend downloads in background
- No Cursor timeout! ✅

### User Impact

**No configuration changes needed!**

Same Cursor config works:
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

**First run experience**:
1. Frontend installs and starts (~5 seconds)
2. Cursor sees tools immediately
3. Backend downloads in background (60-120 seconds)
4. First tool use shows "Loading backend..."
5. Subsequent uses are instant!

### Developer Impact

**Import changes** (if using programmatically):
```python
# Before
from src.claude_skills_mcp.search_engine import SkillSearchEngine

# After
from claude_skills_mcp_backend.search_engine import SkillSearchEngine
```

## New Features

### Backend HTTP Server

The backend now runs as an HTTP server with Streamable HTTP transport, enabling:
- Remote deployment (deploy your own backend)
- Multiple clients connecting to same backend
- Horizontal scaling potential

Run standalone:
```bash
claude-skills-mcp-backend --host 0.0.0.0 --port 8080
```

### CLI Argument Forwarding

Frontend accepts superset of backend arguments and forwards them:
```bash
uvx claude-skills-mcp --config custom.json --verbose
# Forwards --config and --verbose to backend
```

### Docker Deployment

Deploy backend with Docker:
```bash
cd packages/backend
docker build -t claude-skills-mcp-backend .
docker run -p 8080:8765 claude-skills-mcp-backend
```

## Technical Details

### Architecture

```
Cursor (stdio) → Frontend Proxy (stdio server + HTTP client)
                    ↓
                 Backend Server (HTTP/Streamable HTTP)
                    ↓
                 Search Engine (PyTorch + sentence-transformers)
```

**Frontend**:
- MCP server (stdio) for Cursor
- MCP client (streamable HTTP) for backend
- Hardcoded tool schemas (instant response)
- Backend process manager
- Dependencies: mcp, httpx (~15 MB)

**Backend**:
- MCP server (streamable HTTP)
- Vector search engine
- Skill loading and indexing
- Dependencies: torch, sentence-transformers, starlette, uvicorn (~250 MB)

### Why This Works

1. **Cursor timeout avoided**: Frontend (~15 MB) installs in <10 seconds
2. **Tools available immediately**: Hardcoded schemas in frontend
3. **Backend downloads async**: Doesn't block Cursor startup
4. **uvx handles everything**: Frontend spawns backend via `uvx claude-skills-mcp-backend`

## Breaking Changes

### Package Name

Backend now has separate package name:
- `claude-skills-mcp` → Frontend proxy
- `claude-skills-mcp-backend` → Backend server (new package)

### Module Names

If importing directly:
- Old: `claude_skills_mcp.*`
- New: `claude_skills_mcp_backend.*` (for backend functionality)

### Repository Structure

Source code moved to `packages/` directory:
- `packages/frontend/src/claude_skills_mcp/`
- `packages/backend/src/claude_skills_mcp_backend/`

## Migration

### For Cursor Users

**No action needed!** Just update:
```bash
uvx --upgrade claude-skills-mcp
```

On first run after upgrade, backend will auto-download.

### For Developers

1. Update imports:
   ```python
   # Change all imports from:
   from claude_skills_mcp.search_engine import SkillSearchEngine
   # To:
   from claude_skills_mcp_backend.search_engine import SkillSearchEngine
   ```

2. Install both packages:
   ```bash
   pip install claude-skills-mcp claude-skills-mcp-backend
   ```

3. Run tests to verify compatibility

## Upgrade Path

```bash
# Clean old installation
uv cache clean claude-skills-mcp

# Install new version
uvx claude-skills-mcp

# First run downloads backend automatically
```

## Future Roadmap

### v1.1.0 (Coming Soon)
- Remote backend support (`--remote https://skills.k-dense.ai/mcp`)
- Hosted backend service (no local install needed)
- WebSocket support for better performance

### v1.2.0
- Backend clustering and load balancing
- Analytics dashboard
- Custom skill management UI

## Testing

All 62 unit tests pass:
```bash
cd packages/backend
uv run pytest tests/ -m "not integration" -q
# 62 passed
```

## Acknowledgments

This architecture was inspired by:
- mcp-proxy project's stdio ↔ HTTP bridging
- Cursor's timeout requirements
- User feedback on installation complexity

## Support

- [Migration Guide](migration-guide.md)
- [Architecture Documentation](architecture.md)
- [GitHub Issues](https://github.com/K-Dense-AI/claude-skills-mcp/issues)
- Email: orion.li@k-dense.ai

