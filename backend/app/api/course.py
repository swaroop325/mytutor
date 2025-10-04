from fastapi import APIRouter

router = APIRouter()

# All course processing is now handled by AgentCore Runtime (port 8080)
# Backend only handles authentication and triggers the agent
# See /api/v1/agent/* endpoints for AgentCore integration

@router.get("/health")
async def health_check():
    """Health check endpoint for course service"""
    return {
        "status": "healthy",
        "message": "Course processing handled by AgentCore Runtime on port 8080"
    }
