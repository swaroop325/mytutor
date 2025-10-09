"""
Full course processor with module-by-module navigation.
Handles complete course extraction including text, audio, video.
Uses AgentCore memory for persistent knowledge base storage.
Supports YouTube video analysis via browser automation.
"""
import os
import asyncio
import base64
import json
import re
import threading
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.tools.browser_client import BrowserClient
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import SemanticStrategy

# Import training service for assessment generation
try:
    from services.training_service import training_service
except ImportError:
    print("⚠️ Training service not available")
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

print("🔧 Configuring CORS for frontend access...")

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
    """Complete course processor with module navigation and memory integration."""

    def __init__(self, region: str = AWS_REGION):
        self.region = region
        # Initialize Strands agent (will use default Bedrock configuration)
        self.agent = Agent()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)

        # Initialize memory manager (non-blocking)
        self.memory_manager = MemoryManager(region_name=region)
        self.memory = None
        # Note: Memory initialization happens lazily on first use to avoid blocking startup

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

        print(f"📄 Split content into {len(chunks)} contextual chunks to preserve all information")
        return chunks
    
    def _init_memory(self):
        """Initialize or get existing memory for course knowledge bases."""
        try:
            print("🔄 Initializing AgentCore Memory...")
            memory = self.memory_manager.get_or_create_memory(
                name="MyTutorCourseKnowledgeBase",
                description="Persistent storage for processed course content and knowledge",
                strategies=[
                    SemanticStrategy(
                        name="courseSemanticMemory",
                        namespaces=['/strategies/{memoryStrategyId}/actors/{actorId}/sessions/{sessionId}']
                    )
                ]
            )
            print(f"✅ Memory initialized: {memory.get('id')}")
            return memory
        except Exception as e:
            print(f"❌ Warning: Could not initialize memory: {e}")
            print("⚠️  Agent will continue without persistent storage")
            return None

    def _save_module_to_memory(self, user_id: str, course_id: str, module: CourseModule):
        """Save module content to persistent memory."""
        # Lazily initialize memory on first use
        if self.memory is None:
            self.memory = self._init_memory()

        if not self.memory:
            return

        try:
            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )

            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=course_id
            )

            # Store module content as conversational message with size limits
            header_info = f"""
Module: {module.title}
URL: {module.url}
Order: {module.order}

Content:
"""
            footer_info = f"""

Videos: {len(module.videos)} found
Audio: {len(module.audios)} found
Files: {len(module.files)} found
"""
            
            # Calculate available space for content
            header_size = len(header_info)
            footer_size = len(footer_info)
            max_content_size = 8500 - header_size - footer_size  # Leave buffer
            
            # Truncate content if necessary
            if len(module.text_content) > max_content_size:
                truncated_content = module.text_content[:max_content_size] + "\n\n[Content truncated due to size limits...]"
                print(f"⚠️ Module content truncated from {len(module.text_content)} to {len(truncated_content)} characters")
            else:
                truncated_content = module.text_content
            
            module_content = f"""
Module: {module.title}
URL: {module.url}
Order: {module.order}

Content:
{truncated_content}

Videos: {len(module.videos)} found
Audio: {len(module.audios)} found
Files: {len(module.files)} found
"""
            
            # Final safety check
            if len(module_content) > 9000:
                module_content = module_content[:8900] + "\n\n[Content truncated to fit memory limits]"
                print(f"⚠️ Emergency truncation applied to module content, final size: {len(module_content)} characters")

            session.add_turns(
                messages=[
                    ConversationalMessage(
                        module_content,
                        MessageRole.ASSISTANT
                    )
                ]
            )
            print(f"✅ Saved module '{module.title}' to memory")

        except Exception as e:
            print(f"Warning: Could not save module to memory: {e}")

    def _save_summary_to_memory(self, user_id: str, course_id: str, summary: Dict[str, Any]):
        """Save course summary to persistent memory."""
        # Lazily initialize memory on first use
        if self.memory is None:
            self.memory = self._init_memory()

        if not self.memory:
            return

        try:
            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )

            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=f"{course_id}_summary"
            )

            # Store summary
            summary_content = f"""
Course Summary:
Title: {summary.get('title', 'Unknown')}
Total Modules: {summary.get('total_modules', 0)}

Overview:
{summary.get('overview', '')}

Key Topics:
{', '.join(summary.get('key_topics', []))}

Learning Outcomes:
{chr(10).join(f"- {outcome}" for outcome in summary.get('learning_outcomes', []))}
"""

            # Store summary with chunking if needed
            summary_chunks = self._chunk_content_for_memory(summary_content)

            for chunk in summary_chunks:
                # Final safety check: AgentCore Memory has 9000 char limit per turn
                if len(chunk) > 9000:
                    print(f"⚠️ WARNING: Summary chunk too large ({len(chunk)} chars), truncating")
                    chunk = chunk[:8900] + "\n\n[Content truncated due to size limit]"

                session.add_turns(
                    messages=[
                        ConversationalMessage(
                            chunk,
                            MessageRole.ASSISTANT
                        )
                    ]
                )
            
            if len(summary_chunks) > 1:
                print(f"✅ Stored course summary in {len(summary_chunks)} chunks")
            else:
                print(f"✅ Stored course summary in memory")
            print(f"✅ Saved course summary to memory")

        except Exception as e:
            print(f"Warning: Could not save summary to memory: {e}")

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
            print(f"📹 Detected YouTube URL, using browser-based analysis...")

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
                        print(f"⚠️ Connection limit reached, retrying in 5 seconds... (attempt {attempt + 1}/{max_retries})")
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
                print("🎬 YouTube video loaded, analyzing content...")
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

                print(f"✅ YouTube video analyzed and saved to knowledge base")

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
            print(f"Error discovering modules: {e}")
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
            print(f"Error extracting module content: {e}")
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
            return {
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
                "started_at": session.get("started_at")
            }

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
        """Retrieve saved courses from memory for a user."""
        # Lazily initialize memory on first use
        if self.memory is None:
            self.memory = self._init_memory()

        if not self.memory:
            return {
                "status": "error",
                "message": "Memory not initialized",
                "courses": []
            }

        try:
            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )

            # Create a temporary session to query memory
            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=f"query_{int(datetime.utcnow().timestamp())}"
            )

            if query:
                # Semantic search for specific courses
                memory_records = session.search_long_term_memories(
                    query=query,
                    namespace_prefix="/",
                    top_k=10
                )
            else:
                # List all memory records for this user
                memory_records = session.list_long_term_memory_records(
                    namespace_prefix="/"
                )

            # Parse and format results - filter for summaries and extract structured data
            courses = []
            course_map = {}  # Group by course_id

            for record in memory_records:
                namespace = record.get("namespace", "")
                content_text = record.get("content", {}).get("text", "")

                # Check if this is a summary record
                if "_summary" in namespace:
                    # Extract course_id from namespace
                    course_id = namespace.split("/")[-1].replace("_summary", "")

                    # Parse summary content
                    course_data = self._parse_course_summary(content_text, course_id)
                    course_data["id"] = record.get("memoryRecordId")
                    course_data["created_at"] = record.get("createdAt")
                    course_data["namespace"] = namespace

                    course_map[course_id] = course_data
                    courses.append(course_data)

            return {
                "status": "success",
                "courses": courses,
                "total": len(courses)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to retrieve courses: {str(e)}",
                "courses": []
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
        """Retrieve full course details including all modules."""
        # Lazily initialize memory on first use
        if self.memory is None:
            self.memory = self._init_memory()

        if not self.memory:
            return {
                "status": "error",
                "message": "Memory not initialized"
            }

        try:
            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )

            # Create a temporary session to query memory
            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=f"query_{int(datetime.utcnow().timestamp())}"
            )

            # Get all memory records for this course
            memory_records = session.list_long_term_memory_records(
                namespace_prefix=f"/"
            )

            # Separate modules and summary
            modules = []
            summary = None

            for record in memory_records:
                namespace = record.get("namespace", "")
                content_text = record.get("content", {}).get("text", "")

                if course_id in namespace:
                    if "_summary" in namespace:
                        # This is the summary
                        summary = self._parse_course_summary(content_text, course_id)
                    else:
                        # This is a module
                        module_data = self._parse_module_content(content_text)
                        module_data["record_id"] = record.get("memoryRecordId")
                        modules.append(module_data)

            # Sort modules by order
            modules.sort(key=lambda x: x.get("order", 0))

            if not summary:
                return {
                    "status": "error",
                    "message": "Course not found"
                }

            # Combine summary and modules
            return {
                "status": "success",
                "course": {
                    **summary,
                    "modules": modules
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to retrieve course details: {str(e)}"
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
            print(f"❌ Error generating presigned URL: {e}")
            print(traceback.format_exc())
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
                print(f"📋 Auto-generated knowledge base ID: {kb_id}")

            print(f"🚀 Starting async file processing session {session_id} for {len(file_paths)} files")

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
            print(f"❌ Failed to start file processing: {str(e)}")
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

            print(f"🤖 Processing {len(file_paths)} files with specialized agents for KB {kb_id}")

            # Use the specialized agent system
            result = await file_processor.process_files_with_agents(file_paths, user_id)

            # Update progress
            session["processed_files"] = len(file_paths)
            session["progress"] = 100

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

            print(f"✅ {agent_type.upper()} Agent completed processing for session {session_id}")

        except Exception as e:
            print(f"❌ Specialized agents failed: {str(e)}")
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
                print(f"📋 Auto-generated knowledge base ID: {kb_id}")

            print(f"🤖 Processing {len(file_paths)} files with specialized agents for KB {kb_id}")

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

            print(f"✅ {agent_type.upper()} Agent completed processing for KB {kb_id}")
            return result

        except Exception as e:
            print(f"❌ Specialized agents failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process uploaded files: {str(e)}"
            }
    
    async def _store_agent_results_in_memory(self, kb_id: str, user_id: str, result: Dict[str, Any], agent_type: str):
        """Store specialized agent results in AgentCore Memory."""
        try:
            if self.memory is None:
                self.memory = self._init_memory()
            
            if not self.memory:
                return
            
            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )
            
            # Store results for each agent type
            for agent_type, agent_results in result.get("results", {}).items():
                session_id = self._clean_session_id(f"{kb_id}_{agent_type}_results")
                
                session = session_manager.create_memory_session(
                    actor_id=user_id,
                    session_id=session_id
                )
                
                # Compile content from all files processed by this agent
                agent_content = f"""
Agent Type: {agent_type.upper()}
Knowledge Base: {kb_id}
Files Processed: {len(agent_results)}
Processing Date: {datetime.now().isoformat()}

Results Summary:
"""
                
                for i, file_result in enumerate(agent_results, 1):
                    if file_result.get('status') == 'completed':
                        agent_content += f"""

--- File {i}: {os.path.basename(file_result.get('file_path', 'unknown'))} ---
Content: {file_result.get('content', {}).get('text', '')[:1000]}...
Analysis: {file_result.get('analysis', {}).get('ai_analysis', 'No analysis')[:500]}...
"""
                
                # Split content into chunks to preserve all information
                content_chunks = self._chunk_content_for_memory(agent_content)

                for chunk in content_chunks:
                    # Final safety check: AgentCore Memory has 9000 char limit per turn
                    if len(chunk) > 9000:
                        print(f"⚠️ WARNING: Chunk too large ({len(chunk)} chars), truncating to 8900 chars")
                        chunk = chunk[:8900] + "\n\n[Content truncated due to size limit]"

                    session.add_turns(
                        messages=[
                            ConversationalMessage(
                                chunk,
                                MessageRole.ASSISTANT
                            )
                        ]
                    )
                
                if len(content_chunks) > 1:
                    print(f"✅ Stored {agent_type} agent results in {len(content_chunks)} chunks for KB {kb_id}")
                else:
                    print(f"✅ Stored {agent_type} agent results in memory for KB {kb_id}")
                
                print(f"✅ Stored {agent_type} agent results in memory for KB {kb_id}")
                
        except Exception as e:
            print(f"⚠️ Could not store agent results in memory: {e}")
    
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
            print(f"⚠️ Error generating comprehensive analysis: {e}")
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
            print(f"🔄 Processing {len(links)} direct links for user {user_id}")
            
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
            print(f"🔄 Processing mixed content for user {user_id}")
            
            session_id = f"mixed_{abs(hash(f'{course_url}_{file_paths}_{direct_links}')) % 10000000}"
            results = {
                "session_id": session_id,
                "status": "processing",
                "content_sources": {},
                "message": "Processing mixed content sources"
            }
            
            # Process course URL if provided
            if course_url:
                print("📄 Processing course URL...")
                course_result = await self.start_course_processing(
                    session_id=f"{session_id}_course",
                    course_url=course_url,
                    user_id=user_id
                )
                results["content_sources"]["course_url"] = course_result
            
            # Process uploaded files if provided
            if file_paths:
                print("📁 Processing uploaded files...")
                files_result = await self.process_uploaded_files(
                    file_paths=file_paths,
                    user_id=user_id,
                    processing_options=processing_options
                )
                results["content_sources"]["uploaded_files"] = files_result
            
            # Process direct links if provided
            if direct_links:
                print("🔗 Processing direct links...")
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
        """Store processed content in AgentCore Memory for the knowledge base."""
        try:
            # Lazily initialize memory on first use
            if self.memory is None:
                self.memory = self._init_memory()

            if not self.memory:
                print(f"⚠️ Memory not available, skipping storage for {agent_type} agent")
                return

            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )

            # Create a session for this knowledge base and agent type
            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=self._clean_session_id(f"{kb_id}_{agent_type}")
            )

            # Prepare content for storage
            content_summary = f"Knowledge Base: {kb_id}\nAgent: {agent_type.upper()}\nProcessed: {datetime.utcnow().isoformat()}\n\n"
            
            for file_result in processing_result.get("processed_files", []):
                content = file_result.get("content", {})
                analysis = file_result.get("analysis", {})
                filename = file_result.get("filename", "unknown")

                # Extract content from various fields
                text = content.get("text_content", "") or content.get("text", "") or content.get("full_text", "")
                description = content.get("description", "")
                transcript = content.get("transcript", "")

                # Extract AI analysis (this is where video/image content lives)
                ai_analysis = analysis.get("ai_analysis", "")

                file_content = f"File: {filename}\n"
                if text:
                    file_content += f"Text Content:\n{text[:3000]}\n\n"
                if description:
                    file_content += f"Description:\n{description}\n\n"
                if transcript:
                    file_content += f"Transcript:\n{transcript[:3000]}\n\n"
                if ai_analysis:
                    file_content += f"AI Analysis:\n{ai_analysis}\n\n"

                # If no content extracted, log warning
                if not (text or description or transcript or ai_analysis):
                    print(f"⚠️ No content extracted from {filename} in {agent_type} agent")
                    file_content += f"[No content extracted]\n\n"

                content_summary += file_content + "---\n\n"

            # Store in memory with contextual chunking
            content_chunks = self._chunk_content_for_memory(content_summary)

            for chunk in content_chunks:
                # Final safety check: AgentCore Memory has 9000 char limit per turn
                if len(chunk) > 9000:
                    print(f"⚠️ WARNING: Content chunk too large ({len(chunk)} chars), truncating")
                    chunk = chunk[:8900] + "\n\n[Content truncated due to size limit]"

                session.add_turns(
                    messages=[
                        ConversationalMessage(
                            chunk,
                            MessageRole.ASSISTANT
                        )
                    ]
                )
            
            if len(content_chunks) > 1:
                print(f"✅ Stored content summary in {len(content_chunks)} chunks for KB {kb_id}")
            else:
                print(f"✅ Stored content summary in memory for KB {kb_id}")
            
            print(f"✅ Stored {agent_type} content in AgentCore Memory for KB {kb_id}")

        except Exception as e:
            print(f"❌ Failed to store {agent_type} content in memory: {e}")

    async def _store_analysis_in_memory(self, kb_id: str, user_id: str, analysis: str, agent_type: str):
        """Store AI analysis in AgentCore Memory."""
        try:
            if self.memory is None:
                self.memory = self._init_memory()

            if not self.memory:
                return

            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )

            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=self._clean_session_id(f"{kb_id}_{agent_type}_analysis")
            )

            analysis_content = f"Knowledge Base: {kb_id}\nAgent: {agent_type.upper()} Analysis\nGenerated: {datetime.utcnow().isoformat()}\n\nAnalysis:\n{analysis}"

            # Chunk analysis if needed
            analysis_chunks = self._chunk_content_for_memory(analysis_content)

            for chunk in analysis_chunks:
                # Final safety check
                if len(chunk) > 9000:
                    print(f"⚠️ WARNING: Analysis chunk too large ({len(chunk)} chars), truncating")
                    chunk = chunk[:8900] + "\n\n[Content truncated due to size limit]"

                session.add_turns(
                    messages=[
                        ConversationalMessage(
                            chunk,
                            MessageRole.ASSISTANT
                        )
                    ]
                )
            
            print(f"✅ Stored {agent_type} analysis in AgentCore Memory for KB {kb_id}")

        except Exception as e:
            print(f"❌ Failed to store {agent_type} analysis in memory: {e}")

    async def _retrieve_kb_content_from_memory(self, kb_id: str, user_id: str) -> str:
        """Retrieve all content for a knowledge base from AgentCore Memory."""
        try:
            # Use the course memory where content is actually stored
            if self.memory is None:
                self.memory = self._init_memory()

            course_memory = self.memory

            if not course_memory:
                print("❌ Could not access course memory for content retrieval")
                return ""

            # For backward compatibility, also check file memory
            file_memory = self.memory_manager.get_or_create_memory(
                name="MyTutorFileKnowledgeBase",
                description="Storage for processed file content",
                strategies=[
                    SemanticStrategy(
                        name="fileSemanticMemory",
                        namespaces=['/strategies/{memoryStrategyId}/actors/{actorId}/sessions/{sessionId}']
                    )
                ]
            )

            if not file_memory:
                print("❌ Could not access file memory for content retrieval")
                return ""

            # Retrieve content from all agent types
            agent_types = ["pdf", "video", "audio", "image", "text"]
            all_content = []

            print(f"🔍 Retrieving KB content from memory for KB {kb_id}")

            # Try course memory first (where current content is stored), then file memory (backward compatibility)
            memories_to_check = [
                ("course", course_memory),
                ("file", file_memory)
            ]

            for agent_type in agent_types:
                content_found = False

                for memory_name, memory_instance in memories_to_check:
                    if content_found:
                        break

                    try:
                        session_manager = MemorySessionManager(
                            memory_id=memory_instance.get("id"),
                            region_name=self.region
                        )

                        # Try both session ID formats to handle different storage methods
                        session_ids_to_try = [
                            self._clean_session_id(f"{kb_id}_{agent_type}_results"),  # New format
                            self._clean_session_id(f"{kb_id}_{agent_type}")          # Legacy format
                        ]

                        for session_id in session_ids_to_try:
                            if content_found:
                                break
                            try:
                                print(f"  📂 [{memory_name}] Looking for {agent_type} content with session_id: {session_id}")

                                session = session_manager.create_memory_session(
                                    actor_id=user_id,
                                    session_id=session_id
                                )

                                if session is None:
                                    print(f"  ⚠️ Session creation returned None for {session_id}")
                                    continue

                                # Get the events (stored content) using list_events instead of get_conversation_history
                                events = session_manager.list_events(
                                    actor_id=user_id,
                                    session_id=session_id
                                )
                                print(f"  📝 Found {len(events)} events for {agent_type} with session {session_id} in {memory_name} memory")

                                if events:
                                    content_found = True
                                    for event in events:
                                        if event.get('payload'):
                                            for payload_item in event['payload']:
                                                if payload_item.get('conversational', {}).get('content', {}).get('text'):
                                                    content_text = payload_item['conversational']['content']['text']
                                                    content_preview = content_text[:100] + "..." if len(content_text) > 100 else content_text
                                                    print(f"  ✅ [{memory_name}] Retrieved {agent_type} content: {content_preview}")
                                                    all_content.append(f"=== {agent_type.upper()} AGENT CONTENT ===\n{content_text}\n")
                                    break  # Found content, no need to try other session IDs

                            except Exception as session_e:
                                print(f"  ⚠️ Could not retrieve from session {session_id} in {memory_name} memory: {session_e}")
                                continue

                    except Exception as e:
                        print(f"⚠️ Could not retrieve {agent_type} content from {memory_name} memory: {e}")
                        continue

                if not content_found:
                    print(f"  ❌ No content found for {agent_type} agent in any memory or session format")

            total_chars = sum(len(c) for c in all_content)
            print(f"📊 Total content retrieved: {len(all_content)} sections, {total_chars} characters")

            return "\n".join(all_content) if all_content else ""

        except Exception as e:
            print(f"❌ Failed to retrieve KB content from memory: {e}")
            return ""

    async def _retrieve_training_content_from_memory(self, kb_id: str, user_id: str) -> str:
        """Retrieve training content for a knowledge base from AgentCore Memory."""
        try:
            if self.memory is None:
                self.memory = self._init_memory()

            if not self.memory:
                return ""

            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )

            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=self._clean_session_id(f"{kb_id}_training_content")
            )

            # Get the conversation history (stored training content)
            messages = session.get_conversation_history()
            for message in messages:
                if message.content and "Training Content Generated:" in message.content:
                    # Extract just the training content part
                    content_parts = message.content.split("Training Content Generated:")
                    if len(content_parts) > 1:
                        return content_parts[1].strip()

            return ""

        except Exception as e:
            print(f"❌ Failed to retrieve training content from memory: {e}")
            return ""

    def _clean_session_id(self, session_id: str) -> str:
        """Clean session ID to match AWS pattern: [a-zA-Z0-9][a-zA-Z0-9-_]*"""
        # Remove hyphens and underscores, keep only alphanumeric
        cleaned = ''.join(c for c in session_id if c.isalnum())
        # Ensure it starts with alphanumeric and limit length
        return cleaned[:50] if cleaned else "defaultSession"
    
    async def _store_comprehensive_analysis(self, kb_id: str, user_id: str, analysis: str):
        """Store comprehensive analysis in AgentCore Memory."""
        try:
            memory_id = f"MyTutorFileKnowledgeBase-{kb_id[:10]}"
            
            # Create or get memory
            memory = await self.memory_manager.create_memory(
                memory_id=memory_id,
                memory_type="SEMANTIC",
                name="fileSemanticMemory"
            )
            
            # Store the comprehensive analysis (clean session ID for AWS)
            session_id = self._clean_session_id(f"comprehensiveAnalysis{kb_id}")
            
            await self.memory_manager.store_turn(
                memory_id=memory_id,
                session_id=session_id,
                user_message="Comprehensive Analysis Request",
                assistant_message=analysis,
                metadata={
                    "type": "comprehensive_analysis",
                    "knowledge_base_id": kb_id,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            print(f"✅ Stored comprehensive analysis in memory for KB {kb_id}")
            
        except Exception as e:
            print(f"❌ Failed to store comprehensive analysis in memory: {e}")

    async def _store_training_content_in_memory(self, kb_id: str, user_id: str, training_content: str):
        """Store generated training content in AgentCore Memory."""
        try:
            if self.memory is None:
                self.memory = self._init_memory()

            if not self.memory:
                return

            session_manager = MemorySessionManager(
                memory_id=self.memory.get("id"),
                region_name=self.region
            )

            session = session_manager.create_memory_session(
                actor_id=user_id,
                session_id=self._clean_session_id(f"{kb_id}_training_content")
            )

            content = f"Knowledge Base: {kb_id}\nTraining Content Generated: {datetime.utcnow().isoformat()}\n\n{training_content}"

            # Chunk training content if needed
            content_chunks = self._chunk_content_for_memory(content)

            for chunk in content_chunks:
                # Final safety check
                if len(chunk) > 9000:
                    print(f"⚠️ WARNING: Training chunk too large ({len(chunk)} chars), truncating")
                    chunk = chunk[:8900] + "\n\n[Content truncated due to size limit]"

                session.add_turns(
                    messages=[
                        ConversationalMessage(
                            chunk,
                            MessageRole.ASSISTANT
                        )
                    ]
                )
            
            print(f"✅ Stored training content in AgentCore Memory for KB {kb_id}")

        except Exception as e:
            print(f"❌ Failed to store training content in memory: {e}")

    def _extract_key_sections_for_training(self, content: str, max_length: int = 25000) -> str:
        """Extract key sections from content intelligently instead of blind truncation."""
        if len(content) <= max_length:
            return content

        print(f"📚 Extracting key sections from {len(content):,} chars (target: {max_length:,} chars)")

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
        print(f"✅ Extracted {len(result):,} chars ({len(result_sections)} sections)")
        return result

    async def _generate_training_content_with_retry(self, knowledge_base_id: str, user_id: str, max_retries: int = 5) -> Dict[str, Any]:
        """Generate training content with aggressive retry and backoff strategy."""
        for attempt in range(max_retries):
            try:
                print(f"🧠 Generating training content (attempt {attempt + 1}/{max_retries}) for KB {knowledge_base_id}")
                
                # Add progressive delay to avoid hitting rate limits
                if attempt > 0:
                    delay = min(60, 10 * (2 ** (attempt - 1)))  # Cap at 60 seconds
                    print(f"⏳ Waiting {delay}s before retry to respect rate limits...")
                    await asyncio.sleep(delay)
                
                result = await self._generate_training_content_from_kb(knowledge_base_id, user_id)
                
                if result.get("status") == "completed":
                    print(f"✅ Training content generated successfully on attempt {attempt + 1}")
                    return result
                elif "ThrottlingException" in str(result.get("message", "")):
                    print(f"⚠️ Throttled on attempt {attempt + 1}, will retry...")
                    continue
                else:
                    print(f"❌ Non-throttling error: {result.get('message')}")
                    return result
                    
            except Exception as e:
                import traceback
                error_msg = str(e) if str(e) else repr(e)
                if "ThrottlingException" in error_msg or "Too many requests" in error_msg:
                    print(f"⚠️ Throttling exception on attempt {attempt + 1}: {error_msg}")
                    if attempt == max_retries - 1:
                        return {
                            "status": "error",
                            "message": f"Failed after {max_retries} attempts due to throttling: {error_msg}",
                            "error_type": type(e).__name__
                        }
                    continue
                else:
                    print(f"❌ Unexpected error: {error_msg}")
                    print(f"Traceback:\n{traceback.format_exc()}")
                    return {"status": "error", "message": error_msg, "error_type": type(e).__name__}
        
        return {"status": "error", "message": f"Failed to generate training content after {max_retries} attempts"}

    async def _generate_training_content_from_kb(self, knowledge_base_id: str, user_id: str) -> Dict[str, Any]:
        """Generate comprehensive training content from AgentCore Memory knowledge base."""
        try:
            print(f"🧠 Generating training content from AgentCore Memory for KB {knowledge_base_id}")
            
            # Retrieve content from AgentCore Memory
            kb_content = await self._retrieve_kb_content_from_memory(knowledge_base_id, user_id)
            
            if not kb_content:
                print(f"❌ ERROR: No content found in memory for KB {knowledge_base_id}")
                return {
                    "status": "error",
                    "message": "No content available in knowledge base. Please ensure files were processed successfully."
                }

            content_length = len(kb_content)
            print(f"📊 KB content: {content_length:,} characters")

            # **QUALITY FIX**: Use intelligent extraction instead of blind 8K truncation
            if content_length > 30000:
                print(f"📚 Content is long, extracting key sections...")
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
            print(f"❌ Failed to generate training content: {error_msg}")
            print(f"Full traceback:\n{error_details}")
            return {
                "status": "error",
                "message": f"Failed to generate training content: {error_msg}",
                "error_type": type(e).__name__,
                "traceback": error_details
            }

    async def _generate_mcq_question(self, knowledge_base_id: str, session_id: str, questions_answered: int) -> Dict[str, Any]:
        """Generate a single MCQ question for training based on actual knowledge base content."""
        try:
            # Determine difficulty based on progress
            if questions_answered < 5:
                difficulty = "beginner"
            elif questions_answered < 15:
                difficulty = "intermediate"
            else:
                difficulty = "advanced"
            
            # Retrieve actual content from the knowledge base
            user_id = session_id.split('_')[0] if '_' in session_id else "admin"  # Extract user_id from session_id
            kb_content = await self._retrieve_kb_content_from_memory(knowledge_base_id, user_id)
            
            if not kb_content:
                print(f"⚠️ No content found in memory for KB {knowledge_base_id}, using fallback")
                kb_content = "No specific content available. Generate general educational questions."
            
            # Also try to get training content if available
            training_content = await self._retrieve_training_content_from_memory(knowledge_base_id, user_id)

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
            return {
                "status": "error",
                "message": f"Failed to generate MCQ question: {str(e)}"
            }

    async def _generate_learning_content_from_results(self, knowledge_base_id: str, processed_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate learning content directly from provided processing results."""
        try:
            print(f"📚 Generating learning content from provided results for KB: {knowledge_base_id}")
            print(f"   Agent types available: {list(processed_results.keys())}")

            if not processed_results:
                return {
                    "status": "error",
                    "message": "No processed results provided"
                }

            # Use training service to extract learning content
            if training_service:
                result = await training_service.get_learning_content_from_kb(knowledge_base_id, processed_results)
                return result
            else:
                return {
                    "status": "error",
                    "message": "Training service not available"
                }

        except Exception as e:
            logger.error(f"Failed to generate learning content from results: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate learning content: {str(e)}"
            }

    async def _get_learning_content_from_memory(self, knowledge_base_id: str) -> Dict[str, Any]:
        """Get learning content for pre-study phase from knowledge base."""
        try:
            print(f"📚 Retrieving learning content for KB: {knowledge_base_id}")

            # First, try to get the user_id from the knowledge base metadata
            memory = self._init_memory()
            memory_id = memory['id']

            # Retrieve processed content from memory
            kb_content_data = {}

            try:
                session = self._get_or_create_session(memory_id, "admin", knowledge_base_id)
                session_id = session['sessionId']

                # Search for knowledge base results in memory
                messages = await asyncio.to_thread(
                    self.memory_manager.memory_client.search_memory,
                    memoryId=memory_id,
                    memoryStorageType="session",
                    sessionId=session_id,
                    searchText=f"knowledge_base_id:{knowledge_base_id}",
                    maxResults=100
                )

                if messages and 'messages' in messages:
                    for msg in messages['messages']:
                        content = msg.get('content', [{}])[0].get('text', '')
                        if content:
                            try:
                                data = json.loads(content)
                                if isinstance(data, dict) and 'agent_type' in data:
                                    agent_type = data['agent_type']
                                    if agent_type not in kb_content_data:
                                        kb_content_data[agent_type] = []
                                    kb_content_data[agent_type].append(data)
                            except json.JSONDecodeError:
                                continue

            except Exception as e:
                print(f"⚠️ Could not retrieve content from memory: {e}")

            if not kb_content_data:
                print(f"❌ No content data found for KB {knowledge_base_id}")
                return {
                    "status": "error",
                    "message": "No content available for this knowledge base"
                }

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
            logger.error(f"Failed to get learning content: {e}")
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
            result = asyncio.run(processor._generate_mcq_question(knowledge_base_id, session_id, questions_answered))
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
                print(f"✅ CORS enabled on {attr_name}")
                break
    except Exception as e:
        print(f"⚠️  CORS setup skipped: {e}")

    app.run()
