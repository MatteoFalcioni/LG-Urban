# UrbIA

**AI-powered urban data analysis platform for Bologna with sandboxed Python execution.**

Built on LangGraph, this application enables users to perform comprehensive data analysis on any datasets from [Bologna's OpenData](https://opendata.comune.bologna.it/).

🚀 **Now deployed on Railway** [[live demo](https://lg-urban-frontend-production.up.railway.app/)]

---

## 🎯 Core Features

### 💬 Intelligent Conversations
- Multi-threaded chat with streaming responses (SSE)
- Automatic context summarization when context window is exceeded
- PostgreSQL-backed persistence with full message history
- Per-thread LLM configuration (model, temperature, system prompt)
- Support for any OpenRouter llm

### 🐍 Modal Sandbox Code Execution
- Sandboxed Python execution leveraging [Modal.com](https://modal.com)
- Live download of datasets from Bologna's OpenData (constant updates)
- S3 integration for datasets caching
- Secure, isolated environment for untrusted code
- Real-time artifact generation (plots, CSVs, analysis results)

### 🛡️ Hallucination Mitigation
- **Reviewer agent** evaluates data analyst's work and grades quality
- Only accepts analysis without any hallucinations from the analyst
- Failed analyses trigger constructive critique and re-prompting
- Ensures reliability and accuracy of insights

### 📊 Report Writing
- AI-generated comprehensive reports from analysis results
- Human-in-the-loop approval workflow

### 🎨 Modern UI
- **React + TypeScript** frontend with Tailwind CSS
- Real-time streaming responses with SSE
- Dark/light theme support
- Artifact preview and download
- Thread management and archiving
- **Clerk authentication** for secure access

---

## 🚀 Local Quick Start

Want to run locally instead of using the web app?

### 1. 📥 Clone & Install
```bash
git clone https://github.com/your-username/UrbIA.git
cd UrbIA

# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2. 🔧 Configure Environment
Create `.env` from template:
```bash
cp .env.template .env
# Edit .env with your API keys and configuration
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `OPENROUTER_API_KEY` - For LLM access
- `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` - For sandbox execution
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - For S3 storage
- `CLERK_SECRET_KEY` / `VITE_CLERK_PUBLISHABLE_KEY` - For authentication

### 3. 🗄️ Setup Database
```bash
# Start local Postgres (via Docker)
cd infra && docker compose up -d db

# Run migrations
alembic upgrade head
```

### 4. ▶️ Run Backend
```bash
cd ~/UrbIA
uvicorn backend.main:app --reload --port 8000
```

### 5. 🎨 Run Frontend (separate terminal)
```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` 🎉

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│          React + TypeScript UI          │
│  (SSE streaming, Clerk auth, Tailwind)  │
└──────────────┬──────────────────────────┘
               │ HTTP/SSE
┌──────────────▼──────────────────────────────────┐
│           FastAPI Backend (Railway)             │
│  ┌──────────────────────────────────────────┐   │
│  │        LangGraph Agent Workflow          │   │
│  │  ┌─────────────────────────────────────┐ │   │
│  │  │ • Data Analyst (w/ code execution)  │ │   │
│  │  │ • Reviewer (quality control)        │ │   │
│  │  │ • Report Writer                     │ │   │
│  │  └─────────────────────────────────────┘ │   │
│  │                                          │   │
│  │  Tools:                                  │   │
│  │  ├─ 🐍 Python Sandbox (Modal)            │   │
│  │  ├─ 🌐 Bologna OpenData API              │   │
│  │  ├─ 📦 Dataset Management (S3)           │   │
│  │  ├─ 🗺️  Geographic Tools                 │   │
│  └───────────────────────────────────────────┘  │
└─────┬────────┬──────────┬───────────────────────┘
      │        │          │
  ┌───▼──────┐ │    ┌─────▼──────┐
  │PostgreSQL│ │    │   AWS S3   │
  │(Railway) │ │    │(artifacts) │
  │          │ │    └────────────┘
  │ •App DB  │ │
  │ •LG CKPTs│ │    
  └──────────┘ │    
               │
        ┌──────▼─────────┐
        │  Modal.com     │
        │ (sandboxed     │
        │  Python exec)  │
        └────────────────┘
```

### 💾 Database Architecture

**PostgreSQL** (managed by Railway, with AWS RDS ready for scale-up):
- **Main application tables**: `threads`, `messages`, `artifacts`, `configs`, `user_api_keys`
- **LangGraph checkpoints**: `checkpoints`, `checkpoint_writes`, `checkpoint_blobs`
- **Migration system**: Alembic for schema versioning
- **Future**: AWS RDS (PostgreSQL) for production scaling

See [`backend/db/DB-README.md`](./backend/db/DB-README.md) for detailed schema, ER diagrams, and migration guides.

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **LangGraph** - Multi-agent orchestration framework
- **PostgreSQL** - Primary database (Railway-managed)
- **Alembic** - Database migration tool
- **SQLAlchemy** - ORM for database interactions
- **Modal.com** - Serverless Python sandbox execution
- **AWS S3** - Object storage for datasets and artifacts

### Frontend
- **React** + **TypeScript** - Component-based UI
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Zustand** - Lightweight state management
- **React Router** - Client-side routing
- **Clerk** - Authentication provider

### AI/LLM
- **OpenRouter** - Language models
- **LangChain** - LLM integration utilities

### DevOps & CI/CD
- **GitHub Actions** - Automated testing and deployment
- **Railway** - Backend and database hosting
- **Docker** - Local development and testing

---

## 🧪 Testing & Quality

The project includes comprehensive testing:
- ✅ **Modal integration tests** - Sandbox execution validation
- ✅ **API endpoint tests** - Backend functionality verification
- ✅ **Database migration tests** - Schema integrity checks
- ✅ **Frontend build & type checks** - TypeScript compilation
- ✅ **Code linting** - Python (Ruff/Black) + TypeScript (ESLint)

Run tests locally:
```bash
# Backend tests (requires Docker Postgres)
pytest tests/

# Frontend checks
cd frontend
npx tsc --noEmit  # Type checking
npm run lint      # ESLint
npm run build     # Production build
```



