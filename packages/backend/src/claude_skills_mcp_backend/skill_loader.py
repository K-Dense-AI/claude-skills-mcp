"""Skill loading and parsing functionality."""

import base64
import hashlib
import io
import json
import logging
import re
import shutil
import tarfile
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

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
    _document_fetcher : Callable | None
        Function to fetch document content on-demand.
    _document_cache : dict[str, dict[str, Any]]
        In-memory cache for fetched documents.
    """

    def __init__(
        self,
        name: str,
        description: str,
        content: str,
        source: str,
        documents: dict[str, dict[str, Any]] | None = None,
        document_fetcher: Callable | None = None,
    ):
        self.name = name
        self.description = description
        self.content = content
        self.source = source
        self.documents = documents or {}
        self._document_fetcher = document_fetcher
        self._document_cache = {}

    def get_document(self, doc_path: str) -> dict[str, Any] | None:
        """Fetch document content on-demand with caching.

        Parameters
        ----------
        doc_path : str
            Relative path to the document.

        Returns
        -------
        dict[str, Any] | None
            Document content with metadata, or None if not found.
        """
        # Check memory cache first
        if doc_path in self._document_cache:
            return self._document_cache[doc_path]

        # Check if document exists in metadata
        if doc_path not in self.documents:
            return None

        # If already fetched (eager loaded), return from documents
        doc_info = self.documents[doc_path]
        if doc_info.get("fetched") or "content" in doc_info:
            return doc_info

        # Fetch using the document_fetcher (lazy loading)
        if self._document_fetcher:
            content = self._document_fetcher(doc_path)
            if content:
                # Cache it in memory
                self._document_cache[doc_path] = content
                return content

        return None

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

        # Parse frontmatter as YAML - handles multiline scalars (>, |),
        # quoting, and other YAML syntax a line-based regex cannot
        name: str | None = None
        description: str | None = None
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if isinstance(frontmatter, dict):
                if frontmatter.get("name") is not None:
                    name = str(frontmatter["name"]).strip()
                if frontmatter.get("description") is not None:
                    description = str(frontmatter["description"]).strip()
        except yaml.YAMLError as e:
            logger.debug(
                f"YAML parse failed for {source}, falling back to regex: {e}"
            )

        # Regex fallback for frontmatter that is not valid YAML
        if not name:
            name_match = re.search(r"^name:\s*(.+)$", frontmatter_text, re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip().strip("\"'")
        if not description:
            desc_match = re.search(
                r"^description:\s*(.+)$", frontmatter_text, re.MULTILINE
            )
            if desc_match:
                description = desc_match.group(1).strip().strip("\"'")

        if not name or not description:
            logger.warning(f"Missing name or description in skill from {source}")
            return None

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
    text_extensions = config.get(
        "text_file_extensions",
        [".md", ".py", ".txt", ".json", ".yaml", ".yml", ".sh", ".r", ".ipynb"],
    )
    image_extensions = config.get(
        "allowed_image_extensions", [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]
    )
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


def parse_github_source_url(
    url: str, subpath: str = ""
) -> tuple[str, str, str | None, str] | None:
    """Parse a GitHub URL into its components.

    Parameters
    ----------
    url : str
        GitHub repository URL. Can be:
        - Base repo URL: https://github.com/owner/repo
        - URL with branch and subpath: https://github.com/owner/repo/tree/branch/subpath
    subpath : str, optional
        Explicit subpath. Takes precedence over a subpath embedded in the URL.

    Returns
    -------
    tuple[str, str, str | None, str] | None
        (owner, repo, branch, subpath) where branch is None when the URL does
        not pin one, or None if the URL is not a valid GitHub repo URL.
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")

    if len(path_parts) < 2 or not path_parts[0] or not path_parts[1]:
        return None

    owner = path_parts[0]
    repo = path_parts[1]
    branch: str | None = None

    # URL may contain /tree/{branch}/{subpath}
    # e.g., https://github.com/owner/repo/tree/main/subdirectory
    if len(path_parts) > 3 and path_parts[2] == "tree":
        branch = path_parts[3]
        if len(path_parts) > 4 and not subpath:
            subpath = "/".join(path_parts[4:])

    return owner, repo, branch, subpath


