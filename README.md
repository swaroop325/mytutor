# MyTutor - AI-Powered Course Learning Platform

MyTutor is an intelligent course content processing platform that leverages AWS Bedrock, Playwright, and Amazon DCV to automatically extract, analyze, and build knowledge bases from online courses.

## 🎯 Features

- **🔐 Authentication**: Secure JWT-based authentication system
- **🎨 Beautiful UI**: Framer Motion animations with WALL-E style robot mascot
- **🌐 Browser Automation**: Playwright for intelligent content extraction
- **🤖 Smart Scraping**: Automatic extraction of text, structure, and media
- **🧠 AI Analysis**: Amazon Bedrock with Claude for multimodal content analysis
- **📚 Knowledge Base**: Automatic knowledge base creation from course materials
- **🖼️ Screenshot Capture**: Visual content analysis for comprehensive understanding

## 🏗️ Architecture

### Frontend (React + TypeScript + Vite)
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Routing**: React Router
- **State Management**: React Hooks
- **API Client**: Axios

### Backend (Python + FastAPI)
- **Framework**: FastAPI
- **Authentication**: JWT with python-jose
- **Browser Automation**: Playwright
- **AWS Integration**: Boto3 for Bedrock
- **MCP Integration**: AgentCore for browser control
- **AI Processing**: Amazon Bedrock with Claude Sonnet

## 📋 Prerequisites

- **Node.js**: >= 18.x
- **Python**: >= 3.10
- **AWS Account**: With Bedrock access
- **AWS Credentials**: Properly configured
- **Amazon DCV**: (Optional) For remote browser sessions

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
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173"]

# AWS Configuration
AWS_REGION=us-east-1

# Amazon Bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# AgentCore MCP (if using)
MCP_SERVER_URL=http://localhost:3000

# Amazon DCV (if using)
DCV_SERVER_URL=http://localhost:8080
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

### 4. Running the Application

**Option 1: Quick Start with Auto-Reload (Recommended)**
```bash
./dev.sh
```

This script:
- ✅ Starts both backend and frontend
- ✅ Enables auto-reload on file changes
- ✅ Backend auto-reloads on Python changes (uvicorn --reload)
- ✅ Frontend has Hot Module Replacement (Vite HMR)
- ✅ Shows colored output for each service
- ✅ Handles cleanup on exit

**Option 2: Manual Start (Two Terminals)**

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

The application will be available at:
- Frontend: http://localhost:5173 (with HMR)
- Backend API: http://localhost:8000 (with auto-reload)
- API Documentation: http://localhost:8000/docs

## 📖 Usage Guide

### 1. Login

1. Navigate to http://localhost:5173
2. Login with the admin credentials:
   - **Username:** `admin`
   - **Password:** `admin123`
3. You'll be redirected to the dashboard

### 2. Processing a Course

1. Go to the "Course Processing" tab
2. Enter the URL of your online course
3. Click "Start Processing"
4. The system will:
   - Open a browser session using Playwright
   - Navigate to the course URL
   - Wait for you to manually log in to the course platform (if needed)
   - After login, click "I've Logged In - Continue Processing"
5. The system will then:
   - Scrape course content intelligently using Playwright
   - Extract text, structure, and take screenshots
   - Analyze content using Amazon Bedrock (Claude) with multimodal capabilities
   - Build a knowledge base automatically

### 3. Knowledge Base

View your processed courses and knowledge base in the "Knowledge Base" tab.

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
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Core functionality (config, security)
│   │   ├── models/       # Data models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── main.py       # FastAPI app entry point
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── services/     # API services
│   │   ├── types/        # TypeScript types
│   │   └── App.tsx       # Main app component
│   ├── package.json
│   └── .env.example
└── README.md
```

### API Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user

#### Course Processing
- `POST /api/v1/course/create-session` - Create browser session
- `POST /api/v1/course/navigate` - Navigate to course URL
- `POST /api/v1/course/scrape-course` - Scrape course content
- `POST /api/v1/course/analyze-content` - Analyze with Bedrock
- `POST /api/v1/course/build-knowledge-base` - Build knowledge base
- `POST /api/v1/course/process-course-full` - Full pipeline
- `POST /api/v1/course/continue-after-login` - Continue after login

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
