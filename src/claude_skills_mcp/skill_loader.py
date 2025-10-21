"""Skill loading and parsing functionality."""

import base64
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class Skill:
    """Represents a Claude Agent Skill.

    Attributes
    ----------
    name : str
        Skill name.
    description : str
        Short description of the skill.
    content : str
        Full content of the SKILL.md file.
    source : str
        Origin of the skill (GitHub URL or local path).
    documents : dict[str, dict[str, Any]]
        Additional documents from the skill directory.
        Keys are relative paths, values contain metadata and content.
    """

    def __init__(
        self,
        name: str,
        description: str,
        content: str,
        source: str,
        documents: dict[str, dict[str, Any]] | None = None,
    ):
        self.name = name
        self.description = description
        self.content = content
        self.source = source
        self.documents = documents or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert skill to dictionary representation.

        Returns
        -------
        dict[str, Any]
            Dictionary with skill information.
        """
        return {
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "source": self.source,
            "documents": self.documents,
        }


def parse_skill_md(content: str, source: str) -> Skill | None:
    """Parse a SKILL.md file and extract skill information.

    Parameters
    ----------
    content : str
        Content of the SKILL.md file.
    source : str
        Origin of the skill (for tracking).

    Returns
    -------
    Skill | None
        Parsed skill or None if parsing failed.
    """
    try:
        # Parse YAML frontmatter (between --- markers)
        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
        )

        if not frontmatter_match:
            logger.warning(f"No YAML frontmatter found in skill from {source}")
            return None

        frontmatter_text = frontmatter_match.group(1)
        markdown_body = frontmatter_match.group(2)

        # Extract name and description from YAML frontmatter
        name_match = re.search(r"^name:\s*(.+)$", frontmatter_text, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", frontmatter_text, re.MULTILINE)

        if not name_match or not desc_match:
            logger.warning(f"Missing name or description in skill from {source}")
            return None

        name = name_match.group(1).strip()
        description = desc_match.group(1).strip()

        # Remove quotes if present
        name = name.strip("\"'")
        description = description.strip("\"'")

        return Skill(
            name=name,
            description=description,
            content=markdown_body.strip(),  # Store only the markdown body, not the frontmatter
            source=source,
        )

    except Exception as e:
        logger.error(f"Error parsing SKILL.md from {source}: {e}")
        return None


def _is_text_file(file_path: Path, text_extensions: list[str]) -> bool:
    """Check if a file is a text file based on extension.

    Parameters
    ----------
    file_path : Path
        Path to the file.
    text_extensions : list[str]
        List of allowed text file extensions.

    Returns
    -------
    bool
        True if file is a text file.
    """
    return file_path.suffix.lower() in text_extensions


def _is_image_file(file_path: Path, image_extensions: list[str]) -> bool:
    """Check if a file is an image based on extension.

    Parameters
    ----------
    file_path : Path
        Path to the file.
    image_extensions : list[str]
        List of allowed image file extensions.

    Returns
    -------
    bool
        True if file is an image.
    """
    return file_path.suffix.lower() in image_extensions


def _load_text_file(file_path: Path) -> dict[str, Any] | None:
    """Load a text file and return its metadata.

    Parameters
    ----------
    file_path : Path
        Path to the text file.

    Returns
    -------
    dict[str, Any] | None
        Document metadata with content, or None on error.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        return {
            "type": "text",
            "content": content,
            "size": len(content),
        }
    except Exception as e:
        logger.error(f"Error reading text file {file_path}: {e}")
        return None


def _load_image_file(
    file_path: Path, max_size: int, url: str | None = None
) -> dict[str, Any] | None:
    """Load an image file and return its metadata with base64 encoding.

    Parameters
    ----------
    file_path : Path
        Path to the image file.
    max_size : int
        Maximum file size in bytes.
    url : str | None
        Optional URL to the image (for GitHub sources).

    Returns
    -------
    dict[str, Any] | None
        Document metadata with base64 content and/or URL, or None on error.
    """
    try:
        file_size = file_path.stat().st_size
        
        if file_size > max_size:
            logger.warning(
                f"Image {file_path} exceeds size limit ({file_size} > {max_size}), "
                "storing metadata only"
            )
            result = {
                "type": "image",
                "size": file_size,
                "size_exceeded": True,
            }
            if url:
                result["url"] = url
            return result
        
        # Read and base64 encode the image
        image_data = file_path.read_bytes()
        base64_content = base64.b64encode(image_data).decode("utf-8")
        
        result = {
            "type": "image",
            "content": base64_content,
            "size": file_size,
        }
        if url:
            result["url"] = url
        
        return result
    
    except Exception as e:
        logger.error(f"Error reading image file {file_path}: {e}")
        return None


