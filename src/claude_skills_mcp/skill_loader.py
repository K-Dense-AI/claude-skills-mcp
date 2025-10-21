"""Skill loading and parsing functionality."""

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
    """

    def __init__(self, name: str, description: str, content: str, source: str):
        self.name = name
        self.description = description
        self.content = content
        self.source = source

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


def load_from_local(path: str) -> list[Skill]:
    """Load skills from a local directory.

    Parameters
    ----------
    path : str
        Path to local directory containing skills.

    Returns
    -------
    list[Skill]
        List of loaded skills.
    """
    skills: list[Skill] = []

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
                    skills.append(skill)
                    logger.info(f"Loaded skill: {skill.name} from {skill_file}")
            except Exception as e:
                logger.error(f"Error reading {skill_file}: {e}")
                continue

        logger.info(f"Loaded {len(skills)} skills from local path {path}")

    except Exception as e:
        logger.error(f"Error accessing local path {path}: {e}")

    return skills


def load_from_github(url: str, subpath: str = "") -> list[Skill]:
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

    Returns
    -------
    list[Skill]
        List of loaded skills.
    """
    skills: list[Skill] = []

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
            logger.info(f"Loading skills from GitHub: {owner}/{repo} (branch: {branch}, subpath: {subpath})")
        else:
            logger.info(f"Loading skills from GitHub: {owner}/{repo} (branch: {branch})")

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


def load_all_skills(skill_sources: list[dict[str, Any]]) -> list[Skill]:
    """Load skills from all configured sources.

    Parameters
    ----------
    skill_sources : list[dict[str, Any]]
        List of skill source configurations.

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
                skills = load_from_github(url, subpath)
                all_skills.extend(skills)

        elif source_type == "local":
            path = source_config.get("path")
            if path:
                skills = load_from_local(path)
                all_skills.extend(skills)

        else:
            logger.warning(f"Unknown source type: {source_type}")

    logger.info(f"Total skills loaded: {len(all_skills)}")
    return all_skills
