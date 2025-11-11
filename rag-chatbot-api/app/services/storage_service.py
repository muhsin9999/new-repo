"""
S3 storage service for document management.
"""
import os
from typing import Optional
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from app.core.exceptions import StorageError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """Service for S3 storage operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    async def upload_file(
        self,
        file_path: str,
        object_key: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to S3.

        Args:
            file_path: Local path to the file
            object_key: S3 object key (optional, will generate if not provided)
            metadata: Optional metadata to attach to the object

        Returns:
            S3 object key

        Raises:
            StorageError: If upload fails
        """
        try:
            if not object_key:
                file_name = os.path.basename(file_path)
                object_key = f"documents/{uuid4()}/{file_name}"

            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata

            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )

            logger.info(
                "file_uploaded_to_s3",
                object_key=object_key,
                bucket=self.bucket_name
            )

            return object_key

        except ClientError as e:
            logger.error("s3_upload_failed", error=str(e), file_path=file_path)
            raise StorageError(f"Failed to upload file to S3: {str(e)}")

    async def download_file(self, object_key: str, download_path: str) -> str:
        """
        Download a file from S3.

        Args:
            object_key: S3 object key
            download_path: Local path to save the file

        Returns:
            Local file path

        Raises:
            StorageError: If download fails
        """
        try:
            os.makedirs(os.path.dirname(download_path), exist_ok=True)

            self.s3_client.download_file(
                self.bucket_name,
                object_key,
                download_path
            )

            logger.info(
                "file_downloaded_from_s3",
                object_key=object_key,
                download_path=download_path
            )

            return download_path

        except ClientError as e:
            logger.error("s3_download_failed", error=str(e), object_key=object_key)
            raise StorageError(f"Failed to download file from S3: {str(e)}")

    async def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            object_key: S3 object key

        Returns:
            True if successful

        Raises:
            StorageError: If deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )

            logger.info("file_deleted_from_s3", object_key=object_key)
            return True

        except ClientError as e:
            logger.error("s3_delete_failed", error=str(e), object_key=object_key)
            raise StorageError(f"Failed to delete file from S3: {str(e)}")

    async def get_presigned_url(
        self,
        object_key: str,
        expiration: int = None
    ) -> str:
        """
        Generate a presigned URL for temporary access to an object.

        Args:
            object_key: S3 object key
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL

        Raises:
            StorageError: If URL generation fails
        """
        try:
            expiration = expiration or settings.S3_PRESIGNED_URL_EXPIRATION

            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration
            )

            logger.info("presigned_url_generated", object_key=object_key)
            return url

        except ClientError as e:
            logger.error("presigned_url_generation_failed", error=str(e))
            raise StorageError(f"Failed to generate presigned URL: {str(e)}")

    async def list_files(self, prefix: str = "") -> list:
        """
        List files in S3 bucket.

        Args:
            prefix: Optional prefix to filter files

        Returns:
            List of file objects

        Raises:
            StorageError: If listing fails
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            files = response.get("Contents", [])
            logger.info("files_listed", count=len(files), prefix=prefix)

            return files

        except ClientError as e:
            logger.error("s3_list_failed", error=str(e))
            raise StorageError(f"Failed to list files from S3: {str(e)}")

    def check_bucket_exists(self) -> bool:
        """
        Check if the configured S3 bucket exists.

        Returns:
            True if bucket exists
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False
