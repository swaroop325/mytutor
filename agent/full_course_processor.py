"""
Full course processor with module-by-module navigation.
Handles complete course extraction including text, audio, video.
Uses local file-based knowledge base storage (no AgentCore Memory throttling).
Supports YouTube video analysis via browser automation.
"""
import os
import asyncio
import base64
import json
import re
import threading
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from bedrock_agentcore import BedrockAgentCoreApp

# Configure logging
logger = logging.getLogger(__name__)
from bedrock_agentcore.tools.browser_client import BrowserClient

# Import local KB storage instead of AgentCore Memory
from services.local_kb_storage import local_kb_storage

# Import training service for assessment generation
try:
    from services.training_service import training_service
except ImportError:
    logger.warning("Training service not available")
    training_service = None
from playwright.async_api import async_playwright, Page, Browser, Download
from strands import Agent
import boto3
from pathlib import Path
from datetime import datetime, timedelta
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import urllib.parse
from file_processor import file_processor

# Initialize app
app = BedrockAgentCoreApp()

# CORS configuration for frontend communication
os.environ.setdefault("ALLOW_ORIGINS", "http://localhost:5173,http://localhost:3000")
os.environ.setdefault("ALLOW_CREDENTIALS", "true")
os.environ.setdefault("ALLOW_METHODS", "*")
os.environ.setdefault("ALLOW_HEADERS", "*")

logger.info("Configuring CORS for frontend access")

# Alternative approach: directly modify response headers in the invoke handler
# This will be handled at the end of the file

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
# Use inference profile instead of direct model ID
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")

# Storage for active sessions
active_sessions: Dict[str, Dict[str, Any]] = {}


class CourseModule:
    """Represents a single course module."""
    def __init__(self, title: str, url: str, order: int):
        self.title = title
        self.url = url
        self.order = order
        self.text_content = ""
        self.videos = []
        self.audios = []
        self.files = []
        self.screenshots = []
        self.completed = False


