"""
Custom exceptions for the RAG Chatbot API.
Defines application-specific exception classes.
"""
from typing import Any, Dict, Optional


class RagChatbotException(Exception):
    """Base exception for all RAG Chatbot errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(RagChatbotException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(RagChatbotException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, details=details)


class ResourceNotFoundError(RagChatbotException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} with ID '{resource_id}' not found"
        super().__init__(message, status_code=404, details=details)


class ValidationError(RagChatbotException):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=422, details=details)


class RateLimitExceededError(RagChatbotException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, status_code=429, details=details)


class DocumentProcessingError(RagChatbotException):
    """Raised when document processing fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class EmbeddingError(RagChatbotException):
    """Raised when embedding generation fails."""

    def __init__(self, message: str = "Failed to generate embeddings", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class VectorStoreError(RagChatbotException):
    """Raised when vector store operations fail."""

    def __init__(self, message: str = "Vector store operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class LLMError(RagChatbotException):
    """Raised when LLM API calls fail."""

    def __init__(self, message: str = "LLM request failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class StorageError(RagChatbotException):
    """Raised when S3 or storage operations fail."""

    def __init__(self, message: str = "Storage operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class DatabaseError(RagChatbotException):
    """Raised when database operations fail."""

    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class ConfigurationError(RagChatbotException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class FileTypeError(ValidationError):
    """Raised when file type is not allowed."""

    def __init__(self, file_type: str, allowed_types: list, details: Optional[Dict[str, Any]] = None):
        message = f"File type '{file_type}' not allowed. Allowed types: {', '.join(allowed_types)}"
        super().__init__(message, details=details)


class FileSizeError(ValidationError):
    """Raised when file size exceeds limit."""

    def __init__(self, size: int, max_size: int, details: Optional[Dict[str, Any]] = None):
        message = f"File size ({size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        super().__init__(message, details=details)


class ConversationNotFoundError(ResourceNotFoundError):
    """Raised when conversation is not found."""

    def __init__(self, conversation_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("Conversation", conversation_id, details)


class DocumentNotFoundError(ResourceNotFoundError):
    """Raised when document is not found."""

    def __init__(self, document_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("Document", document_id, details)
