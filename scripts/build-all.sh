#!/bin/bash
# Build both frontend and backend packages

set -e

cd "$(dirname "$0")/.."

echo "================================================"
echo "Building Claude Skills MCP Packages"
echo "================================================"
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf packages/frontend/dist packages/backend/dist
echo ""

# Build backend first
echo "Building backend (claude-skills-mcp-backend)..."
cd packages/backend
uv build
cd ../..
echo "✓ Backend built"
echo ""

# Build frontend
echo "Building frontend (claude-skills-mcp)..."
cd packages/frontend
uv build
cd ../..
echo "✓ Frontend built"
echo ""

echo "================================================"
echo "Build Complete!"
echo "================================================"
echo ""
echo "Backend artifacts:"
ls -lh packages/backend/dist/
echo ""
echo "Frontend artifacts:"
ls -lh packages/frontend/dist/
echo ""