class FullCourseProcessor:
    """Complete course processor with local KB storage integration."""

    def __init__(self, region: str = AWS_REGION):
        self.region = region
        # Initialize Strands agent (will use default Bedrock configuration)
        self.agent = Agent()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)

        # Use local KB storage instead of AgentCore Memory
        self.kb_storage = local_kb_storage
        logger.info("FullCourseProcessor initialized with local KB storage")

    def _chunk_content_for_memory(self, content: str, max_size: int = 8000) -> List[str]:
        """Split content into chunks that preserve context and fit within memory limits."""
        if len(content) <= max_size:
            return [content]

        # Split on natural boundaries (paragraphs, sections)
        chunks = []
        paragraphs = content.split('\n\n')
        current_chunk = ""
        overlap_size = 150  # Characters to overlap for context

        for paragraph in paragraphs:
            # Handle very long paragraphs that exceed max_size
            if len(paragraph) > max_size:
                # First, save any accumulated content
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # Split the long paragraph into smaller chunks
                for i in range(0, len(paragraph), max_size - 50):
                    chunk_part = paragraph[i:i + max_size]
                    if i > 0:
                        chunk_part = "[...continued] " + chunk_part
                    chunks.append(chunk_part)
                continue

            if len(current_chunk + paragraph) > max_size and current_chunk:
                # Add overlap from previous chunk for context
                if chunks and len(current_chunk) > overlap_size:
                    context_overlap = f"[...continued from previous section]\n\n"
                    chunks.append(current_chunk)
                    current_chunk = context_overlap + paragraph
                else:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += f"\n\n{paragraph}"
                else:
                    current_chunk = paragraph

        if current_chunk:
            chunks.append(current_chunk)

        logger.info(f"Split content into {len(chunks)} contextual chunks to preserve all information")
        return chunks
    
    def _save_module_to_memory(self, user_id: str, course_id: str, module: CourseModule):
        """No-op: Module saving deprecated in favor of local KB storage."""
        pass

    def _save_summary_to_memory(self, user_id: str, course_id: str, summary: Dict[str, Any]):
        """No-op: Summary saving deprecated in favor of local KB storage."""
        pass

    async def start_course_processing(
        self,
        session_id: str,
        course_url: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Start full course processing pipeline.

        Steps:
        1. Check if YouTube URL -> use specialized YouTube processing
        2. Create MCP browser session
        3. Navigate to course URL
        4. Wait for user login (if needed)
        5. Discover all modules (or analyze YouTube video)
        6. Process each module
        7. Create comprehensive summary
        """
        # Check if YouTube URL
        is_youtube = self._is_youtube_url(course_url)
        if is_youtube:
            logger.info("Detected YouTube URL, using browser-based analysis")

        client = None
        browser = None
        playwright = None

        try:
            # Create MCP browser session with retry logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    client = BrowserClient(region=self.region)
                    client.start(
                        identifier="mytutor_browser_use_tool-NxSRbIljN1"
                    )
                    break
                except Exception as e:
                    if "limit" in str(e).lower() and attempt < max_retries - 1:
                        logger.warning(f"Connection limit reached, retrying in 5 seconds (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(5)
                    else:
                        raise

            # Get WebSocket details for DCV streaming
            ws_url, headers = client.generate_ws_headers()

            # Connect Playwright to MCP browser
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp(
                ws_url,
                headers=headers
            )

            # Get or create page with anti-detection settings
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                page = pages[0] if pages else await context.new_page()
            else:
                # Create context with realistic user agent and viewport
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York'
                )
                page = await context.new_page()

            # Set extra HTTP headers to appear more like a real browser
            await page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            })

            # Navigate to course URL with longer timeout
            await page.goto(course_url, wait_until="networkidle", timeout=60000)

            # Special handling for YouTube videos
            if is_youtube:
                logger.info("YouTube video loaded, analyzing content")
                # Wait for video player to load
                await asyncio.sleep(3)

                # Extract video metadata from page
                video_title = await page.title()
                video_description = await page.evaluate("""
                    () => {
                        const desc = document.querySelector('ytd-text-inline-expander #description-text, #description');
                        return desc ? desc.textContent.trim() : '';
                    }
                """)

                # Get video info
                video_info = await page.evaluate("""
                    () => {
                        const views = document.querySelector('.view-count, #info-text');
                        const author = document.querySelector('ytd-channel-name #text, #owner-name');
                        return {
                            views: views ? views.textContent.trim() : '',
                            author: author ? author.textContent.trim() : ''
                        };
                    }
                """)

                # Take screenshot
                screenshot = await page.screenshot(full_page=True)
                screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')

                # Analyze with AI
                analysis_prompt = f"""
Analyze this YouTube video page that I'm viewing in a browser:

Title: {video_title}
Author: {video_info.get('author', 'Unknown')}
Views: {video_info.get('views', 'Unknown')}

Description:
{video_description[:1000]}

Based on the title, description, and visual layout, provide:
1. Main topic and subject matter
2. Key learning objectives (what viewers will learn)
3. Target audience (beginners/intermediate/advanced)
4. Estimated difficulty level
5. Main concepts likely covered
6. Practical applications
7. 3-5 sentence summary

Format as clear, structured text.
"""

                ai_analysis = self.agent(analysis_prompt).message

                # Store as single module
                video_id = self._extract_youtube_id(course_url)
                module = CourseModule(
                    title=video_title,
                    url=course_url,
                    order=1
                )
                module.text_content = f"""
YouTube Video Analysis

Title: {video_title}
Author: {video_info.get('author', 'Unknown')}
Views: {video_info.get('views', 'Unknown')}

Description:
{video_description}

AI Analysis:
{ai_analysis}
"""
                module.screenshots = [screenshot_base64]
                module.completed = True

                # Save to knowledge base
                course_id = f"youtube_{video_id}"
                self._save_module_to_memory(user_id, course_id, module)

                logger.info("YouTube video analyzed and saved to knowledge base")

            # Extract MCP session ID from WebSocket URL
            # Format: wss://bedrock-agentcore.{region}.amazonaws.com/browser-streams/aws.browser.v1/sessions/{SESSION_ID}/automation
            import re
            mcp_session_match = re.search(r'/sessions/([^/]+)/', ws_url)
            mcp_session_id = mcp_session_match.group(1) if mcp_session_match else None

            # Construct AWS Console URL
            console_url = None
            if mcp_session_id:
                console_url = f"https://{self.region}.console.aws.amazon.com/bedrock-agentcore/builtInTools/browser/aws.browser.v1/session/{mcp_session_id}#"

            # Store session
            active_sessions[session_id] = {
                "client": client,
                "browser": browser,
                "page": page,
                "playwright": playwright,
                "context": context,
                "course_url": course_url,
                "user_id": user_id,
                "ws_url": ws_url,
                "dcv_headers": headers,
                "mcp_session_id": mcp_session_id,
                "console_url": console_url,
                "status": "awaiting_login",
                "modules": [],
                "current_module": 0,
                "total_modules": 0,
                "progress": 0,
                "started_at": datetime.utcnow().isoformat()
            }

            return {
                "status": "awaiting_login",
                "session_id": session_id,
                "mcp_session_id": mcp_session_id,
                "console_url": console_url,
                "dcv_url": ws_url,
                "dcv_headers": headers,
                "message": "Browser session created. Please log in.",
                "page_title": await page.title()
            }

        except Exception as e:
            # Cleanup on error
            if browser:
                try:
                    await browser.close()
                except:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except:
                    pass
            if client:
                try:
                    client.stop()
                except:
                    pass

            error_msg = str(e)
            # Provide helpful message for connection limit errors
            if "limit" in error_msg.lower():
                error_msg = "Connection limit reached. Please wait a moment and try again, or close any open browser sessions in AWS Console."

            return {
                "status": "error",
                "message": f"Failed to start processing: {error_msg}"
            }

    async def continue_after_login(self, session_id: str) -> Dict[str, Any]:
        """
        Continue processing after user login.
        Discovers all modules and starts processing.
        """
        try:
            if session_id not in active_sessions:
                return {"status": "error", "message": "Session not found"}

            session = active_sessions[session_id]
            page: Page = session["page"]

            # Wait for post-login redirects
            await asyncio.sleep(3)
            await page.wait_for_load_state("networkidle")

            # Update status
            session["status"] = "discovering_modules"

            # Discover all course modules
            modules = await self.discover_modules(page)
            session["modules"] = modules
            session["total_modules"] = len(modules)

            # Start processing modules
            session["status"] = "processing_modules"

            # Process in background (non-blocking)
            asyncio.create_task(self.process_all_modules(session_id))

            return {
                "status": "processing_started",
                "session_id": session_id,
                "total_modules": len(modules),
                "message": "Processing started. Modules will be processed sequentially."
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to continue: {str(e)}"
            }

    async def discover_modules(self, page: Page) -> List[CourseModule]:
        """
        Discover all course modules/sections.
        Uses AI to identify course structure.
        """
        try:
            # Extract course navigation/modules
            modules_data = await page.evaluate("""
                () => {
                    // Common selectors for course modules
                    const selectors = [
                        '.module', '.lesson', '.section', '.chapter',
                        '[class*="module"]', '[class*="lesson"]',
                        '[class*="section"]', '[class*="chapter"]',
                        'li a[href*="lesson"]', 'li a[href*="module"]'
                    ];

                    const modules = [];
                    let order = 0;

                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            elements.forEach(el => {
                                const link = el.querySelector('a') || el;
                                const href = link.href;
                                const title = link.textContent.trim();

                                if (href && title && !modules.find(m => m.url === href)) {
                                    modules.push({
                                        title: title,
                                        url: href,
                                        order: order++
                                    });
                                }
                            });

                            if (modules.length > 0) break;
                        }
                    }

                    return modules;
                }
            """)

            # Create CourseModule objects
            modules = [
                CourseModule(
                    title=m["title"],
                    url=m["url"],
                    order=m["order"]
                )
                for m in modules_data
            ]

            # If no modules found, treat current page as single module
            if not modules:
                modules = [
                    CourseModule(
                        title=await page.title(),
                        url=page.url,
                        order=0
                    )
                ]

            return modules

        except Exception as e:
            logger.error(f"Error discovering modules: {e}")
            # Fallback: single module
            return [
                CourseModule(
                    title=await page.title(),
                    url=page.url,
                    order=0
                )
            ]

    async def process_all_modules(self, session_id: str):
        """Process all modules sequentially and save to memory."""
        try:
            session = active_sessions[session_id]
            modules = session["modules"]
            page: Page = session["page"]
            user_id = session["user_id"]
            course_url = session["course_url"]

            # Generate course ID from URL
            course_id = f"course_{abs(hash(course_url)) % 10000000}"

            processed_modules = []

            for idx, module in enumerate(modules):
                session["current_module"] = idx + 1
                session["progress"] = int((idx / len(modules)) * 100)

                # Navigate to module
                await page.goto(module.url, wait_until="networkidle")
                await asyncio.sleep(2)

                # Extract content from module
                content = await self.extract_module_content(page)

                # Update module data
                module.text_content = content["text"]
                module.videos = content["videos"]
                module.audios = content["audios"]
                module.files = content["files"]
                module.screenshots = content["screenshots"]
                module.completed = True

                processed_modules.append(module)

                # Save module to persistent memory
                self._save_module_to_memory(user_id, course_id, module)

                # Save progress
                session["processed_modules"] = processed_modules

            # All modules processed
            session["status"] = "analyzing"
            session["progress"] = 100

            # Analyze complete course
            summary = await self.analyze_complete_course(processed_modules)
            session["summary"] = summary

            # Save summary to persistent memory
            self._save_summary_to_memory(user_id, course_id, summary)

            session["status"] = "completed"

        except Exception as e:
            session["status"] = "error"
            session["error"] = str(e)

    async def extract_module_content(self, page: Page) -> Dict[str, Any]:
        """Extract all content from a single module."""
        try:
            # Extract text content
            text_content = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script, style');
                    scripts.forEach(el => el.remove());

                    const main = document.querySelector('main, article, .content, [role="main"]');
                    return main ? main.innerText : document.body.innerText;
                }
            """)

            # Extract videos
            videos = await page.evaluate("""
                () => {
                    const videos = Array.from(document.querySelectorAll('video, iframe[src*="youtube"], iframe[src*="vimeo"], iframe[src*="wistia"]'));
                    return videos.map(v => ({
                        type: v.tagName.toLowerCase(),
                        src: v.src || v.querySelector('source')?.src,
                        title: v.title || v.getAttribute('aria-label') || 'Video'
                    })).filter(v => v.src);
                }
            """)

            # Extract audio
            audios = await page.evaluate("""
                () => {
                    const audios = Array.from(document.querySelectorAll('audio'));
                    return audios.map(a => ({
                        src: a.src || a.querySelector('source')?.src,
                        title: a.title || 'Audio'
                    })).filter(a => a.src);
                }
            """)

            # Extract downloadable files
            files = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href$=".pdf"], a[href$=".doc"], a[href$=".docx"], a[href$=".ppt"], a[href$=".pptx"], a[href$=".zip"]'));
                    return links.map(link => ({
                        url: link.href,
                        text: link.textContent.trim(),
                        type: link.href.split('.').pop()
                    }));
                }
            """)

            # Take screenshot
            screenshot = await page.screenshot(full_page=True)
            screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')

            return {
                "text": text_content[:20000],  # Limit to 20k chars
                "videos": videos,
                "audios": audios,
                "files": files,
                "screenshots": [screenshot_base64]
            }

        except Exception as e:
            logger.error(f"Error extracting module content: {e}")
            return {
                "text": "",
                "videos": [],
                "audios": [],
                "files": [],
                "screenshots": []
            }

    async def analyze_complete_course(self, modules: List[CourseModule]) -> Dict[str, Any]:
        """
        Analyze complete course using Bedrock.
        Creates comprehensive summary.
        """
        try:
            # Prepare course data for analysis
            course_data = {
                "total_modules": len(modules),
                "modules": [
                    {
                        "title": m.title,
                        "text_preview": m.text_content[:500],
                        "video_count": len(m.videos),
                        "audio_count": len(m.audios),
                        "file_count": len(m.files)
                    }
                    for m in modules
                ]
            }

            # Create analysis prompt
            prompt = f"""
Analyze this complete course and provide a comprehensive summary:

Course Data:
{json.dumps(course_data, indent=2)}

Full Text Content from All Modules:
{' '.join([m.text_content[:1000] for m in modules[:10]])}

Please provide:
1. Course Title
2. Overall Summary (3-4 paragraphs)
3. Key Topics Covered (list)
4. Learning Objectives
5. Difficulty Level
6. Estimated Duration
7. Module-by-Module Breakdown
8. Key Takeaways
9. Resources (videos, files, etc.)