def _load_documents_from_directory(
    skill_dir: Path,
    text_extensions: list[str],
    image_extensions: list[str],
    max_image_size: int,
) -> dict[str, dict[str, Any]]:
    """Load all documents from a skill directory.

    Parameters
    ----------
    skill_dir : Path
        Path to the skill directory.
    text_extensions : list[str]
        List of allowed text file extensions.
    image_extensions : list[str]
        List of allowed image file extensions.
    max_image_size : int
        Maximum image file size in bytes.

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary mapping relative paths to document metadata.
    """
    documents = {}
    
    for file_path in skill_dir.rglob("*"):
        # Skip SKILL.md itself and directories
        if file_path.name == "SKILL.md" or file_path.is_dir():
            continue
        
        # Calculate relative path from skill directory
        try:
            rel_path = str(file_path.relative_to(skill_dir))
        except ValueError:
            continue
        
        # Process text files
        if _is_text_file(file_path, text_extensions):
            doc_data = _load_text_file(file_path)
            if doc_data:
                documents[rel_path] = doc_data
        
        # Process image files
        elif _is_image_file(file_path, image_extensions):
            doc_data = _load_image_file(file_path, max_image_size)
            if doc_data:
                documents[rel_path] = doc_data
    
    return documents


def _load_documents_from_github(
    owner: str,
    repo: str,
    branch: str,
    skill_dir_path: str,
    tree_data: dict[str, Any],
    text_extensions: list[str],
    image_extensions: list[str],
    max_image_size: int,
) -> dict[str, dict[str, Any]]:
    """Load all documents from a GitHub skill directory.

    Parameters
    ----------
    owner : str
        GitHub repository owner.
    repo : str
        GitHub repository name.
    branch : str
        Branch name.
    skill_dir_path : str
        Path to the skill directory within the repo.
    tree_data : dict[str, Any]
        GitHub API tree data for the repository.
    text_extensions : list[str]
        List of allowed text file extensions.
    image_extensions : list[str]
        List of allowed image file extensions.
    max_image_size : int
        Maximum image file size in bytes.

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary mapping relative paths to document metadata.
    """
    documents = {}
    
    # Find all files in the skill directory (but not SKILL.md itself)
    for item in tree_data.get("tree", []):
        if item["type"] != "blob":
            continue
        
        item_path = item["path"]
        
        # Skip if not in the skill directory
        if not item_path.startswith(skill_dir_path):
            continue
        
        # Skip SKILL.md itself
        if item_path.endswith("/SKILL.md") or item_path == f"{skill_dir_path}/SKILL.md":
            continue
        
        # Calculate relative path from skill directory
        if skill_dir_path:
            rel_path = item_path[len(skill_dir_path):].lstrip("/")
        else:
            rel_path = item_path
        
        if not rel_path:
            continue
        
        # Check file extension
        file_ext = Path(item_path).suffix.lower()
        
        # Process text files
        if file_ext in text_extensions:
            try:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{item_path}"
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(raw_url)
                    response.raise_for_status()
                    content = response.text
                
                documents[rel_path] = {
                    "type": "text",
                    "content": content,
                    "size": len(content),
                }
                logger.debug(f"Loaded text document: {rel_path}")
            
            except Exception as e:
                logger.error(f"Error loading text file {item_path} from GitHub: {e}")
        
        # Process image files
        elif file_ext in image_extensions:
            try:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{item_path}"
                
                # First, get the file size from the tree data
                file_size = item.get("size", 0)
                
                if file_size > max_image_size:
                    logger.warning(
                        f"Image {item_path} exceeds size limit ({file_size} > {max_image_size}), "
                        "storing URL only"
                    )
                    documents[rel_path] = {
                        "type": "image",
                        "size": file_size,
                        "size_exceeded": True,
                        "url": raw_url,
                    }
                else:
                    # Fetch and base64 encode the image
                    with httpx.Client(timeout=30.0) as client:
                        response = client.get(raw_url)
                        response.raise_for_status()
                        image_data = response.content
                    
                    base64_content = base64.b64encode(image_data).decode("utf-8")
                    
                    documents[rel_path] = {
                        "type": "image",
                        "content": base64_content,
                        "size": len(image_data),
                        "url": raw_url,
                    }
                    logger.debug(f"Loaded image document: {rel_path}")
            
            except Exception as e:
                logger.error(f"Error loading image file {item_path} from GitHub: {e}")
    
    return documents


