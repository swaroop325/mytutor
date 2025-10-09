# MyTutor AI Agent Instructions

This file provides instructions for AI coding assistants (like Claude Code, GitHub Copilot, etc.) working on the MyTutor project.

**⚠️ IMPORTANT**: This file should be automatically updated whenever significant changes are made to the codebase by AI tools.

## Project Overview

**Project Name**: MyTutor
**Type**: Full-stack AI-powered learning platform with knowledge base management and training
**Last Updated**: 2025-10-07
**Version**: 2.0.0

### Tech Stack

**Frontend**:
- React 18 + TypeScript + Vite
- Tailwind CSS + Framer Motion
- React Router + Axios
- Lucide React icons

**Backend**:
- Python 3.10+ with FastAPI
- Pydantic for validation
- JWT authentication with bcrypt
- File upload and processing
- Multi-agent system architecture
- AWS Bedrock integration

**Agent System**:
- AgentCore Runtime
- Bedrock AgentCore Starter Toolkit
- Multi-modal content processing
- Persistent memory storage

**External Services**:
- Amazon Bedrock (Claude 3.5 Sonnet)
- AgentCore Memory
- AWS S3 (future)

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
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   ├── file_upload.py # File upload and processing
│   │   │   ├── knowledge_base.py # Knowledge base management
│   │   │   ├── agent.py       # Agent integration endpoints
│   │   │   └── course.py      # Legacy course processing
│   │   ├── core/              # Core utilities
│   │   │   ├── config.py      # Configuration with CORS handling
│   │   │   └── security.py    # JWT and bcrypt security
│   │   ├── models/            # Data models (minimal)
│   │   ├── schemas/           # Pydantic schemas
│   │   │   └── file_upload.py # File upload schemas
│   │   ├── services/          # Business logic
│   │   │   ├── knowledge_base_service.py # KB management with training
│   │   │   ├── file_upload_service.py    # File handling and validation
│   │   │   ├── agent_client.py           # Agent communication
│   │   │   └── link_validation_service.py # URL validation
│   │   └── main.py            # FastAPI app entry
│   ├── data/                  # Persistent storage
│   │   ├── knowledge_bases.json # KB registry
│   │   └── training_sessions.json # Training history
│   ├── uploads/               # File storage by category
│   │   ├── document/
│   │   ├── video/
│   │   ├── audio/
│   │   └── image/
│   └── requirements.txt
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── Dashboard.tsx  # Main dashboard with tabs
│   │   │   ├── KnowledgeBaseManager.tsx # KB CRUD operations
│   │   │   ├── CreateKnowledgeBase.tsx  # KB creation wizard
│   │   │   ├── AITutor.tsx             # Training interface
│   │   │   ├── TrainingInterface.tsx   # MCQ training UI
│   │   │   ├── TrainingAnalytics.tsx   # Performance analytics
│   │   │   ├── TrainingHistory.tsx     # Session history
│   │   │   ├── FileUpload.tsx          # Drag & drop upload
│   │   │   ├── DirectLinkInput.tsx     # URL input component
│   │   │   ├── LandingPage.tsx         # Login/register page
│   │   │   └── WallERobot.tsx          # Animated mascot
│   │   ├── services/          # API services
│   │   │   └── api.ts         # Comprehensive API client
│   │   ├── types/             # TypeScript types
│   │   │   └── index.ts       # All type definitions
│   │   └── App.tsx            # Main app with routing
│   └── package.json
│
├── agent/                      # AgentCore Runtime
│   ├── full_course_processor.py # Main agent with memory integration
│   ├── file_processor.py        # Multi-modal file processing
│   ├── course_processor.py      # Course URL processing
│   ├── browser_viewer.py        # Browser automation utilities
│   └── requirements.txt          # Agent dependencies
│
├── logs/                       # Application logs
│   ├── backend.log            # Backend API logs
│   ├── frontend.log           # Frontend build logs
│   └── agent.log              # Agent processing logs
│
├── .kiro/                      # Kiro IDE configuration
│   └── specs/                 # Feature specifications
│
├── README.md                   # Updated project documentation
├── AGENT.md                    # This file
└── start.sh                    # Application startup script
```

## Key Architecture Decisions

### 1. Authentication
- **Method**: JWT tokens with bcrypt password hashing
- **Storage**: localStorage (client-side)
- **Security**: python-jose for JWT handling
- **Expiry**: 24 hours (configurable)
- **Admin User**: Single admin user for MVP (admin/admin123)

### 2. File Processing
- **Multi-Agent System**: Specialized agents for different content types
- **Supported Types**: PDF, DOCX, MP4, MP3, images, etc.
- **Storage**: File-based with categorized folders
- **Validation**: Comprehensive file type and size validation
- **Processing**: Real-time progress tracking

### 3. Knowledge Base Management
- **Storage**: JSON-based persistence (data/knowledge_bases.json)
- **Processing**: Multi-agent pipeline with status tracking
- **Memory**: AgentCore Memory integration for advanced storage
- **Training**: AI-powered MCQ generation from content

### 4. Training System
- **MCQ Generation**: AI-powered adaptive questions
- **Fallback System**: Works without agent for basic functionality
- **Progress Tracking**: Detailed session history and analytics
- **Persistence**: Training sessions saved to JSON
- **Analytics**: Comprehensive performance metrics

### 5. State Management
- **Frontend**: React Hooks with context for global state
- **Backend**: File-based persistence with in-memory caching
- **Real-time Updates**: Polling for processing status
- **Future**: Database migration planned

### 6. API Design
- **Style**: RESTful with comprehensive endpoints
- **Versioning**: `/api/v1/`
- **Response Format**: JSON with consistent error handling
- **File Upload**: Multipart form data with validation
- **Authentication**: JWT bearer tokens

### 7. Agent Integration
- **Runtime**: AgentCore with Bedrock integration
- **Communication**: HTTP API between backend and agent
- **Processing**: Asynchronous with status polling
- **Memory**: Persistent storage for knowledge bases
- **Fallback**: System works without agent for basic features

### 8. UI/UX Design
- **Theme**: Dark gradient theme with modern aesthetics
- **Navigation**: Tab-based interface with clear organization
- **Animations**: Framer Motion for smooth interactions
- **Responsive**: Mobile-first design with desktop optimization
- **Accessibility**: Proper ARIA labels and keyboard navigation

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
SECRET_KEY=your-secret-key-change-in-production-use-openssl-rand-hex-32

# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=MyTutor
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS (comma-separated)
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# AWS Configuration
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# AgentCore Runtime
AGENTCORE_URL=http://localhost:8080
```