Format as JSON.
"""

            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )

            # Parse response
            result = json.loads(response['body'].read())
            analysis_text = result['content'][0]['text']

            return {
                "analysis": analysis_text,
                "total_modules": len(modules),
                "total_videos": sum(len(m.videos) for m in modules),
                "total_audios": sum(len(m.audios) for m in modules),
                "total_files": sum(len(m.files) for m in modules),
                "modules_completed": len([m for m in modules if m.completed])
            }

        except Exception as e:
            return {
                "analysis": f"Analysis failed: {str(e)}",
                "error": True
            }

    async def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get current processing status for both course and file processing."""
        if session_id not in active_sessions:
            return {"status": "not_found", "message": "Session not found"}

        session = active_sessions[session_id]
        session_type = session.get("type", "course_processing")

        # File processing session
        if session_type == "file_processing":
            status_response = {
                "status": session.get("status"),
                "session_id": session_id,
                "type": "file_processing",
                "total_files": session.get("total_files", 0),
                "processed_files": session.get("processed_files", 0),
                "progress": session.get("progress", 0),
                "kb_id": session.get("kb_id"),
                "agent_type": session.get("agent_type"),
                "results": session.get("results"),
                "error": session.get("error"),
                "started_at": session.get("started_at"),
                # Memory save progress removed (now using local KB storage)
                }

            return status_response

        # Course processing session (legacy)
        return {
            "status": session.get("status"),
            "session_id": session_id,
            "type": "course_processing",
            "mcp_session_id": session.get("mcp_session_id"),
            "console_url": session.get("console_url"),
            "course_url": session.get("course_url"),
            "current_module": session.get("current_module", 0),
            "total_modules": session.get("total_modules", 0),
            "progress": session.get("progress", 0),
            "summary": session.get("summary"),
            "started_at": session.get("started_at")
        }

    async def stop_processing(self, session_id: str) -> Dict[str, Any]:
        """Stop processing and cleanup."""
        if session_id in active_sessions:
            session = active_sessions[session_id]

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

            return {"status": "stopped", "message": "Processing stopped"}

        return {"status": "not_found", "message": "Session not found"}

    def get_saved_courses(self, user_id: str, query: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve saved courses - deprecated in favor of local KB storage."""
        logger.info("get_saved_courses called - returning empty result (using local KB storage)")
        return {
            "status": "success",
            "courses": [],
            "total": 0,
            "message": "Course retrieval deprecated - using local KB storage"
        }

    def _parse_course_summary(self, content: str, course_id: str) -> Dict[str, Any]:
        """Parse summary text content into structured data."""
        import re

        # Default values
        parsed = {
            "course_id": course_id,
            "title": "Unknown Course",
            "total_modules": 0,
            "total_videos": 0,
            "total_audios": 0,
            "total_files": 0,
            "overview": "",
            "key_topics": [],
            "learning_outcomes": []
        }

        # Extract title
        title_match = re.search(r"Title:\s*(.+)", content)
        if title_match:
            parsed["title"] = title_match.group(1).strip()

        # Extract total modules
        modules_match = re.search(r"Total Modules:\s*(\d+)", content)
        if modules_match:
            parsed["total_modules"] = int(modules_match.group(1))

        # Extract overview (first paragraph after "Overview:")
        overview_match = re.search(r"Overview:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\nKey Topics:|\Z)", content, re.MULTILINE)
        if overview_match:
            parsed["overview"] = overview_match.group(1).strip()

        # Extract key topics
        topics_match = re.search(r"Key Topics:\s*([^\n]+)", content)
        if topics_match:
            topics_str = topics_match.group(1).strip()
            parsed["key_topics"] = [t.strip() for t in topics_str.split(",")]

        # Extract learning outcomes
        outcomes_section = re.search(r"Learning Outcomes:(.*?)(?=\n\n|\Z)", content, re.DOTALL)
        if outcomes_section:
            outcomes_text = outcomes_section.group(1)
            outcomes = re.findall(r"-\s*(.+)", outcomes_text)
            parsed["learning_outcomes"] = [o.strip() for o in outcomes]

        return parsed

    def get_course_details(self, user_id: str, course_id: str) -> Dict[str, Any]:
        """Retrieve course details - deprecated in favor of local KB storage."""
        logger.info("get_course_details called - returning empty result (using local KB storage)")
        return {
            "status": "success",
            "course": None,
            "message": "Course details retrieval deprecated - using local KB storage"
        }

    def _parse_module_content(self, content: str) -> Dict[str, Any]:
        """Parse module text content into structured data."""
        import re

        parsed = {
            "title": "Unknown Module",
            "url": "",
            "order": 0,
            "text_preview": "",
            "video_count": 0,
            "audio_count": 0,
            "file_count": 0
        }

        # Extract module title
        title_match = re.search(r"Module:\s*(.+)", content)
        if title_match:
            parsed["title"] = title_match.group(1).strip()

        # Extract URL
        url_match = re.search(r"URL:\s*(.+)", content)
        if url_match:
            parsed["url"] = url_match.group(1).strip()

        # Extract order
        order_match = re.search(r"Order:\s*(\d+)", content)
        if order_match:
            parsed["order"] = int(order_match.group(1))

        # Extract content preview
        content_match = re.search(r"Content:\s*(.*?)(?=\n\nVideos:|\nVideos:|\Z)", content, re.DOTALL)
        if content_match:
            full_content = content_match.group(1).strip()
            parsed["text_preview"] = full_content[:500] if len(full_content) > 500 else full_content

        # Extract counts
        videos_match = re.search(r"Videos:\s*(\d+)", content)
        if videos_match:
            parsed["video_count"] = int(videos_match.group(1))

        audios_match = re.search(r"Audio:\s*(\d+)", content)
        if audios_match:
            parsed["audio_count"] = int(audios_match.group(1))

        files_match = re.search(r"Files:\s*(\d+)", content)
        if files_match:
            parsed["file_count"] = int(files_match.group(1))

        return parsed

    def get_dcv_presigned_url(self, session_id: str, mcp_session_id: str) -> Dict[str, Any]:
        """
        Get presigned DCV live view URL using BrowserClient's generate_live_view_url() method.

        Args:
            session_id: Session ID
            mcp_session_id: MCP browser session ID

        Returns:
            Presigned live-view URL for DCV authentication
        """
        try:
            # Get session info
            if session_id not in active_sessions:
                return {
                    "status": "error",
                    "message": "Session not found"
                }

            session = active_sessions[session_id]

            # Get BrowserClient from session
            client = session.get("client")
            if not client:
                return {
                    "status": "error",
                    "message": "Browser client not found in session"
                }

            # Generate presigned URL for DCV live view
            # This returns a properly formatted presigned URL with SigV4 authentication
            import logging
            logger = logging.getLogger(__name__)

            presigned_url = client.generate_live_view_url(expires=300)  # 5 minutes expiration

            logger.info(f"✅ Generated DCV presigned URL for session {mcp_session_id}")
            logger.info(f"   URL: {presigned_url[:100]}...")
            logger.info(f"   URL length: {len(presigned_url)} characters")

            return {
                "status": "success",
                "presignedUrl": presigned_url,
                "sessionId": mcp_session_id
            }

        except Exception as e:
            import traceback
            logger.error(f"Error generating presigned URL: {e}")
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": f"Failed to generate presigned URL: {str(e)}"
            }


    async def start_file_processing(
        self,
        session_id: str,
        file_paths: List[str],
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start file processing and return immediately with session_id.
        Processing happens in background, poll with get_status().
        """
        try:
            agent_type = processing_options.get("agent_type", "general") if processing_options else "general"
            kb_id = processing_options.get("knowledge_base_id") if processing_options else None

            # Auto-generate a knowledge base ID if not provided
            # This ensures content is always stored in memory for later retrieval
            if not kb_id:
                kb_id = f"kb_{str(uuid.uuid4())}"
                logger.info(f"Auto-generated knowledge base ID: {kb_id}")

            logger.info(f"Starting async file processing session {session_id} for {len(file_paths)} files")

            # Store session state
            active_sessions[session_id] = {
                "type": "file_processing",
                "file_paths": file_paths,
                "user_id": user_id,
                "kb_id": kb_id,
                "agent_type": agent_type,
                "status": "processing",
                "total_files": len(file_paths),
                "processed_files": 0,
                "progress": 0,
                "results": None,
                "error": None,
                "started_at": datetime.utcnow().isoformat()
            }

            # Start processing in background thread (non-blocking)
            # Use thread instead of asyncio.create_task because asyncio.run() closes the event loop
            thread = threading.Thread(
                target=lambda: asyncio.run(self._process_files_background(session_id)),
                daemon=True
            )
            thread.start()

            return {
                "status": "processing",
                "session_id": session_id,
                "total_files": len(file_paths),
                "message": "File processing started. Poll /get_status for progress."
            }

        except Exception as e:
            logger.error(f"Failed to start file processing: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to start file processing: {str(e)}"
            }

    async def _process_files_background(self, session_id: str):
        """Background task for processing files."""
        try:
            session = active_sessions.get(session_id)
            if not session:
                return

            file_paths = session["file_paths"]
            user_id = session["user_id"]
            kb_id = session["kb_id"]
            agent_type = session["agent_type"]

            logger.info(f"Processing {len(file_paths)} files with specialized agents for KB {kb_id}")

            # Update to show we've started processing (not stuck at 0%)
            session["progress"] = 10  # Initial progress to show we're working
            session["status"] = "processing_files"

            # Use the specialized agent system (pass session_id for memory save tracking)
            result = await file_processor.process_files_with_agents(file_paths, user_id, session_id)

            # Update progress after file processing completes
            session["processed_files"] = len(file_paths)
            session["progress"] = 90  # File processing done, preparing results

            # If we have a knowledge base ID, store content in AgentCore Memory
            if kb_id and result.get("status") == "completed":
                await self._store_agent_results_in_memory(kb_id, user_id, result, agent_type)

            # Generate comprehensive analysis from all agent results
            if result.get("status") == "completed":
                session["status"] = "analyzing"
                analysis = await self._analyze_agent_results(result.get("results", {}))
                result["comprehensive_analysis"] = analysis

                # Store the comprehensive analysis in memory
                if kb_id:
                    await self._store_comprehensive_analysis(kb_id, user_id, analysis)

            # Store final results
            session["results"] = result
            session["status"] = "completed" if result.get("status") == "completed" else "error"
            session["error"] = result.get("message") if result.get("status") == "error" else None
            session["progress"] = 100  # Mark as fully complete

            logger.info(f"{agent_type.upper()} Agent completed processing for session {session_id}")

        except Exception as e:
            logger.error(f"Specialized agents failed: {str(e)}")
            session = active_sessions.get(session_id)
            if session:
                session["status"] = "error"
                session["error"] = str(e)

    async def process_uploaded_files(
        self,
        file_paths: List[str],
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        LEGACY: Process uploaded files using specialized agents and store in AgentCore Memory.
        This method is kept for backward compatibility but should use start_file_processing instead.
        """
        try:
            agent_type = processing_options.get("agent_type", "general") if processing_options else "general"
            kb_id = processing_options.get("knowledge_base_id") if processing_options else None

            # Auto-generate a knowledge base ID if not provided
            # This ensures content is always stored in memory for later retrieval
            if not kb_id:
                kb_id = f"kb_{str(uuid.uuid4())}"
                logger.info(f"Auto-generated knowledge base ID: {kb_id}")

            logger.info(f"Processing {len(file_paths)} files with specialized agents for KB {kb_id}")

            # Use the new specialized agent system
            result = await file_processor.process_files_with_agents(file_paths, user_id)

            # If we have a knowledge base ID, store content in AgentCore Memory
            if kb_id and result.get("status") == "completed":
                await self._store_agent_results_in_memory(kb_id, user_id, result, agent_type)

            # Generate comprehensive analysis from all agent results
            if result.get("status") == "completed":
                analysis = await self._analyze_agent_results(result.get("results", {}))
                result["comprehensive_analysis"] = analysis

                # Store the comprehensive analysis in memory
                if kb_id:
                    await self._store_comprehensive_analysis(kb_id, user_id, analysis)

            # Add knowledge base ID to result for caller reference
            result["kb_id"] = kb_id

            logger.info(f"{agent_type.upper()} Agent completed processing for KB {kb_id}")
            return result

        except Exception as e:
            logger.error(f"Specialized agents failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process uploaded files: {str(e)}"
            }
    
    async def _store_agent_results_in_memory(self, kb_id: str, user_id: str, result: Dict[str, Any], agent_type: str):
        """Store specialized agent results in local KB storage."""
        try:
            # Store results for each agent type in local file storage
            for agent_type_key, agent_results in result.get("results", {}).items():
                # Save to local KB storage
                self.kb_storage.save_agent_results(
                    kb_id=kb_id,
                    agent_type=agent_type_key,
                    results=agent_results,
                    metadata={
                        "user_id": user_id,
                        "processing_date": datetime.now().isoformat(),
                        "files_processed": len(agent_results)
                    }
                )
                logger.info(f"Stored {agent_type_key} agent results in local KB storage for {kb_id}")

        except Exception as e:
            logger.error(f"Could not store agent results in local storage: {e}")
    
    async def _analyze_agent_results(self, agent_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Generate comprehensive analysis from all agent results."""
        try:
            # Compile content from all agents
            all_analyses = []
            content_summary = {}
            
            for agent_type, results in agent_results.items():
                successful_results = [r for r in results if r.get('status') == 'completed']
                content_summary[agent_type] = {
                    "files_processed": len(successful_results),
                    "total_files": len(results)
                }
                
                for result in successful_results:
                    analysis = result.get('analysis', {}).get('ai_analysis', '')
                    if analysis:
                        all_analyses.append(f"{agent_type.upper()} Analysis: {analysis[:500]}...")
            
            if not all_analyses:
                return {"comprehensive_analysis": "No analysis available", "content_summary": content_summary}
            
            # Generate comprehensive analysis using AI
            prompt = f"""
Analyze this multi-modal content processed by specialized agents:

Content Summary:
{json.dumps(content_summary, indent=2)}

Individual Agent Analyses:
{chr(10).join(all_analyses[:10])}  # Limit to first 10 analyses

Please provide:
1. Overall content themes and topics
2. Cross-modal insights and connections
3. Educational value and learning potential
4. Content organization and structure
5. Recommended learning approach
6. Key concepts and terminology
7. Target audience and difficulty assessment
8. Comprehensive summary in 3-4 sentences

Format as JSON with clear categories.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            comprehensive_analysis = result['content'][0]['text']
            
            return {
                "comprehensive_analysis": comprehensive_analysis,
                "content_summary": content_summary,
                "processing_method": "multi_agent_comprehensive_analysis"
            }
            
        except Exception as e:
            logger.warning(f"Error generating comprehensive analysis: {e}")
            return {
                "comprehensive_analysis": f"Analysis failed: {str(e)}",
                "content_summary": content_summary,
                "processing_method": "basic_summary_only"
            }

    async def process_direct_links(
        self,
        links: List[str],
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process direct resource links and integrate with course pipeline."""
        try:
            logger.info(f"Processing {len(links)} direct links for user {user_id}")
            
            # Use the file processor to handle the links
            result = await file_processor.process_direct_links(
                links=links,
                user_id=user_id,
                processing_options=processing_options
            )
            
            # Generate session ID for tracking
            session_id = f"links_{abs(hash(''.join(links))) % 10000000}"
            
            # Analyze all processed content with AI
            if result.get("status") == "completed":
                all_content = []
                for link_result in result.get("processed_links", []):
                    content = link_result.get("content", {})
                    text = content.get("text_content") or content.get("description") or content.get("transcript", "")
                    if text:
                        all_content.append({
                            "url": link_result.get("url"),
                            "content": text[:2000]  # Limit content for analysis
                        })
                
                if all_content:
                    analysis = await self._analyze_link_collection(all_content)
                    result["analysis"] = analysis
            
            result["session_id"] = session_id
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process direct links: {str(e)}"
            }

    async def process_mixed_content(
        self,
        course_url: Optional[str],
        file_paths: Optional[List[str]],
        direct_links: Optional[List[str]],
        user_id: str,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process mixed content sources (URL + files + links)."""
        try:
            logger.info(f"Processing mixed content for user {user_id}")
            
            session_id = f"mixed_{abs(hash(f'{course_url}_{file_paths}_{direct_links}')) % 10000000}"
            results = {
                "session_id": session_id,
                "status": "processing",
                "content_sources": {},
                "message": "Processing mixed content sources"
            }
            
            # Process course URL if provided
            if course_url:
                logger.info("Processing course URL")
                course_result = await self.start_course_processing(
                    session_id=f"{session_id}_course",
                    course_url=course_url,
                    user_id=user_id
                )
                results["content_sources"]["course_url"] = course_result
            
            # Process uploaded files if provided
            if file_paths:
                logger.info("Processing uploaded files")
                files_result = await self.process_uploaded_files(
                    file_paths=file_paths,
                    user_id=user_id,
                    processing_options=processing_options
                )
                results["content_sources"]["uploaded_files"] = files_result
            
            # Process direct links if provided
            if direct_links:
                logger.info("Processing direct links")
                links_result = await self.process_direct_links(
                    links=direct_links,
                    user_id=user_id,
                    processing_options=processing_options
                )
                results["content_sources"]["direct_links"] = links_result
            
            # Create combined analysis
            all_content = []
            
            # Collect content from files
            if file_paths and results["content_sources"].get("uploaded_files"):
                files_data = results["content_sources"]["uploaded_files"]
                for file_result in files_data.get("processed_files", []):
                    content = file_result.get("content", {})
                    text = content.get("text_content") or content.get("description") or content.get("transcript", "")
                    if text:
                        all_content.append({
                            "source": "file",
                            "name": file_result.get("filename"),
                            "content": text[:1500]
                        })
            
            # Collect content from links
            if direct_links and results["content_sources"].get("direct_links"):
                links_data = results["content_sources"]["direct_links"]
                for link_result in links_data.get("processed_links", []):
                    content = link_result.get("content", {})
                    text = content.get("text_content") or content.get("description") or content.get("transcript", "")
                    if text:
                        all_content.append({
                            "source": "link",
                            "name": link_result.get("url"),
                            "content": text[:1500]
                        })
            
            # Generate combined analysis
            if all_content:
                combined_analysis = await self._analyze_mixed_content(all_content, course_url)
                results["combined_analysis"] = combined_analysis
            
            results["status"] = "completed"
            results["message"] = "Mixed content processing completed"
            
            return results
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process mixed content: {str(e)}"
            }

    async def _analyze_file_collection(self, files_content: List[Dict[str, Any]]) -> str:
        """Analyze a collection of processed files with AI."""
        try:
            content_summary = "\n\n".join([
                f"File: {item['filename']}\nContent Preview:\n{item['content']}"
                for item in files_content[:10]  # Limit to 10 files
            ])
            
            prompt = f"""
Analyze this collection of uploaded files and provide a comprehensive educational summary:

Files Content:
{content_summary}

Please provide:
1. Overall theme and subject matter
2. Key topics covered across all files
3. Learning objectives that can be derived
4. Content organization and structure
5. Educational value and applications
6. Summary of main concepts
7. Recommended learning sequence

Format as clear, structured text suitable for course material analysis.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            return result['content'][0]['text']
            
        except Exception as e:
            return f"Analysis failed: {str(e)}"

    async def _analyze_link_collection(self, links_content: List[Dict[str, Any]]) -> str:
        """Analyze a collection of processed links with AI."""
        try:
            content_summary = "\n\n".join([
                f"URL: {item['url']}\nContent Preview:\n{item['content']}"
                for item in links_content[:10]  # Limit to 10 links
            ])
            
            prompt = f"""
Analyze this collection of web resources and provide a comprehensive educational summary:

Resources Content:
{content_summary}

Please provide:
1. Overall theme and subject matter
2. Key topics covered across all resources
3. Learning objectives that can be derived
4. Quality and credibility of sources
5. Educational value and applications
6. Summary of main concepts
7. How these resources complement each other

Format as clear, structured text suitable for educational resource analysis.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            return result['content'][0]['text']
            
        except Exception as e:
            return f"Analysis failed: {str(e)}"

    async def _analyze_mixed_content(self, all_content: List[Dict[str, Any]], course_url: Optional[str]) -> str:
        """Analyze mixed content sources with AI."""
        try:
            content_summary = "\n\n".join([
                f"Source: {item['source']} - {item['name']}\nContent Preview:\n{item['content']}"
                for item in all_content[:15]  # Limit to 15 items
            ])
            
            course_context = f"\nMain Course URL: {course_url}" if course_url else ""
            
            prompt = f"""
Analyze this mixed collection of educational content from multiple sources and provide a comprehensive summary:

{course_context}

Content from Multiple Sources:
{content_summary}

Please provide:
1. Unified theme and subject matter across all sources
2. Key topics covered comprehensively
3. Learning objectives that span all content
4. How different sources complement each other
5. Recommended learning path through the materials
6. Educational value and practical applications
7. Summary of main concepts and takeaways
8. Content gaps or areas that could be enhanced

Format as clear, structured text suitable for comprehensive course material analysis.
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 3000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            return result['content'][0]['text']
            
        except Exception as e:
            return f"Analysis failed: {str(e)}"

    async def _store_in_agentcore_memory(self, kb_id: str, user_id: str, processing_result: Dict[str, Any], agent_type: str):
        """No-op: Replaced by local KB storage."""
        pass

    async def _store_analysis_in_memory(self, kb_id: str, user_id: str, analysis: str, agent_type: str):
        """No-op: Replaced by local KB storage."""
        pass

    async def _retrieve_kb_content_from_memory(self, kb_id: str, user_id: str) -> str:
        """Retrieve all content for a knowledge base from local storage."""
        try:
            # Load all agent results from local KB storage
            all_results = self.kb_storage.load_agent_results(kb_id)
            
            if not all_results:
                logger.warning(f"No content found in local storage for KB {kb_id}")
                return ""
            
            # Combine content from all agents
            all_content = []
            for agent_type, results in all_results.items():
                if isinstance(results, list):
                    for result in results:
                        if isinstance(result, dict) and result.get("status") == "completed":
                            content = result.get("content", {})

                            # Extract text from various content types
                            text = ""
                            if "text" in content:
                                text = content["text"]
                            elif "text_content" in content:
                                text = content["text_content"]
                            elif "transcript" in content:
                                text = content["transcript"]
                            elif "extracted_text" in content:
                                # For images with extracted text
                                text = content["extracted_text"]
                            elif "educational_content" in content:
                                # For images/videos with educational content
                                edu_content = content["educational_content"]
                                if isinstance(edu_content, dict):
                                    text = edu_content.get("full_text_content", "") or edu_content.get("text", "")
                                else:
                                    text = str(edu_content)

                            if text:
                                all_content.append(f"=== {agent_type.upper()} CONTENT ===\n{text}\n")
            
            total_chars = sum(len(c) for c in all_content)
            logger.info(f"Retrieved {len(all_content)} sections, {total_chars} characters from local storage for KB {kb_id}")
            
            return "\n".join(all_content) if all_content else ""
            
        except Exception as e:
            logger.error(f"Failed to retrieve KB content from local storage: {e}")
            return ""

    async def _retrieve_training_content_from_memory(self, kb_id: str, user_id: str) -> str:
        """Retrieve training content from local storage."""
        try:
            training_content = self.kb_storage.load_training_content(kb_id)
            
            if not training_content:
                logger.warning(f"No training content found in local storage for KB {kb_id}")
                return ""
            
            # Convert to string if it's a dict
            if isinstance(training_content, dict):
                return training_content.get("content", str(training_content))
            
            return str(training_content)
            
        except Exception as e:
            logger.error(f"Failed to retrieve training content from local storage: {e}")
            return ""

    def _clean_session_id(self, session_id: str) -> str:
        """Clean session ID to match AWS pattern: [a-zA-Z0-9][a-zA-Z0-9-_]*"""
        # Remove hyphens and underscores, keep only alphanumeric
        cleaned = ''.join(c for c in session_id if c.isalnum())
        # Ensure it starts with alphanumeric and limit length
        return cleaned[:50] if cleaned else "defaultSession"
    
    async def _store_comprehensive_analysis(self, kb_id: str, user_id: str, analysis: Dict[str, Any]):
        """Store comprehensive analysis in local KB storage."""
        try:
            # Extract the text analysis from the dictionary
            if isinstance(analysis, dict):
                analysis_text = analysis.get("comprehensive_analysis", "")
                if isinstance(analysis_text, str):
                    self.kb_storage.save_comprehensive_analysis(kb_id, analysis_text)
                    logger.info(f"Stored comprehensive analysis in local KB storage for {kb_id}")
                else:
                    # If it's still a dict, convert to JSON
                    self.kb_storage.save_comprehensive_analysis(kb_id, json.dumps(analysis, indent=2))
                    logger.info(f"Stored comprehensive analysis (JSON) in local KB storage for {kb_id}")
            else:
                # If it's already a string, save directly
                self.kb_storage.save_comprehensive_analysis(kb_id, str(analysis))
                logger.info(f"Stored comprehensive analysis in local KB storage for {kb_id}")

        except Exception as e:
            logger.warning(f"Could not store comprehensive analysis in local storage: {e}")
            logger.info("This is non-critical - analysis is available in processed_results")

    async def _store_training_content_in_memory(self, kb_id: str, user_id: str, training_content: str):
        """Store generated training content in local KB storage."""
        try:
            # Parse training content if it's JSON string
            if isinstance(training_content, str):
                try:
                    training_data = json.loads(training_content)
                except:
                    training_data = {"content": training_content}
            else:
                training_data = training_content

            # Save to local KB storage
            self.kb_storage.save_training_content(kb_id, training_data)
            logger.info(f"Stored training content in local KB storage for {kb_id}")

        except Exception as e:
            logger.error(f"Failed to store training content in local storage: {e}")

    def _extract_comprehensive_content_for_questions(self, processed_results: Dict[str, Any]) -> str:
        """Extract comprehensive content from all agent types for question generation.

        This uses the same logic as training_service._extract_content_from_kb_data
        to ensure consistency between learning content and question generation.
        """
        combined_content = []

        # Transform nested structure if needed
        for agent_type, agent_data in processed_results.items():
            results_list = []

            # Handle nested structure: {'audio': {'results': {'audio': [...]}}}
            if isinstance(agent_data, dict) and 'results' in agent_data:
                nested_results = agent_data['results']
                if isinstance(nested_results, dict):
                    # Flatten nested structure
                    for key, val in nested_results.items():
                        if isinstance(val, list):
                            results_list = val
                            break
                else:
                    results_list = nested_results if isinstance(nested_results, list) else []
            elif isinstance(agent_data, list):
                results_list = agent_data

            # Extract content from each result
            for result in results_list:
                if not isinstance(result, dict) or result.get("status") != "completed":
                    continue

                content = result.get("content", {})

                # Extract based on agent type (same logic as training_service)
                if agent_type == "text":
                    text = content.get("full_text", content.get("text", ""))
                    if text:
                        combined_content.append(f"=== Text Content ===\n{text}\n")

                elif agent_type == "pdf":
                    text = content.get("full_text", content.get("text", ""))
                    if text:
                        combined_content.append(f"=== PDF Content ===\n{text}\n")

                elif agent_type == "audio":
                    transcription = content.get("full_transcription", content.get("transcription", ""))
                    if transcription:
                        combined_content.append(f"=== Audio Transcription ===\n{transcription}\n")

                elif agent_type == "video":
                    analysis = result.get("analysis", {})
                    if isinstance(analysis, dict) and "ai_analysis" in analysis:
                        combined_content.append(f"=== Video Analysis ===\n{analysis['ai_analysis']}\n")

                elif agent_type == "image":
                    # PRIORITY: Extract structured educational content first
                    educational_content = content.get("educational_content", {})
                    if educational_content and educational_content.get("full_text_content"):
                        image_parts = [f"=== Image Educational Content ==="]

                        # Add full text content
                        full_text = educational_content.get("full_text_content", "")
                        if full_text:
                            image_parts.append(f"\n{full_text}\n")

                        # Add key concepts
                        key_concepts = educational_content.get("key_concepts", [])
                        if key_concepts:
                            image_parts.append(f"\nKey Concepts: {', '.join(key_concepts)}")

                        # Add commands
                        commands = educational_content.get("commands", [])
                        if commands:
                            image_parts.append("\n\nCommands/Functions:")
                            for cmd in commands[:20]:
                                name = cmd.get("name", "")
                                desc = cmd.get("description", "")
                                if name and desc:
                                    image_parts.append(f"  • {name}: {desc}")

                        combined_content.append("\n".join(image_parts) + "\n")

                    # Fallback to extracted_text
                    elif content.get("extracted_text"):
                        combined_content.append(f"=== Image OCR Text ===\n{content['extracted_text']}\n")

                    # Final fallback to ai_analysis
                    else:
                        analysis = result.get("analysis", {})
                        if isinstance(analysis, dict) and "ai_analysis" in analysis:
                            combined_content.append(f"=== Image Analysis ===\n{analysis['ai_analysis']}\n")

        return "\n".join(combined_content) if combined_content else ""

    def _extract_key_sections_for_training(self, content: str, max_length: int = 25000) -> str:
        """Extract key sections from content intelligently instead of blind truncation."""
        if len(content) <= max_length:
            return content

        logger.info(f"Extracting key sections from {len(content):,} chars (target: {max_length:,} chars)")

        # Split into sections and prioritize important ones
        sections = content.split('\n\n')

        key_sections = []
        regular_sections = []

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Identify key sections
            is_key = any([
                '===' in section,  # Headers
                section.startswith('=== '),  # Agent type headers
                'Analysis' in section,  # AI analysis
                'Summary' in section,  # Summaries
                'Transcription' in section,  # Transcripts
                'Content' in section,  # Main content
                len(section) > 200,  # Substantial sections
            ])

            if is_key:
                key_sections.append(section)
            else:
                regular_sections.append(section)

        # Build result starting with key sections
        result_sections = []
        current_length = 0

        # Add key sections first
        for section in key_sections:
            if current_length + len(section) > max_length:
                # Add partial section if we're close to the limit
                remaining = max_length - current_length
                if remaining > 500:  # Only add if we have meaningful space
                    result_sections.append(section[:remaining] + "...")
                break
            result_sections.append(section)
            current_length += len(section) + 2  # +2 for \n\n

        # Add regular sections if we have space
        for section in regular_sections:
            if current_length + len(section) > max_length:
                break
            result_sections.append(section)
            current_length += len(section) + 2

        result = '\n\n'.join(result_sections)
        logger.info(f"Extracted {len(result):,} chars ({len(result_sections)} sections)")
        return result

    async def _generate_training_content_with_retry(self, knowledge_base_id: str, user_id: str, max_retries: int = 5) -> Dict[str, Any]:
        """Generate training content with aggressive retry and backoff strategy."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Generating training content (attempt {attempt + 1}/{max_retries}) for KB {knowledge_base_id}")
                
                # Add progressive delay to avoid hitting rate limits
                if attempt > 0:
                    delay = min(60, 10 * (2 ** (attempt - 1)))  # Cap at 60 seconds
                    logger.info(f"Waiting {delay}s before retry to respect rate limits")
                    await asyncio.sleep(delay)
                
                result = await self._generate_training_content_from_kb(knowledge_base_id, user_id)
                
                if result.get("status") == "completed":
                    logger.info(f"Training content generated successfully on attempt {attempt + 1}")
                    return result
                elif "ThrottlingException" in str(result.get("message", "")):
                    logger.warning(f"Throttled on attempt {attempt + 1}, will retry")
                    continue
                else:
                    logger.error(f"Non-throttling error: {result.get('message')}")
                    return result
                    
            except Exception as e:
                import traceback
                error_msg = str(e) if str(e) else repr(e)
                if "ThrottlingException" in error_msg or "Too many requests" in error_msg:
                    logger.warning(f"Throttling exception on attempt {attempt + 1}: {error_msg}")
                    if attempt == max_retries - 1:
                        return {
                            "status": "error",
                            "message": f"Failed after {max_retries} attempts due to throttling: {error_msg}",
                            "error_type": type(e).__name__
                        }
                    continue
                else:
                    logger.error(f"Unexpected error: {error_msg}")
                    logger.error(f"Traceback:\n{traceback.format_exc()}")
                    return {"status": "error", "message": error_msg, "error_type": type(e).__name__}
        
        return {"status": "error", "message": f"Failed to generate training content after {max_retries} attempts"}

    async def _generate_training_content_from_kb(self, knowledge_base_id: str, user_id: str) -> Dict[str, Any]:
        """Generate comprehensive training content from AgentCore Memory knowledge base."""
        try:
            logger.info(f"Generating training content from AgentCore Memory for KB {knowledge_base_id}")
            
            # Retrieve content from AgentCore Memory
            kb_content = await self._retrieve_kb_content_from_memory(knowledge_base_id, user_id)
            
            if not kb_content:
                logger.error(f"No content found in memory for KB {knowledge_base_id}")
                return {
                    "status": "error",
                    "message": "No content available in knowledge base. Please ensure files were processed successfully."
                }

            content_length = len(kb_content)
            logger.info(f"KB content: {content_length:,} characters")

            # **QUALITY FIX**: Use intelligent extraction instead of blind 8K truncation
            if content_length > 30000:
                logger.info("Content is long, extracting key sections")
                content_to_use = self._extract_key_sections_for_training(kb_content, max_length=25000)
                note = f"\n[Intelligently extracted {len(content_to_use):,} chars from {content_length:,} total, prioritizing key sections]"
            else:
                content_to_use = kb_content
                note = ""

            prompt = f"""
IMPORTANT: You must generate training materials based ONLY on the actual content provided below. Do NOT create generic examples or hypothetical content.

Knowledge Base Content from Multiple Agents:
{content_to_use}
{note}

Generate training materials that are DIRECTLY DERIVED from the content above:
1. Learning Objectives (5-7 key objectives based on the actual content)
2. Key Concepts and Definitions (10-15 important terms from the content)
3. Topic Areas for MCQ Generation (based on content themes)
4. Difficulty Levels (Beginner, Intermediate, Advanced)
5. Assessment Categories (Comprehension, Application, Analysis)

Format as JSON:
{{
    "learning_objectives": ["objective1", "objective2", ...],
    "key_concepts": [
        {{"term": "concept", "definition": "definition", "difficulty": "beginner|intermediate|advanced"}},
        ...
    ],
    "topic_areas": ["area1", "area2", ...],
    "assessment_categories": ["comprehension", "application", "analysis"],
    "total_questions_available": 50,
    "content_summary": "Brief summary of what the knowledge base covers"
}}
"""
            
            response = self.bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 3000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            training_content = result['content'][0]['text']
            
            # Store the training content back in memory
            await self._store_training_content_in_memory(knowledge_base_id, user_id, training_content)
            
            return {
                "status": "completed",
                "knowledge_base_id": knowledge_base_id,
                "training_content": training_content,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            error_msg = str(e) if str(e) else repr(e)
            logger.error(f"Failed to generate training content: {error_msg}")
            logger.error(f"Full traceback:\n{error_details}")
            return {
                "status": "error",
                "message": f"Failed to generate training content: {error_msg}",
                "error_type": type(e).__name__,
                "traceback": error_details
            }

    async def _generate_mcq_question(self, knowledge_base_id: str, session_id: str, questions_answered: int, processed_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a single MCQ question for training based on actual knowledge base content."""
        try:
            # Determine difficulty based on progress
            if questions_answered < 5:
                difficulty = "beginner"
            elif questions_answered < 15:
                difficulty = "intermediate"
            else:
                difficulty = "advanced"

            logger.info(f"Generating MCQ question #{questions_answered + 1}")
            logger.debug(f"Processed results provided: {bool(processed_results)}")

            if processed_results:
                logger.debug("Processed results structure:")
                logger.debug(f"   Top-level keys: {list(processed_results.keys())}")
                if 'image' in processed_results:
                    logger.debug(f"   Image keys: {list(processed_results['image'].keys())}")

            # **FAST PATH**: Use processed_results directly from backend (skip slow memory retrieval)
            kb_content = ""
            if processed_results:
                logger.debug("Using processed_results from backend (fast path)")

                # **FIX**: Use comprehensive content extraction (same as training_service)
                # This extracts from ALL agent types (text, pdf, audio, video, image)
                kb_content = self._extract_comprehensive_content_for_questions(processed_results)

                if kb_content:
                    logger.debug(f"Extracted comprehensive content: {len(kb_content)} characters")
                    logger.debug(f"   Content preview: {kb_content[:200]}")
                else:
                    logger.warning("Comprehensive extraction returned empty content")

            # Fallback if no content found
            if not kb_content:
                logger.warning("No educational content available, using generic fallback")
                kb_content = "No specific content available. Generate general educational questions."
            else:
                logger.debug(f"Final kb_content length: {len(kb_content)} characters")

            # Skip training content retrieval for speed (it's slow and usually empty)
            training_content = ""

            # Add variety to question generation by focusing on different aspects
            focus_areas = [
                "key concepts and definitions",
                "practical applications and examples",
                "comparisons and distinctions between topics",
                "cause and effect relationships",
                "problem-solving approaches",
                "detailed procedures and steps",
                "important facts and figures",
                "theoretical foundations"
            ]
            focus_area = focus_areas[questions_answered % len(focus_areas)]

            # **QUALITY FIX**: Increase limits and use smart extraction
            kb_content_length = len(kb_content)
            if kb_content_length > 15000:
                kb_content_to_use = self._extract_key_sections_for_training(kb_content, max_length=12000)
            else:
                kb_content_to_use = kb_content

            training_content_to_use = training_content[:4000] if training_content and len(training_content) > 4000 else (training_content or "No training content available")

            prompt = f"""
Generate a UNIQUE multiple-choice question based on the following knowledge base content:

KNOWLEDGE BASE CONTENT:
{kb_content_to_use}

TRAINING CONTENT (if available):
{training_content_to_use}

Requirements:
- This is question #{questions_answered + 1} - make it DIFFERENT from previous questions
- Difficulty level: {difficulty}
- Focus specifically on: {focus_area}
- Include 4 answer options (A, B, C, D) that are plausible but only one correct
- Provide the correct answer
- Include a detailed explanation that references the content
- Create a question that tests a DIFFERENT aspect than typical questions would

Format as JSON:
{{
    "question": "The question text here?",
    "options": {{
        "A": "Option A text",
        "B": "Option B text",
        "C": "Option C text",
        "D": "Option D text"
    }},
    "correct_answer": "A",
    "explanation": "Detailed explanation of why this is correct and why others are wrong, referencing the knowledge base content",
    "difficulty": "{difficulty}",
    "topic": "Main topic area from the content",
    "learning_objective": "What this question tests based on the actual content"
}}

IMPORTANT: Generate a UNIQUE question. Focus on {focus_area}. Do not repeat common question patterns.
"""

            logger.debug("Sending prompt to Bedrock")
            logger.debug(f"   KB content in prompt: {len(kb_content_to_use)} chars")
            logger.debug(f"   First 100 chars of KB content: {kb_content_to_use[:100]}")

            # Call Bedrock with retry logic for throttling
            max_retries = 3
            retry_delay = 2  # Start with 2 seconds

            for attempt in range(max_retries):
                try:
                    response = self.bedrock_client.invoke_model(
                        modelId=BEDROCK_MODEL,
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 1500,
                            "temperature": 0.7,  # Higher temperature for more variation
                            "messages": [{"role": "user", "content": prompt}]
                        })
                    )

                    result = json.loads(response['body'].read())
                    question_json = result['content'][0]['text']
                    break  # Success, exit retry loop

                except Exception as bedrock_error:
                    if "ThrottlingException" in str(bedrock_error) and attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Bedrock throttled, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        import time
                        time.sleep(wait_time)
                    else:
                        raise  # Re-raise if not throttling or last attempt
            
            # Try to parse the JSON response
            try:
                question_data = json.loads(question_json)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                question_data = {
                    "question": "What is the main concept covered in this course material?",
                    "options": {
                        "A": "Basic fundamentals",
                        "B": "Advanced applications",
                        "C": "Theoretical concepts",
                        "D": "Practical implementations"
                    },
                    "correct_answer": "A",
                    "explanation": "This question tests understanding of the foundational concepts.",
                    "difficulty": difficulty,
                    "topic": "General Knowledge",
                    "learning_objective": "Understand core concepts"
                }

            # Ensure the question has a 'type' field (frontend expects this)
            if "type" not in question_data:
                question_data["type"] = "mcq"

            return {
                "status": "completed",
                "question": question_data,
                "session_id": session_id,
                "question_number": questions_answered + 1
            }

        except Exception as e:
            logger.error(f"Failed to generate MCQ question: {e}")
            import traceback
            traceback.print_exc()
            error_msg = str(e) or repr(e) or "Unknown error occurred"
            return {
                "status": "error",
                "message": f"Failed to generate MCQ question: {error_msg}"
            }

    async def _generate_enhanced_question(self, knowledge_base_id: str, session_id: str, question_type: str, questions_answered: int, processed_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a question of specified type (mcq, open_ended, fill_blank, etc.) based on actual KB content."""
        try:
            logger.info("="*80)
            logger.info("🚀 ENHANCED QUESTION GENERATION STARTED")
            logger.info(f"🎯 Question type: {question_type} | Question #{questions_answered + 1}")
            logger.info(f"📦 Processed results received: {processed_results is not None}")
            if processed_results:
                logger.info(f"📦 Processed results keys: {list(processed_results.keys())}")
            logger.info("="*80)

            # Determine difficulty
            if questions_answered < 5:
                difficulty = "beginner"
            elif questions_answered < 15:
                difficulty = "intermediate"
            else:
                difficulty = "advanced"

            # **FAST PATH**: Skip slow memory retrieval, use processed_results directly
            logger.info(f"📦 Processed results provided: {bool(processed_results)}")

            kb_content = ""
            if processed_results:
                logger.info("✅ Using processed_results from backend (fast path)")
                # Extract educational content from processed_results
                if processed_results:
                    # Extract educational content from image results
                    image_results = processed_results.get('image', {}).get('results', {}).get('image', [])
                    logger.info(f"📊 Found {len(image_results) if image_results else 0} image results")
                    if image_results:
                        for result in image_results:
                            edu_content = result.get('content', {}).get('educational_content', {})
                            if edu_content and edu_content.get('full_text_content'):
                                logger.info("✅ Found educational content in processed_results!")
                                kb_content = f"=== EDUCATIONAL CONTENT ===\n{edu_content['full_text_content']}\n"

                                # Add key concepts
                                if edu_content.get('key_concepts'):
                                    kb_content += f"\nKey Concepts: {', '.join(edu_content['key_concepts'])}\n"

                                # Add commands
                                if edu_content.get('commands'):
                                    kb_content += "\nCommands/Functions:\n"
                                    for cmd in edu_content['commands'][:15]:
                                        kb_content += f"  • {cmd.get('name', '')}: {cmd.get('description', '')}\n"

                                logger.info(f"📊 Loaded {len(kb_content)} characters from processed_results")
                                break
                            else:
                                logger.warning(f"⚠️ Image result missing educational_content or full_text_content")

                # Final fallback if still no content
                if not kb_content or len(kb_content) < 500:
                    logger.warning(f"❌ No content available (len={len(kb_content)}), falling back to MCQ")
                    return await self._generate_mcq_question(knowledge_base_id, session_id, questions_answered)

            # Prepare content
            kb_content_length = len(kb_content)
            if kb_content_length > 15000:
                kb_content_to_use = self._extract_key_sections_for_training(kb_content, max_length=12000)
            else:
                kb_content_to_use = kb_content

            # Generate question using training agent
            if training_service and question_type != "mcq":
                logger.info(f"Using training agent to generate {question_type} question")
                assessment = await training_service.training_agent.generate_assessment(
                    kb_content_to_use,
                    {"type": "knowledge_base", "difficulty": difficulty},
                    {
                        "question_types": [question_type],
                        "question_count": 1,
                        "difficulty_levels": [difficulty]
                    }
                )

                if assessment and assessment.questions:
                    question = assessment.questions[0]
                    question_dict = {
                        "type": question.question_type,
                        "question": question.question_text,
                        "difficulty": question.difficulty,
                        "topic": question.topic,
                        "learning_objective": question.learning_objective
                    }

                    # Add type-specific fields
                    if question_type == "open_ended":
                        question_dict["suggested_answer"] = getattr(question, 'suggested_answer', "")
                        question_dict["rubric"] = getattr(question, 'rubric', [])
                    elif question_type == "fill_blank":
                        question_dict["blanks"] = getattr(question, 'blanks', [])
                        question_dict["answers"] = getattr(question, 'answers', [])

                    return {
                        "status": "completed",
                        "question": question_dict,
                        "session_id": session_id,
                        "question_number": questions_answered + 1
                    }
                else:
                    logger.warning("Training agent returned no questions, falling back to MCQ")

            # Fallback to MCQ
            return await self._generate_mcq_question(knowledge_base_id, session_id, questions_answered)

        except Exception as e:
            logger.error(f"Failed to generate {question_type} question: {e}")
            import traceback
            traceback.print_exc()
            error_msg = str(e) or repr(e) or "Unknown error occurred"
            return {
                "status": "error",
                "message": f"Failed to generate {question_type} question: {error_msg}"
            }

    async def _generate_learning_content_from_results(self, knowledge_base_id: str, processed_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate learning content directly from provided processing results."""
        try:
            logger.info(f"Generating learning content from provided results for KB: {knowledge_base_id}")
            logger.debug(f"   Agent types available: {list(processed_results.keys())}")

            if not processed_results:
                return {
                    "status": "error",
                    "message": "No processed results provided"
                }

            # **CRITICAL FIX**: Transform nested structure to flat structure expected by training_service
            # Current: processed_results['audio']['results']['audio'][0]
            # Expected: content_data['audio'][0]
            transformed_data = {}
            for agent_type, agent_data in processed_results.items():
                if isinstance(agent_data, dict) and 'results' in agent_data:
                    # Extract the actual results from nested structure
                    nested_results = agent_data['results']
                    if isinstance(nested_results, dict):
                        # Flatten: {'audio': {'results': {'audio': [...]}} -> {'audio': [...]}
                        transformed_data.update(nested_results)
                    else:
                        transformed_data[agent_type] = nested_results
                else:
                    transformed_data[agent_type] = agent_data

            logger.debug(f"   Transformed structure: {list(transformed_data.keys())}")
            for key, val in transformed_data.items():
                count = len(val) if isinstance(val, list) else 'not a list'
                logger.debug(f"     {key}: {count} items")

            # Use training service to extract learning content
            if training_service:
                result = await training_service.get_learning_content_from_kb(knowledge_base_id, transformed_data)
                return result
            else:
                return {
                    "status": "error",
                    "message": "Training service not available"
                }

        except Exception as e:
            logger.error(f"Failed to generate learning content from results: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Failed to generate learning content: {str(e)}"
            }

    async def _get_learning_content_from_memory(self, knowledge_base_id: str) -> Dict[str, Any]:
        """Get learning content for pre-study phase from local KB storage."""
        try:
            logger.info(f"Retrieving learning content from local storage for KB: {knowledge_base_id}")

            # Load all agent results from local KB storage
            kb_content_data = self.kb_storage.load_agent_results(knowledge_base_id)

            if not kb_content_data:
                logger.error(f"No content data found in local storage for KB {knowledge_base_id}")
                return {
                    "status": "error",
                    "message": "No content available for this knowledge base"
                }

            logger.info(f"Loaded {len(kb_content_data)} agent types from local storage")

            # Use training service to extract learning content
            if training_service:
                result = await training_service.get_learning_content_from_kb(knowledge_base_id, kb_content_data)
                return result
            else:
                return {
                    "status": "error",
                    "message": "Training service not available"
                }

        except Exception as e:
            logger.error(f"Failed to get learning content from local storage: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Failed to get learning content: {str(e)}"
            }


# Global processor
processor = FullCourseProcessor()


@app.entrypoint
def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent entrypoint for full course processing.

    Actions:
    - start_course_processing: Create session and open browser
    - continue_after_login: Start module discovery and processing
    - get_status: Get current processing status
    - stop_processing: Stop and cleanup
    - get_saved_courses: Retrieve saved courses from memory
    """
    try:
        action = payload.get("action")

        if action == "start_course_processing":
            import time
            session_id = payload.get("session_id", f"session{int(time.time())}")
            course_url = payload.get("course_url")
            user_id = payload.get("user_id", "unknown")

            result = asyncio.run(processor.start_course_processing(
                session_id, course_url, user_id
            ))
            return result

        elif action == "continue_after_login":
            session_id = payload.get("session_id")
            result = asyncio.run(processor.continue_after_login(session_id))
            return result

        elif action == "get_status":
            session_id = payload.get("session_id")
            result = asyncio.run(processor.get_status(session_id))
            return result

        elif action == "stop_processing":
            session_id = payload.get("session_id")
            result = asyncio.run(processor.stop_processing(session_id))
            return result

        elif action == "get_saved_courses":
            user_id = payload.get("user_id", "unknown")
            query = payload.get("query")
            result = processor.get_saved_courses(user_id, query)
            return result

        elif action == "get_course_details":
            user_id = payload.get("user_id", "unknown")
            course_id = payload.get("course_id")
            result = processor.get_course_details(user_id, course_id)
            return result

        elif action == "get_dcv_url":
            session_id = payload.get("session_id")
            mcp_session_id = payload.get("mcp_session_id")
            result = processor.get_dcv_presigned_url(session_id, mcp_session_id)
            return result

        elif action == "start_file_processing":
            import time
            session_id = payload.get("session_id", f"file_session_{int(time.time())}")
            file_paths = payload.get("file_paths", [])
            user_id = payload.get("user_id", "unknown")
            processing_options = payload.get("processing_options")
            result = asyncio.run(processor.start_file_processing(session_id, file_paths, user_id, processing_options))
            return result

        elif action == "process_uploaded_files":
            # Check if async mode is requested
            async_mode = payload.get("async_mode", False)

            if async_mode:
                # Use new async method
                import time
                session_id = payload.get("session_id", f"file_session_{int(time.time())}")
                file_paths = payload.get("file_paths", [])
                user_id = payload.get("user_id", "unknown")
                processing_options = payload.get("processing_options")
                result = asyncio.run(processor.start_file_processing(session_id, file_paths, user_id, processing_options))
                return result
            else:
                # Use legacy synchronous method (for backward compatibility)
                file_paths = payload.get("file_paths", [])
                user_id = payload.get("user_id", "unknown")
                processing_options = payload.get("processing_options")
                result = asyncio.run(processor.process_uploaded_files(file_paths, user_id, processing_options))
                return result

        elif action == "process_direct_links":
            links = payload.get("links", [])
            user_id = payload.get("user_id", "unknown")
            processing_options = payload.get("processing_options")
            result = asyncio.run(processor.process_direct_links(links, user_id, processing_options))
            return result

        elif action == "process_mixed_content":
            course_url = payload.get("course_url")
            file_paths = payload.get("file_paths")
            direct_links = payload.get("direct_links")
            user_id = payload.get("user_id", "unknown")
            processing_options = payload.get("processing_options")
            result = asyncio.run(processor.process_mixed_content(
                course_url, file_paths, direct_links, user_id, processing_options
            ))
            return result

        elif action == "validate_links":
            links = payload.get("links", [])
            user_id = payload.get("user_id", "unknown")
            # For now, return a simple validation response
            # In production, this would use the link validation service
            return {
                "status": "completed",
                "validated_links": [{"url": link, "status": "valid"} for link in links],
                "message": f"Validated {len(links)} links"
            }

        elif action == "generate_training_content":
            knowledge_base_id = payload.get("knowledge_base_id")
            user_id = payload.get("user_id", "unknown")
            result = asyncio.run(processor._generate_training_content_with_retry(knowledge_base_id, user_id))
            return result

        elif action == "generate_mcq_question":
            knowledge_base_id = payload.get("knowledge_base_id")
            session_id = payload.get("session_id")
            questions_answered = payload.get("questions_answered", 0)
            processed_results = payload.get("processed_results")  # Get processed_results from payload
            result = asyncio.run(processor._generate_mcq_question(knowledge_base_id, session_id, questions_answered, processed_results))
            return result

        elif action == "generate_enhanced_question":
            logger.info("🔥 INVOKE HANDLER: generate_enhanced_question called")
            knowledge_base_id = payload.get("knowledge_base_id")
            session_id = payload.get("session_id")
            question_type = payload.get("question_type", "mcq")
            questions_answered = payload.get("questions_answered", 0)
            processed_results = payload.get("processed_results")  # Get processed_results from payload
            logger.info(f"🔥 INVOKE HANDLER: processed_results present = {processed_results is not None}")
            if processed_results:
                logger.info(f"🔥 INVOKE HANDLER: processed_results keys = {list(processed_results.keys())}")
            result = asyncio.run(processor._generate_enhanced_question(knowledge_base_id, session_id, question_type, questions_answered, processed_results))
            logger.info("🔥 INVOKE HANDLER: Returning result")
            return result

        elif action == "get_learning_content":
            knowledge_base_id = payload.get("knowledge_base_id")
            result = asyncio.run(processor._get_learning_content_from_memory(knowledge_base_id))
            return result

        elif action == "generate_learning_content_from_results":
            knowledge_base_id = payload.get("knowledge_base_id")
            processed_results = payload.get("processed_results", {})
            result = asyncio.run(processor._generate_learning_content_from_results(knowledge_base_id, processed_results))
            return result

        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


if __name__ == "__main__":
    # Add CORS middleware before running the app
    try:
        from fastapi.middleware.cors import CORSMiddleware
        import inspect

        # Get the actual FastAPI instance from BedrockAgentCoreApp
        for attr_name in dir(app):
            attr = getattr(app, attr_name)
            if hasattr(attr, 'add_middleware') and not attr_name.startswith('_'):
                attr.add_middleware(
                    CORSMiddleware,
                    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
                logger.info(f"CORS enabled on {attr_name}")
                break
    except Exception as e:
        logger.warning(f"CORS setup skipped: {e}")

    app.run()
