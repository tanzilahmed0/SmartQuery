import logging
import os
from datetime import timedelta
from typing import Any, Dict, Optional

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class StorageService:
    """MinIO storage service for file operations"""

    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minio_admin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minio_dev_password123")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "smartquery-files")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.client = None

    def connect(self) -> bool:
        """Establish MinIO connection"""
        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )

            # Test connection by checking if bucket exists
            bucket_exists = self.client.bucket_exists(self.bucket_name)
            if not bucket_exists:
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")

            logger.info("MinIO connection established successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {str(e)}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Check MinIO health"""
        try:
            if not self.client:
                self.connect()

            # Check bucket existence and get basic info
            bucket_exists = self.client.bucket_exists(self.bucket_name)

            # Count objects in bucket (for basic stats)
            objects = list(self.client.list_objects(self.bucket_name, recursive=True))
            object_count = len(objects)

            return {
                "status": "healthy",
                "endpoint": self.endpoint,
                "bucket_name": self.bucket_name,
                "bucket_exists": bucket_exists,
                "object_count": object_count,
            }

        except Exception as e:
            logger.error(f"MinIO health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}

    def get_client(self):
        """Get MinIO client"""
        if not self.client:
            self.connect()
        return self.client

    def generate_presigned_url(
        self, object_name: str, expiry_seconds: int = 3600
    ) -> Optional[str]:
        """Generate presigned URL for file upload"""
        try:
            client = self.get_client()
            url = client.presigned_put_object(
                self.bucket_name, object_name, expires=timedelta(seconds=expiry_seconds)
            )
            return url
        except Exception as e:
            logger.error(
                f"Failed to generate presigned URL for {object_name}: {str(e)}"
            )
            return None

    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in storage"""
        try:
            client = self.get_client()
            client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False
        except Exception as e:
            logger.error(f"Error checking file existence for {object_name}: {str(e)}")
            return False


# Global storage service instance
storage_service = StorageService()
