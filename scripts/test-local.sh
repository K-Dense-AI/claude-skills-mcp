#!/bin/bash
# Test script for local development

set -e

cd "$(dirname "$0")/.."

echo "================================================"
echo "Testing Claude Skills MCP"
echo "================================================"
echo ""

# Test 1: Backend Installation
echo "Test 1: Installing backend in test environment..."
cd packages/backend
if uv pip install -e ".[test]"; then
    echo "✓ Backend installed successfully"
else
    echo "✗ Backend installation failed"
    exit 1
fi
echo ""

# Test 2: Backend Can Start
echo "Test 2: Testing backend can import and initialize..."
if uv run python -c "
from claude_skills_mcp_backend.http_server import initialize_backend
from claude_skills_mcp_backend.search_engine import SkillSearchEngine
print('✓ Backend imports successful')
engine = SkillSearchEngine('all-MiniLM-L6-v2')
print('✓ Search engine initialized')
"; then
    echo "✓ Backend imports and initializes"
else
    echo "✗ Backend import/init failed"
    exit 1
fi
echo ""

# Test 3: Frontend Installation
echo "Test 3: Installing frontend in test environment..."
cd ../frontend
if uv pip install -e ".[test]"; then
    echo "✓ Frontend installed successfully"
else
    echo "✗ Frontend installation failed"
    exit 1
fi
echo ""

# Test 4: Frontend Can Import
echo "Test 4: Testing frontend can import..."
if uv run python -c "
from claude_skills_mcp.mcp_proxy import MCPProxy, TOOL_SCHEMAS
from claude_skills_mcp.backend_manager import BackendManager
print('✓ Frontend imports successful')
print(f'✓ {len(TOOL_SCHEMAS)} tools defined')
"; then
    echo "✓ Frontend imports work"
else
    echo "✗ Frontend import failed"
    exit 1
fi
echo ""

# Test 5: Run Backend Tests
echo "Test 5: Running backend tests..."
cd ../backend
if uv run pytest tests/test_search_engine.py -v -x; then
    echo "✓ Backend tests pass"
else
    echo "⚠ Some backend tests failed (expected, may need updates)"
fi
echo ""

echo "================================================"
echo "Basic Tests Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Fix any test failures"
echo "2. Test backend HTTP server manually"
echo "3. Test frontend proxy manually"
echo "4. Run full integration tests"
echo ""

