# MyTutor AI Agent Instructions

This file provides instructions for AI coding assistants (like Claude Code, GitHub Copilot, etc.) working on the MyTutor project.

**⚠️ IMPORTANT**: This file should be automatically updated whenever significant changes are made to the codebase by AI tools.

## Project Overview

**Project Name**: MyTutor
**Type**: Full-stack AI-powered course learning platform
**Last Updated**: 2025-10-04
**Version**: 1.0.0

### Tech Stack

**Frontend**:
- React 18 + TypeScript + Vite
- Tailwind CSS + Framer Motion
- React Router + Axios

**Backend**:
- Python 3.10+ with FastAPI
- Pydantic for validation
- JWT authentication
- Playwright for browser automation
- AWS Bedrock integration

**External Services**:
- Amazon Bedrock (Claude Sonnet)
- Amazon DCV (optional)

## Code Style & Conventions

### Python (Backend)

```python
# File naming: snake_case
# example: bedrock_service.py

# Class naming: PascalCase
class BedrockService:
    pass

# Function naming: snake_case
async def analyze_course_content():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3

# Use type hints
def process_data(data: str) -> dict:
    pass

# Async functions when dealing with I/O
async def fetch_data():
    pass
```

### TypeScript (Frontend)

```typescript
// File naming: PascalCase for components, camelCase for utilities
// Components: LandingPage.tsx
// Utils: apiService.ts

// Interface naming: PascalCase with 'I' prefix (optional)
interface User {
  id: string;
  username: string;
}

// Function naming: camelCase
const handleLogin = async () => {};

// Component naming: PascalCase
export const Dashboard = () => {};

// Use explicit types
const fetchUser = async (id: string): Promise<User> => {};
```

## Project Structure

```
mytutor/
├── backend/
│   ├── app/
│   │   ├── api/              # API route handlers
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   └── course.py     # Course processing endpoints
│   │   ├── core/             # Core utilities
│   │   │   ├── config.py     # Configuration
│   │   │   └── security.py   # Security utilities
│   │   ├── models/           # Data models
│   │   │   └── user.py
│   │   ├── schemas/          # Pydantic schemas
│   │   │   ├── auth.py
│   │   │   └── course.py
│   │   ├── services/         # Business logic
│   │   │   ├── bedrock_service.py
│   │   │   ├── browser_service.py
│   │   │   └── agentcore_service.py
│   │   └── main.py           # FastAPI app entry
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── LandingPage.tsx
│   │   │   ├── WallERobot.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── CourseInput.tsx
│   │   │   └── KnowledgeBaseView.tsx
│   │   ├── services/         # API services
│   │   │   └── api.ts
│   │   ├── types/            # TypeScript types
│   │   │   └── index.ts
│   │   └── App.tsx
│   ├── package.json
│   └── .env.example
│
├── README.md
├── ARCHITECTURE.md
├── SETUP_GUIDE.md
└── AGENT.md (this file)
```

## Key Architecture Decisions

### 1. Authentication
- **Method**: JWT tokens
- **Storage**: localStorage (client-side)
- **Hashing**: bcrypt for passwords
- **Expiry**: 24 hours (configurable)

### 2. State Management
- **Frontend**: React Hooks (useState, useEffect)
- **Backend**: In-memory (MVP) - should migrate to database
- **Future**: Redux/Zustand for complex state

### 3. API Design
- **Style**: RESTful
- **Versioning**: `/api/v1/`
- **Response Format**: JSON
- **Error Handling**: Standard HTTP status codes

### 4. Browser Automation
- **Primary**: Playwright (Python)
- **MCP Integration**: AgentCore for advanced automation
- **Remote Sessions**: Amazon DCV (optional)

### 5. AI Integration
- **Service**: Amazon Bedrock
- **Model**: Claude 3.5 Sonnet v2
- **Input**: Text + Images (multimodal)
- **Output**: Structured JSON

## Common Tasks for AI Assistants

### Adding a New API Endpoint

1. **Create schema** in `backend/app/schemas/`
2. **Add endpoint** in `backend/app/api/`
3. **Update main.py** to include router (if new file)
4. **Create service** if business logic is complex
5. **Update frontend** service in `frontend/src/services/api.ts`
6. **Create/update component** to use the endpoint

### Adding a New Frontend Component

