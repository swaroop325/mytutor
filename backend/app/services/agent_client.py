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

    async def continue_after_login(self, session_id: str) -> Dict[str, Any]:
        """
        Continue processing after user login.

        Args:
            session_id: Session ID

        Returns:
            Continuation confirmation
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "continue_after_login",
                        "session_id": session_id
                    }
                )
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to continue processing: {str(e)}"
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

    async def get_dcv_presigned_url(
        self,
        session_id: str,
        mcp_session_id: str
    ) -> Dict[str, Any]:
        """
        Get presigned URL for DCV live view.

        Args:
            session_id: Session ID
            mcp_session_id: MCP browser session ID

        Returns:
            Presigned URL and session info
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_dcv_url",
                        "session_id": session_id,
                        "mcp_session_id": mcp_session_id
                    }
                )
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get DCV URL: {str(e)}"
            }

    async def get_saved_courses(
        self,
        user_id: str,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all saved courses for a user.

        Args:
            user_id: User ID
            query: Optional search query for semantic search

        Returns:
            List of courses
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_saved_courses",
                        "user_id": user_id,
                        "query": query
                    }
                )
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get saved courses: {str(e)}",
                "courses": []
            }

    async def get_course_details(
        self,
        user_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information for a specific course.

        Args:
            user_id: User ID
            course_id: Course ID

        Returns:
            Course details with modules
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.agent_url}/invocations",
                    json={
                        "action": "get_course_details",
                        "user_id": user_id,
                        "course_id": course_id
                    }
                )
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get course details: {str(e)}"
            }


# Global agent client instance
agent_client = AgentClient()
