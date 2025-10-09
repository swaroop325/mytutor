"""
Knowledge Base API endpoints for creating knowledge bases and training sessions.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional
from pydantic import BaseModel

from app.core.security import decode_token
from app.services.knowledge_base_service import knowledge_base_service, KnowledgeBase, TrainingSession


router = APIRouter()


class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    description: Optional[str] = None
    file_ids: List[str]


class StartTrainingRequest(BaseModel):
    knowledge_base_id: str
    question_types: Optional[List[str]] = None
    question_count: Optional[int] = None
    study_time: Optional[int] = None


class AnswerQuestionRequest(BaseModel):
    session_id: str
    answer: str
    question_type: Optional[str] = None


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload.get("sub")


@router.post("/create", response_model=KnowledgeBase)
async def create_knowledge_base(
    request: CreateKnowledgeBaseRequest,
    user_id: str = Depends(get_current_user)
):
    """Create a new knowledge base from uploaded files."""
    try:
        # Get actual file paths from file upload service
        from app.services.file_upload_service import file_upload_service
        
        file_paths = []
        for file_id in request.file_ids:
            file_info = file_upload_service.get_file_info(file_id)
            if file_info:
                file_paths.append(file_info.file_path)
            else:
                # Fallback: if file_id looks like a path, use it directly
                # Otherwise, try to infer from context or use a generic path
                if "/" in file_id or "\\" in file_id:
                    file_paths.append(file_id)
                else:
                    # For now, create a generic path - the categorization will be fixed
                    file_paths.append(f"/uploads/unknown/{file_id}")
        
        kb = await knowledge_base_service.create_knowledge_base(
            name=request.name,
            file_paths=file_paths,
            user_id=user_id,
            description=request.description
        )
        
        return kb
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create knowledge base: {str(e)}")


@router.get("/list")
async def list_knowledge_bases(user_id: str = Depends(get_current_user)):
    """List all knowledge bases for the current user."""
    try:
        knowledge_bases = knowledge_base_service.list_knowledge_bases(user_id)

        # Enrich with training_content_generated field for frontend filtering
        enriched_kbs = []
        for kb in knowledge_bases:
            kb_dict = kb.dict() if hasattr(kb, 'dict') else kb.__dict__
            kb_dict['training_content_generated'] = (
                kb.training_content is not None and
                kb.training_content.get("status") == "completed"
            )
            enriched_kbs.append(kb_dict)

        return {"knowledge_bases": enriched_kbs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge bases: {str(e)}")


@router.get("/{kb_id}")
async def get_knowledge_base(
    kb_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get a specific knowledge base by ID."""
    try:
        kb = knowledge_base_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        return kb
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge base: {str(e)}")