1. **Create component** in `frontend/src/components/`
2. **Use TypeScript** for type safety
3. **Follow naming convention**: PascalCase
4. **Add route** if it's a page (in App.tsx)
5. **Use Tailwind** for styling
6. **Add Framer Motion** for animations (if needed)

### Modifying Authentication

1. **Backend**: Update `app/api/auth.py` and `app/core/security.py`
2. **Frontend**: Update `services/api.ts` and auth components
3. **Update schemas** if changing request/response format
4. **Test thoroughly** - auth is critical!

### Adding External Service Integration

1. **Create service file** in `backend/app/services/`
2. **Add configuration** in `app/core/config.py`
3. **Add environment variables** to `.env.example`
4. **Update README** with setup instructions
5. **Create schemas** for request/response
6. **Add API endpoints** that use the service

## Environment Variables

### Backend (.env)

```env
# Required
SECRET_KEY=                    # JWT secret key

# Optional
API_V1_STR=/api/v1
PROJECT_NAME=MyTutor
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
MCP_SERVER_URL=http://localhost:3000
DCV_SERVER_URL=http://localhost:8080
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Testing Guidelines

### Backend Tests (Future)

```python
# Use pytest
# Test files: test_*.py

import pytest
from fastapi.testclient import TestClient

def test_login():
    # Test implementation
    pass
```

### Frontend Tests (Future)

```typescript
// Use Vitest + React Testing Library
// Test files: *.test.tsx

import { render, screen } from '@testing-library/react';

test('renders login button', () => {
  // Test implementation
});
```

## Security Best Practices

1. **Never commit** `.env` files
2. **Always validate** user input (Pydantic on backend)
3. **Use parameterized queries** when adding database
4. **Sanitize** user-generated content
5. **Rate limit** API endpoints in production
6. **Use HTTPS** in production
7. **Regular dependency updates**

## Dependency Management

### Adding Backend Dependencies

```bash
# Add to requirements.txt
pip install <package>
pip freeze > requirements.txt  # Update requirements
```

### Adding Frontend Dependencies

```bash
npm install <package>
# package.json is auto-updated
```

## Error Handling Patterns

### Backend

```python
from fastapi import HTTPException

try:
    # Operation
    result = await some_operation()
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=str(e)
    )
```

### Frontend

```typescript
try {
  const response = await api.post('/endpoint', data);
  return response.data;
} catch (error: any) {
  const message = error.response?.data?.detail || 'An error occurred';
  throw new Error(message);
}
```

## Database Migration (Future)

When adding database:

1. **Choose ORM**: SQLAlchemy (Python) or Prisma
2. **Create models** in `backend/app/models/`
3. **Set up migrations**: Alembic
4. **Update services** to use database
5. **Remove in-memory storage**

## API Documentation

- **Auto-generated**: http://localhost:8000/docs (Swagger)
- **Alternative**: http://localhost:8000/redoc (ReDoc)
- **Update**: Add docstrings to endpoints

Example:

```python
@router.post("/login")
async def login(user_data: UserLogin):
    """
    Login endpoint

    - **username**: User's username
    - **password**: User's password

    Returns JWT token and user info
    """
    # Implementation
```

## Git Workflow

```bash
# Feature branch
git checkout -b feature/new-feature

# Commit messages
git commit -m "feat: Add new feature"
git commit -m "fix: Fix bug in authentication"
git commit -m "docs: Update README"

# Types: feat, fix, docs, style, refactor, test, chore
```

## Performance Considerations

1. **Lazy load** components in React
2. **Use async/await** for I/O operations
3. **Implement caching** for frequently accessed data
4. **Optimize images** (WebP, lazy loading)
5. **Database indexing** when adding DB
6. **CDN** for static assets in production

## Monitoring & Logging

### Backend Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Processing course")
logger.error("Error occurred", exc_info=True)
```

### Frontend Error Tracking

```typescript
// Add Sentry or similar
Sentry.captureException(error);
```

## AI Assistant Specific Instructions

### When Making Changes

1. **Update this AGENT.md** if you:
   - Add/remove major features
   - Change project structure
   - Add new dependencies
   - Modify architecture decisions

2. **Update README.md** if you:
   - Change setup instructions
   - Add new features
   - Modify usage instructions

3. **Update ARCHITECTURE.md** if you:
   - Change system architecture
   - Add new services
   - Modify data flow

