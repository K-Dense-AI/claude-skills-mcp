# Usage Examples

This guide provides detailed examples and use cases beyond the Quick Start in the main README.

## Advanced Configuration Examples

## Real-World Use Cases

### Bioinformatics Research

**Scenario**: You're analyzing single-cell RNA sequencing data

**Skills that will be found**:
- `scanpy` - Single-cell analysis framework
- `anndata` - Annotated data matrices
- `umap-learn` - Dimensionality reduction
- `pytorch-lightning` - Deep learning models

**Example queries**:
- "Analyze single-cell RNA sequencing data with clustering"
- "Perform differential expression analysis between cell types"
- "Visualize gene expression patterns in UMAP space"

### Drug Discovery Pipeline

**Scenario**: Screening compounds and predicting activity

**Skills that will be found**:
- `rdkit` - Molecular manipulation
- `deepchem` - ML for chemistry
- `chembl-database` - Bioactive compounds
- `diffdock` - Protein-ligand docking
- `medchem` - Drug-likeness filtering

**Example queries**:
- "Screen chemical libraries for drug-like properties"
- "Predict protein-ligand binding affinity"
- "Filter compounds by Lipinski's rule of five"

### Genomic Variant Analysis

**Scenario**: Clinical genomics and variant interpretation

**Skills that will be found**:
- `clinvar-database` - Clinical variant database
- `ensembl-database` - Genome annotations
- `biopython` - Sequence manipulation
- `pysam` - SAM/BAM file handling

**Example queries**:
- "Interpret genomic variants for clinical significance"
- "Access variant pathogenicity predictions"
- "Analyze VCF files from whole genome sequencing"

### Materials Science

**Scenario**: Computational materials research

**Skills that will be found**:
- `pymatgen` - Materials analysis
- `astropy` - Scientific computing

**Example queries**:
- "Analyze crystal structures and phase diagrams"
- "Calculate electronic structure properties"

## Connecting to AI Assistants

This MCP server works with any MCP-compatible application. Here are configuration examples for popular platforms:

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

### Cursor & Other MCP-Compatible Editors

Configuration is similar for any MCP-compatible IDE. Refer to your editor's MCP integration documentation for specific configuration file locations.

## Advanced Configuration Patterns

### Using Browser URLs with Subpaths

You can paste GitHub URLs directly from your browser:

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/scientific-thinking"
    }
  ]
}
```

This automatically extracts:
- Repository: `K-Dense-AI/claude-scientific-skills`
- Branch: `main`
- Subpath: `scientific-thinking`

### Loading Only Specific Skill Categories

Load only scientific thinking skills (document processing, peer review, etc.):

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/scientific-thinking"
    }
  ],
  "default_top_k": 5
}
```

Load only database skills:

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/scientific-databases"
    }
  ]
}
```

### Team-Specific Configuration

Combine company GitHub repo with local team skills:

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/your-org/company-skills"
    },
    {
      "type": "local",
      "path": "~/team-skills"
    }
  ],
  "default_top_k": 5
}
```

### Multiple Repositories

Load skills from multiple sources:

```json
{
  "skill_sources": [
    {
      "type": "github",
      "url": "https://github.com/K-Dense-AI/claude-scientific-skills"
    },
    {
      "type": "github",
      "url": "https://github.com/anthropics/claude-cookbooks/tree/main/skills/custom_skills"
    },
    {
      "type": "github",
      "url": "https://github.com/Jeffallan/claude-skills"
    }
  ]
}
```

## Creating Custom Skills

### Skill Structure

Each skill is a directory containing a `SKILL.md` file:

```
my-custom-skill/
├── SKILL.md              # Required: skill definition
├── examples.py           # Optional: code examples
├── reference.md          # Optional: detailed reference
└── data/                 # Optional: supporting files
```

### SKILL.md Format

```markdown
---
name: My Custom Skill
description: Brief, searchable description (used for vector matching)
allowed-tools: Read, Write, Execute  # Optional: tool restrictions
---

# My Custom Skill

## When to Use This Skill

Describe when an AI assistant should use this skill and what problems it solves.

## Quick Start

```python
# Minimal working example
import my_library
result = my_library.do_something()
```

## Detailed Usage

[More comprehensive documentation...]

## Common Patterns

- Pattern 1
- Pattern 2

## Troubleshooting

Common issues and solutions.
```

### Best Practices for Skill Descriptions

The `description` field is crucial for search quality:

✅ **Good descriptions** (will be found by vector search):
- "Analyze RNA sequencing data and identify differentially expressed genes"
- "Screen chemical compounds for drug-like properties and bioactivity"
- "Predict protein structures using AlphaFold and analyze conformations"

