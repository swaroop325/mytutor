# MyTutor - AI-Powered Learning Platform

MyTutor is an intelligent learning platform that combines file processing, knowledge base creation, and AI-powered training to create personalized learning experiences. The platform supports multiple content types and provides interactive training sessions with adaptive MCQ questions.

## 🎯 Features

### 🔐 **Authentication & Security**
- Secure JWT-based authentication system
- User session management
- Protected API endpoints

### 📁 **Multi-Modal File Processing**
- **Document Support**: PDF, DOCX, DOC, PPTX, PPT, TXT
- **Video Processing**: MP4, AVI, MOV, MKV, WMV, FLV, WebM
- **Audio Processing**: MP3, WAV, M4A, AAC, FLAC, OGG
- **Image Analysis**: JPEG, PNG, GIF, WebP, BMP, TIFF, SVG
- **Drag & Drop Interface**: Easy file upload with validation
- **Batch Processing**: Multiple files simultaneously

### 🧠 **Knowledge Base Management**
- **Intelligent Categorization**: Automatic file type detection
- **Multi-Agent Processing**: Specialized agents for different content types
- **Progress Tracking**: Real-time processing status
- **Persistent Storage**: Knowledge bases saved with training history
- **Memory Integration**: AgentCore Memory for advanced storage

### 🎓 **AI-Powered Training**
- **Adaptive MCQ Generation**: Questions tailored to your content
- **Interactive Learning**: Real-time feedback and explanations
- **Progress Tracking**: Detailed analytics and performance metrics
- **Training History**: Complete session history with scores
- **Fallback System**: Works even when AI agent is offline

### 📊 **Analytics & Insights**
- **Performance Analytics**: Comprehensive training statistics
- **Learning Trends**: Track improvement over time
- **Knowledge Base Analytics**: Performance by content type
- **Session History**: Detailed training session records
- **Visual Dashboards**: Beautiful charts and progress indicators

### 🎨 **Modern UI/UX**
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Framer Motion Animations**: Smooth, engaging interactions
- **WALL-E Robot Mascot**: Friendly, animated guide
- **Dark Theme**: Modern gradient backgrounds
- **Intuitive Navigation**: Tab-based interface with clear organization

## 🏗️ Architecture

### Frontend (React + TypeScript + Vite)
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with custom gradients
- **Animations**: Framer Motion for smooth interactions
- **Routing**: React Router with protected routes
- **State Management**: React Hooks with context
- **API Client**: Axios with interceptors
- **Icons**: Lucide React for consistent iconography

### Backend (Python + FastAPI)
- **Framework**: FastAPI with async/await
- **Authentication**: JWT with python-jose and bcrypt
- **File Processing**: Multi-agent system for different content types
- **Storage**: File-based persistence with JSON
- **AI Integration**: Amazon Bedrock with Claude Sonnet
- **Memory**: AgentCore Memory for advanced knowledge storage
- **File Handling**: Comprehensive upload and validation system

### Agent System (AgentCore + Bedrock)
- **AgentCore Runtime**: Handles AI processing and memory
- **Multi-Agent Processing**: Specialized agents for PDF, video, audio, image, text
- **Browser Automation**: Playwright for web content extraction
- **Memory Integration**: Persistent storage for knowledge bases
- **Training Generation**: AI-powered MCQ question creation

## 📋 Prerequisites

- **Node.js**: >= 18.x
- **Python**: >= 3.10
- **AWS Account**: With Bedrock access (for AI features)
- **AWS Credentials**: Properly configured
- **AgentCore**: For advanced AI processing (optional)
- **UV/UVX**: For Python package management (recommended)

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
cd mytutor
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Create .env file from example
cp .env.example .env

# Edit .env and add your AWS credentials
```

**Backend .env Configuration:**

```env
# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=MyTutor

