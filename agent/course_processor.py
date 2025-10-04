"""
Course processing agent with MCP browser automation.
Handles full course content extraction pipeline.
"""
import os
import asyncio
import base64
from typing import Optional, Dict, Any
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.tools.browser_client import browser_session, BrowserClient
from playwright.async_api import async_playwright, Page, Browser
from strands import Agent

app = BedrockAgentCoreApp()

# AWS region for browser session
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Global session storage (in production, use Redis/DynamoDB)
active_sessions: Dict[str, Dict[str, Any]] = {}


class CourseProcessorAgent:
    """Agent for processing course content with MCP browser automation."""

    def __init__(self, region: str = AWS_REGION):
        self.region = region
        self.agent = Agent(
            model_provider="bedrock",
            model_name="anthropic.claude-3-5-sonnet-20241022-v2:0"
        )

    async def open_browser_session(self, course_url: str) -> Dict[str, Any]:
        """
        Open MCP browser session and navigate to course URL.

        Args:
            course_url: URL of the course to open

        Returns:
            Session information with status awaiting_login
        """
        try:
            # Create browser session using MCP
            client = BrowserClient(region=self.region)
            client.start()

            # Get WebSocket connection details
            ws_url, headers = client.generate_ws_headers()

            # Launch Playwright and connect to MCP browser
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

            # Navigate to course URL
            await page.goto(course_url, wait_until="networkidle")
            page_title = await page.title()

            # Store session info
            session_id = client.session_id
            active_sessions[session_id] = {
                "client": client,
                "browser": browser,
                "page": page,
                "playwright": playwright,
                "ws_url": ws_url,
                "headers": headers,
                "course_url": course_url
            }

            return {
                "status": "awaiting_login",
                "session_id": session_id,
                "message": f"Browser opened at {course_url}. Please log in manually.",
                "course_url": course_url,
                "page_title": page_title,
                "ws_url": ws_url
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to open browser: {str(e)}"
            }

    async def scrape_course_content(self, session_id: str) -> Dict[str, Any]:
        """
        Scrape course content after user has logged in.

        Args:
            session_id: Browser session ID

        Returns:
            Scraped course content
        """
        try:
            if session_id not in active_sessions:
                return {
                    "status": "error",
                    "message": "Session not found or expired"
                }

            session = active_sessions[session_id]
            page: Page = session["page"]

            # Wait for any post-login redirects
            await asyncio.sleep(2)
            await page.wait_for_load_state("networkidle")

            # Extract page title
            title = await page.title()

            # Extract main text content
            text_content = await page.evaluate("""
                () => {
                    // Remove script and style elements
                    const scripts = document.querySelectorAll('script, style');
                    scripts.forEach(el => el.remove());

                    // Get main content
                    const main = document.querySelector('main, article, .content, .course-content, #content');
                    return main ? main.innerText : document.body.innerText;
                }
            """)

            # Extract course structure (headings)
            sections = await page.evaluate("""
                () => {
                    const headings = Array.from(document.querySelectorAll('h1, h2, h3'));
                    return headings.map(h => ({
                        level: h.tagName.toLowerCase(),
                        text: h.textContent.trim()
                    })).filter(h => h.text.length > 0);
                }
            """)

            # Take full-page screenshot
            screenshot = await page.screenshot(full_page=True)
            screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')

            # Extract videos
            videos = await page.evaluate("""
                () => {
                    const videos = Array.from(document.querySelectorAll('video, iframe[src*="youtube"], iframe[src*="vimeo"]'));
                    return videos.map(v => ({
                        type: v.tagName.toLowerCase(),
                        src: v.src || v.querySelector('source')?.src,
                        title: v.title || v.getAttribute('aria-label') || 'Untitled'
                    })).filter(v => v.src);
                }
            """)

            # Extract downloadable files
            files = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href$=".pdf"], a[href$=".doc"], a[href$=".docx"], a[href$=".ppt"], a[href$=".pptx"]'));
                    return links.map(link => ({
                        url: link.href,
                        text: link.textContent.trim(),
                        type: link.href.split('.').pop()
                    }));
                }
            """)

            return {
                "status": "scraped",
                "course_url": session["course_url"],
                "title": title,
                "text_content": text_content[:10000],  # Limit to 10k chars
                "sections": sections[:20],  # Limit to 20 sections
                "screenshots": [screenshot_base64],
                "videos": videos,
                "files": files
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to scrape content: {str(e)}"
            }

    async def analyze_with_bedrock(self, scraped_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze scraped content using Bedrock AI.

        Args:
            scraped_content: Content scraped from course page

        Returns:
            AI analysis of course content
        """
        try:
            # Prepare analysis prompt
            analysis_prompt = f"""
Analyze the following course content and provide a structured summary:

Title: {scraped_content.get('title', 'Unknown')}

Content Preview:
{scraped_content.get('text_content', '')[:2000]}

Sections:
{scraped_content.get('sections', [])}

Please provide:
1. Course title
2. Brief summary (2-3 sentences)
3. Main topics covered (list)
4. Difficulty level (beginner/intermediate/advanced)
5. Estimated time to complete

Format as JSON.
"""

            # Run agent analysis
            result = self.agent(analysis_prompt)

            return {
                "status": "analyzed",
                "analysis": result.message,
                "course_url": scraped_content.get("course_url")
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to analyze content: {str(e)}"
            }

    async def close_session(self, session_id: str) -> Dict[str, Any]:
        """
        Close browser session and cleanup resources.

        Args:
            session_id: Browser session ID

        Returns:
            Status of cleanup
        """
        try:
            if session_id in active_sessions:
                session = active_sessions[session_id]

                # Close browser and cleanup
                if session.get("page"):
                    await session["page"].close()
                if session.get("browser"):
                    await session["browser"].close()
                if session.get("playwright"):
                    await session["playwright"].stop()
                if session.get("client"):
                    session["client"].stop()

                # Remove from active sessions
                del active_sessions[session_id]

                return {
                    "status": "closed",
                    "message": "Session closed successfully"
                }
            else:
                return {
                    "status": "not_found",
                    "message": "Session not found"
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to close session: {str(e)}"
            }