❌ **Poor descriptions** (won't match well):
- "RNA analysis" (too vague)
- "Use this for compounds" (not specific)
- "AlphaFold" (just a name, no context)

**Tips:**
- Include action verbs (analyze, predict, screen, visualize)
- Mention the scientific domain
- Describe the use case, not just the tool
- Think about how users will ask for help

### Local Development Workflow

1. Create your skill directory:
```bash
mkdir -p ~/my-skills/custom-analysis
cd ~/my-skills/custom-analysis
```

2. Create SKILL.md with proper frontmatter

3. Test loading:
```bash
cat > test-config.json << 'EOF'
{
  "skill_sources": [{"type": "local", "path": "~/my-skills"}]
}
EOF

uv run claude-skills-mcp --config test-config.json --verbose
```

4. Test search relevance:
```bash
# Use the test client or integration tests
pytest tests/test_integration.py::test_local_demo -v -s
```

## Performance Tuning

### Optimizing Search Results

**Increase results for better coverage:**
```json
{
  "default_top_k": 10
}
```

**Use a more powerful embedding model:**
```json
{
  "embedding_model": "all-mpnet-base-v2"
}
```

Note: Larger models improve accuracy but increase memory usage and startup time.

### Reducing Memory Usage

**Use smaller embedding model:**
```json
{
  "embedding_model": "all-MiniLM-L6-v2"  // ~90MB, good quality
}
```

vs.

```json
{
  "embedding_model": "all-mpnet-base-v2"  // ~420MB, higher quality
}
```

### Faster Startup

- Load fewer skills (use subpath filtering)
- Use smaller embedding models
- Keep skills on local filesystem instead of GitHub

## Exploring Available Skills

### Using `list_skills` Tool

The `list_skills` tool provides a complete inventory of all loaded skills. This is useful for:
- Understanding what skills are available in your configuration
- Debugging why certain skills might not appear in searches
- Exploring the skill repository structure

**Example conversation:**
```
User: What skills do you have access to?

AI: I'll check what skills are loaded...
[Invokes list_skills tool]

The server currently has 78 skills loaded from K-Dense-AI/claude-scientific-skills:
1. biopython - Comprehensive biological sequence analysis and manipulation
2. rdkit - Chemical informatics and molecular manipulation
3. scanpy - Single-cell RNA sequencing analysis framework
...
```

**When to use `list_skills` vs `find_helpful_skills`:**
- Use `list_skills` to browse all available skills (exploration)
- Use `find_helpful_skills` to find relevant skills for a specific task (task-oriented)

**Note:** `list_skills` returns ALL skills, which can be a large amount of text. For finding skills relevant to your task, prefer `find_helpful_skills` which uses semantic search to return only the most relevant matches.

## Troubleshooting

### Skills Not Matching Expected Results

**Problem**: Search returns irrelevant skills

**Solutions**:
- Improve skill descriptions to be more specific
- Use domain-specific keywords in your query
- Increase `top_k` to see more options
- Check if expected skills are actually loaded (use `--verbose`)

### GitHub Rate Limit

**Problem**: "API rate limit exceeded"

**Solutions**:
- Wait an hour (60 requests/hour for unauthenticated)
- Use local directories instead of GitHub for development
- The server automatically caches GitHub API responses (see below)

**Automatic Caching:**

The server uses two-level caching to minimize GitHub API usage and speed up startup:

**Level 1: API Response Cache** (24-hour validity)
- Caches repository tree structure
- Location: `/tmp/claude_skills_mcp_cache/{md5}.json`
- Avoids repeated GitHub API calls (60/hour limit)
- Refreshes automatically after 24 hours

**Level 2: Document Content Cache** (permanent)
- Caches individual skill documents on first access
- Location: `/tmp/claude_skills_mcp_cache/documents/{md5}.cache`
- Fetched lazily when `read_skill_document` is called
- Persists across server restarts

**Lazy Document Loading**:
- At startup: Only SKILL.md files are fetched (~90 requests)
- On demand: Additional documents fetched when accessed via `read_skill_document`
- Once cached: Documents served from disk (no network calls)

**Performance Benefits**:
- Startup time: 60s → 15s (4x improvement)
- No more Cursor/client timeouts during initialization
- Document access: First time ~200ms, subsequent <1ms
- Dramatically faster development workflow

**Note**: Only the tree API call counts against the rate limit, not the raw content downloads.

### Slow Startup

**Problem**: Server takes too long to start

**Causes**:
- First run downloads embedding model (~100MB)
- Loading many skills from GitHub
- Large embedding model

**Solutions**:
- Model is cached after first download
- Use subpath filtering to load fewer skills
- Use local directories for faster access

