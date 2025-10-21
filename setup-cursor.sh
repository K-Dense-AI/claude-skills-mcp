#!/bin/bash
# One-line setup script for Claude Skills MCP in Cursor
# Usage: curl -sSL https://raw.githubusercontent.com/.../setup-cursor.sh | bash

set -e

echo "================================================"
echo "Claude Skills MCP - Cursor Setup"
echo "================================================"
echo ""

# Check if uv is installed
if ! command -v uvx &> /dev/null; then
    echo "📦 Installing uv (required for uvx)..."
    echo ""
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to current shell
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # Verify installation
    if ! command -v uvx &> /dev/null; then
        echo ""
        echo "⚠️  uv installed but not in PATH"
        echo "Please restart your terminal and run this script again"
        echo "Or add to your shell profile:"
        echo '  export PATH="$HOME/.cargo/bin:$PATH"'
        exit 1
    fi
    
    echo "✓ uv installed successfully"
    echo ""
else
    echo "✓ Found uv: $(uvx --version)"
    echo ""
fi

# Pre-warm the uvx cache
echo "📥 Pre-downloading dependencies..."
echo ""
echo "This is a one-time download (~250 MB, takes 60-120 seconds)"
echo "Future startups will be fast (5-10 seconds)"
echo ""
echo "Downloading..."

# Run uvx to cache everything
if uvx claude-skills-mcp --help > /dev/null 2>&1; then
    echo ""
    echo "✓ Dependencies cached successfully!"
else
    echo ""
    echo "❌ Failed to download dependencies"
    echo "Please check your internet connection and try again"
    exit 1
fi

echo ""

# Configure Cursor
echo "⚙️  Configuring Cursor..."
CURSOR_CONFIG="$HOME/.cursor/mcp.json"
CURSOR_DIR="$HOME/.cursor"

# Create .cursor directory if it doesn't exist
mkdir -p "$CURSOR_DIR"

# Backup existing config
if [ -f "$CURSOR_CONFIG" ]; then
    BACKUP_FILE="$CURSOR_CONFIG.backup.$(date +%s)"
    cp "$CURSOR_CONFIG" "$BACKUP_FILE"
    echo "  (Backed up existing config to $(basename $BACKUP_FILE))"
fi

# Update or create config using Python
python3 << 'PYEOF'
import json
import os
from pathlib import Path

config_path = Path.home() / ".cursor" / "mcp.json"

# Load existing config or create new
if config_path.exists():
    with open(config_path) as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            config = {"mcpServers": {}}
else:
    config = {"mcpServers": {}}

# Ensure mcpServers exists
if "mcpServers" not in config:
    config["mcpServers"] = {}

# Add claude-skills configuration
config["mcpServers"]["claude-skills"] = {
    "command": "uvx",
    "args": ["claude-skills-mcp"]
}

# Write back
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✓ Updated {config_path}")
PYEOF

echo ""
echo "================================================"
echo "✓ Setup Complete!"
echo "================================================"
echo ""
echo "Configuration:"
echo "  Location: ~/.cursor/mcp.json"
echo "  Command: uvx claude-skills-mcp"
echo ""
echo "Next steps:"
echo "  1. Restart Cursor"
echo "  2. The AI assistant will have access to 90+ skills!"
echo ""
echo "Benefits:"
echo "  • Fast startup (5-10 seconds)"
echo "  • Auto-updates on new releases"
echo "  • 90+ scientific and general-purpose skills"
echo ""
echo "To update later:"
echo "  Dependencies auto-update when new versions release"
echo "  Just restart Cursor to get the latest version"
echo ""
echo "To uninstall:"
echo "  Remove 'claude-skills' from ~/.cursor/mcp.json"
echo "  Run: uv cache clean claude-skills-mcp"
echo ""

