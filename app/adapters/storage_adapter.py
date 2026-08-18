import os
import uuid

import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import AppException


class StorageAdapter:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        self.upload_dir = settings.LOCAL_STORAGE_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_file(self, file: UploadFile, subfolder: str = "general") -> str:
        """Validates and persists uploaded file safely, returning the URL / path."""
        # Validate file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        content = await file.read()
        if len(content) > max_bytes:
            raise AppException(
                code="FILE_TOO_LARGE",
                message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # Sanitize extension
        orig_name = file.filename or "upload.bin"
        ext = os.path.splitext(orig_name)[1].lower()
        allowed_exts = [".jpg", ".jpeg", ".png", ".webp", ".pdf", ".csv", ".xlsx"]
        if ext not in allowed_exts:
            raise AppException(code="DISALLOWED_FILE_EXTENSION", message=f"Extension '{ext}' is not permitted.")

        # Create unique file name
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_folder = os.path.join(self.upload_dir, subfolder)
        os.makedirs(target_folder, exist_ok=True)
        target_path = os.path.join(target_folder, unique_name)

        async with aiofiles.open(target_path, "wb") as f:
            await f.write(content)

        return f"/uploads/{subfolder}/{unique_name}"


LocalStorageAdapter = StorageAdapter
