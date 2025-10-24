# Architecture Guide

This document describes the internal architecture of the Claude Skills MCP Server v1.0.0, which uses a two-package design to solve the Cursor timeout issue while maintaining simple user experience.

## Overview

The v1.0.0 system uses a **frontend-backend architecture** with two separate packages:

- **Frontend** (`claude-skills-mcp`): Lightweight MCP proxy that starts instantly
- **Backend** (`claude-skills-mcp-backend`): Heavy server with vector search and skill loading

The backend consists of seven core components working together to provide intelligent skill discovery through the Model Context Protocol.

## Core Components

### 1. Configuration System (`config.py`)

**Purpose**: Manages server configuration and provides sensible defaults.

**Key Features**:
- Default configuration with both Anthropic and K-Dense AI scientific skills repositories
- JSON-based config loading with validation
- Fallback to defaults if config unavailable or malformed
- Config printer (--example-config) showing default configuration
- Support for multiple skill sources (GitHub repos and local directories)

**Configuration Flow**:
```
Command line --config option
    ↓
Load JSON file
    ↓
Merge with defaults
    ↓
Pass to skill loader and search engine
```

### 2. Skill Loader (`skill_loader.py`)

**Purpose**: Load skills from various sources and parse their content.

**Key Features**:
- **GitHub repository loading** via API (no authentication required)
- **Local directory scanning** for development and custom skills
- **YAML frontmatter parsing** to extract skill metadata
- **Support for multiple formats**:
  - Direct skills (SKILL.md files)
  - Claude Code plugin repositories
- **Robust error handling**:
  - Network issues with retries
  - Missing files and malformed content
  - Rate limiting (60 requests/hour)
- **Automatic caching** of GitHub API responses (24-hour validity)
- **Document loading**: Scripts, references, images, and other assets

**Loading Process**:
```
Source Configuration
    ↓
GitHub API → Cache → Parse SKILL.md
    ↓
Extract: name, description, content
    ↓
Load additional documents
    ↓
Return Skill objects
```

**Caching Mechanism**:
- Cache location: System temp directory (`/tmp/claude_skills_mcp_cache/`)
- Cache key: MD5 hash of URL + branch
- Cache validity: 24 hours
- Automatic invalidation after expiry
- Dramatically reduces GitHub API usage

**Lazy Document Loading**:

To solve startup timeout issues (60+ seconds), documents are loaded lazily:

**Problem**: Fetching all documents for 90 skills at startup caused timeouts.

**Solution**: 
1. **Startup**: Load only SKILL.md files + document metadata (paths, sizes, types, URLs)
2. **On-Demand**: Fetch document content when `read_skill_document` is called
3. **Memory Cache**: Cache in Skill object for repeated access
4. **Disk Cache**: Persist to `/tmp/claude_skills_mcp_cache/documents/` for future runs

**Performance Impact**:
- Startup time: 60s → 15s (4x improvement)
- Network requests at startup: 300+ → 90 (SKILL.md only)
- First document access: ~200ms (network fetch + cache)
- Subsequent access: <1ms (memory or disk cache)

**Cache Directory Structure**:
```
/tmp/claude_skills_mcp_cache/
├── {md5_hash}.json          # GitHub API tree cache (24h TTL)
└── documents/
    ├── {md5_hash}.cache     # Individual document cache (permanent)
    ├── {md5_hash}.cache
    └── ...
```

**Document Access Flow**:
```
read_skill_document called
    ↓
Match documents by pattern  
    ↓
For each matched document:
    ↓
Check if fetched? → Yes: Use existing content
    ↓ No
skill.get_document(path)
    ↓
Check memory cache → Found: Return
    ↓ Not found
Check disk cache → Found: Return
    ↓ Not found
Fetch from GitHub
    ↓
Save to disk cache
    ↓
Cache in memory
    ↓
Return content
```

### 3. Search Engine (`search_engine.py`)

**Purpose**: Enable semantic search over skill descriptions using vector embeddings.

**Key Features**:
- **Sentence-transformers** for local embeddings
- **Default model**: `all-MiniLM-L6-v2` (384 dimensions, ~90MB)
- **Vector indexing** at startup for fast queries
- **Cosine similarity** search algorithm
- **Configurable top-K** results
- **No API keys** required - fully local operation

