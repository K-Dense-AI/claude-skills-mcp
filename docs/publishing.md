# Publishing to PyPI Guide

## Pre-Publication Checklist

### ✅ Package Metadata (Complete)
- [x] Package name: `claude-skills-mcp`
- [x] Version: `0.1.0`
- [x] Description
- [x] README.md (used as PyPI long description)
- [x] License: PolyForm Noncommercial 1.0.0
- [x] License file: `LICENSE.md` (automatically included)
- [x] Authors: K-Dense AI
- [x] Keywords for discoverability
- [x] Classifiers for categorization
- [x] Python version constraint: `>=3.12,<3.13`
- [x] Project URLs (homepage, repository, bug tracker, etc.)
- [x] Entry point: `claude-skills-mcp` command

### ✅ Dependencies (Complete)
- [x] All runtime dependencies specified
- [x] Test dependencies in `[project.optional-dependencies]`
- [x] Build backend configured (hatchling)

### ✅ Testing (Complete)
- [x] 40 tests passing
- [x] Coverage: 56%
- [x] GitHub CI configured
- [x] Integration tests with local and GitHub skills
- [x] No linting errors

### ✅ Documentation (Complete)
- [x] README.md with quick start
- [x] Usage examples in docs/usage.md
- [x] Testing guide in docs/testing.md
- [x] Configuration examples
- [x] K-Dense AI branding and links

### ✅ Build Verification (Complete)
- [x] Package builds successfully: `uv build`
- [x] LICENSE.md included in distributions
- [x] All files properly packaged

## Publishing Steps

### 1. Test with TestPyPI First (Recommended)

TestPyPI is a separate instance for testing before real publication.

#### Register on TestPyPI
1. Go to https://test.pypi.org/account/register/
2. Create account and verify email

#### Create API Token
1. Go to https://test.pypi.org/manage/account/#api-tokens
2. Create token with "Entire account" scope
3. Save the token (you won't see it again!)

#### Upload to TestPyPI
```bash
# Build the package
uv build

# Upload to TestPyPI
uv publish --publish-url https://test.pypi.org/legacy/
# Enter your API token when prompted (include the pypi- prefix)
```

#### Test Installation from TestPyPI
```bash
# Install from TestPyPI
uvx --from https://test.pypi.org/simple/ claude-skills-mcp --help

# Test it works
uvx --from https://test.pypi.org/simple/ claude-skills-mcp --example-config
```

### 2. Publish to Real PyPI

Once you've verified everything works on TestPyPI:

#### Register on PyPI
1. Go to https://pypi.org/account/register/
2. Create account and verify email
3. Note: TestPyPI and PyPI are separate - you need accounts on both

#### Create API Token
1. Go to https://pypi.org/manage/account/#api-tokens
2. Create token with "Entire account" scope
3. Save the token securely

#### Upload to PyPI
```bash
# Build the package (if not already built)
uv build

# Upload to real PyPI
uv publish
# Enter your API token when prompted
```

#### Verify Publication
Your package will be available at:
```
https://pypi.org/project/claude-skills-mcp/
```

Users can then install with:
```bash
uvx claude-skills-mcp
```

### 3. Post-Publication

#### Tag the Release
```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

#### Create GitHub Release
1. Go to https://github.com/K-Dense-AI/claude-skills-mcp/releases
2. Click "Draft a new release"
3. Select tag `v0.1.0`
4. Add release notes
5. Publish release

#### Update README Badge (Optional)
Add PyPI badge to README.md:
```markdown
[![PyPI version](https://badge.fury.io/py/claude-skills-mcp.svg)](https://badge.fury.io/py/claude-skills-mcp)
```

## Verification Before Publishing

### Check Package Contents
```bash
# View source distribution contents
tar -tzf dist/claude_skills_mcp-0.1.0.tar.gz

# View wheel contents
unzip -l dist/claude_skills_mcp-0.1.0-py3-none-any.whl

# Verify LICENSE.md is included
tar -tzf dist/claude_skills_mcp-0.1.0.tar.gz | grep LICENSE.md
unzip -l dist/claude_skills_mcp-0.1.0-py3-none-any.whl | grep LICENSE.md
```

### Test Local Installation
```bash
# Install from local wheel
uv pip install dist/claude_skills_mcp-0.1.0-py3-none-any.whl

# Test the command works
claude-skills-mcp --help
claude-skills-mcp --example-config
```

### Run Full Test Suite
```bash
# All tests with coverage
uv run pytest tests/

# Integration tests
uv run pytest tests/ -m integration
```

## Troubleshooting

### Build Fails
- Check pyproject.toml syntax
- Ensure all required files exist (README.md, LICENSE.md)
- Run `uv sync` to update dependencies

### Upload Fails
- Verify API token is correct (includes `pypi-` prefix)
- Check network connection
- Ensure package name doesn't conflict with existing packages

### Installation Fails
- Verify Python version compatibility (3.12 required)
- Check dependencies are available on PyPI
- Test with `--verbose` flag for detailed errors

## Version Updates

For future releases:

1. Update version in `pyproject.toml`
2. Update version in `src/claude_skills_mcp/__init__.py`
3. Run tests: `uv run pytest tests/`
4. Build: `uv build`
5. Publish: `uv publish`
6. Tag release: `git tag -a v0.x.0 -m "Release v0.x.0"`
7. Push tags: `git push origin v0.x.0`

## Current Status

✅ **Package is ready for publication!**

All requirements met:
- Proper metadata configuration
- License file included in distributions
- Tests passing (40/40)
- Documentation complete
- Build system configured
- Entry points working

You can now publish with confidence! 🚀