### Agent (.env)

```env
# AWS Configuration
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# Memory Configuration
MEMORY_NAME=MyTutorCourseKnowledgeBase
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
| 2025-10-04 | Initial project setup with authentication and Bedrock | Claude Code |
| 2025-10-04 | Added browser automation with Playwright and AgentCore | Claude Code |
| 2025-10-04 | Created frontend with WALL-E robot and modern UI | Claude Code |
| 2025-10-04 | Implemented course processing with agent architecture | Claude Code |
| 2025-10-07 | **Major Feature Update: Knowledge Base System** | Kiro AI |
| 2025-10-07 | Added comprehensive file upload system with drag & drop | Kiro AI |
| 2025-10-07 | Implemented multi-agent file processing (PDF, video, audio, image, text) | Kiro AI |
| 2025-10-07 | Created knowledge base management with CRUD operations | Kiro AI |
| 2025-10-07 | Added direct link processing and validation | Kiro AI |
| 2025-10-07 | Implemented AI-powered training system with MCQ generation | Kiro AI |
| 2025-10-07 | Added training interface with adaptive questions and explanations | Kiro AI |
| 2025-10-07 | Created comprehensive training analytics and history tracking | Kiro AI |
| 2025-10-07 | Integrated AgentCore Memory for persistent knowledge storage | Kiro AI |
| 2025-10-07 | Added fallback system for training when agent is offline | Kiro AI |
| 2025-10-07 | Implemented file categorization with intelligent type detection | Kiro AI |
| 2025-10-07 | Added real-time processing status with progress tracking | Kiro AI |
| 2025-10-07 | Created training session persistence with JSON storage | Kiro AI |
| 2025-10-07 | Fixed knowledge base deletion to clean up training sessions | Kiro AI |
| 2025-10-07 | Added comprehensive API endpoints for all features | Kiro AI |
| 2025-10-07 | Updated dashboard with tab-based navigation (KB, Tutor, Analytics) | Kiro AI |
| 2025-10-07 | Enhanced UI with responsive design and modern components | Kiro AI |
| 2025-10-07 | Fixed CORS configuration and model ID format for Bedrock | Kiro AI |
| 2025-10-07 | Added proper error handling and loading states throughout | Kiro AI |
| 2025-10-07 | Updated documentation (README.md and AGENT.md) | Kiro AI |

---

**Last Updated**: 2025-10-07
**Maintained By**: AI Assistants working on MyTutor

**Note**: AI assistants should update this file whenever making significant changes to the codebase.

## Current Feature Status

### ✅ **Completed Features**
- **Authentication**: JWT-based login system
- **File Upload**: Multi-format drag & drop with validation
- **Knowledge Base Management**: Full CRUD with processing status
- **Multi-Agent Processing**: Specialized agents for different content types
- **AI Training**: MCQ generation with adaptive difficulty
- **Training Analytics**: Comprehensive performance tracking
- **Training History**: Persistent session storage and retrieval
- **Memory Integration**: AgentCore Memory for advanced storage
- **Fallback System**: Works without agent for basic functionality
- **Modern UI**: Responsive design with animations and dark theme

### 🚧 **In Progress**
- **Agent Optimization**: Improving processing speed and reliability
- **Advanced Analytics**: More detailed performance insights
- **Content Extraction**: Enhanced text and media extraction

### 📋 **Planned Features**
- **Database Migration**: Move from JSON to PostgreSQL/MongoDB
- **User Management**: Multi-user support with roles
- **Export Features**: Training data and knowledge base export
- **Advanced Training**: Spaced repetition and adaptive learning
- **Content Recommendations**: AI-powered learning path suggestions
- **Mobile App**: React Native mobile application
- **API Rate Limiting**: Production-ready API protection
- **Caching Layer**: Redis for improved performance