def _get_repo_cache_dir() -> Path:
    """Get repository snapshot cache directory.

    Returns
    -------
    Path
        Path to the snapshot cache directory.
    """
    cache_dir = Path(tempfile.gettempdir()) / "claude_skills_mcp_cache" / "repos"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _snapshot_dir_for(owner: str, repo: str, ref: str) -> Path:
    """Get the cache directory for a specific repo snapshot."""
    key = hashlib.md5(f"{owner}/{repo}@{ref}".encode()).hexdigest()
    return _get_repo_cache_dir() / key


def _load_cached_snapshot(
    owner: str, repo: str, ref: str, max_age_hours: int
) -> Path | None:
    """Return the extracted snapshot root if a valid cached copy exists."""
    snapshot_dir = _snapshot_dir_for(owner, repo, ref)
    meta_file = snapshot_dir / "meta.json"

    if not meta_file.exists():
        return None

    try:
        meta = json.loads(meta_file.read_text())
        cached_time = datetime.fromisoformat(meta["timestamp"])
        root = snapshot_dir / meta["root"]
        if datetime.now() - cached_time <= timedelta(hours=max_age_hours) and root.is_dir():
            logger.info(f"Using cached snapshot of {owner}/{repo}@{ref}")
            return root
    except Exception as e:
        logger.warning(f"Invalid snapshot metadata for {owner}/{repo}@{ref}: {e}")

    return None


def _fetch_tarball_bytes(owner: str, repo: str, ref: str) -> bytes:
    """Download a repository tarball from GitHub codeload.

    A tarball download is a single request that does not count against the
    GitHub API rate limit, unlike per-file raw fetches plus tree API calls.
    codeload accepts branch names, tags, and commit SHAs as the ref.

    Raises
    ------
    httpx.HTTPStatusError
        If the download fails (e.g., 404 for a missing ref).
    """
    tarball_url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{ref}"
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        response = client.get(tarball_url)
        response.raise_for_status()
        return response.content


def _extract_snapshot(owner: str, repo: str, ref: str, tarball: bytes) -> Path | None:
    """Extract a tarball into the snapshot cache and return its root."""
    snapshot_dir = _snapshot_dir_for(owner, repo, ref)

    try:
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
        snapshot_dir.mkdir(parents=True)

        with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
            # The "data" filter blocks path traversal and special files
            tar.extractall(snapshot_dir, filter="data")

        # GitHub tarballs contain a single top-level directory ({repo}-{ref})
        roots = [p for p in snapshot_dir.iterdir() if p.is_dir()]
        if len(roots) != 1:
            logger.error(f"Unexpected tarball layout for {owner}/{repo}@{ref}")
            return None

        root = roots[0]
        meta_file = snapshot_dir / "meta.json"
        meta_file.write_text(
            json.dumps({"timestamp": datetime.now().isoformat(), "root": root.name})
        )
        logger.info(f"Extracted snapshot of {owner}/{repo}@{ref} to {root}")
        return root

    except Exception as e:
        logger.error(f"Error extracting tarball for {owner}/{repo}@{ref}: {e}")
        return None


def _ensure_repo_snapshot(
    owner: str,
    repo: str,
    branch: str | None,
    force_refresh: bool = False,
    max_age_hours: int = 24,
) -> tuple[Path, str] | tuple[None, None]:
    """Get an extracted local snapshot of a GitHub repository.

    Parameters
    ----------
    owner : str
        Repository owner.
    repo : str
        Repository name.
    branch : str | None
        Ref to download (branch, tag, or SHA). None tries 'main' then 'master'.
    force_refresh : bool, optional
        Skip the cached snapshot and re-download, by default False.
    max_age_hours : int, optional
        Maximum snapshot age before re-download, by default 24.

    Returns
    -------
    tuple[Path, str] | tuple[None, None]
        (snapshot_root, resolved_ref), or (None, None) on failure.
    """
    candidates = [branch] if branch else ["main", "master"]

    if not force_refresh:
        for ref in candidates:
            root = _load_cached_snapshot(owner, repo, ref, max_age_hours)
            if root is not None:
                return root, ref

    for ref in candidates:
        try:
            logger.info(f"Downloading tarball of {owner}/{repo}@{ref}...")
            tarball = _fetch_tarball_bytes(owner, repo, ref)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404 and branch is None:
                logger.info(f"Ref '{ref}' not found for {owner}/{repo}, trying next")
                continue
            logger.error(f"HTTP error downloading {owner}/{repo}@{ref}: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Error downloading {owner}/{repo}@{ref}: {e}")
            return None, None

        root = _extract_snapshot(owner, repo, ref, tarball)
        if root is None:
            return None, None
        return root, ref

    logger.error(
        f"No usable ref found for {owner}/{repo} (tried: {', '.join(candidates)})"
    )
    return None, None


