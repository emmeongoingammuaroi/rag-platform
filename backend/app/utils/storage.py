"""S3-compatible object storage client (works with MinIO and AWS S3)."""

import logging
from io import BytesIO

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class ObjectStorage:
    """S3-compatible storage with lazy initialization.

    Works identically with MinIO (local) and AWS S3 (production).
    """

    def __init__(self) -> None:
        self._client: "boto3.client" | None = None  # type: ignore[type-arg]

    @property
    def client(self) -> "boto3.client":  # type: ignore[type-arg]
        """Get or create the S3 client (lazy init)."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
                config=BotoConfig(signature_version="s3v4"),
            )
            self._ensure_bucket()
        return self._client

    def _ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        except ClientError:
            logger.info(f"Creating bucket: {settings.S3_BUCKET_NAME}")
            self.client.create_bucket(Bucket=settings.S3_BUCKET_NAME)

    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload a file to object storage.

        Args:
            key: Object key (path within the bucket).
            data: File content as bytes.
            content_type: MIME type of the file.

        Returns:
            The object key (use for retrieval).
        """
        self.client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info(f"Uploaded {key} ({len(data)} bytes)")
        return key

    def download(self, key: str) -> bytes:
        """Download a file from object storage.

        Args:
            key: Object key.

        Returns:
            File content as bytes.

        Raises:
            FileNotFoundError: If the object does not exist.
        """
        try:
            response = self.client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
            return response["Body"].read()  # type: ignore[no-any-return]
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"Object not found: {key}") from e
            raise

    def delete(self, key: str) -> None:
        """Delete a file from object storage.

        Args:
            key: Object key to delete.
        """
        self.client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        logger.info(f"Deleted {key}")

    def exists(self, key: str) -> bool:
        """Check if an object exists.

        Args:
            key: Object key.

        Returns:
            True if the object exists.
        """
        try:
            self.client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
            return True
        except ClientError:
            return False

    def download_to_tempfile(self, key: str) -> BytesIO:
        """Download a file and return as an in-memory file-like object.

        Args:
            key: Object key.

        Returns:
            BytesIO with the file content.
        """
        data = self.download(key)
        buf = BytesIO(data)
        buf.seek(0)
        return buf


object_storage = ObjectStorage()
