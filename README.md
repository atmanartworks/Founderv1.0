# FounderGPT

**Enterprise AI Knowledge Platform** with Retrieval-Augmented Generation (RAG), Citations, and Role-Based Access Control (RBAC).

FounderGPT is a secure, full-stack AI assistant similar to ChatGPT Enterprise, designed to answer questions based on your organization's private documents with precise citations and document highlighting.

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

### Core Features
- **🔐 Google OAuth Authentication** - Domain-restricted authentication with JWT sessions
- **📁 Document Vault** - Secure cloud storage for PDF, DOCX, PPTX files
- **🤖 RAG-Powered AI Chat** - GPT-4 powered assistant with document context
- **📝 Precise Citations** - Structured citations with `[1]`, `[2]` format
- **🎯 Document Highlighting** - Click citations to view highlighted source documents
- **👥 Role-Based Access Control** - Admin, Manager, User roles with permission enforcement
- **💬 Multi-turn Conversations** - Persistent chat threads with history
- **📊 Document Generation** - AI-generated reports, proposals, and summaries

### Advanced Features
- **🔄 Streaming Responses** - Real-time streaming for better UX
- **📂 Folder Management** - Hierarchical folder structure with permissions
- **🔍 Advanced Document Parsing** - Llama Parse for better extraction (tables, images, layout)
- **📈 Analytics & Logging** - Conversation logs for auditing and training data
- **📤 Export Functionality** - Export conversations as JSONL/CSV
- **🛡️ Row-Level Security** - Database-level permission enforcement

---

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Database**: Supabase (PostgreSQL + pgvector)
- **AI/ML Stack**:
  - **LLM**: OpenAI GPT-4
  - **Embeddings**: OpenAI `text-embedding-3-small`
  - **RAG Framework**: LlamaIndex (best for RAG applications)
  - **Document Extraction**: Llama Parse (better extraction than basic readers)
  - **Vector Database**: Supabase pgvector (integrated, simpler than Qdrant)
- **Storage**: Supabase Storage
- **Authentication**: Supabase Auth (Google OAuth)

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS + Shadcn UI
- **PDF Viewer**: react-pdf
- **Deployment**: Vercel (Frontend) + Generic Server (Backend)

### Why These Choices?
- **LlamaIndex over LangChain**: Better designed for RAG applications, cleaner abstractions
- **Supabase pgvector over Qdrant**: Integrated with database, simpler setup, good performance
- **Llama Parse over Docling**: Better integrated with LlamaIndex, supports more formats

---

## 📦 Prerequisites

- **Node.js** 18+ and npm/yarn
- **Python** 3.10+
- **Supabase Account** (free tier works)
  - PostgreSQL database with pgvector extension
  - Storage bucket configured
- **OpenAI API Key** (with GPT-4 access)
- **Llama Parse API Key** (optional, for advanced document parsing)
- **Google OAuth Credentials** (for authentication)

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd founderv1
```

### 2. Install Dependencies

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 3. Configure Environment Variables

**Copy `.env.example` to `.env` and fill in your values:**
```bash
cp .env.example .env
```

**Edit `.env` with your actual keys:**
```env
# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Optional: Llama Parse (for advanced document parsing)
LLAMA_CLOUD_API_KEY=llx-xxxxxxxxxxxxx

# App Config
ENV=development
PORT=8000
```

**Frontend `.env.local`:**
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

### 4. Setup Database

1. **Enable pgvector extension** in Supabase SQL Editor:
```sql
create extension if not exists vector;
```

2. **Run schema** from `backend/database/schema.sql`:
   - Go to Supabase Dashboard → SQL Editor
   - Copy and paste contents of `backend/database/schema.sql`
   - Execute

3. **Create Storage Bucket**:
   - Go to Supabase Dashboard → Storage
   - Create bucket named `GPTv1` (or update `STORAGE_BUCKET_NAME` in `.env`)
   - Set policies: Authenticated users can upload/read

### 5. Configure Google OAuth

1. **In Supabase Dashboard**:
   - Go to Authentication → Providers
   - Enable **Google** provider
   - Add your Google OAuth Client ID and Secret
   - Set Redirect URL: `https://your-project.supabase.co/auth/v1/callback`