**Search Process**:
```
Startup:
  Load skills → Generate embeddings → Build index

Query:
  Encode query → Compute similarity → Rank → Return top-K
```

**Performance Characteristics**:
- Startup: 5-10 seconds (load model + index skills)
- Query time: <1 second
- Memory: ~500MB (model + embeddings)
- Scales well: tested with 70+ skills

**Embedding Model Details**:
- **all-MiniLM-L6-v2**: Fast, good quality, 384 dimensions
- **all-mpnet-base-v2**: Higher quality, slower, 768 dimensions (optional)
- Models are cached after first download

### 4. MCP Handlers (`mcp_handlers.py`) and HTTP Server (`http_server.py`)

**Purpose**: Implement the Model Context Protocol specification over Streamable HTTP.

**Key Features**:
- **Standard MCP protocol** implementation
- **Three tools** with optimized descriptions:
  1. `find_helpful_skills` - Semantic search
  2. `read_skill_document` - Access skill files
  3. `list_skills` - Browse all skills
- **Progressive disclosure** of skill content:
  - Tool descriptions (always visible)
  - Skill metadata (on search)
  - Full content (when relevant)
  - Referenced files (on demand)
- **Content truncation** (configurable)
- **Streamable HTTP transport** for remote access
- **Frontend Proxy** (`mcp_proxy.py`, `backend_manager.py`):
  - Stdio MCP server for Cursor
  - HTTP MCP client for backend
  - Backend process management
  - Auto-downloads backend via `uvx`
- **Formatted output** with:
  - Relevance scores
  - Source links
  - Document metadata

**Tool Invocation Flow (v1.0.0)**:
```
AI Assistant (e.g., Cursor)
    ↓
Frontend Proxy (stdio MCP server)
    ↓
HTTP Client → Backend (streamable HTTP MCP server)
    ↓
MCP Handler (find_helpful_skills, read_skill_document, list_skills)
    ↓
Search Engine / Skill Loader
    ↓
Format Response
    ↓
Frontend Proxy → AI Assistant
```

**Progressive Disclosure Implementation**:
1. **Level 1**: Tool names/descriptions (always in context)
2. **Level 2**: Skill names/descriptions (search results)
3. **Level 3**: Full SKILL.md content (when skill is relevant)
4. **Level 4**: Additional documents (scripts, data, references)

This architecture minimizes context window usage while ensuring all necessary information is available when needed.

### 5. Entry Point (`__main__.py`)

**Purpose**: Provide CLI interface and manage server lifecycle.

**Key Features**:
- **CLI argument parsing**:
  - `--config`: Custom configuration file
  - `--example-config`: Print example config
  - `--verbose`: Enable debug logging
- **Async server lifecycle**:
  - Load configuration
  - Initialize components
  - Run server
  - Handle shutdown gracefully
- **Comprehensive error handling**:
  - Missing dependencies
  - Network failures
  - Invalid configuration
- **Logging configuration**:
  - Info level by default
  - Debug level with --verbose
  - Structured log messages

**Startup Sequence**:
```
Parse CLI arguments
    ↓
Load configuration
    ↓
Initialize skill loader
    ↓
Load skills from sources (background thread)
    ↓
Initialize search engine
    ↓
Index skills (incremental)
    ↓
Initialize auto-update system (if enabled)
    ↓
Start MCP server
    ↓
Listen for tool calls
```

### 6. Auto-Update System (`update_checker.py`, `scheduler.py`, `state_manager.py`)

**Purpose**: Automatically detect and reload skills when remote or local sources change.

**Key Features**:
- **Hourly scheduling** synchronized to exact clockface hours (e.g., 12:00, 13:00)
- **Efficient change detection**:
  - GitHub: Commit SHA comparison (1 API call per repo)
  - Local: File modification time tracking
- **State persistence** survives server restarts
- **API rate limit awareness** (60 req/hr unauthenticated, 5000 with token)
- **Graceful error handling** with retry on next cycle

**Components**:

**UpdateChecker**:
- Orchestrates update checking across all sources
- Tracks API usage and warns when approaching limits
- Returns list of changed sources for selective reloading

**GitHubSourceTracker**:
- Checks HEAD commit SHA via GitHub API
- Compares against last known SHA from persistent state
- Only triggers update if SHA has changed
- Respects rate limits and tracks usage

**LocalSourceTracker**:
- Scans for `SKILL.md` files in configured directories
- Tracks modification times of all skill files
- Detects new, modified, or deleted files

**HourlyScheduler**:
- Calculates time until next exact hour on startup
- Runs update checks at configured intervals (default: 60 min)
- Aligns to clockface hours for predictable scheduling
- Handles cancellation and errors gracefully

**StateManager**:
- Persists commit SHAs and modification times to disk
- Cache location: `/tmp/claude_skills_mcp_cache/state/`
- Prevents false positives on first check after restart

**Update Flow**:
```
Hourly Scheduler (wait until :00)
    ↓
Check GitHub sources (commit SHA)
    ↓
Check local sources (mtime)
    ↓
Changes detected?
    ├─ No → Log and continue
    └─ Yes → Reload all skills
               ↓
           Re-index embeddings
               ↓
           Update complete
```

**Configuration**:
```json
{
  "auto_update_enabled": true,
  "auto_update_interval_minutes": 60,
  "github_api_token": null
}
```