def _get_document_metadata_from_snapshot(
    skill_dir: Path,
    snapshot_root: Path,
    owner: str,
    repo: str,
    ref: str,
    text_extensions: list[str],
    image_extensions: list[str],
) -> dict[str, dict[str, Any]]:
    """Build document metadata for a skill directory inside a repo snapshot.

    Content is not loaded here - documents are read lazily from the local
    snapshot when accessed (progressive disclosure without network calls).

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary mapping relative paths to document metadata (no content).
    """
    documents: dict[str, dict[str, Any]] = {}

    for file_path in sorted(skill_dir.rglob("*")):
        if file_path.name == "SKILL.md" or file_path.is_dir():
            continue

        rel_path = file_path.relative_to(skill_dir).as_posix()
        repo_path = file_path.relative_to(snapshot_root).as_posix()

        if _is_text_file(file_path, text_extensions):
            doc_type = "text"
        elif _is_image_file(file_path, image_extensions):
            doc_type = "image"
        else:
            continue

        documents[rel_path] = {
            "type": doc_type,
            "size": file_path.stat().st_size,
            "url": f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{repo_path}",
            "fetched": False,
        }

    return documents


def _create_snapshot_document_fetcher(
    skill_dir: Path,
    documents: dict[str, dict[str, Any]],
    text_extensions: list[str],
    image_extensions: list[str],
    max_image_size: int,
) -> Callable:
    """Create a fetcher that reads documents from the local snapshot on demand.

    Returns
    -------
    callable
        Function that loads a document by relative path.
    """

    def fetch_document(doc_path: str) -> dict[str, Any] | None:
        meta = documents.get(doc_path)
        if meta is None:
            return None

        file_path = (skill_dir / doc_path).resolve()
        try:
            file_path.relative_to(skill_dir.resolve())
        except ValueError:
            logger.warning(f"Refusing to read outside skill directory: {doc_path}")
            return None

        if not file_path.is_file():
            logger.warning(f"Document missing from snapshot: {doc_path}")
            return None

        if _is_text_file(file_path, text_extensions):
            doc = _load_text_file(file_path)
        elif _is_image_file(file_path, image_extensions):
            doc = _load_image_file(file_path, max_image_size, url=meta.get("url"))
        else:
            return None

        if doc:
            doc["fetched"] = True
            if "url" in meta:
                doc.setdefault("url", meta["url"])
        return doc

    return fetch_document


