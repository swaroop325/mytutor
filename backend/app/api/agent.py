"""
Agent API endpoints - Only triggers AgentCore runtime.
All heavy processing happens in the agent.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.agent_client import agent_client
from app.core.security import decode_token


router = APIRouter()


class StartProcessingRequest(BaseModel):
    course_url: str


class StatusRequest(BaseModel):
    session_id: str


def get_current_user(token: str):
    """Decode JWT token and get user."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload.get("sub")


@router.post("/start-processing")
async def start_processing(request: StartProcessingRequest, token: str = Depends(get_current_user)):
    """
    Start course processing via AgentCore runtime.
    Backend only triggers the agent.
    """
    try:
        result = await agent_client.start_course_processing(
            course_url=request.course_url,
            user_id=token
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


@router.post("/stop")
async def stop_processing(request: StatusRequest):
    """Stop course processing."""
    try:
        result = await agent_client.stop_processing(request.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
