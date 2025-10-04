from typing import Optional
import httpx


class AgentCoreService:
    """
    Service for integrating with AgentCore MCP (Model Context Protocol).
    AgentCore provides browser automation capabilities.
    """

    def __init__(self, mcp_server_url: Optional[str] = None):
        self.mcp_server_url = mcp_server_url or "http://localhost:3000"
        self.client = httpx.AsyncClient()

    async def connect_mcp(self) -> dict:
        """Connect to AgentCore MCP server"""
        try:
            response = await self.client.post(
                f"{self.mcp_server_url}/mcp/connect",
                json={"client_id": "mytutor"}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    async def create_browser_tool(self, config: dict) -> dict:
        """Create a browser automation tool via MCP"""
        try:
            response = await self.client.post(
                f"{self.mcp_server_url}/mcp/tools/browser",
                json=config
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def execute_browser_action(
        self,
        action: str,
        parameters: dict
    ) -> dict:
        """
        Execute browser actions through AgentCore MCP.

        Actions can include:
        - navigate: Go to a URL
        - click: Click an element
        - type: Type text
        - screenshot: Take a screenshot
        - extract: Extract content
        """
        try:
            response = await self.client.post(
                f"{self.mcp_server_url}/mcp/execute",
                json={
                    "tool": "browser",
                    "action": action,
                    "parameters": parameters
                }
            )
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    async def browse_course_with_mcp(
        self,
        course_url: str,
        login_required: bool = False
    ) -> dict:
        """
        Use AgentCore MCP to browse and extract course content.
        """
        results = {
            "url": course_url,
            "login_required": login_required,
            "actions": [],
            "content": None
        }

        # Navigate to course
        nav_result = await self.execute_browser_action(
            "navigate",
            {"url": course_url}
        )
        results["actions"].append(nav_result)

        if login_required:
            # Wait for user to login manually
            results["actions"].append({
                "action": "wait_for_login",
                "message": "Please log in to the course platform"
            })

        # Extract course content
        extract_result = await self.execute_browser_action(
            "extract",
            {
                "selectors": [
                    "h1, h2, h3",  # Headings
                    ".course-content",  # Course content
                    ".lesson",  # Lessons
                    ".module"  # Modules
                ]
            }
        )
        results["content"] = extract_result

        # Take screenshot
        screenshot_result = await self.execute_browser_action(
            "screenshot",
            {"full_page": True}
        )
        results["screenshot"] = screenshot_result

        return results

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


agentcore_service = AgentCoreService()
