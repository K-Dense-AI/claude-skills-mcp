# API Documentation

Complete reference for all MCP tools provided by the Claude Skills server.

## Overview

The server exposes three MCP tools for working with Claude Agent Skills, following [MCP specification best practices](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) with optimized descriptions designed to improve AI model integration and invocation accuracy.

---

## Tool 1: `search_skills`

**Purpose**: Search and discover relevant Claude Agent Skills using semantic similarity.

### Description

Search and discover proven Claude Agent Skills that provide expert guidance for your tasks. Use this tool whenever you're starting a new task, facing a coding challenge, or need specialized techniques. Returns highly relevant skills with complete implementation guides, code examples, and best practices ranked by relevance.

### When to Use

- Starting a new project or task
- Need specialized knowledge or techniques
- Looking for best practices in a domain
- Want to see example implementations
- Need reusable workflows or patterns

### Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_description` | string | Yes | - | Description of the task you want to accomplish. Be specific about your goal, context, or problem domain for better results (e.g., 'debug Python API errors', 'process genomic data', 'build React dashboard') |
| `top_k` | integer | No | 3 | Number of skills to return (1-20). Higher values provide more options but may include less relevant results |
| `list_documents` | boolean | No | true | Include a list of available documents (scripts, references, assets) for each skill |

### Output Format

Returns the most relevant skills with:
- **Skill name**: Unique identifier
- **Description**: Brief summary of what the skill does
- **Relevance score**: 0-1, higher is better
- **Source**: GitHub URL or local path
- **Full content**: Complete SKILL.md markdown (or truncated with source link if `max_skill_content_chars` is configured)
- **Document count**: Number of additional files available
- **Document list**: Paths and metadata for scripts, references, assets (if `list_documents=true`)

### Examples

**Example 1: Bioinformatics Task**
```
Input:
{
  "task_description": "analyze single-cell RNA sequencing data and identify cell types",
  "top_k": 3
}

Output:
Found 3 relevant skill(s)

Skill 1: scanpy
Relevance Score: 0.8234
Source: K-Dense-AI/claude-scientific-skills
Description: Single-cell RNA sequencing analysis framework...
Additional Documents: 2 file(s)
[Full SKILL.md content...]
```

**Example 2: Drug Discovery**
```
Input:
{
  "task_description": "screen chemical compounds for drug-like properties",
  "top_k": 5
}

Output:
Found 5 relevant skill(s)

Skill 1: rdkit
Relevance Score: 0.7856
[...]

Skill 2: deepchem
Relevance Score: 0.7234
[...]
```

**Example 3: General Data Analysis**
```
Input:
{
  "task_description": "exploratory data analysis with visualizations",
  "top_k": 3
}

Output:
Found 3 relevant skill(s)

Skill 1: exploratory-data-analysis
Relevance Score: 0.5846
[...]
```

### Best Practices

**Write specific task descriptions**:
- ✅ Good: "analyze RNA sequencing data and identify differentially expressed genes"
- ❌ Poor: "RNA analysis"

**Use domain terminology**:
- ✅ Good: "perform molecular docking for protein-ligand binding prediction"
- ❌ Poor: "analyze molecules"

**Include context**:
- ✅ Good: "build interactive web dashboard for visualizing clinical trial data"
- ❌ Poor: "make a dashboard"

**Adjust top_k based on needs**:
- `top_k=1-3`: When you want the most relevant skill only
- `top_k=5-10`: When exploring options or comparing approaches
- `top_k=15-20`: When doing comprehensive research

---

## Tool 2: `read_skill_document`

**Purpose**: Retrieve specific documents (scripts, references, assets) from a skill.

### Description

Access additional resources from skills including Python scripts, example data files, reference materials, and images. Supports pattern matching to retrieve multiple files at once. Use this after searching for skills to access implementation details, example code, or supporting documentation.

### When to Use

- Need to see the actual Python/R/shell script from a skill
- Want to examine example data or configurations
- Looking for reference documentation or detailed guides
- Need to access images, diagrams, or other assets
- Want to see all available files for a skill

### Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skill_name` | string | Yes | - | Name of the skill (as returned by search_skills) |
| `document_path` | string | No | null | Path or pattern to match documents. If not provided, lists all available documents |
| `include_base64` | boolean | No | false | For images: if true, return base64-encoded content; if false, return only URL |

### Document Path Patterns

| Pattern | Matches | Example |
|---------|---------|---------|
| `scripts/example.py` | Exact file | Single Python script |
| `scripts/*.py` | All matching | All Python scripts in scripts/ |
| `references/*` | All in directory | All reference documents |
| `*.json` | By extension | All JSON files |
| (omitted) | All documents | Complete file listing |

### Output Format

**Single document (text)**:
```
Document: scripts/analysis.py
================================================================================
[Full Python script content...]
```

**Single document (image)**:
```
Image: assets/workflow.png
Size: 245.3 KB
URL: https://raw.githubusercontent.com/.../workflow.png
(Set include_base64=true to get base64-encoded content)
```

