"""Tests for document loading functionality."""

import base64
from pathlib import Path


from claude_skills_mcp.skill_loader import (
    Skill,
    _is_text_file,
    _is_image_file,
    _load_text_file,
    _load_image_file,
    _load_documents_from_directory,
    load_from_local,
)


class TestFileTypeDetection:
    """Test file type detection functions."""

    def test_is_text_file_python(self):
        """Test detection of Python files."""
        text_extensions = [".py", ".txt", ".md"]
        assert _is_text_file(Path("script.py"), text_extensions)

    def test_is_text_file_markdown(self):
        """Test detection of Markdown files."""
        text_extensions = [".py", ".txt", ".md"]
        assert _is_text_file(Path("README.md"), text_extensions)

    def test_is_text_file_not_text(self):
        """Test rejection of non-text files."""
        text_extensions = [".py", ".txt", ".md"]
        assert not _is_text_file(Path("image.png"), text_extensions)

    def test_is_image_file_png(self):
        """Test detection of PNG files."""
        image_extensions = [".png", ".jpg", ".jpeg"]
        assert _is_image_file(Path("diagram.png"), image_extensions)

    def test_is_image_file_case_insensitive(self):
        """Test case-insensitive image detection."""
        image_extensions = [".png", ".jpg", ".jpeg"]
        assert _is_image_file(Path("DIAGRAM.PNG"), image_extensions)

    def test_is_image_file_not_image(self):
        """Test rejection of non-image files."""
        image_extensions = [".png", ".jpg", ".jpeg"]
        assert not _is_image_file(Path("script.py"), image_extensions)


class TestTextFileLoading:
    """Test text file loading."""

    def test_load_text_file_valid(self, tmp_path):
        """Test loading a valid text file."""
        test_file = tmp_path / "test.py"
        test_content = "print('Hello, world!')\n"
        test_file.write_text(test_content)

        result = _load_text_file(test_file)

        assert result is not None
        assert result["type"] == "text"
        assert result["content"] == test_content
        assert result["size"] == len(test_content)

    def test_load_text_file_empty(self, tmp_path):
        """Test loading an empty text file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        result = _load_text_file(test_file)

        assert result is not None
        assert result["type"] == "text"
        assert result["content"] == ""
        assert result["size"] == 0

    def test_load_text_file_nonexistent(self, tmp_path):
        """Test loading a nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"

        result = _load_text_file(test_file)

        assert result is None


class TestImageFileLoading:
    """Test image file loading."""

    def test_load_image_file_small(self, tmp_path):
        """Test loading a small image file."""
        test_file = tmp_path / "small.png"
        # Create a small PNG-like file
        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        test_file.write_bytes(image_data)

        result = _load_image_file(test_file, max_size=1024)

        assert result is not None
        assert result["type"] == "image"
        assert "content" in result
        assert result["content"] == base64.b64encode(image_data).decode("utf-8")
        assert result["size"] == len(image_data)

    def test_load_image_file_with_url(self, tmp_path):
        """Test loading an image file with URL."""
        test_file = tmp_path / "image.png"
        image_data = b"\x89PNG\r\n\x1a\n"
        test_file.write_bytes(image_data)

        url = "https://example.com/image.png"
        result = _load_image_file(test_file, max_size=1024, url=url)

        assert result is not None
        assert result["type"] == "image"
        assert result["url"] == url
        assert "content" in result

    def test_load_image_file_size_exceeded(self, tmp_path):
        """Test loading an image that exceeds size limit."""
        test_file = tmp_path / "large.png"
        # Create a file larger than the limit
        image_data = b"x" * 2048
        test_file.write_bytes(image_data)

        result = _load_image_file(test_file, max_size=1024)

        assert result is not None
        assert result["type"] == "image"
        assert result["size_exceeded"] is True
        assert "content" not in result
        assert result["size"] == len(image_data)

    def test_load_image_file_size_exceeded_with_url(self, tmp_path):
        """Test loading a large image with URL."""
        test_file = tmp_path / "large.png"
        image_data = b"x" * 2048
        test_file.write_bytes(image_data)

        url = "https://example.com/large.png"
        result = _load_image_file(test_file, max_size=1024, url=url)

        assert result is not None
        assert result["size_exceeded"] is True
        assert result["url"] == url
        assert "content" not in result


