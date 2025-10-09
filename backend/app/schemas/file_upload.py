from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class FileCategory(str, Enum):
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


class FileStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class UploadedFileInfo(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    category: FileCategory
    status: FileStatus
    upload_path: str
    file_path: Optional[str] = None  # Full file path for easy access
    user_id: Optional[str] = None    # User who uploaded the file
    created_at: str
    processed_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    content_type: str
    category: FileCategory
    status: FileStatus
    upload_url: Optional[str] = None  # For direct upload to S3 if implemented
    message: str


class FileProcessingRequest(BaseModel):
    file_ids: List[str]
    user_id: str
    processing_options: Optional[Dict[str, Any]] = None


class FileProcessingResponse(BaseModel):
    session_id: str
    files: List[UploadedFileInfo]
    status: str
    message: str


class DirectLinkRequest(BaseModel):
    links: List[str] = Field(..., min_items=1, max_items=20)
    user_id: str


class DirectLinkResponse(BaseModel):
    session_id: str
    validated_links: List[Dict[str, Any]]
    invalid_links: List[Dict[str, str]]
    status: str
    message: str


class MixedContentRequest(BaseModel):
    course_url: Optional[str] = None
    file_ids: Optional[List[str]] = None
    direct_links: Optional[List[str]] = None
    user_id: str
    processing_options: Optional[Dict[str, Any]] = None


class MixedContentResponse(BaseModel):
    session_id: str
    content_sources: Dict[str, Any]
    status: str
    message: str


class FileValidationError(BaseModel):
    filename: str
    error_type: str
    error_message: str


class FileUploadBatchResponse(BaseModel):
    successful_uploads: List[FileUploadResponse]
    failed_uploads: List[FileValidationError]
    total_files: int
    successful_count: int
    failed_count: int