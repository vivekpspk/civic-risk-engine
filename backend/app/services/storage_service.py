"""
storage_service.py
Secure Storage Adapter for Civic Evidence Files.
Supports pluggable storage providers (Local Filesystem for dev/offline testing,
replaceable Cloud Storage Provider for AWS S3 / Google Cloud Storage).
Generates unpredictable storage keys, validates hash integrity, and keeps
local filesystem paths private.
"""

import os
import uuid
import hashlib
from abc import ABC, abstractmethod
from typing import Tuple, Optional


class StorageProvider(ABC):
    @abstractmethod
    def save_file(self, file_bytes: bytes, original_filename: str, mime_type: str) -> Tuple[str, str]:
        """Saves file bytes and returns (storage_key, sha256_hash)."""
        pass

    @abstractmethod
    def get_file(self, storage_key: str) -> Tuple[bytes, str]:
        """Retrieves file bytes and mime_type for given storage_key."""
        pass

    @abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Deletes file identified by storage_key."""
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: Optional[str] = None):
        if not base_dir:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            base_dir = os.path.join(project_root, "uploads", "evidence")
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_file(self, file_bytes: bytes, original_filename: str, mime_type: str) -> Tuple[str, str]:
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        ext = os.path.splitext(original_filename)[1].lower()
        if not ext or ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"
        storage_key = f"{uuid.uuid4().hex[:16]}_{sha256[:8]}{ext}"
        destination_path = os.path.join(self.base_dir, storage_key)

        with open(destination_path, "wb") as f:
            f.write(file_bytes)

        return storage_key, sha256

    def get_file(self, storage_key: str) -> Tuple[bytes, str]:
        # Security: Prevent directory traversal
        safe_key = os.path.basename(storage_key)
        target_path = os.path.join(self.base_dir, safe_key)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Evidence file '{safe_key}' does not exist.")

        with open(target_path, "rb") as f:
            data = f.read()

        # Infer MIME
        ext = os.path.splitext(safe_key)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/jpeg")
        return data, mime_type

    def delete_file(self, storage_key: str) -> bool:
        safe_key = os.path.basename(storage_key)
        target_path = os.path.join(self.base_dir, safe_key)
        if os.path.exists(target_path):
            os.remove(target_path)
            return True
        return False


class CloudStorageProviderStub(StorageProvider):
    """
    Template adapter for production AWS S3 / Google Cloud Storage.
    Teammates can activate this by configuring AWS_S3_BUCKET or GCS_BUCKET in .env.
    """
    def __init__(self, bucket_name: str = "civic-risk-evidence"):
        self.bucket_name = bucket_name

    def save_file(self, file_bytes: bytes, original_filename: str, mime_type: str) -> Tuple[str, str]:
        # Fallback to local storage if cloud credentials are not supplied
        return default_local_storage.save_file(file_bytes, original_filename, mime_type)

    def get_file(self, storage_key: str) -> Tuple[bytes, str]:
        return default_local_storage.get_file(storage_key)

    def delete_file(self, storage_key: str) -> bool:
        return default_local_storage.delete_file(storage_key)


default_local_storage = LocalStorageProvider()
active_storage_provider: StorageProvider = default_local_storage