@router.get("/{kb_id}/status")
async def get_knowledge_base_status(
    kb_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get the processing status of a knowledge base."""
    try:
        kb = knowledge_base_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        return {
            "id": kb.id,
            "name": kb.name,
            "status": kb.status,
            "progress": {
                "total_files": kb.total_files,
                "processed_files": kb.processed_files,
                "percentage": int((kb.processed_files / kb.total_files * 100)) if kb.total_files > 0 else 0
            },
            "agents": [
                {
                    "type": agent.agent_type,
                    "status": agent.status,
                    "progress": agent.progress,
                    "files_processed": agent.files_processed,
                    "total_files": agent.total_files,
                    "error": agent.error_message
                }
                for agent in kb.agent_statuses
            ],
            "training_ready": kb.training_ready,
            "training_content_generated": kb.training_content is not None and kb.training_content.get("status") == "completed",
            "updated_at": kb.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/training/start", response_model=TrainingSession)
async def start_training_session(
    request: StartTrainingRequest,
    user_id: str = Depends(get_current_user)
):
    """Start a new training session for a knowledge base."""
    try:
        session = await knowledge_base_service.start_training_session(
            kb_id=request.knowledge_base_id,
            user_id=user_id
        )
        
        # Validate that the session has a valid current_question
        if not session.current_question:
            raise ValueError("Failed to generate initial question for training session")
        
        # Ensure all required fields are present and properly formatted
        question = session.current_question
        required_fields = ['question', 'options', 'correct_answer', 'explanation']
        for field in required_fields:
            if not question.get(field):
                raise ValueError(f"Invalid question structure: missing field '{field}'")
            
            # Ensure string fields are actually strings (not None)
            if field in ['question', 'explanation'] and not isinstance(question[field], str):
                raise ValueError(f"Invalid question structure: field '{field}' must be a string")
        
        return session
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start training session: {str(e)}")


@router.post("/training/answer")
async def answer_question(
    request: AnswerQuestionRequest,
    user_id: str = Depends(get_current_user)
):
    """Answer a question in a training session."""
    try:
        result = await knowledge_base_service.answer_question(
            session_id=request.session_id,
            answer=request.answer
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {str(e)}")


@router.get("/training/{session_id}")
async def get_training_session(
    session_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get a training session by ID."""
    try:
        session = knowledge_base_service.get_training_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Training session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training session: {str(e)}")


@router.post("/training/{session_id}/end")
async def end_training_session(
    session_id: str,
    user_id: str = Depends(get_current_user)
):
    """End a training session and get final results."""
    try:
        result = await knowledge_base_service.end_training_session(session_id)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end training session: {str(e)}")


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a knowledge base and all associated data."""
    try:
        result = await knowledge_base_service.delete_knowledge_base(kb_id, user_id)
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete knowledge base: {str(e)}")


@router.get("/training/history/user", response_model=List[TrainingSession])
async def get_user_training_history(
    user_id: str = Depends(get_current_user)
):
    """Get all training sessions for the current user."""
    try:
        sessions = knowledge_base_service.get_user_training_history(user_id)
        return sessions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training history: {str(e)}")


@router.get("/{kb_id}/training/history", response_model=List[TrainingSession])
async def get_knowledge_base_training_history(
    kb_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get all training sessions for a specific knowledge base."""
    try:
        # Verify user has access to this knowledge base
        kb = knowledge_base_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        sessions = knowledge_base_service.get_knowledge_base_training_history(kb_id)
        # Filter sessions for this user only
        user_sessions = [s for s in sessions if s.user_id == user_id]
        return user_sessions
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge base training history: {str(e)}")


class RecategorizeRequest(BaseModel):
    file_paths: List[str]


@router.post("/{kb_id}/recategorize")
async def recategorize_knowledge_base(
    kb_id: str,
    request: RecategorizeRequest,
    user_id: str = Depends(get_current_user)
):
    """Recategorize a knowledge base with correct file paths/types."""
    try:
        result = await knowledge_base_service.recategorize_knowledge_base(kb_id, request.file_paths)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to recategorize knowledge base: {str(e)}")


@router.post("/{kb_id}/generate-training")
async def generate_training_content_manual(
    kb_id: str,
    user_id: str = Depends(get_current_user)
):
    """Manually trigger training content generation for a knowledge base."""
    try:
        kb = knowledge_base_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # Note: Knowledge bases are not user-specific in current model
        # In production, you might want to add user_id to KnowledgeBase model
        
        # Trigger training content generation with retry logic
        await knowledge_base_service._generate_training_content(kb_id, user_id)
        
        # Return updated knowledge base
        updated_kb = knowledge_base_service.get_knowledge_base(kb_id)
        return updated_kb
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate training content: {str(e)}")

@router.get("/{kb_id}/learning-content")
async def get_learning_content(
    kb_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get learning content for studying before assessment."""
    try:
        kb = knowledge_base_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        learning_content = await knowledge_base_service.get_learning_content(kb_id)
        return learning_content
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get learning content: {str(e)}")


@router.get("/{kb_id}/cleanup-status")
async def verify_kb_cleanup(
    kb_id: str,
    user_id: str = Depends(get_current_user)
):
    """Verify that a knowledge base and its training sessions have been properly cleaned up."""
    try:
        result = knowledge_base_service.verify_kb_cleanup(kb_id)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify cleanup: {str(e)}")


@router.post("/{kb_id}/cleanup-files")
async def cleanup_kb_files(
    kb_id: str,
    user_id: str = Depends(get_current_user)
):
    """Manually clean up uploaded files for a completed knowledge base."""
    try:
        await knowledge_base_service._cleanup_uploaded_files(kb_id, user_id)
        return {
            "status": "success",
            "message": f"Files cleaned up for knowledge base {kb_id}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup files: {str(e)}")