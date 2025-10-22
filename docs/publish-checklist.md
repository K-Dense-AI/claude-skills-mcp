# v1.0.0 Publishing Checklist

## Status: Ready for Testing & Publishing

### ✅ Completed

- ✅ Two-package architecture implemented
- ✅ Backend package (`claude-skills-mcp-backend`) complete
- ✅ Frontend package (`claude-skills-mcp`) complete
- ✅ Both packages build successfully
- ✅ All 62 backend unit tests pass
- ✅ Documentation updated (README, migration guide, release notes)
- ✅ Build and publish scripts created
- ✅ Old src/ directory removed
- ✅ Repository structure cleaned up

### 🧪 Testing Required

**Before publishing, YOU should**:

1. **Publish backend to PyPI first**:
   ```bash
   cd packages/backend
   uv publish
   ```
   Wait for indexing (~30 seconds)

2. **Test frontend with published backend**:
   ```bash
   # Clear cache to simulate first-time user
   uv cache clean claude-skills-mcp-backend
   
   # Test frontend with uvx
   uvx --from /path/to/packages/frontend/dist/claude_skills_mcp-1.0.0-py3-none-any.whl claude-skills-mcp --verbose
   ```
   
   This will test:
   - Frontend starts quickly
   - Backend auto-downloads via uvx
   - Connection works
   - Tools function properly

3. **Publish frontend to PyPI**:
   ```bash
   cd packages/frontend
   uv publish
   ```

4. **Test full uvx flow** (as end user would):
   ```bash
   # Clean everything
   uv cache clean claude-skills-mcp
   uv cache clean claude-skills-mcp-backend
   
   # Test fresh install
   time uvx claude-skills-mcp --help
   # Should be fast (<10s) for frontend
   ```

## Publishing Workflow

### Step 1: Publish Backend

```bash
cd /Users/haoxuanl/kdense/claude-skills-mcp/packages/backend

# Verify build
ls -lh dist/
# Should see:
# - claude_skills_mcp_backend-1.0.0-py3-none-any.whl (24KB)
# - claude_skills_mcp_backend-1.0.0.tar.gz (36KB)

# Publish to PyPI
uv publish

# Verify on PyPI
open https://pypi.org/project/claude-skills-mcp-backend/
```

### Step 2: Wait for Indexing

```bash
echo "Waiting for PyPI to index backend..."
sleep 30
```

### Step 3: Publish Frontend

```bash
cd /Users/haoxuanl/kdense/claude-skills-mcp/packages/frontend

# Verify build
ls -lh dist/
# Should see:
# - claude_skills_mcp-1.0.0-py3-none-any.whl (11KB)
# - claude_skills_mcp-1.0.0.tar.gz (9.1KB)

# Publish to PyPI
uv publish

# Verify on PyPI
open https://pypi.org/project/claude-skills-mcp/
```

### Step 4: Create GitHub Release

```bash
cd /Users/haoxuanl/kdense/claude-skills-mcp

# Create git tag
git tag -a v1.0.0 -m "v1.0.0 - Two-package architecture"

# Push tag
git push origin v1.0.0

# Create release on GitHub with:
# - Tag: v1.0.0
# - Title: "v1.0.0 - Two-Package Architecture (Cursor Timeout Fix)"
# - Description: See docs/v1-release-notes.md
# - Attach: Both wheel files
```

### Step 5: Test Published Version

```bash
# Clean environment
uv cache clean claude-skills-mcp
uv cache clean claude-skills-mcp-backend

# Test as end user
uvx claude-skills-mcp

# Verify:
# 1. Frontend starts quickly
# 2. Backend downloads automatically
# 3. Tools work
```

### Step 6: Update Cursor Directory

1. Visit https://cursor.directory/mcp/claude-skills-mcp
2. Update description to mention two-package architecture
3. Highlight instant startup
4. Add note about backend auto-download

## Post-Publishing

### Announce

- ✅ Update GitHub README
- ✅ Post to Cursor community
- ✅ Update documentation links
- ✅ Monitor for issues

### Monitor

Check for issues:
- Backend installation failures
- Frontend/backend connection issues
- Cursor timeout still happening
- Documentation unclear

## Rollback Plan (If Needed)

If critical issues found:

1. **Mark v1.0.0 as yanked** on PyPI (don't delete)
2. **Publish v1.0.1** with fixes
3. **Update GitHub release** with fix notes

## Success Criteria

- [ ] Backend published to PyPI successfully
- [ ] Frontend published to PyPI successfully
- [ ] End-to-end `uvx` test works
- [ ] Cursor timeout issue resolved
- [ ] No critical bugs in first 24 hours
- [ ] Positive user feedback

## Known Limitations (v1.0.0)

1. **No remote backend yet**: Coming in v1.1.0
2. **First tool use slow**: Backend downloads in background (one-time)
3. **No reconnection logic**: If backend crashes, need to restart frontend

These are acceptable for v1.0.0 and can be improved in future versions.

## Questions for You

Before you publish, please confirm:

1. **Do you want to test locally first?** I can help you test the full flow
2. **Deploy backend remotely before publishing?** You could deploy to your server and test
3. **Publish to test.pypi.org first?** Safer for initial testing

Let me know and I'll assist with testing!