**API Budget** (default 2 GitHub sources):
- Commit checks: 2 calls/hour
- On change: +2 tree API calls = 4 total/hour
- Remaining: 56 calls/hour for other operations
- Raw content access: Unlimited (doesn't count against limit)

See [auto-update.md](auto-update.md) for detailed documentation.

## Data Flow

### Complete Request Flow

```
User Query
    ↓
AI Assistant (Claude, GPT, etc.)
    ↓
MCP Client
    ↓
MCP Server (stdio)
    ↓
Tool Handler (find_helpful_skills)
    ↓
Search Engine
    ↓
Cosine Similarity Computation
    ↓
Rank Skills
    ↓
Format Response
    ↓
Return to AI Assistant
    ↓
AI uses skill content
```

### Skill Loading Flow

```
Configuration
    ↓
Skill Loader
    ├─ GitHub API (with caching)
    │    ↓
    │  Download tree
    │    ↓
    │  Find SKILL.md files
    │    ↓
    │  Download content
    │    ↓
    │  Load documents
    │
    └─ Local Filesystem
         ↓
       Scan directories
         ↓
       Find SKILL.md files
         ↓
       Read content
         ↓
       Load documents
    ↓
Parse SKILL.md (YAML + Markdown)
    ↓
Create Skill objects
    ↓
Return to Search Engine for indexing
```

## Design Decisions

### Why Local Embeddings?

- **No API keys required**: Easier setup for users
- **Privacy**: All processing happens locally
- **Cost**: No per-query charges
- **Speed**: <1 second per query
- **Offline**: Works without internet (after initial setup)

**Trade-off**: Slightly lower quality than large cloud models, but excellent for this use case.

### Why Progressive Disclosure?

Following Anthropic's Agent Skills architecture:

1. **Context Window Efficiency**: Don't load all skills upfront
2. **Relevance Filtering**: Only show skills that match the task
3. **On-Demand Detail**: Load full content only when needed
4. **Scalability**: Works with hundreds of skills without overwhelming context

### Why Caching?

**Problem**: GitHub API has a 60 requests/hour limit for unauthenticated access.

**Solution**: 
- Cache tree API responses (the rate-limited call)
- 24-hour validity is reasonable for skill repositories
- Dramatically speeds up development and testing
- Cache in temp directory for automatic cleanup

**Benefits**:
- First run: ~20-30 seconds (with API calls + lazy document loading)
- Subsequent runs: ~10-15 seconds (from cache)
- No rate limit issues during development

### Why Three Tools?

1. **`find_helpful_skills`**: Task-oriented discovery (main use case)
2. **`read_skill_document`**: Access scripts and assets (progressive disclosure)
3. **`list_skills`**: Exploration and debugging (understand what's available)

This separation allows AI assistants to:
- Find relevant skills efficiently
- Access additional resources on demand
- Debug configuration issues
- Explore available capabilities

## Extension Points

The architecture is designed to be extensible:

### Adding New Skill Sources

Implement in `skill_loader.py`:
```python
def load_from_custom_source(url: str, config: dict) -> list[Skill]:
    # Your implementation
    return skills
```

Then add to `load_all_skills()`.

### Adding New Embedding Models

Update `config.py`:
```python
"embedding_model": "your-model-name"
```

The search engine automatically loads any sentence-transformers model.

### Adding New Tools

1. Define tool in `server.py` `list_tools()`
2. Implement handler method `_handle_your_tool()`
3. Add route in `call_tool()`

### Custom Skill Formats

Extend `parse_skill_md()` in `skill_loader.py` to handle custom frontmatter fields or markdown extensions.

## Performance Optimization

### Startup Time

- **Fast path**: Use local directories instead of GitHub
- **Lazy loading**: Consider implementing lazy skill loading
- **Smaller model**: Use `all-MiniLM-L6-v2` instead of larger models

### Query Time

Already very fast (<1 second). Further optimization possible:
- **Approximate search**: Use FAISS or similar for 1000+ skills
- **Caching**: Cache frequent queries (not implemented)

### Memory Usage

- **Model size**: 90-420MB depending on choice
- **Skills**: ~1KB per skill
- **Documents**: Varies based on skill complexity

Total: ~500MB typical, scales linearly with skill count.

## Security Considerations

### GitHub API

- **No authentication**: Uses public API (60 req/hour limit)
- **No credentials**: Never stores or transmits auth tokens
- **HTTPS only**: All GitHub requests use TLS

### Local Files

- **Path validation**: Checks for directory traversal
- **Home directory expansion**: Supports `~` in paths
- **Error isolation**: Failed skills don't crash server

### MCP Protocol

- **Stdio transport**: Isolated from network
- **No code execution**: Skills are data only (markdown)
- **Sandboxing**: Running via MCP provides OS-level isolation

**Note**: The `read_skill_document` tool can access Python scripts and other files. These are loaded as text/data only, not executed.

## Testing Strategy

See [Testing Guide](testing.md) for comprehensive testing instructions.

**Architecture tests**:
- Unit tests for each component
- Integration tests for data flow
- End-to-end tests with real repositories

**Coverage**:
- Configuration: 86%
- Skill Loader: 68%
- Search Engine: 100%
- Server: Tested via integration tests

## Troubleshooting

### Server won't start

Check:
1. Python 3.12 installed (not 3.13)
2. Dependencies installed (`uv sync`)
3. Configuration valid JSON

### Skills not loading

Check:
1. GitHub rate limit (wait an hour)
2. Repository exists and is public
3. SKILL.md files have valid frontmatter
4. Use `--verbose` to see detailed logs

### Search returns poor results

Check:
1. Skill descriptions are specific and descriptive
2. Query uses domain-appropriate terminology
3. Increase `top_k` to see more results
4. Consider using larger embedding model

### High memory usage

Solutions:
1. Use smaller embedding model
2. Limit number of skill sources
3. Use subpath filtering to load fewer skills

## Package Structure (v1.0.0)

### Frontend Package (`claude-skills-mcp`)

**Location**: `packages/frontend/`

**Modules**:
- `__main__.py`: CLI entry point with argument forwarding
- `mcp_proxy.py`: MCP stdio server + HTTP client proxy
- `backend_manager.py`: Backend process lifecycle management

**Dependencies**: `mcp`, `httpx` (~15 MB total)

### Backend Package (`claude-skills-mcp-backend`)

**Location**: `packages/backend/`

**Modules**:
- `__main__.py`: CLI entry point
- `http_server.py`: Streamable HTTP server with Starlette/Uvicorn
- `mcp_handlers.py`: MCP tool implementations
- `search_engine.py`: Vector search with sentence-transformers
- `skill_loader.py`: GitHub and local skill loading
- `config.py`: Configuration management

**Dependencies**: `mcp`, `torch`, `sentence-transformers`, `starlette`, `uvicorn`, `httpx`, `numpy` (~250 MB total)

