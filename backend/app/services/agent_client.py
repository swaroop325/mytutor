"""
Agent client service for communicating with AgentCore runtime.
Backend only triggers the agent and receives status updates.
"""
import httpx
from typing import Dict, Any, Optional


class AgentClient:
    """Client for communicating with AgentCore runtime."""

    def __init__(self, agent_url: str = "http://localhost:8080"):
        self.agent_url = agent_url
        self.timeout = 30.0

    async def start_course_processing(
        self,
        course_url: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Trigger agent to start course processing.

        Args:
            course_url: URL of the course
            user_id: User ID for tracking

        Returns:
            Agent response with session info
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "start_course_processing",
                        "course_url": course_url,
                        "user_id": user_id
                    }
                )
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to connect to agent: {str(e)}"
            }

    async def get_processing_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current status of course processing.

        Args:
            session_id: Session ID

        Returns:
            Current processing status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_status",
                        "session_id": session_id
                    }
                )
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get status: {str(e)}"
            }

    async def stop_processing(self, session_id: str) -> Dict[str, Any]:
        """
        Stop course processing.

        Args:
            session_id: Session ID

        Returns:
            Stop confirmation
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "stop_processing",
                        "session_id": session_id
                    }
                )
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to stop processing: {str(e)}"
            }


# Global agent client instance
agent_client = AgentClient()
