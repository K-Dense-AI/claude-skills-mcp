"""Vector search engine for finding relevant skills."""

import logging
import threading
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from .skill_loader import Skill

logger = logging.getLogger(__name__)


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

            # Generate embeddings from skill descriptions
            descriptions = [skill.description for skill in skills]
            model = self._ensure_model_loaded()
            self.embeddings = model.encode(descriptions, convert_to_numpy=True)

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

            # Generate embeddings for new skills
            descriptions = [skill.description for skill in skills]
            model = self._ensure_model_loaded()
            new_embeddings = model.encode(descriptions, convert_to_numpy=True)

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
        # Normalize vectors
        vec_norm = vec / np.linalg.norm(vec)
        matrix_norm = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)

        # Compute dot product (cosine similarity for normalized vectors)
        similarities = np.dot(matrix_norm, vec_norm)

        return similarities
