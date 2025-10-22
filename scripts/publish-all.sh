#!/bin/bash
# Publish both packages to PyPI
# IMPORTANT: Backend must be published first since frontend depends on it

set -e

cd "$(dirname "$0")/.."

echo "================================================"
echo "Publishing Claude Skills MCP Packages to PyPI"
echo "================================================"
echo ""

# Verify builds exist
if [ ! -d "packages/backend/dist" ] || [ ! -d "packages/frontend/dist" ]; then
    echo "Error: Build artifacts not found. Run ./scripts/build-all.sh first"
    exit 1
fi

echo "Publishing backend first (claude-skills-mcp-backend)..."
echo "This is required because frontend depends on it."
echo ""
cd packages/backend
uv publish
cd ../..
echo "✓ Backend published to PyPI"
echo ""

echo "Waiting 30 seconds for PyPI to index backend..."
sleep 30
echo ""

echo "Publishing frontend (claude-skills-mcp)..."
cd packages/frontend
uv publish
cd ../..
echo "✓ Frontend published to PyPI"
echo ""

echo "================================================"
echo "Publish Complete!"
echo "================================================"
echo ""
echo "Published packages:"
echo "  - claude-skills-mcp-backend v1.0.0"
echo "  - claude-skills-mcp v1.0.0"
echo ""
echo "Verify at:"
echo "  - https://pypi.org/project/claude-skills-mcp-backend/"
echo "  - https://pypi.org/project/claude-skills-mcp/"
echo ""

