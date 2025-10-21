# Skill Subfolder Loading Implementation Summary

## Overview
Enhanced the Claude Skills MCP server to load and expose all content from skill directories (scripts, references, assets) in addition to the main SKILL.md file. Added a new MCP tool `read_skill_document` for retrieving specific skill documents.

**Fully supports the official [Anthropic Skills repository](https://github.com/anthropics/skills)** with diverse file types including Python scripts (.py), XML files (.xml), images (.png, .jpg, .svg), and other rich media content.

## Changes Implemented

### 1. Configuration Updates (`config.py`)
Added new configuration options:
- `load_skill_documents` (bool, default: True): Enable/disable document loading
- `max_image_size_bytes` (int, default: 5MB): Maximum size for base64-encoding images
- `allowed_image_extensions` (list): Supported image file types
- `text_file_extensions` (list): Supported text file types

### 2. Skill Class Enhancement (`skill_loader.py`)
- Added `documents` attribute to `Skill` class: `dict[str, dict[str, Any]]`
- Document structure stores file metadata and content:
  - Text files: `{"type": "text", "content": "...", "size": 123}`
  - Images: `{"type": "image", "content": "base64...", "url": "https://...", "size": 456}`
  - Oversized images: `{"type": "image", "size_exceeded": True, "url": "https://...", "size": 789}`

### 3. Document Loading Functions (`skill_loader.py`)
Added helper functions:
- `_is_text_file()`: Check if file is a text file by extension
- `_is_image_file()`: Check if file is an image by extension
- `_load_text_file()`: Load and return text file content
- `_load_image_file()`: Load and base64-encode images (with size limits)
- `_load_documents_from_directory()`: Recursively scan local directory for documents
- `_load_documents_from_github()`: Load documents from GitHub using API tree data

### 4. Enhanced Skill Loaders (`skill_loader.py`)
Updated both `load_from_local()` and `load_from_github()` to:
- Accept `config` parameter with document loading settings
- Recursively scan skill directories for additional files
- Load and process text files and images
- Store documents with proper relative paths from skill root
- Handle GitHub API efficiently to avoid rate limits

### 5. New MCP Tool: `read_skill_document` (`server.py`)
New tool for retrieving skill documents with:
- **Parameters:**
  - `skill_name` (required): Name of the skill
  - `document_path` (optional): Path or glob pattern (e.g., "scripts/*.py")
  - `include_base64` (optional, default: False): Return base64 or URL for images
- **Features:**
  - Pattern matching using fnmatch (supports wildcards)
  - Lists all documents if no path specified
  - Returns URLs for images by default (efficiency)
  - Optional base64 encoding for images
  - Handles single file and multiple file matches

### 6. Enhanced `search_skills` Tool (`server.py`)
Updated to include document information:
- New parameter: `list_documents` (bool, default: False)
- Shows document count for each skill
- Optionally lists all available documents with type and size
- Helps users discover what additional resources are available

### 7. Implementation Details
- **Local Loading:** Uses `Path.rglob()` to recursively scan directories
- **GitHub Loading:** Uses GitHub API tree data to enumerate all files
- **Base64 Encoding:** Applied to images under size limit with URL fallback
- **Pattern Matching:** Uses `fnmatch` for glob-style patterns
- **Error Handling:** Graceful handling of missing files, network errors, size limits

## File Changes
- `src/claude_skills_mcp/config.py`: Added configuration options
- `src/claude_skills_mcp/skill_loader.py`: Enhanced skill loading with documents
- `src/claude_skills_mcp/server.py`: Added new MCP tool and updated search output
- `src/claude_skills_mcp/__main__.py`: Pass config to skill loaders
- `config.example.json`: Updated with new configuration options
- `tests/test_document_loading.py`: Comprehensive test suite (21 new tests)

## Test Coverage
- Added 21 new unit tests covering:
  - File type detection
  - Text file loading
  - Image file loading with size limits
  - Directory scanning
  - Skill class with documents
  - Local loading with documents
- All 57 tests pass
- Coverage increased from 42% to 48%

## Usage Examples

### Search with Document Listing
```json
{
  "task_description": "exploratory data analysis",
  "list_documents": true
}
```

### List All Documents for a Skill
```json
{
  "skill_name": "Exploratory Data Analysis"
}
```

### Get Specific Document
```json
{
  "skill_name": "Exploratory Data Analysis",
  "document_path": "scripts/analysis.py"
}
```

### Get All Python Scripts
```json
{
  "skill_name": "Exploratory Data Analysis",
  "document_path": "scripts/*.py"
}
```

### Get Image with Base64
```json
{
  "skill_name": "Exploratory Data Analysis",
  "document_path": "assets/workflow.png",
  "include_base64": true
}
```

## Technical Considerations
- **Memory Usage:** Base64-encoded images increase memory consumption
- **Performance:** GitHub loading makes additional API calls per skill
- **Rate Limits:** GitHub API has 60 req/hour limit (unauthenticated)
- **Size Limits:** Configurable to prevent excessive memory usage
- **Backwards Compatibility:** All existing functionality preserved; document loading can be disabled

## Supported File Types

### Text Files (Loaded with Full Content)
- Python scripts (.py)
- Markdown files (.md)
- JSON files (.json)
- YAML files (.yaml, .yml)
- XML files (.xml) - **newly added**
- Shell scripts (.sh)
- R scripts (.r)
- Jupyter notebooks (.ipynb)
- Plain text (.txt)

### Images (Base64 Encoded or URL)
- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- SVG (.svg)
- WebP (.webp)

Size limit: 5MB (configurable). Images exceeding the limit store URL only.

### Not Currently Supported
- PDF files (.pdf) - Binary format requiring special parsing (future enhancement)
- Video files - Deferred to future enhancement
- Other binary formats

## Anthropic Skills Repository Compatibility
The implementation is fully compatible with the [official Anthropic Skills repository](https://github.com/anthropics/skills), which contains:
- Python scripts for automation and skill logic
- XML configuration files
- Images for documentation and visual examples
- JSON and YAML for data and configuration
- Diverse skill examples showcasing various file types

## Future Enhancements
- Add caching for GitHub API responses
- Support for GitHub authentication to increase rate limits
- PDF parsing support for document skills
- Support for additional file types (videos, data files)
- Compression for large text files
- Streaming support for large documents