**Multiple documents**:
```
Found 3 documents matching 'scripts/*.py':

================================================================================
Document: scripts/preprocess.py
Type: text
Size: 3.2 KB
Content:
--------------------------------------------------------------------------------
[Script content...]
================================================================================

Document: scripts/analyze.py
[...]
```

**List all documents** (no path specified):
```
Available documents for skill 'exploratory-data-analysis':
  - scripts/eda.py (text, 5.4 KB)
  - examples/dataset.csv (text, 2.1 KB)
  - references/guide.md (text, 8.7 KB)
  - assets/flowchart.png (image, 123.4 KB)
```

### Examples

**Example 1: Get specific script**
```
Input:
{
  "skill_name": "scanpy",
  "document_path": "scripts/clustering.py"
}

Output:
Document: scripts/clustering.py
================================================================================
import scanpy as sc
import numpy as np

# Load single-cell data
[...]
```

**Example 2: Get all Python scripts**
```
Input:
{
  "skill_name": "rdkit",
  "document_path": "scripts/*.py"
}

Output:
Found 4 documents matching 'scripts/*.py':
- scripts/molecule_utils.py
- scripts/descriptor_calc.py
- scripts/similarity.py
- scripts/visualization.py
[Full content for each...]
```

**Example 3: List all available files**
```
Input:
{
  "skill_name": "exploratory-data-analysis"
}

Output:
Available documents for skill 'exploratory-data-analysis':
  - scripts/eda.py (text, 5.4 KB)
  - examples/sample_data.csv (text, 2.1 KB)
  - references/statistics_guide.md (text, 8.7 KB)
```

**Example 4: Get image with base64**
```
Input:
{
  "skill_name": "scientific-visualization",
  "document_path": "examples/heatmap.png",
  "include_base64": true
}

Output:
Image: examples/heatmap.png
Base64 Content: iVBORw0KGgoAAAANSUhEUgAA...
Alternatively, access via URL: https://raw.githubusercontent.com/.../heatmap.png
```

### Best Practices

**List files first**:
1. Call without `document_path` to see what's available
2. Then request specific files you need

**Use patterns efficiently**:
- `scripts/*.py` - Get all Python scripts at once
- `examples/*` - Get all examples
- Avoid overly broad patterns that return too much data

**Images**:
- Use `include_base64=false` (default) for large images
- Only use `include_base64=true` when you need to process the image directly

**File size considerations**:
- Text files are returned in full
- Images >5MB return URL only (regardless of include_base64)
- Use patterns to retrieve multiple small files efficiently

---

## Tool 3: `list_skills`

**Purpose**: List all loaded skills with their metadata.

### Description

Returns a complete inventory of all loaded skills with their names, descriptions, sources, and document counts. Use this for exploration or debugging to see what skills are available. **NOTE**: For finding relevant skills for a specific task, use the `search_skills` tool instead - it performs semantic search to find the most appropriate skills.

### When to Use

- **Exploration**: Browse what skills are available
- **Debugging**: Verify expected skills are loaded
- **Configuration validation**: Check skill sources are working
- **Inventory**: See total skills and their sources

### When NOT to Use

- **Task-oriented queries**: Use `search_skills` instead
- **Finding relevant skills**: Use `search_skills` for semantic matching
- **Production use cases**: This returns ALL skills (large output)

### Input Parameters

No input parameters required (empty object `{}`).

### Output Format

```
Total skills loaded: 78

================================================================================

1. biopython
   Description: Comprehensive biological sequence analysis and manipulation
   Source: K-Dense-AI/claude-scientific-skills
   Documents: 3 file(s)

2. rdkit
   Description: Chemical informatics and molecular manipulation
   Source: K-Dense-AI/claude-scientific-skills  
   Documents: 5 file(s)

3. scanpy
   Description: Single-cell RNA sequencing analysis framework
   Source: K-Dense-AI/claude-scientific-skills
   Documents: 2 file(s)

[... all remaining skills ...]
```

### Examples

**Example 1: Basic inventory**
```
Input:
{}

Output:
Total skills loaded: 78

1. biopython
   Description: Comprehensive biological sequence analysis...
   Source: K-Dense-AI/claude-scientific-skills
   Documents: 3 file(s)
[...]
```

**Example 2: Verify specific skill loaded**
```
After calling list_skills, search the output for "exploratory-data-analysis"
to verify it's in the loaded set.
```

### Best Practices

**Use for debugging**:
- Verify your configuration loaded the right repositories
- Check if a specific skill exists
- Understand the total scope of available skills

**Don't use for task queries**:
- ❌ Wrong: Call list_skills to find skills for "RNA analysis"
- ✅ Right: Call search_skills("RNA analysis") instead

**Output size warning**:
- With 70+ skills, output can be 50-100KB
- This consumes significant context window
- Only call when you actually need the full inventory

**Typical workflow**:
1. Call `list_skills` once to understand available skills
2. Use `search_skills` for all subsequent task-oriented queries

---

## Comparison: When to Use Which Tool