# Security
SECRET_KEY=your-secret-key-change-in-production-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS Origins (comma-separated)
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# AWS Configuration
AWS_REGION=us-east-1
# Use inference profile format for Claude 3.5 Sonnet
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# AgentCore Runtime URL
AGENTCORE_URL=http://localhost:8080
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file from example
cp .env.example .env
```

**Frontend .env Configuration:**

```env
VITE_API_URL=http://localhost:8000/api/v1
```

### 4. Agent Setup (Optional - for AI features)

```bash
cd agent

# Install UV (Python package manager)
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or use pip:
pip install uv

# Install dependencies
uv pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### 5. Running the Application

**Option 1: Quick Start (Recommended)**
```bash
./start.sh
```

**Option 2: Manual Start (Three Terminals)**

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Agent (Optional - for AI features):**
```bash
cd agent
bedrock-agentcore run full_course_processor.py --port 8080
```

The application will be available at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Agent Runtime**: http://localhost:8080 (if running)

## 📖 Usage Guide

### 1. Login

1. Navigate to http://localhost:5173
2. Login with the admin credentials:
   - **Username:** `admin`
   - **Password:** `admin123`
3. You'll be redirected to the dashboard

### 2. Creating Knowledge Bases

#### **Option A: File Upload**
1. Go to the "Knowledge Base" tab
2. Click "Create New" knowledge base
3. Enter a name and description
4. **Upload Files**:
   - Drag & drop files or click to browse
   - Supports: PDF, DOCX, MP4, MP3, images, etc.
   - Multiple files can be uploaded simultaneously
5. Click "Create Knowledge Base"
6. Wait for processing to complete (real-time progress shown)

#### **Option B: Direct Links**
1. In the knowledge base creator
2. Switch to "Direct Links" tab
3. Enter URLs to online resources
4. System will validate and process the links

#### **Option C: Mixed Content**
1. Combine file uploads with direct links
2. Add course URLs along with supplementary files
3. System processes all content types together

### 3. AI Training Sessions

1. Go to the "AI Tutor" tab
2. Select a completed knowledge base
3. Click "Start Training Session"
4. Answer adaptive MCQ questions
5. Get instant feedback and explanations
6. Track your progress and scores

### 4. Analytics & Progress

1. Go to the "Training Analytics" tab
2. View comprehensive performance metrics:
   - Total sessions and questions answered
   - Average and best scores
   - Performance trends over time
   - Knowledge base-specific analytics
3. Review detailed training history
4. Track learning progress across different topics

## 🔧 Technology Stack

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- React Router
- Axios

### Backend
- Python 3.10+
- FastAPI
- Pydantic
- python-jose (JWT)
- passlib (Password hashing)
- Boto3 (AWS SDK)
- Playwright (Browser automation)
- Anthropic SDK

### AWS Services
- **Amazon Bedrock**: AI model inference (Claude Sonnet)
- **Amazon DCV**: Remote desktop/browser sessions
- **AWS IAM**: Credentials management

### Browser Automation
- **Playwright**: Powerful browser automation for content extraction
- **AgentCore MCP**: (Optional) Model Context Protocol integration

## 🏭 Production Deployment

### Backend Deployment

1. Update environment variables for production
2. Use a production WSGI server (e.g., Gunicorn):

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

3. Set up reverse proxy (Nginx/Apache)
4. Configure SSL certificates
5. Use a proper database (PostgreSQL/MongoDB) instead of in-memory storage

### Frontend Deployment

```bash
npm run build
```

Deploy the `dist` folder to:
- AWS S3 + CloudFront
- Vercel
- Netlify
- Or any static hosting service

## 🔒 Security Considerations

1. **Change the SECRET_KEY** in production
2. **Use environment variables** for all sensitive data
3. **Enable HTTPS** for all communications
4. **Implement rate limiting** on API endpoints
5. **Use a real database** with proper access controls
6. **Validate and sanitize** all user inputs
7. **Implement proper session management**
8. **Regular security audits** of dependencies

## 🛠️ Development

### Project Structure