def load_from_local(path: str, config: dict[str, Any] | None = None) -> list[Skill]:
    """Load skills from a local directory.

    Parameters
    ----------
    path : str
        Path to local directory containing skills.
    config : dict[str, Any] | None
        Configuration dictionary with document loading settings.

    Returns
    -------
    list[Skill]
        List of loaded skills.
    """
    skills: list[Skill] = []
    
    # Get configuration settings
    if config is None:
        config = {}
    
    load_documents = config.get("load_skill_documents", True)
    text_extensions = config.get("text_file_extensions", [".md", ".py", ".txt", ".json", ".yaml", ".yml", ".sh", ".r", ".ipynb"])
    image_extensions = config.get("allowed_image_extensions", [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"])
    max_image_size = config.get("max_image_size_bytes", 5242880)

    try:
        local_path = Path(path).expanduser().resolve()

        if not local_path.exists():
            logger.warning(f"Local path {path} does not exist, skipping")
            return skills

        if not local_path.is_dir():
            logger.warning(f"Local path {path} is not a directory, skipping")
            return skills

        # Find all SKILL.md files recursively
        skill_files = list(local_path.rglob("SKILL.md"))

        for skill_file in skill_files:
            try:
                content = skill_file.read_text(encoding="utf-8")
                skill = parse_skill_md(content, str(skill_file))
                if skill:
                    # Load additional documents from the skill directory
                    if load_documents:
                        skill_dir = skill_file.parent
                        documents = _load_documents_from_directory(
                            skill_dir, text_extensions, image_extensions, max_image_size
                        )
                        skill.documents = documents
                        if documents:
                            logger.info(
                                f"Loaded {len(documents)} additional documents for skill: {skill.name}"
                            )
                    
                    skills.append(skill)
                    logger.info(f"Loaded skill: {skill.name} from {skill_file}")
            except Exception as e:
                logger.error(f"Error reading {skill_file}: {e}")
                continue

        logger.info(f"Loaded {len(skills)} skills from local path {path}")

    except Exception as e:
        logger.error(f"Error accessing local path {path}: {e}")

    return skills


def load_from_github(url: str, subpath: str = "", config: dict[str, Any] | None = None) -> list[Skill]:
    """Load skills from a GitHub repository.

    Parameters
    ----------
    url : str
        GitHub repository URL. Can be:
        - Base repo URL: https://github.com/owner/repo
        - URL with branch and subpath: https://github.com/owner/repo/tree/branch/subpath
    subpath : str, optional
        Subdirectory within the repo to search, by default "".
        If the URL already contains a subpath, this parameter is ignored.
    config : dict[str, Any] | None
        Configuration dictionary with document loading settings.

    Returns
    -------
    list[Skill]
        List of loaded skills.
    """
    skills: list[Skill] = []
    
    # Get configuration settings
    if config is None:
        config = {}
    
    load_documents = config.get("load_skill_documents", True)
    text_extensions = config.get("text_file_extensions", [".md", ".py", ".txt", ".json", ".yaml", ".yml", ".sh", ".r", ".ipynb"])
    image_extensions = config.get("allowed_image_extensions", [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"])
    max_image_size = config.get("max_image_size_bytes", 5242880)

    try:
        # Parse GitHub URL to extract owner, repo, branch, and subpath
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        if len(path_parts) < 2:
            logger.error(f"Invalid GitHub URL: {url}")
            return skills

        owner = path_parts[0]
        repo = path_parts[1]
        branch = "main"  # Default branch

        # Check if URL contains /tree/{branch}/{subpath} format
        # e.g., https://github.com/owner/repo/tree/main/subdirectory
        if len(path_parts) > 3 and path_parts[2] == "tree":
            branch = path_parts[3]
            # Extract subpath from URL if provided (overrides subpath parameter)
            if len(path_parts) > 4:
                url_subpath = "/".join(path_parts[4:])
                if not subpath:  # Only use URL subpath if not explicitly provided
                    subpath = url_subpath
                    logger.info(f"Extracted subpath from URL: {subpath}")

        if subpath:
            logger.info(
                f"Loading skills from GitHub: {owner}/{repo} (branch: {branch}, subpath: {subpath})"
            )
        else:
            logger.info(
                f"Loading skills from GitHub: {owner}/{repo} (branch: {branch})"
            )

        # Get repository tree
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

        with httpx.Client(timeout=30.0) as client:
            response = client.get(api_url)
            response.raise_for_status()
            tree_data = response.json()

        # Find all SKILL.md files
        skill_paths = []
        for item in tree_data.get("tree", []):
            if item["type"] == "blob" and item["path"].endswith("SKILL.md"):
                # Apply subpath filter if provided
                if subpath:
                    if item["path"].startswith(subpath):
                        skill_paths.append(item["path"])
                else:
                    skill_paths.append(item["path"])

        # Load each SKILL.md file
        for skill_path in skill_paths:
            try:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{skill_path}"

                with httpx.Client(timeout=30.0) as client:
                    response = client.get(raw_url)
                    response.raise_for_status()
                    content = response.text

                source = f"{url}/tree/{branch}/{skill_path}"
                skill = parse_skill_md(content, source)

                if skill:
                    # Load additional documents from the skill directory
                    if load_documents:
                        # Get the skill directory path (parent of SKILL.md)
                        skill_dir_path = str(Path(skill_path).parent)
                        if skill_dir_path == ".":
                            skill_dir_path = ""
                        
                        documents = _load_documents_from_github(
                            owner, repo, branch, skill_dir_path, tree_data,
                            text_extensions, image_extensions, max_image_size
                        )
                        skill.documents = documents
                        if documents:
                            logger.info(
                                f"Loaded {len(documents)} additional documents for skill: {skill.name}"
                            )
                    
                    skills.append(skill)
                    logger.info(f"Loaded skill: {skill.name} from {source}")

            except Exception as e:
                logger.error(f"Error loading {skill_path} from GitHub: {e}")
                continue

        logger.info(f"Loaded {len(skills)} skills from GitHub repo {url}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Try 'master' branch instead
            try:
                logger.info(
                    f"Branch 'main' not found, trying 'master' for {owner}/{repo}"
                )
                branch = "master"
                api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

                with httpx.Client(timeout=30.0) as client:
                    response = client.get(api_url)
                    response.raise_for_status()
                    tree_data = response.json()

                # Repeat the loading process with master branch
                skill_paths = []
                for item in tree_data.get("tree", []):
                    if item["type"] == "blob" and item["path"].endswith("SKILL.md"):
                        if subpath:
                            if item["path"].startswith(subpath):
                                skill_paths.append(item["path"])
                        else:
                            skill_paths.append(item["path"])

                for skill_path in skill_paths:
                    try:
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{skill_path}"

                        with httpx.Client(timeout=30.0) as client:
                            response = client.get(raw_url)
                            response.raise_for_status()
                            content = response.text

                        source = f"{url}/tree/{branch}/{skill_path}"
                        skill = parse_skill_md(content, source)

                        if skill:
                            # Load additional documents from the skill directory
                            if load_documents:
                                # Get the skill directory path (parent of SKILL.md)
                                skill_dir_path = str(Path(skill_path).parent)
                                if skill_dir_path == ".":
                                    skill_dir_path = ""
                                
                                documents = _load_documents_from_github(
                                    owner, repo, branch, skill_dir_path, tree_data,
                                    text_extensions, image_extensions, max_image_size
                                )
                                skill.documents = documents
                                if documents:
                                    logger.info(
                                        f"Loaded {len(documents)} additional documents for skill: {skill.name}"
                                    )
                            
                            skills.append(skill)
                            logger.info(f"Loaded skill: {skill.name} from {source}")

                    except Exception as e:
                        logger.error(f"Error loading {skill_path} from GitHub: {e}")
                        continue

                logger.info(f"Loaded {len(skills)} skills from GitHub repo {url}")

            except Exception as e2:
                logger.error(
                    f"Error loading from GitHub repo {url} (tried both main and master): {e2}"
                )
        else:
            logger.error(f"HTTP error loading from GitHub {url}: {e}")

    except Exception as e:
        logger.error(f"Error loading from GitHub {url}: {e}")

    return skills


def load_all_skills(skill_sources: list[dict[str, Any]], config: dict[str, Any] | None = None) -> list[Skill]:
    """Load skills from all configured sources.

    Parameters
    ----------
    skill_sources : list[dict[str, Any]]
        List of skill source configurations.
    config : dict[str, Any] | None
        Configuration dictionary with document loading settings.

    Returns
    -------
    list[Skill]
        All loaded skills from all sources.
    """
    all_skills: list[Skill] = []

    for source_config in skill_sources:
        source_type = source_config.get("type")

        if source_type == "github":
            url = source_config.get("url")
            subpath = source_config.get("subpath", "")
            if url:
                skills = load_from_github(url, subpath, config)
                all_skills.extend(skills)

        elif source_type == "local":
            path = source_config.get("path")
            if path:
                skills = load_from_local(path, config)
                all_skills.extend(skills)

        else:
            logger.warning(f"Unknown source type: {source_type}")

    logger.info(f"Total skills loaded: {len(all_skills)}")
    return all_skills
