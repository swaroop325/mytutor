# MyTutor Backend

Lightweight FastAPI backend that handles **only** authentication and agent triggering.

## Purpose

The backend is intentionally minimal - all heavy processing (browser automation, scraping, AI analysis) is handled by the **AgentCore Runtime** (port 8080).

## Responsibilities

✅ **User Authentication** (JWT)
✅ **Trigger AgentCore Runtime**
❌ **No browser automation**
❌ **No content scraping**
❌ **No AI processing**

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /login` - User login, returns JWT token
- `POST /register` - User registration (currently disabled for MVP)

### Agent Integration (`/api/v1/agent`)
- `POST /start-processing` - Trigger AgentCore to start course processing
- `POST /status` - Get processing status from AgentCore
- `POST /stop` - Stop processing

### Course Service (`/api/v1/course`)
- `GET /health` - Health check
- **Note:** All processing endpoints removed - use AgentCore directly

## Architecture

```
Frontend → Backend (Auth) → AgentCore Runtime
                             (All heavy processing)
```

## Setup

1. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Run server:**
```bash
uvicorn app.main:app --reload --port 8000
```

## Configuration (.env)

```env
# API Settings
API_V1_STR=/api/v1
PROJECT_NAME=MyTutor

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173"]

# AgentCore Runtime
AGENTCORE_URL=http://localhost:8080
```

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── agent.py         # AgentCore integration
│   │   └── course.py        # Course health check only
│   ├── core/
│   │   ├── config.py        # Configuration settings
│   │   └── security.py      # JWT and password utilities
│   ├── models/
│   │   └── user.py          # User data model
│   ├── schemas/
│   │   ├── auth.py          # Auth request/response schemas
│   │   └── course.py        # Course schemas (minimal)
│   ├── services/
│   │   ├── agent_client.py  # HTTP client for AgentCore
│   │   └── _unused/         # Old services (browser, bedrock, etc.)
│   └── main.py              # FastAPI app entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Removed Services

The following services have been moved to `app/services/_unused/`:
- `browser_service.py` - Now handled by AgentCore
- `bedrock_service.py` - Now handled by AgentCore
- `agentcore_service.py` - Replaced by direct HTTP calls

## Development

```bash
# Auto-reload on code changes
uvicorn app.main:app --reload --port 8000

# View API docs
http://localhost:8000/docs
```

## Production

```bash
# Install production server
pip install gunicorn

# Run with workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Trigger agent
curl -X POST http://localhost:8000/api/v1/agent/start-processing \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"course_url": "https://example.com/course"}'
```

## Notes

- **MVP Setup:** Single admin user (username: `admin`, password: `admin123`)
- **Session Storage:** In-memory (use Redis/DynamoDB for production)
- **CORS:** Configured for localhost:5173 (frontend)
- **Security:** Change SECRET_KEY in production

---

**For course processing, see AgentCore Runtime documentation in `/agent`**
