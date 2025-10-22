# Getting Started

This guide covers the minimal setup to run the Claude Skills MCP server in its current v1.0.0 two-package architecture.

## Quick Start (Cursor)

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

Restart Cursor. The lightweight frontend starts instantly and displays tools. On the first tool use, the backend downloads in the background. Subsequent uses are instant.

## Quick Start (CLI)

Run the server locally with defaults:

```bash
uvx claude-skills-mcp
```

## Configuration (Current Version)

If you need a config file with the current defaults:

```bash
uvx claude-skills-mcp --example-config > config.json
```

Run with your config:

```bash
uvx claude-skills-mcp --config config.json
```

Notes (v1.0.0):
- Frontend (`claude-skills-mcp`) is a lightweight MCP stdio server and proxy.
- Backend (`claude-skills-mcp-backend`) provides vector search over skills and runs over HTTP.
- On first use, the backend is auto-installed and started in the background.

## Troubleshooting (Current)

- First tool call shows "Loading backend...": expected on first run while backend downloads.
- Ensure Python 3.12 is available and `uv` manages the environment.
- For verbose logs:

```bash
uvx claude-skills-mcp --verbose
```

## Next Steps

- Architecture details: see `architecture.md`.
- API reference (tools and parameters): see `api.md`.
- Usage patterns and examples: see `usage.md`.
- Testing instructions: see `testing.md`.


