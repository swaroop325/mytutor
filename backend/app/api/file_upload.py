"""
File Upload API endpoints for handling file uploads and direct link processing.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Header
from typing import List, Optional
import uuid
from datetime import datetime

from app.core.security import decode_token
from app.services.file_upload_service import file_upload_service
from app.services.agent_client import agent_client
from app.services.link_validation_service import link_validation_service
from app.schemas.file_upload import (
    FileUploadResponse, FileUploadBatchResponse, FileProcessingRequest, 
    FileProcessingResponse, DirectLinkRequest, DirectLinkResponse,
    MixedContentRequest, MixedContentResponse, UploadedFileInfo
)


router = APIRouter()


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload.get("sub")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_single_file(
    file: UploadFile = File(...),
    authorization: str = Depends(get_current_user)
):
    """Upload a single file."""
    user_id = authorization
    
    try:
        file_info = await file_upload_service.save_file(file, user_id)

        return FileUploadResponse(
            file_id=file_info.id,
            filename=file_info.filename,
            file_size=file_info.file_size,
            content_type=file_info.content_type,
            category=file_info.category,
            status=file_info.status,
            message="File uploaded successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Upload error: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload-multiple", response_model=FileUploadBatchResponse)
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    authorization: str = Depends(get_current_user)
):
    """Upload multiple files."""
    user_id = authorization
    
    if len(files) > 10:  # Max 10 files per batch
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per upload")
    
    try:
        successful_uploads, failed_uploads = await file_upload_service.save_multiple_files(files, user_id)
        
        # Convert to response format
        successful_responses = [
            FileUploadResponse(
                file_id=file_info.id,
                filename=file_info.filename,
                file_size=file_info.file_size,
                content_type=file_info.content_type,
                category=file_info.category,
                status=file_info.status,
                message="File uploaded successfully"
            )
            for file_info in successful_uploads
        ]
        
        return FileUploadBatchResponse(
            successful_uploads=successful_responses,
            failed_uploads=failed_uploads,
            total_files=len(files),
            successful_count=len(successful_uploads),
            failed_count=len(failed_uploads)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")


@router.post("/process-files", response_model=FileProcessingResponse)
async def process_uploaded_files(
    request: FileProcessingRequest,
    authorization: str = Depends(get_current_user)
):
    """Process uploaded files through AgentCore."""
    user_id = authorization
    
    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Get file information
        files_info = []
        for file_id in request.file_ids:
            file_info = file_upload_service.get_file_info(file_id)
            if file_info:
                files_info.append(file_info)
        
        if not files_info:
            raise HTTPException(status_code=404, detail="No valid files found")
        
        # Get actual file paths for processing
        file_paths = []
        for file_id in request.file_ids:
            file_info = file_upload_service.get_file_info(file_id)
            if file_info and hasattr(file_info, 'upload_path'):
                file_paths.append(file_info.upload_path)
        
        if not file_paths:
            # Fallback: use mock file paths for demonstration
            file_paths = [f"/tmp/mock_file_{file_id}.txt" for file_id in request.file_ids]
        
        # Send to AgentCore for processing
        result = await agent_client.process_uploaded_files(
            file_paths=file_paths,
            user_id=user_id,
            processing_options=request.processing_options
        )
        
        return FileProcessingResponse(
            session_id=result.get("session_id", str(uuid.uuid4())),
            files=files_info,
            status=result.get("status", "processing"),
            message=result.get("message", "Files are being processed by AgentCore")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process-links", response_model=DirectLinkResponse)
async def process_direct_links(
    request: DirectLinkRequest,
    authorization: str = Depends(get_current_user)
):
    """Process direct resource links."""
    user_id = authorization
    
    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Validate links using the validation service
        validation_results = await link_validation_service.validate_multiple_links(request.links)
        
        validated_links = []
        invalid_links = []
        
        for result in validation_results["results"]:
            if result["valid"] and result["accessible"]:
                # Check security risk
                if result["security_risk"] == "high":
                    invalid_links.append({
                        "url": result["url"],
                        "error": f"High security risk: {', '.join(result['security_warnings'])}"
                    })
                else:
                    validated_links.append({
                        "url": result["url"],
                        "type": result["resource_type"],
                        "platform": result["platform"],
                        "file_type": result["file_type"],
                        "security_risk": result["security_risk"],
                        "metadata": result["metadata"],
                        "status": "valid"
                    })
            else:
                invalid_links.append({
                    "url": result["url"],
                    "error": result["error"] or "Link validation failed"
                })
        
        if not validated_links:
            raise HTTPException(status_code=400, detail="No valid and accessible links provided")
        
        # Send to AgentCore for processing
        result = await agent_client.process_direct_links(
            links=[link["url"] for link in validated_links],
            user_id=user_id,
            processing_options={
                "validation_results": validation_results,
                "link_metadata": {link["url"]: link for link in validated_links}
            }
        )
        
        return DirectLinkResponse(
            session_id=result.get("session_id", str(uuid.uuid4())),
            validated_links=validated_links,
            invalid_links=invalid_links,
            status=result.get("status", "processing"),
            message=f"Processing {len(validated_links)} valid links"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Link processing failed: {str(e)}")


@router.post("/process-mixed", response_model=MixedContentResponse)
async def process_mixed_content(
    request: MixedContentRequest,
    authorization: str = Depends(get_current_user)
):
    """Process mixed content (URL + files + links)."""
    user_id = authorization
    
    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        content_sources = {}
        
        # Process course URL
        if request.course_url:
            content_sources["course_url"] = {
                "url": request.course_url,
                "type": "web_course",
                "status": "pending"
            }
        
        # Process uploaded files
        if request.file_ids:
            files_info = []
            for file_id in request.file_ids:
                file_info = file_upload_service.get_file_info(file_id)
                if file_info:
                    files_info.append({
                        "file_id": file_id,
                        "filename": file_info.filename,
                        "category": file_info.category,
                        "status": "pending"
                    })
            content_sources["uploaded_files"] = files_info
        
        # Process direct links
        if request.direct_links:
            validated_links = []
            for link in request.direct_links:
                if link.startswith(('http://', 'https://')):
                    validated_links.append({
                        "url": link,
                        "type": "direct_link",
                        "status": "pending"
                    })
            content_sources["direct_links"] = validated_links
        
        if not content_sources:
            raise HTTPException(status_code=400, detail="No content sources provided")
        
        # Get actual file paths for processing
        file_paths = None
        if request.file_ids:
            file_paths = []
            for file_id in request.file_ids:
                file_info = file_upload_service.get_file_info(file_id)
                if file_info and hasattr(file_info, 'upload_path'):
                    file_paths.append(file_info.upload_path)
        
        # Send to AgentCore for processing
        result = await agent_client.process_mixed_content(
            course_url=request.course_url,
            file_paths=file_paths,
            direct_links=request.direct_links,
            user_id=user_id,
            processing_options=request.processing_options
        )
        
        return MixedContentResponse(
            session_id=result.get("session_id", str(uuid.uuid4())),
            content_sources=result.get("content_sources", content_sources),
            status=result.get("status", "processing"),
            message=result.get("message", "Processing mixed content sources")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mixed content processing failed: {str(e)}")


@router.get("/files")
async def get_user_files(authorization: str = Depends(get_current_user)):
    """Get all uploaded files for the current user."""
    user_id = authorization
    
    try:
        files = file_upload_service.get_user_files(user_id)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve files: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, authorization: str = Depends(get_current_user)):
    """Delete an uploaded file."""
    user_id = authorization
    
    try:
        success = file_upload_service.delete_file(file_id, user_id)
        if success:
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found or access denied")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.post("/validate-links")
async def validate_links(
    request: DirectLinkRequest,
    authorization: str = Depends(get_current_user)
):
    """Validate direct resource links without processing them."""
    user_id = authorization
    
    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Validate links using the validation service
        validation_results = await link_validation_service.validate_multiple_links(request.links)
        
        return {
            "validation_results": validation_results,
            "summary": {
                "total_links": validation_results["total_links"],
                "valid_links": validation_results["valid_links"],
                "accessible_links": validation_results["accessible_links"],
                "high_risk_links": validation_results["high_risk_links"],
                "platforms_detected": validation_results["summary"]["platforms"],
                "file_types_detected": validation_results["summary"]["file_types"],
                "security_summary": validation_results["summary"]["security_risks"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Link validation failed: {str(e)}")