```
mytutor/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   ├── file_upload.py # File upload endpoints
│   │   │   ├── knowledge_base.py # Knowledge base management
│   │   │   ├── agent.py       # Agent integration
│   │   │   └── course.py      # Legacy course processing
│   │   ├── core/              # Core functionality
│   │   │   ├── config.py      # Configuration management
│   │   │   └── security.py    # JWT and security utilities
│   │   ├── models/            # Data models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   │   ├── knowledge_base_service.py # KB management
│   │   │   ├── file_upload_service.py    # File handling
│   │   │   ├── agent_client.py           # Agent communication
│   │   │   └── link_validation_service.py # Link validation
│   │   └── main.py            # FastAPI app entry point
│   ├── data/                  # Persistent storage
│   │   ├── knowledge_bases.json # Knowledge base registry
│   │   └── training_sessions.json # Training history
│   ├── uploads/               # File upload storage
│   └── requirements.txt
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── Dashboard.tsx  # Main dashboard
│   │   │   ├── KnowledgeBaseManager.tsx # KB management
│   │   │   ├── AITutor.tsx    # Training interface
│   │   │   ├── TrainingAnalytics.tsx # Analytics dashboard
│   │   │   ├── TrainingHistory.tsx   # Training history
│   │   │   ├── FileUpload.tsx        # File upload UI
│   │   │   └── CreateKnowledgeBase.tsx # KB creation
│   │   ├── services/          # API services
│   │   │   └── api.ts         # Axios API client
│   │   ├── types/             # TypeScript types
│   │   │   └── index.ts       # Type definitions
│   │   └── App.tsx            # Main app component
│   └── package.json
│
├── agent/                      # AgentCore Runtime
│   ├── full_course_processor.py # Main agent processor
│   ├── file_processor.py        # File processing agent
│   ├── course_processor.py      # Course processing agent
│   └── requirements.txt
│
├── logs/                       # Application logs
│   ├── backend.log
│   ├── frontend.log
│   └── agent.log
│
└── README.md
```

### API Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user

#### File Upload
- `POST /api/v1/files/upload` - Upload single file
- `POST /api/v1/files/upload-batch` - Upload multiple files
- `POST /api/v1/files/validate-links` - Validate direct links
- `GET /api/v1/files/files` - Get user files
- `DELETE /api/v1/files/files/{file_id}` - Delete file

#### Knowledge Base
- `POST /api/v1/knowledge-base/create` - Create knowledge base
- `GET /api/v1/knowledge-base/list` - List knowledge bases
- `GET /api/v1/knowledge-base/{kb_id}` - Get knowledge base details
- `GET /api/v1/knowledge-base/{kb_id}/status` - Get processing status
- `DELETE /api/v1/knowledge-base/{kb_id}` - Delete knowledge base
- `POST /api/v1/knowledge-base/{kb_id}/recategorize` - Fix file categorization

#### Training
- `POST /api/v1/knowledge-base/training/start` - Start training session
- `POST /api/v1/knowledge-base/training/answer` - Answer question
- `GET /api/v1/knowledge-base/training/{session_id}` - Get session details
- `POST /api/v1/knowledge-base/training/{session_id}/end` - End session

#### Training History
- `GET /api/v1/knowledge-base/training/history/user` - Get user training history
- `GET /api/v1/knowledge-base/{kb_id}/training/history` - Get KB training history

#### Agent Integration
- `POST /api/v1/agent/start-course-processing` - Start course processing
- `GET /api/v1/agent/status/{session_id}` - Get processing status
- `POST /api/v1/agent/continue-after-login` - Continue after login
- `POST /api/v1/agent/stop-processing` - Stop processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- AWS Bedrock team for Claude integration
- AgentCore for MCP browser automation
- Amazon DCV for remote sessions
- Anthropic for Claude AI models

## 📞 Support

For issues, questions, or contributions, please open an issue on the GitHub repository.

---

**Built with ❤️ using AWS Bedrock, Playwright, and modern web technologies**
