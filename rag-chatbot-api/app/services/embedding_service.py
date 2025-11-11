"""
Embedding service for generating vector embeddings.
Uses Sentence Transformers for local embedding generation.
"""
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.core.exceptions import EmbeddingError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, model_name: str = None):
        """
        Initialize embedding service.

        Args:
            model_name: Name of the sentence transformer model
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.model: SentenceTransformer = None
        self._load_model()

    def _load_model(self):
        """Load the embedding model."""
        try:
            logger.info("loading_embedding_model", model=self.model_name)
            self.model = SentenceTransformer(self.model_name)
            logger.info("embedding_model_loaded", model=self.model_name)

        except Exception as e:
            logger.error("embedding_model_load_failed", error=str(e))
            raise EmbeddingError(f"Failed to load embedding model: {str(e)}")

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            if not self.model:
                self._load_model()

            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            # Convert to list
            embedding_list = embedding.tolist()

            logger.debug(
                "embedding_generated",
                text_length=len(text),
                embedding_dim=len(embedding_list)
            )

            return embedding_list

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            if not self.model:
                self._load_model()

            logger.info("generating_batch_embeddings", count=len(texts))

            # Generate embeddings in batches
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 100
            )

            # Convert to list of lists
            embeddings_list = [emb.tolist() for emb in embeddings]

            logger.info(
                "batch_embeddings_generated",
                count=len(embeddings_list),
                embedding_dim=len(embeddings_list[0]) if embeddings_list else 0
            )

            return embeddings_list

        except Exception as e:
            logger.error("batch_embedding_generation_failed", error=str(e))
            raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}")

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.

        Returns:
            Embedding dimension
        """
        if not self.model:
            self._load_model()

        return self.model.get_sentence_embedding_dimension()

    async def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0 to 1)
        """
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Compute cosine similarity
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

            return float(similarity)

        except Exception as e:
            logger.error("similarity_computation_failed", error=str(e))
            return 0.0

    async def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar embeddings to a query embedding.

        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embedding vectors
            top_k: Number of top results to return

        Returns:
            List of (index, similarity_score) tuples
        """
        try:
            similarities = []

            for idx, candidate_emb in enumerate(candidate_embeddings):
                sim = await self.compute_similarity(query_embedding, candidate_emb)
                similarities.append((idx, sim))

            # Sort by similarity (descending) and return top k
            similarities.sort(key=lambda x: x[1], reverse=True)

            return similarities[:top_k]

        except Exception as e:
            logger.error("similarity_search_failed", error=str(e))
            return []
