"""
Celery application and tasks for background processing.
"""
import os
import tempfile
from celery import Celery

from app.config import settings
from app.services.document_service import DocumentService
from app.services.storage_service import StorageService
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "rag_chatbot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.DOCUMENT_PROCESSING_TIMEOUT,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000
)


@celery_app.task(name="process_document", bind=True)
def process_document_task(
    self,
    document_id: str,
    s3_key: str,
    content_type: str,
    user_id: str,
    document_name: str
):
    """
    Background task to process a document.

    Args:
        self: Task instance (bound)
        document_id: Document ID
        s3_key: S3 object key
        content_type: MIME type
        user_id: User ID
        document_name: Document name

    Returns:
        Processing result dictionary
    """
    try:
        logger.info(
            "processing_task_started",
            task_id=self.request.id,
            document_id=document_id
        )

        # Update task state
        self.update_state(state="PROCESSING", meta={"progress": 10})

        # Download file from S3
        storage_service = StorageService()
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(document_name)[1]) as tmp_file:
            file_path = tmp_file.name

        # Use asyncio to run async functions
        import asyncio
        loop = asyncio.get_event_loop()

        loop.run_until_complete(
            storage_service.download_file(s3_key, file_path)
        )

        self.update_state(state="PROCESSING", meta={"progress": 30})
        logger.info("file_downloaded", document_id=document_id)

        # Process document
        document_service = DocumentService()

        result = loop.run_until_complete(
            document_service.process_document(
                document_id=document_id,
                file_path=file_path,
                content_type=content_type,
                user_id=user_id,
                document_name=document_name
            )
        )

        self.update_state(state="PROCESSING", meta={"progress": 90})

        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

        logger.info(
            "processing_task_complete",
            task_id=self.request.id,
            document_id=document_id
        )

        return {
            "status": "success",
            "document_id": document_id,
            **result
        }

    except Exception as e:
        logger.error(
            "processing_task_failed",
            task_id=self.request.id,
            document_id=document_id,
            error=str(e)
        )

        # Cleanup on error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e)
        }


@celery_app.task(name="delete_document_vectors")
def delete_document_vectors_task(document_id: str):
    """
    Background task to delete document vectors.

    Args:
        document_id: Document ID

    Returns:
        Deletion result
    """
    try:
        logger.info("deletion_task_started", document_id=document_id)

        document_service = DocumentService()

        import asyncio
        loop = asyncio.get_event_loop()

        success = loop.run_until_complete(
            document_service.delete_document_vectors(document_id)
        )

        logger.info("deletion_task_complete", document_id=document_id)

        return {"status": "success" if success else "failed", "document_id": document_id}

    except Exception as e:
        logger.error("deletion_task_failed", document_id=document_id, error=str(e))
        return {"status": "failed", "document_id": document_id, "error": str(e)}


# Periodic tasks (optional)
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks."""
    # Example: Cleanup old data every day
    # sender.add_periodic_task(86400.0, cleanup_old_data.s(), name='cleanup daily')
    pass


@celery_app.task(name="cleanup_old_data")
def cleanup_old_data():
    """Periodic task to cleanup old data."""
    logger.info("cleanup_task_started")
    # Implement cleanup logic
    logger.info("cleanup_task_complete")
    return {"status": "success"}
