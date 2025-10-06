"""
Agent API endpoints - Only triggers AgentCore runtime.
All heavy processing happens in the agent.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from app.services.agent_client import agent_client
from app.core.security import decode_token
from typing import Optional


router = APIRouter()


class StartProcessingRequest(BaseModel):
    course_url: str


class StatusRequest(BaseModel):
    session_id: str


class DCVUrlRequest(BaseModel):
    session_id: str
    mcp_session_id: str


class SearchCoursesRequest(BaseModel):
    query: Optional[str] = None


class CourseDetailsRequest(BaseModel):
    course_id: str


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Decode JWT token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload.get("sub")


@router.post("/start-processing")
async def start_processing(request: StartProcessingRequest, user_id: str = Depends(get_current_user)):
    """
    Start course processing via AgentCore runtime.
    Backend only triggers the agent.
    """
    try:
        result = await agent_client.start_course_processing(
            course_url=request.course_url,
            user_id=user_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status")
async def get_status(request: StatusRequest):
    """Get current processing status from agent."""
    try:
        result = await agent_client.get_processing_status(request.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/continue-processing")
async def continue_processing(request: StatusRequest, user_id: str = Depends(get_current_user)):
    """Continue course processing after user login."""
    try:
        result = await agent_client.continue_after_login(request.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-processing")
async def stop_processing(request: StatusRequest):
    """Stop course processing."""
    try:
        result = await agent_client.stop_processing(request.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-dcv-url")
async def get_dcv_url(request: DCVUrlRequest, user_id: str = Depends(get_current_user)):
    """Get presigned DCV URL for live browser viewing."""
    try:
        result = await agent_client.get_dcv_presigned_url(
            session_id=request.session_id,
            mcp_session_id=request.mcp_session_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses")
async def get_courses(user_id: str = Depends(get_current_user)):
    """Get all saved courses for the authenticated user."""
    try:
        result = await agent_client.get_saved_courses(user_id=user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/search")
async def search_courses(request: SearchCoursesRequest, user_id: str = Depends(get_current_user)):
    """Search courses using semantic search."""
    try:
        result = await agent_client.get_saved_courses(
            user_id=user_id,
            query=request.query
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/details")
async def get_course_details(request: CourseDetailsRequest, user_id: str = Depends(get_current_user)):
    """Get detailed information for a specific course."""
    try:
        result = await agent_client.get_course_details(
            user_id=user_id,
            course_id=request.course_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