2. **Get Google OAuth Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create OAuth 2.0 credentials
   - Add authorized redirect URI: `https://your-project.supabase.co/auth/v1/callback`

### 6. Run Application

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

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/v1/docs

---

## 💻 Development Setup

### Project Structure
```
founderv1/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # API routes
│   │   ├── core/                # Configuration
│   │   ├── db/                  # Database clients
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # Business logic
│   │   └── main.py              # FastAPI app
│   ├── database/
│   │   ├── schema.sql           # Database schema
│   │   └── rls_fix.sql          # RLS policies
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   └── lib/                 # Utilities
│   └── package.json
├── citation/                    # Citation reference implementation
├── .env.example                 # Environment template
├── .env                         # Your actual config (gitignored)
└── README.md
```

### Development Workflow

1. **Backend Changes**: Auto-reload with `--reload` flag
2. **Frontend Changes**: Hot-reload enabled in Next.js
3. **Database Changes**: Update `schema.sql` and re-run in Supabase
4. **API Testing**: Use FastAPI docs at `/api/v1/docs`

### Running Tests
```bash
# Backend tests (when implemented)
cd backend
pytest

# Frontend tests (when implemented)
cd frontend
npm test
```

---

## 🚀 Production Deployment

### Frontend Deployment (Vercel)

1. **Connect Repository to Vercel**:
   ```bash
   cd frontend
   vercel
   ```

2. **Set Environment Variables in Vercel Dashboard**:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

3. **Update CORS in Backend**:
   - Add your Vercel domain to `CORS_ORIGINS` in `.env`

### Backend Deployment (Generic Server)

**Option 1: Docker (Recommended)**
```bash
cd backend
docker build -t foundergpt-api .
docker run -p 8000:8000 --env-file ../.env foundergpt-api
```

**Option 2: Systemd Service**
```bash
# Create service file: /etc/systemd/system/foundergpt.service
[Unit]
Description=FounderGPT API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/founderv1/backend
Environment="PATH=/path/to/founderv1/backend/venv/bin"
ExecStart=/path/to/founderv1/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable foundergpt
sudo systemctl start foundergpt
```

**Option 3: Supervisor**
```ini
# /etc/supervisor/conf.d/foundergpt.conf
[program:foundergpt]
command=/path/to/founderv1/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/path/to/founderv1/backend
user=www-data
autostart=true
autorestart=true
```

### Production Environment Variables

**Backend `.env`:**
```env
ENV=production
FRONTEND_URL=https://your-domain.vercel.app
API_BASE_URL=https://api.your-domain.com
CORS_ORIGINS=https://your-domain.vercel.app
LOG_LEVEL=WARNING
```

**Frontend `.env.local` (in Vercel):**
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_URL=https://api.your-domain.com/api/v1
```

### Security Checklist for Production

- [ ] Change all default passwords
- [ ] Use strong, unique API keys
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Set up CORS properly
- [ ] Enable RLS policies in Supabase
- [ ] Use environment-specific configs
- [ ] Enable logging and monitoring
- [ ] Set up backup strategy
- [ ] Review and restrict API rate limits
- [ ] Enable Supabase database backups

---

## 🏗 Architecture

### System Architecture
```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │─────▶│   Backend    │─────▶│  Supabase   │
│  (Next.js)  │◀─────│   (FastAPI)  │◀─────│ (Postgres+  │
│             │      │              │      │  Storage)   │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   OpenAI     │
                     │  (GPT-4 +    │
                     │  Embeddings) │
                     └──────────────┘
```

### Data Flow

1. **Document Upload**:
   - User uploads → Frontend → Backend → Supabase Storage
   - Background job: Extract text → Chunk → Embed → Store in pgvector

2. **Chat Query**:
   - User query → Backend → Generate embedding
   - Vector search in pgvector (with permission filtering)
   - Retrieve chunks → Build context → GPT-4 → Response with citations

3. **Citation Click**:
   - Click citation → Frontend → Download document → PDF Viewer
   - Extract character offsets → Highlight text → Navigate to page

---

## 📚 API Documentation

### Authentication
- `GET /api/v1/auth/me` - Get current user
- `GET /api/v1/auth/admin-dashboard` - Admin-only route

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/` - List user's documents
- `DELETE /api/v1/documents/{id}` - Delete document