def load_from_github(
    url: str,
    subpath: str = "",
    config: dict[str, Any] | None = None,
    force_refresh: bool = False,
) -> list[Skill]:
    """Load skills from a GitHub repository via a tarball snapshot.

    The whole repository is downloaded as one tarball (a single request that
    does not count against the GitHub API rate limit), extracted to a local
    cache, and skills plus their documents are served from that snapshot.

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
    force_refresh : bool, optional
        Re-download the repository even if a fresh snapshot is cached.

    Returns
    -------
    list[Skill]
        List of loaded skills.
    """
    skills: list[Skill] = []

    if config is None:
        config = {}

    load_documents = config.get("load_skill_documents", True)
    text_extensions = config.get(
        "text_file_extensions",
        [".md", ".py", ".txt", ".json", ".yaml", ".yml", ".sh", ".r", ".ipynb"],
    )
    image_extensions = config.get(
        "allowed_image_extensions", [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]
    )
    max_image_size = config.get("max_image_size_bytes", 5242880)

    parsed = parse_github_source_url(url, subpath)
    if parsed is None:
        logger.error(f"Invalid GitHub URL: {url}")
        return skills
    owner, repo, branch, subpath = parsed

    logger.info(
        f"Loading skills from GitHub: {owner}/{repo}"
        + (f" (branch: {branch})" if branch else "")
        + (f" (subpath: {subpath})" if subpath else "")
    )

    snapshot_root, ref = _ensure_repo_snapshot(
        owner, repo, branch, force_refresh=force_refresh
    )
    if snapshot_root is None:
        return skills

    # Collect SKILL.md files, respecting the subpath filter
    if subpath:
        subpath_dir = snapshot_root / subpath
        if subpath_dir.is_dir():
            skill_files = sorted(subpath_dir.rglob("SKILL.md"))
        else:
            # Prefix-match fallback (subpath may be a partial path)
            skill_files = sorted(
                p
                for p in snapshot_root.rglob("SKILL.md")
                if p.relative_to(snapshot_root).as_posix().startswith(subpath)
            )
            if not skill_files:
                logger.warning(f"Subpath '{subpath}' not found in {owner}/{repo}@{ref}")
    else:
        skill_files = sorted(snapshot_root.rglob("SKILL.md"))

    for skill_file in skill_files:
        try:
            content = skill_file.read_text(encoding="utf-8")
            repo_rel = skill_file.relative_to(snapshot_root).as_posix()
            source = f"https://github.com/{owner}/{repo}/tree/{ref}/{repo_rel}"

            skill = parse_skill_md(content, source)
            if not skill:
                continue

            if load_documents:
                skill_dir = skill_file.parent
                documents = _get_document_metadata_from_snapshot(
                    skill_dir,
                    snapshot_root,
                    owner,
                    repo,
                    ref,
                    text_extensions,
                    image_extensions,
                )
                skill.documents = documents
                skill._document_fetcher = _create_snapshot_document_fetcher(
                    skill_dir,
                    documents,
                    text_extensions,
                    image_extensions,
                    max_image_size,
                )
                if documents:
                    logger.info(
                        f"Found {len(documents)} additional documents for skill: {skill.name}"
                    )

            skills.append(skill)
            logger.info(f"Loaded skill: {skill.name} from {source}")

        except Exception as e:
            logger.error(f"Error loading {skill_file} from snapshot: {e}")
            continue

    logger.info(f"Loaded {len(skills)} skills from GitHub repo {url}")
    return skills


def load_all_skills(
    skill_sources: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
    force_refresh: bool = False,
) -> list[Skill]:
    """Load skills from all configured sources.

    Parameters
    ----------
    skill_sources : list[dict[str, Any]]
        List of skill source configurations.
    config : dict[str, Any] | None
        Configuration dictionary with document loading settings.
    force_refresh : bool, optional
        Re-download GitHub sources even if fresh snapshots are cached.
        Used by the auto-updater so detected changes actually land.

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
                skills = load_from_github(
                    url, subpath, config, force_refresh=force_refresh
                )
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


def load_skills_in_batches(
    skill_sources: list[dict[str, Any]],
    config: dict[str, Any] | None,
    batch_callback: Callable[[list[Skill], int], None],
    batch_size: int = 10,
) -> None:
    """Load skills from all sources in batches with callbacks.

    This function loads skills incrementally and calls the callback
    after each batch, allowing for progressive indexing.

    Parameters
    ----------
    skill_sources : list[dict[str, Any]]
        List of skill source configurations.
    config : dict[str, Any] | None
        Configuration dictionary with document loading settings.
    batch_callback : Callable[[list[Skill], int], None]
        Callback function called with (batch_skills, total_loaded) after each batch.
    batch_size : int, optional
        Number of skills per batch, by default 10.
    """
    current_batch: list[Skill] = []
    total_loaded = 0

    def process_batch() -> None:
        """Process and clear the current batch."""
        nonlocal total_loaded
        if current_batch:
            total_loaded += len(current_batch)
            batch_callback(current_batch.copy(), total_loaded)
            current_batch.clear()

    for source_config in skill_sources:
        source_type = source_config.get("type")

        try:
            if source_type == "github":
                url = source_config.get("url")
                subpath = source_config.get("subpath", "")
                if url:
                    skills = load_from_github(url, subpath, config)
                    for skill in skills:
                        current_batch.append(skill)
                        if len(current_batch) >= batch_size:
                            process_batch()

            elif source_type == "local":
                path = source_config.get("path")
                if path:
                    skills = load_from_local(path, config)
                    for skill in skills:
                        current_batch.append(skill)
                        if len(current_batch) >= batch_size:
                            process_batch()

            else:
                logger.warning(f"Unknown source type: {source_type}")

        except Exception as e:
            logger.error(f"Error loading from source {source_config}: {e}")
            continue

    # Process any remaining skills in the final batch
    process_batch()

    logger.info(f"Finished loading {total_loaded} skills in batches")
