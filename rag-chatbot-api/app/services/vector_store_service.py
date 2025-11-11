"""
Vector store service for Pinecone integration.
Handles vector indexing, search, and management.
"""
from typing import Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

from app.config import settings
from app.core.exceptions import VectorStoreError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VectorStoreService:
    """Service for Pinecone vector store operations."""

    def __init__(self):
        """Initialize Pinecone client."""
        try:
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index_name = settings.PINECONE_INDEX_NAME
            self.dimension = settings.EMBEDDING_DIMENSION
            self._index = None

            logger.info("pinecone_client_initialized")

        except Exception as e:
            logger.error("pinecone_init_failed", error=str(e))
            raise VectorStoreError(f"Failed to initialize Pinecone: {str(e)}")

    def _get_index(self):
        """Get or create Pinecone index."""
        if self._index is None:
            try:
                # Check if index exists
                if self.index_name not in self.pc.list_indexes().names():
                    logger.info("creating_pinecone_index", name=self.index_name)

                    self.pc.create_index(
                        name=self.index_name,
                        dimension=self.dimension,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud="aws",
                            region=settings.PINECONE_ENVIRONMENT
                        )
                    )

                self._index = self.pc.Index(self.index_name)
                logger.info("pinecone_index_ready", name=self.index_name)

            except Exception as e:
                logger.error("pinecone_index_init_failed", error=str(e))
                raise VectorStoreError(f"Failed to get index: {str(e)}")

        return self._index

    async def upsert_vectors(
        self,
        vectors: List[Dict],
        namespace: Optional[str] = None
    ) -> Dict:
        """
        Upsert vectors into the index.

        Args:
            vectors: List of vector dictionaries with 'id', 'values', and 'metadata'
            namespace: Optional namespace for the vectors

        Returns:
            Upsert response dictionary

        Raises:
            VectorStoreError: If upsert fails
        """
        try:
            index = self._get_index()

            response = index.upsert(
                vectors=vectors,
                namespace=namespace or ""
            )

            logger.info(
                "vectors_upserted",
                count=len(vectors),
                namespace=namespace
            )

            return {"upserted_count": response.upserted_count}

        except Exception as e:
            logger.error("vector_upsert_failed", error=str(e))
            raise VectorStoreError(f"Failed to upsert vectors: {str(e)}")

    async def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict] = None,
        namespace: Optional[str] = None,
        include_metadata: bool = True
    ) -> List[Dict]:
        """
        Query vectors in the index.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filter
            namespace: Optional namespace to query
            include_metadata: Whether to include metadata in results

        Returns:
            List of matching results with scores

        Raises:
            VectorStoreError: If query fails
        """
        try:
            index = self._get_index()

            response = index.query(
                vector=query_vector,
                top_k=top_k,
                filter=filter_dict,
                namespace=namespace or "",
                include_metadata=include_metadata
            )

            results = []
            for match in response.matches:
                results.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata if include_metadata else {}
                })

            logger.info(
                "vectors_queried",
                top_k=top_k,
                results_count=len(results),
                namespace=namespace
            )

            return results

        except Exception as e:
            logger.error("vector_query_failed", error=str(e))
            raise VectorStoreError(f"Failed to query vectors: {str(e)}")

    async def delete_vectors(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete vectors by IDs.

        Args:
            ids: List of vector IDs to delete
            namespace: Optional namespace

        Returns:
            True if successful

        Raises:
            VectorStoreError: If deletion fails
        """
        try:
            index = self._get_index()

            index.delete(
                ids=ids,
                namespace=namespace or ""
            )

            logger.info(
                "vectors_deleted",
                count=len(ids),
                namespace=namespace
            )

            return True

        except Exception as e:
            logger.error("vector_deletion_failed", error=str(e))
            raise VectorStoreError(f"Failed to delete vectors: {str(e)}")

    async def delete_by_filter(
        self,
        filter_dict: Dict,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete vectors by metadata filter.

        Args:
            filter_dict: Metadata filter dictionary
            namespace: Optional namespace

        Returns:
            True if successful

        Raises:
            VectorStoreError: If deletion fails
        """
        try:
            index = self._get_index()

            index.delete(
                filter=filter_dict,
                namespace=namespace or ""
            )

            logger.info(
                "vectors_deleted_by_filter",
                filter=filter_dict,
                namespace=namespace
            )

            return True

        except Exception as e:
            logger.error("vector_deletion_by_filter_failed", error=str(e))
            raise VectorStoreError(f"Failed to delete vectors by filter: {str(e)}")

    async def fetch_vectors(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict:
        """
        Fetch vectors by IDs.

        Args:
            ids: List of vector IDs to fetch
            namespace: Optional namespace

        Returns:
            Dictionary of vectors

        Raises:
            VectorStoreError: If fetch fails
        """
        try:
            index = self._get_index()

            response = index.fetch(
                ids=ids,
                namespace=namespace or ""
            )

            logger.info(
                "vectors_fetched",
                count=len(response.vectors),
                namespace=namespace
            )

            return response.vectors

        except Exception as e:
            logger.error("vector_fetch_failed", error=str(e))
            raise VectorStoreError(f"Failed to fetch vectors: {str(e)}")

    async def get_index_stats(self) -> Dict:
        """
        Get statistics about the index.

        Returns:
            Index statistics dictionary

        Raises:
            VectorStoreError: If stats retrieval fails
        """
        try:
            index = self._get_index()
            stats = index.describe_index_stats()

            logger.info("index_stats_retrieved", total_vectors=stats.total_vector_count)

            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }

        except Exception as e:
            logger.error("index_stats_failed", error=str(e))
            raise VectorStoreError(f"Failed to get index stats: {str(e)}")