### Chat
- `POST /api/v1/chat/query` - Send query, get RAG response
- `POST /api/v1/chat/conversations` - Create conversation
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/{id}/messages` - Get messages

### Admin (Protected)
- `GET /api/v1/admin/users` - List all users
- `POST /api/v1/admin/users` - Create user
- `PUT /api/v1/admin/users/{id}` - Update user
- `DELETE /api/v1/admin/users/{id}` - Delete user

**Full API Docs**: http://localhost:8000/api/v1/docs (Swagger UI)

---

## 🗄 Database Schema

### Core Tables
- **users**: User profiles with roles (admin/manager/user)
- **folders**: Hierarchical folder structure with permissions
- **documents**: File metadata and storage paths
- **document_chunks**: Text chunks with embeddings (vector)
- **conversations**: Chat sessions
- **messages**: Chat messages with citations (JSONB)
- **audit_logs**: Activity logging

See `backend/database/schema.sql` for full schema.

---

## 🔒 Security

### Authentication
- Google OAuth via Supabase Auth
- Domain restriction: Only `@silambarasantr.com` emails allowed
- JWT-based sessions with automatic refresh

### Authorization
- **Role-Based Access Control (RBAC)**:
  - Admin: Full access to all features
  - Manager: Access to assigned folders/documents
  - User: Access to granted documents only

### Data Protection
- **Row-Level Security (RLS)** policies in Supabase
- Permission checks at API level
- Secure file storage in Supabase Storage
- Service role key kept secret (backend only)

### Best Practices
- Never expose `SUPABASE_SERVICE_ROLE_KEY` to frontend
- Use environment variables for all secrets
- Enable HTTPS in production
- Regular security audits
- Keep dependencies updated

---

## 🐛 Troubleshooting

### Backend Issues

**Backend won't start:**
- Check `.env` file exists and has all required variables
- Verify Python version: `python3 --version` (should be 3.10+)
- Check if port 8000 is already in use: `lsof -i :8000`

**Import errors:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Supabase connection errors:**
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`
- Check Supabase project is active
- Test connection: `curl https://your-project.supabase.co/rest/v1/`

### Frontend Issues

**Build errors:**
```bash
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

**Authentication not working:**
- Check `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `.env.local`
- Verify Google OAuth is configured in Supabase
- Check browser console for errors

**Upload fails:**
- Verify Supabase Storage bucket `GPTv1` exists
- Check bucket permissions allow authenticated uploads
- Verify file size is within limits (default: 10MB)

### Document Processing Issues

**Processing stuck/hangs:**
- Check backend logs: `tail -f /tmp/backend.log`
- Verify OpenAI API key has credits
- Check document size (very large files may timeout)
- Ensure Llama Parse API key is valid (if using)

**No search results:**
- Verify document processing completed (check `document_chunks` table)
- Ensure embeddings were generated (check `embedding` column)
- Test OpenAI API key: `curl https://api.openai.com/v1/models -H "Authorization: Bearer YOUR_KEY"`

### Chat Issues

**No responses:**
- Check OpenAI API key and credits
- Verify documents are processed and have chunks
- Check backend logs for errors

**Citations not working:**
- Verify citation format in response (should have `[1]`, `[2]`, etc.)
- Check `citations` field in messages table
- Ensure document viewer components are loaded

---

## 📝 Project Status

See `PROJECT_ASSESSMENT.md` for detailed alignment analysis and roadmap.

**Current Status**: ~60% aligned with requirements
- ✅ Core features implemented
- ⚠️ Advanced features in progress
- 📋 Roadmap available

---

## 🤝 Contributing

This is an internal project. For feature requests or bug reports, contact the development team.

---

## 📄 License

Proprietary - All rights reserved.

---

## 📞 Support

For issues or questions:
1. Check this README
2. Review `PROJECT_ASSESSMENT.md` for roadmap
3. Check backend logs: `/tmp/backend.log`
4. Contact development team

---

**Last Updated**: 2024-12-XX
**Version**: 1.0.0
