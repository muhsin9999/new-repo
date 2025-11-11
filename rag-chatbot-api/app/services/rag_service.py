"""
RAG (Retrieval Augmented Generation) service.
Orchestrates document retrieval and response generation.
"""
from typing import Dict, List, Optional

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_store_service import VectorStoreService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RAGService:
    """Service for RAG operations."""

    def __init__(self):
        """Initialize RAG service with dependencies."""
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        self.vector_store_service = VectorStoreService()

        # RAG configuration
        self.retrieval_top_k = settings.RETRIEVAL_TOP_K
        self.max_context_length = settings.MAX_CONTEXT_LENGTH

    async def generate_response(
        self,
        query: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Generate a response using RAG.

        Args:
            query: User's query
            user_id: User ID for filtering documents
            conversation_history: Optional previous messages
            filters: Optional metadata filters for retrieval

        Returns:
            Dictionary with response and metadata
        """
        try:
            logger.info("rag_request_started", query_length=len(query), user_id=user_id)

            # Step 1: Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)

            # Step 2: Retrieve relevant context
            retrieval_filters = filters or {}
            retrieval_filters["user_id"] = user_id

            retrieved_chunks = await self.vector_store_service.query_vectors(
                query_vector=query_embedding,
                top_k=self.retrieval_top_k,
                filter_dict=retrieval_filters
            )

            logger.info(
                "context_retrieved",
                chunks_count=len(retrieved_chunks),
                top_score=retrieved_chunks[0]["score"] if retrieved_chunks else 0
            )

            # Step 3: Build context from retrieved chunks
            context = self._build_context(retrieved_chunks)

            # Step 4: Create prompt with context
            system_message = self._get_system_message()
            messages = await self.llm_service.create_prompt(
                system_message=system_message,
                user_message=query,
                context=context,
                chat_history=conversation_history
            )

            # Step 5: Generate response
            llm_response = await self.llm_service.generate_response(messages)

            # Step 6: Format response with sources
            response = {
                "response": llm_response["content"],
                "sources": self._format_sources(retrieved_chunks),
                "tokens_used": llm_response["tokens_used"]["total"],
                "model": llm_response["model"],
                "metadata": {
                    "retrieval_count": len(retrieved_chunks),
                    "context_length": len(context),
                    "finish_reason": llm_response["finish_reason"]
                }
            }

            logger.info(
                "rag_response_generated",
                tokens=response["tokens_used"],
                sources=len(response["sources"])
            )

            return response

        except Exception as e:
            logger.error("rag_generation_failed", error=str(e))
            raise

    async def generate_response_stream(
        self,
        query: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filters: Optional[Dict] = None
    ):
        """
        Generate a streaming response using RAG.

        Args:
            query: User's query
            user_id: User ID for filtering documents
            conversation_history: Optional previous messages
            filters: Optional metadata filters for retrieval

        Yields:
            Response chunks as strings
        """
        try:
            logger.info("rag_streaming_started", query_length=len(query))

            # Retrieve context
            query_embedding = await self.embedding_service.generate_embedding(query)

            retrieval_filters = filters or {}
            retrieval_filters["user_id"] = user_id

            retrieved_chunks = await self.vector_store_service.query_vectors(
                query_vector=query_embedding,
                top_k=self.retrieval_top_k,
                filter_dict=retrieval_filters
            )

            # Build context and prompt
            context = self._build_context(retrieved_chunks)
            system_message = self._get_system_message()
            messages = await self.llm_service.create_prompt(
                system_message=system_message,
                user_message=query,
                context=context,
                chat_history=conversation_history
            )

            # Stream response
            async for chunk in self.llm_service.generate_response_stream(messages):
                yield chunk

            logger.info("rag_streaming_complete")

        except Exception as e:
            logger.error("rag_streaming_failed", error=str(e))
            raise

    def _build_context(self, retrieved_chunks: List[Dict]) -> str:
        """
        Build context string from retrieved chunks.

        Args:
            retrieved_chunks: List of retrieved chunk dictionaries

        Returns:
            Formatted context string
        """
        if not retrieved_chunks:
            return ""

        context_parts = []
        current_length = 0

        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata", {})
            content = metadata.get("content", "")

            # Check if adding this chunk would exceed max context length
            if current_length + len(content) > self.max_context_length:
                break

            # Add chunk with source information
            source_info = f"[Source: {metadata.get('document_name', 'Unknown')}]"
            context_parts.append(f"{source_info}\n{content}\n")

            current_length += len(content)

        context = "\n---\n".join(context_parts)
        return context

    def _format_sources(self, retrieved_chunks: List[Dict]) -> List[Dict]:
        """
        Format retrieved chunks as source references.

        Args:
            retrieved_chunks: List of retrieved chunk dictionaries

        Returns:
            List of formatted source dictionaries
        """
        sources = []

        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata", {})

            sources.append({
                "document_id": metadata.get("document_id", ""),
                "document_name": metadata.get("document_name", "Unknown"),
                "chunk_id": chunk.get("id", ""),
                "content": metadata.get("content", "")[:200] + "...",  # Preview
                "relevance_score": round(chunk.get("score", 0), 4)
            })

        return sources

    def _get_system_message(self) -> str:
        """
        Get the system message for the LLM.

        Returns:
            System message string
        """
        return """You are a helpful AI assistant with access to a knowledge base.

When answering questions:
1. Use the provided context to inform your answers
2. If the context doesn't contain relevant information, say so honestly
3. Cite sources when you use information from the context
4. Be concise and accurate
5. If you're unsure, acknowledge the uncertainty

Always prioritize accuracy over speculation."""

    async def similarity_search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform similarity search without generating a response.

        Args:
            query: Search query
            user_id: User ID for filtering
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of similar chunks
        """
        try:
            query_embedding = await self.embedding_service.generate_embedding(query)

            retrieval_filters = filters or {}
            retrieval_filters["user_id"] = user_id

            results = await self.vector_store_service.query_vectors(
                query_vector=query_embedding,
                top_k=top_k,
                filter_dict=retrieval_filters
            )

            logger.info("similarity_search_complete", results_count=len(results))
            return self._format_sources(results)

        except Exception as e:
            logger.error("similarity_search_failed", error=str(e))
            raise
