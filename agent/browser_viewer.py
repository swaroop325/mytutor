"""
Browser viewer service that streams MCP browser screenshots to frontend.
Allows users to see and monitor the browser session in real-time.
"""
import os
import asyncio
import base64
from typing import Dict, Any, Optional
from bedrock_agentcore.tools.browser_client import BrowserClient
from playwright.async_api import async_playwright, Page
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Browser Viewer Service")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active browser sessions
active_sessions: Dict[str, Dict[str, Any]] = {}
# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


class BrowserViewer:
    """Manages browser sessions and streams screenshots to frontend."""

    def __init__(self, region: str = "us-east-1"):
        self.region = region

    async def create_session_with_streaming(
        self,
        session_id: str,
        course_url: str,
        websocket: WebSocket
    ):
        """
        Create MCP browser session and stream screenshots to frontend.

        Args:
            session_id: Unique session identifier
            course_url: URL to navigate to
            websocket: WebSocket connection for streaming
        """
        try:
            # Create MCP browser client
            client = BrowserClient(region=self.region)
            client.start()

            # Get WebSocket connection details
            ws_url, headers = client.generate_ws_headers()

            # Connect Playwright to MCP browser
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp(
                ws_url,
                headers=headers
            )

            # Get or create page
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                page = pages[0] if pages else await context.new_page()
            else:
                context = await browser.new_context()
                page = await context.new_page()

            # Navigate to URL
            await page.goto(course_url, wait_until="networkidle")

            # Store session
            active_sessions[session_id] = {
                "client": client,
                "browser": browser,
                "page": page,
                "playwright": playwright,
                "course_url": course_url,
                "streaming": True
            }

            # Send initial status
            await websocket.send_json({
                "type": "session_created",
                "session_id": session_id,
                "course_url": course_url,
                "page_title": await page.title()
            })

            # Start streaming screenshots
            await self.stream_screenshots(session_id, websocket)

        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to create session: {str(e)}"
            })
            await websocket.close()

    async def stream_screenshots(self, session_id: str, websocket: WebSocket):
        """
        Continuously capture and stream screenshots to frontend.

        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        try:
            session = active_sessions.get(session_id)
            if not session:
                return

            page: Page = session["page"]

            while session.get("streaming", False):
                try:
                    # Capture screenshot
                    screenshot = await page.screenshot()
                    screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')

                    # Get current URL and title
                    current_url = page.url
                    current_title = await page.title()

                    # Send screenshot to frontend
                    await websocket.send_json({
                        "type": "screenshot",
                        "session_id": session_id,
                        "screenshot": screenshot_base64,
                        "url": current_url,
                        "title": current_title,
                        "timestamp": asyncio.get_event_loop().time()
                    })

                    # Wait before next screenshot (2 screenshots per second)
                    await asyncio.sleep(0.5)

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Streaming error: {str(e)}"
                    })
                    break

        except Exception as e:
            print(f"Screenshot streaming failed: {e}")

    async def stop_streaming(self, session_id: str):
        """Stop streaming for a session."""
        if session_id in active_sessions:
            active_sessions[session_id]["streaming"] = False

    async def close_session(self, session_id: str):
        """Close browser session and cleanup."""
        if session_id in active_sessions:
            session = active_sessions[session_id]
            session["streaming"] = False

            # Cleanup
            if session.get("page"):
                await session["page"].close()
            if session.get("browser"):
                await session["browser"].close()
            if session.get("playwright"):
                await session["playwright"].stop()
            if session.get("client"):
                session["client"].stop()

            del active_sessions[session_id]


viewer = BrowserViewer()


@app.websocket("/ws/browser/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for browser streaming.

    Frontend connects to: ws://localhost:8081/ws/browser/{session_id}
    """
    await websocket.accept()
    active_connections[session_id] = websocket

    try:
        # Wait for initial message with course URL
        data = await websocket.receive_json()

        if data.get("action") == "start_session":
            course_url = data.get("course_url")
            if not course_url:
                await websocket.send_json({
                    "type": "error",
                    "message": "course_url is required"
                })
                return

            # Create session and start streaming
            await viewer.create_session_with_streaming(
                session_id,
                course_url,
                websocket
            )

        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "stop_streaming":
                await viewer.stop_streaming(session_id)
                await websocket.send_json({
                    "type": "streaming_stopped",
                    "session_id": session_id
                })

            elif data.get("action") == "close_session":
                await viewer.close_session(session_id)
                await websocket.send_json({
                    "type": "session_closed",
                    "session_id": session_id
                })
                break

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Cleanup
        if session_id in active_connections:
            del active_connections[session_id]
        await viewer.close_session(session_id)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "active_connections": len(active_connections)
    }


@app.get("/sessions")
async def list_sessions():
    """List active browser sessions."""
    return {
        "sessions": [
            {
                "session_id": sid,
                "course_url": session.get("course_url"),
                "streaming": session.get("streaming", False)
            }
            for sid, session in active_sessions.items()
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8081,
        log_level="info"
    )