class TestDocumentDirectoryLoading:
    """Test loading documents from a directory."""

    def test_load_documents_from_directory_mixed_files(self, tmp_path):
        """Test loading various file types from a directory."""
        # Create test files
        (tmp_path / "script.py").write_text("print('test')")
        (tmp_path / "data.json").write_text('{"key": "value"}')
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (tmp_path / "SKILL.md").write_text("# Skill")  # Should be skipped

        # Create subdirectory
        subdir = tmp_path / "scripts"
        subdir.mkdir()
        (subdir / "helper.py").write_text("def help(): pass")

        text_extensions = [".py", ".json"]
        image_extensions = [".png"]
        max_image_size = 1024

        documents = _load_documents_from_directory(
            tmp_path, text_extensions, image_extensions, max_image_size
        )

        # Should have 3 files (script.py, data.json, scripts/helper.py, image.png)
        # SKILL.md should be excluded
        assert len(documents) == 4
        assert "script.py" in documents
        assert "data.json" in documents
        assert "scripts/helper.py" in documents
        assert "image.png" in documents
        assert "SKILL.md" not in documents

        # Check content
        assert documents["script.py"]["type"] == "text"
        assert documents["script.py"]["content"] == "print('test')"
        assert documents["image.png"]["type"] == "image"

    def test_load_documents_from_directory_empty(self, tmp_path):
        """Test loading from an empty directory."""
        documents = _load_documents_from_directory(tmp_path, [".py"], [".png"], 1024)

        assert len(documents) == 0


class TestSkillClassWithDocuments:
    """Test Skill class with documents."""

    def test_skill_initialization_with_documents(self):
        """Test creating a skill with documents."""
        documents = {
            "script.py": {"type": "text", "content": "code", "size": 4},
            "image.png": {"type": "image", "content": "base64data", "size": 100},
        }

        skill = Skill(
            name="Test Skill",
            description="A test skill",
            content="# Test\n\nContent",
            source="test.md",
            documents=documents,
        )

        assert skill.name == "Test Skill"
        assert skill.documents == documents
        assert len(skill.documents) == 2

    def test_skill_initialization_without_documents(self):
        """Test creating a skill without documents."""
        skill = Skill(
            name="Test Skill",
            description="A test skill",
            content="# Test\n\nContent",
            source="test.md",
        )

        assert skill.documents == {}

    def test_skill_to_dict_with_documents(self):
        """Test converting skill with documents to dict."""
        documents = {"script.py": {"type": "text", "content": "code", "size": 4}}

        skill = Skill(
            name="Test Skill",
            description="A test skill",
            content="# Test",
            source="test.md",
            documents=documents,
        )

        skill_dict = skill.to_dict()

        assert "documents" in skill_dict
        assert skill_dict["documents"] == documents


class TestLoadFromLocalWithDocuments:
    """Test loading skills with documents from local directory."""

    def test_load_from_local_with_documents(self, tmp_path):
        """Test loading a skill with additional documents."""
        # Create skill directory
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        # Create SKILL.md
        skill_content = """---
name: Test Skill
description: A test skill with documents
---

# Test Skill

This is a test skill.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create additional documents
        (skill_dir / "script.py").write_text("print('hello')")
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "helper.py").write_text("def help(): pass")

        # Load skills with config
        config = {
            "load_skill_documents": True,
            "text_file_extensions": [".py"],
            "allowed_image_extensions": [".png"],
            "max_image_size_bytes": 1024,
        }

        skills = load_from_local(str(tmp_path), config)

        assert len(skills) == 1
        skill = skills[0]
        assert skill.name == "Test Skill"
        assert len(skill.documents) == 2
        assert "script.py" in skill.documents
        assert "scripts/helper.py" in skill.documents

    def test_load_from_local_without_document_loading(self, tmp_path):
        """Test loading a skill with document loading disabled."""
        # Create skill directory
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        # Create SKILL.md
        skill_content = """---
name: Test Skill
description: A test skill
---

# Test Skill

This is a test skill.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create additional documents (should be ignored)
        (skill_dir / "script.py").write_text("print('hello')")

        # Load skills with document loading disabled
        config = {
            "load_skill_documents": False,
        }

        skills = load_from_local(str(tmp_path), config)

        assert len(skills) == 1
        skill = skills[0]
        assert skill.name == "Test Skill"
        assert len(skill.documents) == 0

    def test_load_from_local_with_image_documents(self, tmp_path):
        """Test loading a skill with image documents."""
        # Create skill directory
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        # Create SKILL.md
        skill_content = """---
name: Test Skill
description: A test skill with images
---

# Test Skill

This skill has images.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create image file
        assets_dir = skill_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        # Load skills with config
        config = {
            "load_skill_documents": True,
            "text_file_extensions": [".py"],
            "allowed_image_extensions": [".png"],
            "max_image_size_bytes": 1024,
        }

        skills = load_from_local(str(tmp_path), config)

        assert len(skills) == 1
        skill = skills[0]
        assert "assets/diagram.png" in skill.documents
        assert skill.documents["assets/diagram.png"]["type"] == "image"
        assert "content" in skill.documents["assets/diagram.png"]
