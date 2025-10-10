import os
import uuid
import hashlib
import mimetypes
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from fastapi import UploadFile, HTTPException
from app.schemas.file_upload import FileCategory, FileStatus, UploadedFileInfo, FileValidationError


class FileUploadService:
    """Service for handling file uploads, validation, and storage."""
    
    # Supported file types and their categories
    SUPPORTED_TYPES = {
        'application/pdf': FileCategory.DOCUMENT,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileCategory.DOCUMENT,
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': FileCategory.DOCUMENT,
        'application/msword': FileCategory.DOCUMENT,
        'application/vnd.ms-powerpoint': FileCategory.DOCUMENT,
        'video/mp4': FileCategory.VIDEO,
        'video/avi': FileCategory.VIDEO,
        'video/mov': FileCategory.VIDEO,
        'video/quicktime': FileCategory.VIDEO,
        'video/x-msvideo': FileCategory.VIDEO,
        'audio/mp3': FileCategory.AUDIO,
        'audio/mpeg': FileCategory.AUDIO,
        'audio/wav': FileCategory.AUDIO,
        'audio/x-wav': FileCategory.AUDIO,
        'audio/m4a': FileCategory.AUDIO,
        'audio/mp4': FileCategory.AUDIO,
        'image/jpeg': FileCategory.IMAGE,
        'image/jpg': FileCategory.IMAGE,
        'image/png': FileCategory.IMAGE,
        'image/gif': FileCategory.IMAGE,
        'image/webp': FileCategory.IMAGE,
    }
    
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB per file
    MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2GB total
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for each category
        for category in FileCategory:
            (self.upload_dir / category.value).mkdir(exist_ok=True)
        
        # File registry for tracking uploaded files
        self.registry_file = Path("data/file_registry.json")
        self.registry_file.parent.mkdir(exist_ok=True)
        self._file_registry = self._load_file_registry()
    
    def validate_file(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """Validate uploaded file."""
        
        # Check file type
        if file.content_type not in self.SUPPORTED_TYPES:
            return False, f"Unsupported file type: {file.content_type}"
        
        # Check file size
        if hasattr(file, 'size') and file.size and file.size > self.MAX_FILE_SIZE:
            return False, f"File size exceeds {self.MAX_FILE_SIZE / (1024*1024):.0f}MB limit"
        
        # Check filename
        if not file.filename or len(file.filename) > 255:
            return False, "Invalid filename"
        
        return True, None
    
    def scan_for_malware(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Basic malware scanning (placeholder implementation)."""
        # In production, integrate with actual malware scanning service
        # For now, just check file extensions and basic patterns
        
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']
        if any(file_path.name.lower().endswith(ext) for ext in suspicious_extensions):
            return False, "Potentially malicious file type detected"
        
        return True, None
    
    def generate_safe_filename(self, original_filename: str, category: FileCategory) -> str:
        """Generate a safe, unique filename."""
        # Extract extension
        name, ext = os.path.splitext(original_filename)
        
        # Generate unique identifier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        # Create safe filename
        safe_name = f"{timestamp}_{unique_id}{ext}"
        return safe_name
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def save_file(self, file: UploadFile, user_id: str) -> UploadedFileInfo:
        """Save uploaded file to disk."""
        
        # Validate file
        is_valid, error_msg = self.validate_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Get file category
        category = self.SUPPORTED_TYPES[file.content_type]
        
        # Generate safe filename
        safe_filename = self.generate_safe_filename(file.filename, category)
        
        # Create file path
        file_path = self.upload_dir / category.value / safe_filename
        
        # Save file
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Reset file pointer for potential reuse
            await file.seek(0)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
        # Scan for malware
        is_safe, scan_error = self.scan_for_malware(file_path)
        if not is_safe:
            # Delete the file
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=scan_error)
        
        # Calculate file hash
        file_hash = self.calculate_file_hash(file_path)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Create file info
        file_info = UploadedFileInfo(
            id=str(uuid.uuid4()),
            filename=safe_filename,
            original_filename=file.filename,
            file_size=file_size,
            content_type=file.content_type,
            category=category,
            status=FileStatus.COMPLETED,
            upload_path=str(file_path),
            file_path=str(file_path),  # Add file_path for easy access
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            metadata={
                "user_id": user_id,
                "file_hash": file_hash,
                "upload_method": "direct"
            }
        )
        
        # Register file in registry
        self._register_file(file_info)
        
        logger.info(f"✅ File uploaded and registered: {safe_filename} ({category.value})")
        
        return file_info
    
    async def save_multiple_files(self, files: List[UploadFile], user_id: str) -> Tuple[List[UploadedFileInfo], List[FileValidationError]]:
        """Save multiple files and return results."""
        
        successful_uploads = []
        failed_uploads = []
        total_size = 0
        
        # Pre-validate total size
        for file in files:
            if hasattr(file, 'size') and file.size:
                total_size += file.size
        
        if total_size > self.MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"Total file size exceeds {self.MAX_TOTAL_SIZE / (1024*1024):.0f}MB limit"
            )
        
        # Process each file
        for file in files:
            try:
                file_info = await self.save_file(file, user_id)
                successful_uploads.append(file_info)
            except HTTPException as e:
                failed_uploads.append(FileValidationError(
                    filename=file.filename or "unknown",
                    error_type="validation_error",
                    error_message=e.detail
                ))
            except Exception as e:
                failed_uploads.append(FileValidationError(
                    filename=file.filename or "unknown",
                    error_type="system_error",
                    error_message=str(e)
                ))
        
        return successful_uploads, failed_uploads
    
    def get_file_info(self, file_id: str) -> Optional[UploadedFileInfo]:
        """Get file information by ID."""
        return self._file_registry.get(file_id)
    
    def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete a file by ID."""
        try:
            file_info = self._file_registry.get(file_id)
            if not file_info:
                return False
            
            # Verify user owns the file
            if file_info.user_id != user_id:
                return False
            
            # Delete physical file
            file_path = Path(file_info.file_path or file_info.upload_path)
            if file_path.exists():
                file_path.unlink()
            
            # Remove from registry
            del self._file_registry[file_id]
            self._save_file_registry()
            
            logger.info(f"✅ File deleted: {file_info.filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting file {file_id}: {e}")
            return False
    
    def get_user_files(self, user_id: str) -> List[UploadedFileInfo]:
        """Get all files for a user."""
        return [file_info for file_info in self._file_registry.values() if file_info.user_id == user_id]
    
    def _load_file_registry(self) -> Dict[str, UploadedFileInfo]:
        """Load file registry from disk."""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    registry = {}
                    for file_id, file_data in data.items():
                        registry[file_id] = UploadedFileInfo(**file_data)
                    return registry
            return {}
        except Exception as e:
            logger.warning(f"⚠️ Error loading file registry: {e}")
            return {}
    
    def _save_file_registry(self):
        """Save file registry to disk."""
        try:
            data = {}
            for file_id, file_info in self._file_registry.items():
                data[file_id] = file_info.dict()
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Error saving file registry: {e}")
    
    def _register_file(self, file_info: UploadedFileInfo):
        """Register a file in the registry."""
        self._file_registry[file_info.id] = file_info
        self._save_file_registry()


# Global instance
file_upload_service = FileUploadService()