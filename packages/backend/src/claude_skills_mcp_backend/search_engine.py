"""Vector search engine for finding relevant skills."""

import hashlib
import logging
import tempfile
import threading
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from .skill_loader import Skill

logger = logging.getLogger(__name__)


def _embedding_text(skill: Skill) -> str:
    """Text used to embed a skill for semantic search."""
    return f"{skill.name}: {skill.description}"


def _get_embedding_cache_dir() -> Path:
    """Get embedding cache directory.

    Returns
    -------
    Path
        Path to embedding cache directory.
    """
    cache_dir = Path(tempfile.gettempdir()) / "claude_skills_mcp_cache" / "embeddings"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


class SkillSearchEngine:
    """Search engine for finding relevant skills using vector similarity.

    Attributes
    ----------
    model : SentenceTransformer | None
        Embedding model for generating vectors (lazy-loaded).
    model_name : str
        Name of the sentence-transformers model to use.
    skills : list[Skill]
        List of indexed skills.
    embeddings : np.ndarray | None
        Embeddings matrix for all skill descriptions.
    _lock : threading.Lock
        Lock for thread-safe access to skills and embeddings.
    """

    def __init__(self, model_name: str):
        """Initialize the search engine.

        Parameters
        ----------
        model_name : str
            Name of the sentence-transformers model to use.
        """
        logger.info(
            f"Search engine initialized (model: {model_name}, lazy-loading enabled)"
        )
        self.model: SentenceTransformer | None = None
        self.model_name = model_name
        self.skills: list[Skill] = []
        self.embeddings: np.ndarray | None = None
        self._lock = threading.Lock()

    def _ensure_model_loaded(self) -> SentenceTransformer:
        """Ensure the embedding model is loaded (lazy initialization).

        Returns
        -------
        SentenceTransformer
            The loaded embedding model.
        """
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Embedding model loaded: {self.model_name}")
        return self.model

    def _encode_with_cache(self, texts: list[str]) -> np.ndarray:
        """Encode texts, reusing a disk cache for repeated batches.

        Embeddings are keyed by model name plus the exact batch of texts, so
        unchanged skill sources produce cache hits across restarts. A cache
        hit also avoids loading the embedding model, which is the dominant
        startup cost on warm starts.

        Parameters
        ----------
        texts : list[str]
            Texts to embed.

        Returns
        -------
        np.ndarray
            Embeddings matrix for the texts.
        """
        digest = hashlib.sha256(
            "\x00".join([self.model_name, *texts]).encode("utf-8")
        ).hexdigest()
        cache_path = _get_embedding_cache_dir() / f"{digest}.npy"

        if cache_path.exists():
            try:
                embeddings = np.load(cache_path)
                if embeddings.shape[0] == len(texts):
                    logger.info(
                        f"Loaded {len(texts)} embeddings from cache: {cache_path}"
                    )
                    return embeddings
                logger.warning(
                    f"Embedding cache shape mismatch, re-encoding: {cache_path}"
                )
            except Exception as e:
                logger.warning(f"Failed to load embedding cache {cache_path}: {e}")

        model = self._ensure_model_loaded()
        embeddings = model.encode(texts, convert_to_numpy=True)

        try:
            np.save(cache_path, embeddings)
            logger.debug(f"Saved embeddings to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save embedding cache {cache_path}: {e}")

        return embeddings

    def index_skills(self, skills: list[Skill]) -> None:
        """Index a list of skills by generating their embeddings.

        Parameters
        ----------
        skills : list[Skill]
            Skills to index.
        """
        with self._lock:
            if not skills:
                logger.warning("No skills to index")
                self.skills = []
                self.embeddings = None
                return

            logger.info(f"Indexing {len(skills)} skills...")
            self.skills = skills

            # Embed name + description so both contribute to relevance
            texts = [_embedding_text(skill) for skill in skills]
            self.embeddings = self._encode_with_cache(texts)

            logger.info(f"Successfully indexed {len(skills)} skills")

    def add_skills(self, skills: list[Skill]) -> None:
        """Add skills incrementally and update embeddings.

        Parameters
        ----------
        skills : list[Skill]
            Skills to add to the index.
        """
        if not skills:
            return

        with self._lock:
            logger.info(f"Adding {len(skills)} skills to index...")

            # Embed name + description so both contribute to relevance
            texts = [_embedding_text(skill) for skill in skills]
            new_embeddings = self._encode_with_cache(texts)

            # Append to existing skills and embeddings
            self.skills.extend(skills)

            if self.embeddings is None:
                # First batch of skills
                self.embeddings = new_embeddings
            else:
                # Append to existing embeddings
                self.embeddings = np.vstack([self.embeddings, new_embeddings])

            logger.info(
                f"Successfully added {len(skills)} skills. Total: {len(self.skills)} skills"
            )

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Search for the most relevant skills based on a query.

        Parameters
        ----------
        query : str
            The task description or query to search for.
        top_k : int, optional
            Number of top results to return, by default 3.

        Returns
        -------
        list[dict[str, Any]]
            List of skill dictionaries with relevance scores, sorted by relevance.
        """
        with self._lock:
            if not self.skills or self.embeddings is None:
                logger.warning("No skills indexed, returning empty results")
                return []

            # Ensure top_k doesn't exceed available skills
            top_k = min(top_k, len(self.skills))

            logger.info(f"Searching for: '{query}' (top_k={top_k})")

            # Generate embedding for the query
            model = self._ensure_model_loaded()
            query_embedding = model.encode([query], convert_to_numpy=True)[0]

            # Compute cosine similarity
            similarities = self._cosine_similarity(query_embedding, self.embeddings)

            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]

            # Build results
            results = []
            for idx in top_indices:
                skill = self.skills[idx]
                score = float(similarities[idx])

                result = skill.to_dict()
                result["relevance_score"] = score
                results.append(result)

                logger.debug(f"Found skill: {skill.name} (score: {score:.4f})")

            logger.info(f"Returning {len(results)} results")
            return results

    @staticmethod
    def _cosine_similarity(vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between a vector and a matrix of vectors.

        Parameters
        ----------
        vec : np.ndarray
            Query vector.
        matrix : np.ndarray
            Matrix of vectors to compare against.

        Returns
        -------
        np.ndarray
            Similarity scores.
        """
        # Normalize vectors (epsilon guard against zero-norm vectors)
        vec_norm = vec / max(float(np.linalg.norm(vec)), 1e-12)
        matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix_norm = matrix / np.maximum(matrix_norms, 1e-12)

        # Compute dot product (cosine similarity for normalized vectors)
        similarities = np.dot(matrix_norm, vec_norm)

        return similarities