| Scenario | Use This Tool | Why |
|----------|---------------|-----|
| "I need help with X" | `search_skills` | Semantic search finds relevant skills |
| "Show me the Python script" | `read_skill_document` | Access specific files from skills |
| "What skills are available?" | `list_skills` | Complete inventory |
| "Find protein analysis tools" | `search_skills` | Semantic matching |
| "Get all scripts from scanpy" | `read_skill_document` | Pattern matching |
| "Verify config is working" | `list_skills` | See what loaded |
| "Compare 5 approaches" | `search_skills` with top_k=5 | Multiple results |
| "I want that example data" | `read_skill_document` | Get specific files |

## Progressive Disclosure Pattern

The tools are designed to work together following Anthropic's progressive disclosure architecture:

**Level 1: Discovery** (search_skills)
```
Task: "analyze RNA sequencing data"
    ↓
Returns: Top 3 relevant skills with descriptions
```

**Level 2: Exploration** (search_skills with high top_k)
```
Increase top_k to 10 to see more options
Compare approaches and choose best fit
```

**Level 3: Implementation** (read_skill_document)
```
Access Python scripts from chosen skill
Get example data and configurations
Read detailed reference documentation
```

**Level 4: Inventory** (list_skills, rarely needed)
```
Understand complete available skill set
Verify configuration
Debug loading issues
```

This pattern ensures:
- Minimal context window usage initially
- Relevant information surfaced quickly
- Detailed resources available on demand
- Complete flexibility for exploration

## Error Handling

### Common Error Responses

**No skills loaded**:
```
No relevant skills found for the given task description.
```
Solution: Check server configuration and skill sources.

**Skill not found**:
```
Skill 'xyz' not found. Please use search_skills to find valid skill names.
```
Solution: Use exact skill name from search_skills results.

**Document not found**:
```
No documents matching 'pattern' found in skill 'name'.
```
Solution: List all documents first (call without document_path).

**Image too large**:
```
Image: large_diagram.png
Size: 8.5 MB (exceeds limit)
URL: https://raw.githubusercontent.com/.../large_diagram.png
```
Solution: Access via URL rather than base64.

## Configuration Impact

### max_skill_content_chars

When set, truncates skill content in `search_skills` results:

```json
{
  "max_skill_content_chars": 5000
}
```

**Effect**:
```
[Skill content truncated at 5000 characters]
[View full skill at: https://github.com/...]
```

**Recommendation**: 
- Leave at `null` (unlimited) unless context window is a concern
- If set, use 5000-10000 for good balance

### default_top_k

Changes default number of results in `search_skills`:

```json
{
  "default_top_k": 5
}
```

**Recommendation**:
- 3 (default): Good for most cases
- 5-10: Better for exploration
- 1: When you only want the top match

### load_skill_documents

Controls whether `read_skill_document` works:

```json
{
  "load_skill_documents": false
}
```

**Effect**: `read_skill_document` will report no documents available.

**Recommendation**: Leave as `true` unless optimizing for startup time.

## Performance Characteristics

### search_skills
- **Query time**: <1 second
- **Startup cost**: 5-10 seconds (indexing)
- **Scales**: Linear with number of skills

### read_skill_document
- **Access time**: Instant (cached in memory)
- **Network**: No network calls (pre-loaded)
- **Memory**: ~1-10KB per document

### list_skills
- **Query time**: <100ms (just formatting)
- **Output size**: 50-100KB for 70+ skills
- **Context impact**: Significant with many skills

## Tips for AI Assistants

When integrating these tools into an AI assistant:

### Search Strategy

1. **Start with search_skills**: Almost always the right first step
2. **Be specific**: Better search results with detailed task descriptions
3. **Iterate**: Can call search_skills multiple times with refined queries
4. **Increase top_k**: When initial results aren't perfect

### Document Access

1. **List first**: Call read_skill_document without path to see options
2. **Batch requests**: Use patterns to get related files together
3. **Selective loading**: Only request documents you'll actually use

### Context Management

1. **Prefer search over list**: search_skills is more efficient
2. **Progressive disclosure**: Load details only when needed
3. **Truncate wisely**: Use max_skill_content_chars if context is tight

### Error Recovery

1. **Skill not found**: Re-search with different query
2. **No results**: Broaden search terms or increase top_k
3. **Document missing**: List documents to see what's available

## API Best Practices Summary

✅ **Do**:
- Use `search_skills` for task-oriented queries
- Provide specific, detailed task descriptions
- Use `read_skill_document` for accessing scripts and files
- List documents before requesting specific ones
- Call `list_skills` once for inventory, then use `search_skills`

❌ **Don't**:
- Use `list_skills` for every query (high context cost)
- Use vague task descriptions in `search_skills`
- Request base64 images unless necessary
- Request documents you won't use
- Rely on exact skill names - use search instead

## Further Reading

- [Getting Started](getting-started.md) - Installation and quick start
- [Architecture Guide](architecture.md) - System design and components
- [Usage Examples](usage.md) - Advanced configuration and patterns
- [MCP Specification](https://modelcontextprotocol.io/specification/)
- [Agent Skills Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

