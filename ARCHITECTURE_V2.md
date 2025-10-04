# MyTutor Architecture v2.0

## Complete Flow Architecture

### Overview

MyTutor uses a **clean separation of concerns** architecture:
- **Frontend**: User interface and DCV browser streaming
- **Backend**: Authentication and agent triggering only
- **AgentCore Runtime**: All heavy processing (MCP, scraping, AI analysis)

## Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 1. User Login (React)                                      │ │
│  │    - Username: admin                                       │ │
│  │    - Password: admin123                                    │ │
│  └────────────────┬───────────────────────────────────────────┘ │
└───────────────────┼─────────────────────────────────────────────┘
                    │
                    ▼ JWT Token
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 2. Authentication Only                                     │ │
│  │    - Verify credentials                                    │ │
│  │    - Generate JWT token                                    │ │
│  │    - Return to frontend                                    │ │
│  └────────────────┬───────────────────────────────────────────┘ │
│                   │                                              │
│  ┌────────────────▼───────────────────────────────────────────┐ │
│  │ 3. Trigger AgentCore Runtime                               │ │
│  │    POST /api/v1/agent/start-processing                     │ │
│  │    {                                                        │ │
│  │      "course_url": "https://...",                          │ │
│  │      "user_id": "admin-001"                                │ │
│  │    }                                                        │ │
│  └────────────────┬───────────────────────────────────────────┘ │
└───────────────────┼─────────────────────────────────────────────┘
                    │ HTTP Request
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AGENTCORE RUNTIME (Port 8080)                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 4. Create MCP Browser Session                              │ │
│  │    - Uses bedrock_agentcore.tools.browser_client           │ │
│  │    - Creates secure browser in AWS                         │ │
│  │    - Returns DCV streaming URL + headers                   │ │
│  └────────────────┬───────────────────────────────────────────┘ │
│                   │                                              │
│                   │ DCV URL + Headers                            │
│                   ▼                                              │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼ Return to Frontend
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 5. Stream Browser via Amazon DCV                           │ │
│  │    - Connect to DCV streaming URL                          │ │
│  │    - Show live browser in modal/iframe                     │ │
│  │    - User can SEE the browser session                      │ │
│  └────────────────┬───────────────────────────────────────────┘ │
│                   │                                              │
│  ┌────────────────▼───────────────────────────────────────────┐ │
│  │ 6. User Logs Into Course Platform                          │ │
│  │    - Visible in DCV stream                                 │ │
│  │    - User manually enters credentials                      │ │
│  │    - Clicks "I've Logged In - Continue"                    │ │
│  └────────────────┬───────────────────────────────────────────┘ │
└───────────────────┼─────────────────────────────────────────────┘
                    │
                    ▼ Continue Request
┌─────────────────────────────────────────────────────────────────┐
│                  AGENTCORE RUNTIME                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 7. Discover Course Modules                                 │ │
│  │    - Use Playwright to find all modules                    │ │
│  │    - Extract module links and titles                       │ │
│  │    - Build module list                                     │ │
│  └────────────────┬───────────────────────────────────────────┘ │
│                   │                                              │
│  ┌────────────────▼───────────────────────────────────────────┐ │
│  │ 8. Process Each Module (Loop)                              │ │
│  │                                                             │ │
│  │    For each module:                                        │ │
│  │    ┌─────────────────────────────────────┐                │ │
│  │    │ a. Navigate to module URL           │                │ │
│  │    │ b. Wait for page load                │                │ │
│  │    │ c. Extract text content              │                │ │
│  │    │ d. Find and extract videos:          │                │ │
│  │    │    - YouTube embeds                   │                │ │
│  │    │    - Vimeo embeds                     │                │ │
│  │    │    - HTML5 video tags                 │                │ │
│  │    │    - Other video sources              │                │ │
│  │    │ e. Find and extract audio:            │                │ │
│  │    │    - HTML5 audio tags                 │                │ │
│  │    │    - Audio file links                 │                │ │
│  │    │ f. Find downloadable files:           │                │ │
│  │    │    - PDFs                             │                │ │
│  │    │    - Docs, PPTX                       │                │ │
│  │    │    - ZIP files                        │                │ │
│  │    │ g. Take full-page screenshot          │                │ │
│  │    │ h. Mark module complete               │                │ │
│  │    │ i. Update progress (frontend polls)   │                │ │
│  │    └─────────────────────────────────────┘                │ │
│  │                                                             │ │
│  └────────────────┬───────────────────────────────────────────┘ │
│                   │                                              │
│  ┌────────────────▼───────────────────────────────────────────┐ │
│  │ 9. AI Analysis with Bedrock                                │ │
│  │    - Aggregate all module content                          │ │
│  │    - Send to Claude 3.5 Sonnet v2                          │ │
│  │    - Generate comprehensive summary:                       │ │
│  │      * Course title and description                        │ │
│  │      * Key topics covered                                  │ │
│  │      * Learning objectives                                 │ │
│  │      * Module-by-module breakdown                          │ │
│  │      * Resource summary (videos, files)                    │ │
│  │      * Estimated duration                                  │ │
│  │      * Difficulty level                                    │ │
│  └────────────────┬───────────────────────────────────────────┘ │
└───────────────────┼─────────────────────────────────────────────┘
                    │
                    ▼ Return Summary
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 10. Display Complete Course Summary                        │ │
│  │     - Total modules processed                              │ │
│  │     - Video count                                          │ │
│  │     - Audio count                                          │ │
│  │     - File count                                           │ │
│  │     - AI-generated summary                                 │ │
│  │     - Module-by-module details                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Frontend (React + TypeScript)
**Purpose**: User interface and DCV browser streaming

