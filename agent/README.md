# MyTutor AgentCore Runtime

This directory contains the AgentCore-based AI agent for MyTutor's course processing capabilities with MCP browser automation.

## Files

- `my_agent.py` - Simple agent with basic browser integration
- `course_processor.py` - **Production-ready** course processor with full MCP browser automation
- `browser_viewer.py` - **Browser streaming service** - streams MCP browser screenshots to frontend
- `requirements.txt` - Python dependencies
- `start_services.sh` - Script to start all agent services

## Setup

1. **Activate virtual environment:**
```bash
source .venv/bin/activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
playwright install
```

3. **Configure AWS credentials:**
```bash
export AWS_REGION=us-east-1
```

## Usage

### Quick Start - Run All Services

```bash
./start_services.sh
```

This starts:
- **Course Processor Agent** on `http://localhost:8080`
- **Browser Viewer Service** on `http://localhost:8081`

### Manual Start

**Terminal 1 - Browser Viewer:**
```bash
source .venv/bin/activate
python browser_viewer.py
```

**Terminal 2 - Course Processor:**
```bash
source .venv/bin/activate
python course_processor.py
```

## API Reference

### Course Processor Agent (port 8080)

The agent listens on `http://localhost:8080` and supports the following actions:

### 1. Open Browser Session

Opens MCP browser and navigates to course URL, waits for user login.

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "open_browser",
    "course_url": "https://example.com/course"
  }'
```

**Response:**
```json
{
  "status": "awaiting_login",
  "session_id": "session-12345",
  "message": "Browser opened at URL. Please log in manually.",
  "course_url": "https://example.com/course",
  "page_title": "Course Login",
  "ws_url": "wss://..."
}
```

### 2. Scrape Content (After Login)

After user has logged in manually, scrape the course content.

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "scrape_content",
    "session_id": "session-12345"
  }'
```

**Response:**
```json
{
  "status": "scraped",
  "course_url": "https://example.com/course",
  "title": "Course Title",
  "text_content": "...",
  "sections": [...],
  "screenshots": ["base64..."],
  "videos": [...],
  "files": [...]
}
```

### 3. Analyze Content

Analyze scraped content using Bedrock AI.

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "analyze_content",
    "scraped_content": {
      "title": "Course Title",
      "text_content": "...",
      "sections": [...]
    }
  }'
```

### 4. Close Session

Close browser session and cleanup resources.

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "action": "close_session",
    "session_id": "session-12345"
  }'
```

## Integration with Backend

Your FastAPI backend can invoke the agent using HTTP requests:

```python
import httpx

# Start browser session
async def start_course_processing(course_url: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/invocations",
            json={
                "action": "open_browser",
                "course_url": course_url
            }
        )
        return response.json()

# Continue after login
async def continue_processing(session_id: str):
    async with httpx.AsyncClient() as client:
        # Scrape content
        scrape_response = await client.post(
            "http://localhost:8080/invocations",
            json={
                "action": "scrape_content",
                "session_id": session_id
            }
        )
        scraped = scrape_response.json()

        # Analyze content
        analyze_response = await client.post(
            "http://localhost:8080/invocations",
            json={
                "action": "analyze_content",
                "scraped_content": scraped
            }
        )

        return analyze_response.json()
```

## Deployment

### Configure Agent

```bash
agentcore configure -e course_processor.py
```

### Deploy to AWS

```bash
agentcore launch
```

### Test Deployed Agent

```bash
agentcore invoke '{
  "action": "open_browser",
  "course_url": "https://example.com/course"
}'
```

## AWS Requirements

- AWS credentials configured
- Access to Amazon Bedrock
- Claude Sonnet 3.5 v2 model access
- Bedrock AgentCore browser tool permissions
- Proper IAM permissions

## Architecture

1. **MCP Browser Session**: Creates secure browser environment in AWS
2. **Playwright Connection**: Connects to MCP browser via Chrome DevTools Protocol
3. **Manual Login**: User logs in to course platform via browser
4. **Content Scraping**: Extracts text, structure, media, and files
5. **AI Analysis**: Bedrock analyzes content and creates structured summary
6. **Cleanup**: Proper resource cleanup and session management

## Session Management

- Sessions stored in-memory (suitable for MVP)
- For production: Use Redis or DynamoDB for persistence
- Sessions auto-expire after timeout
- Cleanup ensures no resource leaks