# Global processor instance
processor = CourseProcessorAgent()


@app.entrypoint
def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI agent entrypoint for course content processing.

    Supported actions:
    - open_browser: Open browser session and navigate to course URL
    - scrape_content: Scrape course content after login
    - analyze_content: Analyze scraped content with Bedrock
    - close_session: Close browser session
    - full_pipeline: Execute complete processing pipeline (manual login required)

    Args:
        payload: Dictionary containing:
            - action: Action to perform
            - course_url: URL of the course (for open_browser)
            - session_id: Session ID (for scrape/analyze/close)
            - scraped_content: Content to analyze (for analyze_content)

    Returns:
        Dictionary with processing result and status
    """
    try:
        action = payload.get("action", "chat")

        if action == "open_browser":
            course_url = payload.get("course_url")
            if not course_url:
                return {
                    "status": "error",
                    "result": "course_url is required"
                }

            result = asyncio.run(processor.open_browser_session(course_url))
            return result

        elif action == "scrape_content":
            session_id = payload.get("session_id")
            if not session_id:
                return {
                    "status": "error",
                    "result": "session_id is required"
                }

            result = asyncio.run(processor.scrape_course_content(session_id))
            return result

        elif action == "analyze_content":
            scraped_content = payload.get("scraped_content")
            if not scraped_content:
                return {
                    "status": "error",
                    "result": "scraped_content is required"
                }

            result = asyncio.run(processor.analyze_with_bedrock(scraped_content))
            return result

        elif action == "close_session":
            session_id = payload.get("session_id")
            if not session_id:
                return {
                    "status": "error",
                    "result": "session_id is required"
                }

            result = asyncio.run(processor.close_session(session_id))
            return result

        elif action == "chat":
            user_message = payload.get("prompt", "Hello!")
            result = processor.agent(user_message)
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
            "result": f"Error: {str(e)}",
            "status": "error"
        }


if __name__ == "__main__":
    app.run()
