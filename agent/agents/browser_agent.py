import os
import asyncio
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.tools.browser_client import browser_session
from strands import Agent
from playwright.async_api import async_playwright

app = BedrockAgentCoreApp()

# AWS region for browser session
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize Strands agent with Bedrock
agent = Agent(
    model_provider="bedrock",
    model_name="anthropic.claude-3-5-sonnet-20241022-v2:0"
)

async def open_browser_and_wait_for_login(course_url: str, region: str = AWS_REGION):
    """
    Open browser using MCP, navigate to course URL, and wait for user login.

    Args:
        course_url: URL of the course to open
        region: AWS region for browser session

    Returns:
        Dictionary with session info and status
    """
    try:
        with browser_session(region) as client:
            # Get WebSocket connection details
            ws_url, headers = client.generate_ws_headers()

            # Launch Playwright and connect to MCP browser session
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp(
                ws_url,
                headers=headers
            )

            # Get default context and page
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                if pages:
                    page = pages[0]
                else:
                    page = await context.new_page()
            else:
                context = await browser.new_context()
                page = await context.new_page()

            # Navigate to course URL
            await page.goto(course_url)
            await page.wait_for_load_state('networkidle')

            return {
                "status": "awaiting_login",
                "session_id": client.session_id,
                "ws_url": ws_url,
                "message": f"Browser opened at {course_url}. Please log in manually.",
                "course_url": course_url,
                "page_title": await page.title()
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to open browser: {str(e)}"
        }

async def continue_after_login(session_id: str, course_url: str):
    """
    Continue processing after user has logged in.

    Args:
        session_id: Browser session ID
        course_url: URL of the course

    Returns:
        Dictionary with scraped content
    """
    try:
        # Reconnect to existing session and scrape content
        # Note: Session persistence would need to be managed
        return {
            "status": "processing",
            "message": "Continuing after login",
            "session_id": session_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to continue: {str(e)}"
        }

@app.entrypoint
def invoke(payload):
    """
    AI agent entrypoint for course content processing.

    Args:
        payload: Dictionary containing:
            - action: Action to perform (open_browser, continue_processing, etc.)
            - course_url: URL of the course (required for open_browser)
            - session_id: Session ID (required for continue_processing)
            - prompt: User message or instruction
            - context: Optional context data

    Returns:
        Dictionary with:
            - result: Agent response or processing result
            - status: Processing status
    """
    try:
        action = payload.get("action", "chat")

        if action == "open_browser":
            # Open browser and navigate to course URL
            course_url = payload.get("course_url")
            if not course_url:
                return {
                    "status": "error",
                    "result": "course_url is required for open_browser action"
                }

            result = asyncio.run(open_browser_and_wait_for_login(course_url))
            return result

        elif action == "continue_processing":
            # Continue after user login
            session_id = payload.get("session_id")
            course_url = payload.get("course_url")

            if not session_id or not course_url:
                return {
                    "status": "error",
                    "result": "session_id and course_url are required"
                }

            result = asyncio.run(continue_after_login(session_id, course_url))
            return result

        elif action == "chat":
            # Regular chat with agent
            user_message = payload.get("prompt", "Hello! How can I help you today?")
            result = agent(user_message)

            return {
                "result": result.message,
                "status": "success"
            }
        else:
            return {
                "status": "error",
                "result": f"Unknown action: {action}"
            }

    except Exception as e:
        return {
            "result": f"Error processing request: {str(e)}",
            "status": "error"
        }

if __name__ == "__main__":
    app.run()