**Responsibilities**:
- User authentication (login form)
- Display JWT token status
- Trigger course processing via backend
- **Stream Amazon DCV browser** (user can see browser)
- Show real-time processing progress
- Display final course summary
- User can see the browser logging in

**Does NOT Handle**:
- Browser automation
- Content scraping
- AI analysis
- Heavy processing

**Key Files**:
- `src/components/CourseProcessor.tsx` - Main processing UI
- `src/components/LandingPage.tsx` - Login
- `src/services/api.ts` - API calls

### Backend (FastAPI + Python)
**Purpose**: Lightweight auth and agent triggering only

**Responsibilities**:
- User authentication (JWT)
- Trigger AgentCore runtime
- Proxy status requests to agent
- **No heavy processing**

**Does NOT Handle**:
- Browser automation
- Content scraping
- Module navigation
- AI analysis

**Key Files**:
- `app/api/auth.py` - Login/register
- `app/api/agent.py` - Agent triggering
- `app/services/agent_client.py` - HTTP client to agent

### AgentCore Runtime (Port 8080)
**Purpose**: All heavy processing and automation

**Responsibilities**:
- Create MCP browser sessions
- Provide DCV streaming URL to frontend
- Navigate through course modules
- Extract text, video, audio, files
- Take screenshots
- Analyze content with Bedrock
- Generate comprehensive summaries
- Track processing progress

**Key Files**:
- `agent/full_course_processor.py` - Main processor
- Uses `bedrock_agentcore.tools.browser_client`
- Uses Playwright for automation
- Uses Boto3 for Bedrock

## Data Flow

### 1. Authentication Flow
```
User → Frontend → Backend → JWT Token → Frontend
```

### 2. Course Processing Flow
```
Frontend → Backend → AgentCore → MCP Browser → DCV Stream → Frontend
                                      ↓
                              Course Modules Discovery
                                      ↓
                          Module-by-Module Processing
                                      ↓
                          Text/Video/Audio Extraction
                                      ↓
                              Bedrock Analysis
                                      ↓
                          Summary → Frontend
```

### 3. Progress Tracking Flow
```
Frontend (polls every 2s) → Backend → AgentCore → Status Response
```

## Amazon DCV Integration

### What is Amazon DCV?
Amazon DCV (NICE DCV) provides **high-performance remote desktop streaming**.

### How We Use It:
1. **AgentCore creates MCP browser** in AWS
2. **MCP returns DCV streaming URL**
3. **Frontend connects to DCV URL**
4. **User sees live browser** in their interface
5. **User logs in manually** (visible in stream)

### Benefits:
- ✅ User can SEE the browser session
- ✅ Real-time interaction visibility
- ✅ Secure streaming from AWS
- ✅ No local browser needed
- ✅ Works from anywhere

## Module Processing Details

### Discovery Phase
```javascript
// Playwright evaluates page to find modules
const modules = await page.evaluate(() => {
  // Look for common course module patterns
  const selectors = [
    '.module', '.lesson', '.section',
    '[class*="module"]', '[href*="lesson"]'
  ];

  // Extract module links and titles
  return modules.map(m => ({
    title: m.textContent,
    url: m.href,
    order: index
  }));
});
```

### Extraction Phase (Per Module)
```javascript
For each module:
  1. Navigate to module.url
  2. Wait for networkidle
  3. Extract:
     - Text: main content, paragraphs, headings
     - Videos: <video>, <iframe youtube/vimeo>
     - Audio: <audio>, audio file links
     - Files: PDFs, DOCs, PPTs, ZIPs
     - Screenshot: Full page capture
  4. Update progress: (current/total) * 100
  5. Emit status to frontend
```

### Analysis Phase
```javascript
// Aggregate all module content
const courseData = {
  modules: allModules,
  totalVideos: sum(modules.videos),
  totalAudios: sum(modules.audios),
  totalFiles: sum(modules.files),
  textContent: concatenate(modules.text)
};

// Send to Bedrock Claude
const summary = await bedrock.invokeModel({
  model: "claude-3-5-sonnet-v2",
  prompt: "Analyze this course..."
});
```

## Technology Stack

### Frontend
- React 18 + TypeScript
- Framer Motion (animations)
- Axios (HTTP client)
- Amazon DCV Client (browser streaming)

### Backend
- FastAPI (Python web framework)
- JWT authentication
- HTTPX (async HTTP client to agent)

### AgentCore Runtime
- bedrock-agentcore (MCP browser tools)
- Strands Agent framework
- Playwright (browser automation)
- Boto3 (AWS Bedrock client)
- Amazon DCV (browser streaming)

## Deployment

### Development
```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: AgentCore
cd agent && source .venv/bin/activate && python full_course_processor.py
```

### Production
- **Frontend**: Deploy to Vercel/Netlify
- **Backend**: Deploy to AWS ECS/Lambda
- **AgentCore**: Deploy via `agentcore launch`

## Security Considerations

1. **JWT tokens** for auth (not handled by agent)
2. **MCP browser isolation** (each session isolated in AWS)
3. **No credential storage** (user logs in manually)
4. **DCV encrypted streaming**
5. **Agent runs in AWS** (not exposed publicly)

## Scalability

### Current (MVP)
- In-memory session storage
- Single agent instance
- Sequential module processing

### Future (Production)
- Redis for session storage
- Multiple agent instances
- Parallel module processing
- Queue-based job distribution
- Database for course data

## Monitoring

### Frontend
- User sees real-time progress
- Module completion status
- Error messages

### Backend
- Request logging
- Auth success/failure

### AgentCore
- Session creation/cleanup
- Module processing status
- Bedrock API calls
- Error tracking

---

**Last Updated**: 2025-10-04
**Version**: 2.0.0