4. **Always**:
   - Follow existing code style
   - Add comments for complex logic
   - Update type definitions
   - Test your changes
   - Consider security implications

### Code Generation Guidelines

1. **Use existing patterns** from the codebase
2. **Maintain consistency** with current implementation
3. **Add proper error handling**
4. **Include type hints/types**
5. **Follow DRY principle**
6. **Consider edge cases**

### When Unsure

1. **Check existing implementations** for similar features
2. **Follow industry best practices**
3. **Prioritize security and performance**
4. **Ask for clarification** if requirements are unclear
5. **Document your decisions**

## Useful Commands

### Development

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev

# Install dependencies
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

### Production Build

```bash
# Backend
cd backend
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app

# Frontend
cd frontend
npm run build
```

### Linting & Formatting

```bash
# Backend (future)
black .
flake8 .

# Frontend (future)
npm run lint
npm run format
```

## Common Pitfalls to Avoid

1. ❌ Don't store secrets in code
2. ❌ Don't use synchronous I/O in FastAPI
3. ❌ Don't forget to validate user input
4. ❌ Don't hardcode URLs or configuration
5. ❌ Don't skip error handling
6. ❌ Don't commit large files
7. ❌ Don't use `any` type in TypeScript unnecessarily
8. ❌ With `verbatimModuleSyntax` enabled, use `import type` for type-only imports
9. ❌ Always include `.js` extension in imports when using TypeScript with Vite

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Playwright Documentation](https://playwright.dev/)
- [Tailwind CSS](https://tailwindcss.com/)

## Change Log

| Date | Change | Updated By |
|------|--------|------------|
| 2025-10-04 | Initial project setup | Claude Code |
| 2025-10-04 | Added authentication system | Claude Code |
| 2025-10-04 | Integrated AWS Bedrock | Claude Code |
| 2025-10-04 | Added browser automation | Claude Code |
| 2025-10-04 | Created frontend with WALL-E robot | Claude Code |
| 2025-10-04 | Fixed Tailwind CSS v4 PostCSS config | Claude Code |
| 2025-10-04 | Fixed TypeScript type imports (verbatimModuleSyntax) | Claude Code |
| 2025-10-04 | Redesigned UI to isomorphic login/register page | Claude Code |
| 2025-10-04 | Added Lucide React icons throughout UI | Claude Code |
| 2025-10-04 | Removed separate Register component | Claude Code |
| 2025-10-04 | Fixed Tailwind CSS v3 configuration | Claude Code |
| 2025-10-04 | Added dev.sh script with auto-reload for both services | Claude Code |
| 2025-10-04 | Simplified to single admin user (username: admin, password: admin123) | Claude Code |
| 2025-10-04 | Removed registration UI - MVP with login only | Claude Code |
| 2025-10-04 | Fixed bcrypt/passlib compatibility - switched to bcrypt directly | Claude Code |
| 2025-10-04 | Removed Nova Act dependency - using Playwright exclusively | Claude Code |
| 2025-10-04 | Removed all Nova Act references from codebase | Claude Code |
| 2025-10-04 | Enhanced browser_service with intelligent scraping features | Claude Code |
| 2025-10-04 | Bootstrapped AgentCore runtime in /agent directory | Claude Code |
| 2025-10-04 | Created course_processor.py with MCP browser automation | Claude Code |
| 2025-10-04 | Integrated Playwright + MCP for secure browser sessions | Claude Code |
| 2025-10-04 | Complete architecture redesign - Agent-centric processing | Claude Code |
| 2025-10-04 | Created full_course_processor.py with module navigation | Claude Code |
| 2025-10-04 | Integrated Amazon DCV streaming for browser viewing | Claude Code |
| 2025-10-04 | Added text/video/audio/file extraction per module | Claude Code |
| 2025-10-04 | Backend simplified to auth + agent triggering only | Claude Code |
| 2025-10-04 | Frontend polls agent for real-time progress updates | Claude Code |
| 2025-10-04 | Removed all old course processing endpoints from backend | Claude Code |
| 2025-10-04 | Moved unused services to _unused folder | Claude Code |
| 2025-10-04 | Updated Dashboard to use CourseProcessor component | Claude Code |

---

**Last Updated**: 2025-10-04
**Maintained By**: AI Assistants working on MyTutor

**Note**: AI assistants should update this file whenever making significant changes to the codebase.
