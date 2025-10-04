import asyncio
import base64
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
from app.schemas.course import BrowserSession


class BrowserService:
    """
    Browser automation service using Playwright.
    Handles course content scraping and extraction.
    """

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def initialize(self):
        """Initialize Playwright browser"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            # Use headless=False for debugging, headless=True for production
            self.browser = await self.playwright.chromium.launch(headless=False)

    async def create_session(self) -> BrowserSession:
        """Create a new browser session"""
        await self.initialize()

        session_id = f"session-{hash(str(asyncio.current_task()))}"

        return BrowserSession(
            session_id=session_id,
            dcv_url=f"http://localhost:8080/session/{session_id}",
            status="active"
        )

    async def navigate_to_course(self, url: str) -> dict:
        """Navigate to course URL and prepare for interaction"""
        await self.initialize()

        if not self.page:
            self.page = await self.browser.new_page()

        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')

        return {
            "status": "navigated",
            "url": url,
            "title": await self.page.title()
        }

    async def scrape_course_content(self, url: str) -> dict:
        """
        Scrape course content using Playwright.
        Extracts text, structure, and takes screenshots for AI analysis.
        """
        await self.initialize()

        if not self.page:
            self.page = await self.browser.new_page()

        # Navigate to course page
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')

        # Extract page title
        title = await self.page.title()

        # Extract main text content
        text_content = await self.page.evaluate("""
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
        sections = await self.page.evaluate("""
            () => {
                const headings = Array.from(document.querySelectorAll('h1, h2, h3'));
                return headings.map(h => ({
                    level: h.tagName.toLowerCase(),
                    text: h.textContent.trim()
                })).filter(h => h.text.length > 0);
            }
        """)

        # Take screenshot for multimodal AI analysis
        screenshot = await self.page.screenshot(full_page=True)
        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')

        # Get full HTML if needed for detailed parsing
        html_content = await self.page.content()

        return {
            "url": url,
            "title": title,
            "text_content": text_content[:10000],  # Limit to 10k chars
            "sections": sections[:20],  # Limit to 20 sections
            "screenshots": [screenshot_base64],
            "html_preview": html_content[:5000]  # First 5k chars of HTML
        }

    async def intelligent_scrape(self, url: str, wait_for_login: bool = False) -> dict:
        """
        Intelligent course scraping with optional manual login support.

        Args:
            url: Course URL to scrape
            wait_for_login: If True, allows time for manual login before scraping
        """
        await self.initialize()

        if not self.page:
            self.page = await self.browser.new_page()

        # Navigate to course
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')

        if wait_for_login:
            # Return early to allow manual login
            return {
                "status": "awaiting_login",
                "message": "Please log in manually in the browser window",
                "url": url,
                "next_action": "Call continue_scraping after login"
            }

        # Proceed with scraping
        return await self.scrape_course_content(url)

    async def continue_scraping(self, url: str) -> dict:
        """
        Continue scraping after manual login.
        Assumes page is already navigated and user is logged in.
        """
        if not self.page:
            raise Exception("No active page. Call navigate_to_course first.")

        # Wait a bit for any post-login redirects
        await asyncio.sleep(2)
        await self.page.wait_for_load_state('networkidle')

        # Now scrape the authenticated content
        return await self.scrape_course_content(self.page.url)

    async def extract_videos(self) -> list:
        """Extract video URLs from the current page"""
        if not self.page:
            return []

        videos = await self.page.evaluate("""
            () => {
                const videos = Array.from(document.querySelectorAll('video, iframe[src*="youtube"], iframe[src*="vimeo"]'));
                return videos.map(v => ({
                    type: v.tagName.toLowerCase(),
                    src: v.src || v.querySelector('source')?.src,
                    title: v.title || v.getAttribute('aria-label') || 'Untitled'
                })).filter(v => v.src);
            }
        """)

        return videos

    async def extract_downloadable_files(self) -> list:
        """Extract downloadable file links (PDFs, docs, etc.)"""
        if not self.page:
            return []

        files = await self.page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href$=".pdf"], a[href$=".doc"], a[href$=".docx"], a[href$=".ppt"], a[href$=".pptx"]'));
                return links.map(link => ({
                    url: link.href,
                    text: link.textContent.trim(),
                    type: link.href.split('.').pop()
                }));
            }
        """)

        return files

    async def close(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


browser_service = BrowserService()
