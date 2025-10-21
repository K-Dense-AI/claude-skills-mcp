# Usage Examples

## Running the Server

### Basic Usage (Default Configuration)

```bash
uvx claude-skills-mcp
```

This will:
1. Load the K-Dense-AI Scientific Skills repository
2. Index 69+ scientific skills
3. Start the MCP server on stdio

### With Custom Configuration

```bash
# Generate example config
uvx claude-skills-mcp --example-config > my-config.json

# Edit my-config.json to add your skill sources

# Run with custom config
uvx claude-skills-mcp --config my-config.json
```

### With Verbose Logging

```bash
uvx claude-skills-mcp --verbose
```

## Using the MCP Tool

Once the server is running and connected to Claude, you can use the `search_skills` tool:

### Example 1: RNA Analysis

**Task**: "I need to analyze RNA sequencing data and identify differentially expressed genes"

**Expected Results**: Skills like:
- `pydeseq2` - Differential expression analysis
- `scanpy` - Single-cell RNA analysis
- `anndata` - Annotated data matrices

### Example 2: Drug Discovery

**Task**: "I want to screen chemical compounds for drug targets"

**Expected Results**: Skills like:
- `rdkit` - Chemistry toolkit
- `deepchem` - Deep learning for chemistry
- `chembl-database` - Bioactive molecules database
- `zinc-database` - Commercially available compounds

### Example 3: Protein Structure

**Task**: "I need to predict and analyze protein structures"

**Expected Results**: Skills like:
- `alphafold-database` - Protein structure predictions
- `pdb-database` - Protein Data Bank access
- `biopython` - Biological computation

### Example 4: Statistical Analysis

**Task**: "Perform Bayesian statistical modeling on experimental data"

**Expected Results**: Skills like:
- `pymc-bayesian-modeling` - Probabilistic programming
- `statistical-analysis` - Statistical thinking skill

## Connecting to Claude

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

### Claude Code

Add to your MCP settings in Claude Code:

```json
{
  "mcpServers": {
    "claude-skills": {
      "command": "uvx",
      "args": ["claude-skills-mcp", "--config", "/path/to/config.json"]
    }
  }
}
```

## Configuration Examples

### Scientific Research Focus

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 5
}
```

### Mixed Sources

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills"
    },
    {
      "type": "github",
      "url": "https://github.com/anthropics/claude-cookbooks",
      "subpath": "skills/custom_skills"
    },
    {
      "type": "local",
      "path": "~/my-custom-skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 3
}
```

### Local Skills Only

```json
{
  "skill_sources": [
    {
      "type": "local",
      "path": "~/.claude/skills"
    },
    {
      "type": "local",
      "path": "/Users/me/work/team-skills"
    }
  ],
  "embedding_model": "all-MiniLM-L6-v2",
  "default_top_k": 3
}
```

## Creating Your Own Skills

Create a directory with a `SKILL.md` file:

```markdown
---
name: My Custom Skill
description: Brief description of what this skill does and when to use it
---

# My Custom Skill

## Overview

Detailed information about the skill...

## Quick Start

```python
# Example code
import my_library
```

## Use Cases

- Use case 1
- Use case 2

## Best Practices

...
```

Then add the directory to your config:

```json
{
  "skill_sources": [
    {
      "type": "local",
      "path": "/path/to/my-skills"
    }
  ]
}
```

## Troubleshooting

### No skills loaded

- Check your internet connection if using GitHub sources
- Verify GitHub repository URLs are correct
- Check file paths for local sources
- Use `--verbose` flag to see detailed logs

### Low relevance scores

- Try different task descriptions
- Increase `top_k` to see more results
- Ensure skill descriptions are clear and comprehensive

### Server won't start

- Ensure Python 3.12 is available
- Check that all dependencies are installed: `uv sync`
- Review error logs with `--verbose` flag

