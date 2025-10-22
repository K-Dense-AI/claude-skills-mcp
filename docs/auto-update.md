# Auto-Update Feature

## Overview

The claude-skills-mcp-backend now includes automatic hourly skill updates synchronized to exact clockface hours (e.g., 12:00:00, 13:00:00).

## How It Works

### Change Detection

#### GitHub Sources
- Uses commit SHA comparison via GitHub API (`/repos/{owner}/{repo}/commits/{branch}`)
- Makes 1 API call per repository to check the HEAD commit
- Only re-indexes if the commit SHA has changed
- Respects GitHub API rate limits (60 req/hr unauthenticated, 5000 req/hr with token)

#### Local Sources
- Tracks modification times (`mtime`) of all `SKILL.md` files
- Detects new, modified, or deleted skill files
- No external API calls required

### Scheduling

- **First Check**: Synchronized to the next exact clockface hour (e.g., if started at 12:34, first check at 13:00)
- **Subsequent Checks**: Every N minutes (configurable, default 60)
- **Alignment**: For 60-minute intervals, checks occur at :00 of each hour

### State Persistence

- Commit SHAs and file modification times are persisted to disk
- Stored in system temp directory: `/tmp/claude_skills_mcp_cache/state/`
- Survives server restarts to avoid unnecessary initial updates
- First check after startup establishes baseline (no update triggered)

### Re-indexing Strategy

- If changes detected: Reload all skills and rebuild embeddings
- If no changes: Continue with existing index
- On errors: Keep existing skills, log error, retry next cycle

## Configuration

### Enable/Disable

```json
{
  "auto_update_enabled": true,
  "auto_update_interval_minutes": 60,
  "github_api_token": null
}
```

### GitHub Token (Optional)

Provide a personal access token to increase API rate limit from 60 to 5000 requests/hour:

```json
{
  "github_api_token": "ghp_your_token_here"
}
```

## API Usage Tracking

### Monitoring

The `/health` endpoint provides real-time API usage information:

```json
{
  "auto_update_enabled": true,
  "next_update_check": "2024-01-15T14:00:00",
  "last_update_check": "2024-01-15T13:00:00",
  "github_api_calls_this_hour": 2,
  "github_api_limit": 60,
  "github_authenticated": false
}
```

### Budget Management

With default configuration (2 GitHub sources):
- **Commit checks**: 2 API calls/hour
- **On change detected**: +2 tree API calls = 4 total/hour
- **Remaining budget**: 56 calls/hour for other operations
- **Warning threshold**: 50 calls/hour (logged automatically)

### Raw GitHub Content

Accessing `raw.githubusercontent.com` for skill content does **not** count against the API rate limit.

## Error Handling

- All exceptions caught and logged
- Server continues running on update failures
- Existing skills preserved
- Errors available via `/health` endpoint (last 5 errors)
- Automatic retry on next scheduled cycle

## Implementation Details

### Architecture

```
http_server.py
  |
  +-- UpdateChecker (orchestrates updates)
  |     |
  |     +-- GitHubSourceTracker (commit SHA tracking)
  |     |     |
  |     |     +-- StateManager (persist SHAs)
  |     |
  |     +-- LocalSourceTracker (mtime tracking)
  |           |
  |           +-- StateManager (persist mtimes)
  |
  +-- HourlyScheduler (clockface-aligned scheduling)
        |
        +-- update_callback (check & reload)
```

### Key Files

- `update_checker.py`: Change detection for GitHub and local sources
- `scheduler.py`: Hourly scheduling with clockface alignment
- `state_manager.py`: State persistence to disk
- `http_server.py`: Integration with backend server
- `config.py`: Configuration management

## Testing

### Unit Tests

```bash
# Update checker tests
uv run pytest tests/test_update_checker.py -v

# Scheduler tests  
uv run pytest tests/test_scheduler.py -v
```

### Integration Test

```bash
# Test with real GitHub API
uv run pytest tests/test_integration.py::test_update_detection -v
```

## Example Usage

### Server Startup

```bash
# Start with default configuration (auto-update enabled)
uvx claude-skills-mcp-backend

# Start with custom config
uvx claude-skills-mcp-backend --config my-config.json
```

### Health Check

```bash
curl http://localhost:8765/health
```

Example response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "skills_loaded": 85,
  "models_loaded": true,
  "loading_complete": true,
  "auto_update_enabled": true,
  "next_update_check": "2024-01-15T14:00:00",
  "last_update_check": "2024-01-15T13:00:00",
  "github_api_calls_this_hour": 2,
  "github_api_limit": 60,
  "github_authenticated": false
}
```

## Disabling Auto-Update

To disable automatic updates, set in your config:

```json
{
  "auto_update_enabled": false
}
```

Skills will still be loaded on startup, but won't auto-update.

## Performance Impact

- **Negligible**: Update checks run in background
- **API calls**: 2-4 per hour (minimal)
- **Re-indexing**: Only when changes detected
- **Memory**: State files < 1KB per source
- **CPU**: Brief spike during re-indexing only

## Best Practices

1. **Use a token** for production environments with frequent updates
2. **Monitor** API usage via `/health` endpoint
3. **Set appropriate intervals** based on your update frequency needs
4. **Test** with integration tests before deploying
5. **Check logs** for update status and errors

