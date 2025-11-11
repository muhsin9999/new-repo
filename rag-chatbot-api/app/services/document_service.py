"""
Document service for document processing operations.
"""
import os
import tempfile
from typing import List
from uuid import uuid4

from app.services.embedding_service import EmbeddingService
from app.services.storage_service import StorageService
from app.services.vector_store_service import VectorStoreService
from app.utils.file_parser import FileParser
from app.utils.logging import get_logger
from app.utils.text_splitter import TextSplitter

logger = get_logger(__name__)


class DocumentService:
    """Service for document processing."""

    def __init__(self):
        """Initialize document service with dependencies."""
        self.storage_service = StorageService()
        self.embedding_service = EmbeddingService()
        self.vector_store_service = VectorStoreService()
        self.text_splitter = TextSplitter()

    async def process_document(
        self,
        document_id: str,
        file_path: str,
        content_type: str,
        user_id: str,
        document_name: str
    ) -> dict:
        """
        Process a document end-to-end:
        1. Parse file
        2. Split into chunks
        3. Generate embeddings
        4. Store in vector database

        Args:
            document_id: Unique document ID
            file_path: Path to the document file
            content_type: MIME type of the document
            user_id: User ID who owns the document
            document_name: Original document name

        Returns:
            Processing results dictionary
        """
        try:
            logger.info(
                "document_processing_started",
                document_id=document_id,
                file_path=file_path
            )

            # Step 1: Parse document
            text_content = await FileParser.parse_file(file_path, content_type)
            logger.info("document_parsed", document_id=document_id, length=len(text_content))

            # Step 2: Split into chunks
            chunks = self.text_splitter.split_text(text_content)
            logger.info("document_chunked", document_id=document_id, chunks=len(chunks))

            # Step 3: Generate embeddings
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = await self.embedding_service.generate_embeddings_batch(chunk_texts)
            logger.info("embeddings_generated", document_id=document_id, count=len(embeddings))

            # Step 4: Prepare vectors for Pinecone
            vectors = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"{document_id}_chunk_{idx}"

                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "document_id": document_id,
                        "document_name": document_name,
                        "chunk_index": idx,
                        "content": chunk["content"],
                        "token_count": chunk["token_count"],
                        "user_id": user_id
                    }
                })

            # Step 5: Upsert to Pinecone
            await self.vector_store_service.upsert_vectors(vectors)
            logger.info("vectors_upserted", document_id=document_id, count=len(vectors))

            result = {
                "document_id": document_id,
                "status": "completed",
                "chunks_created": len(chunks),
                "total_tokens": sum(c["token_count"] for c in chunks)
            }

            logger.info("document_processing_complete", **result)
            return result

        except Exception as e:
            logger.error(
                "document_processing_failed",
                document_id=document_id,
                error=str(e)
            )
            raise

    async def delete_document_vectors(self, document_id: str) -> bool:
        """
        Delete all vectors associated with a document.

        Args:
            document_id: Document ID

        Returns:
            True if successful
        """
        try:
            await self.vector_store_service.delete_by_filter(
                filter_dict={"document_id": document_id}
            )

            logger.info("document_vectors_deleted", document_id=document_id)
            return True

        except Exception as e:
            logger.error("document_vector_deletion_failed", error=str(e))
            return False

    async def search_documents(
        self,
        query: str,
        user_id: str,
        top_k: int = 5
    ) -> List[dict]:
        """
        Search for relevant document chunks.

        Args:
            query: Search query
            user_id: User ID for filtering
            top_k: Number of results to return

        Returns:
            List of matching chunks
        """
        try:
            query_embedding = await self.embedding_service.generate_embedding(query)

            results = await self.vector_store_service.query_vectors(
                query_vector=query_embedding,
                top_k=top_k,
                filter_dict={"user_id": user_id}
            )

            logger.info("document_search_complete", results=len(results))
            return results

        except Exception as e:
            logger.error("document_search_failed", error=str(e))
            return []
