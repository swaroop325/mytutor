"""
Full course processor with module-by-module navigation.
Handles complete course extraction including text, audio, video.
Uses AgentCore memory for persistent knowledge base storage.
"""
import os
import asyncio
import base64
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.tools.browser_client import BrowserClient
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import SemanticStrategy
from playwright.async_api import async_playwright, Page, Browser, Download
from strands import Agent
import boto3
from pathlib import Path

app = BedrockAgentCoreApp()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

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

            # Store module content as conversational message
            module_content = f"""
Module: {module.title}
URL: {module.url}
Order: {module.order}

Content:
{module.text_content[:10000]}

Videos: {len(module.videos)} found
Audio: {len(module.audios)} found
Files: {len(module.files)} found
"""

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

            session.add_turns(
                messages=[
                    ConversationalMessage(
                        summary_content,
                        MessageRole.ASSISTANT
                    )
                ]
            )
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
        1. Create MCP browser session
        2. Navigate to course URL
        3. Wait for user login
        4. Discover all modules
        5. Process each module
        6. Create comprehensive summary
        """
        try:
            # Create MCP browser session
            client = BrowserClient(region=self.region)
            client.start()

            # Get WebSocket details for DCV streaming
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

            # Navigate to course URL
            await page.goto(course_url, wait_until="networkidle")

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
                "dcv_url": ws_url,
                "dcv_headers": headers,
                "message": "Browser session created. Please log in.",
                "page_title": await page.title()
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to start processing: {str(e)}"
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
        """Get current processing status."""
        if session_id not in active_sessions:
            return {"status": "not_found", "message": "Session not found"}

        session = active_sessions[session_id]

        return {
            "status": session.get("status"),
            "session_id": session_id,
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

            # Parse and format results
            courses = []
            for record in memory_records:
                courses.append({
                    "id": record.get("memoryRecordId"),
                    "content": record.get("content", {}).get("text", ""),
                    "created_at": record.get("createdAt"),
                    "namespace": record.get("namespace")
                })

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
            session_id = payload.get("session_id", f"session-{int(time.time())}")
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
    app.run()
