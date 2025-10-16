# LG-Urban

A production-ready LangGraph chat application with sandboxed code execution capabilities.

## Overview

LG-Urban combines:
- **LG-App-Template**: Chat UI with PostgreSQL-backed conversation history
- **LangGraph-Sandbox**: Docker-sandboxed Python code execution with artifact management

## Features

- 🗣️ **Interactive Chat**: Multi-threaded conversations with streaming responses
- 💻 **Code Execution**: Sandboxed Python execution in Docker containers
- 📁 **Artifact Management**: Deduplicated file storage with download URLs
- 🗄️ **PostgreSQL Storage**: Transactional chat history and artifact metadata
- 🎨 **Modern UI**: React + TypeScript + TailwindCSS frontend
- 🔄 **Real-time Streaming**: Server-Sent Events (SSE) for live responses
- 💾 **Persistent Sessions**: LangGraph checkpointer for conversation state

## Architecture

```
┌─────────────┐
│   Frontend  │ (React + TypeScript)
│  (Port 5173)│
└──────┬──────┘
       │ HTTP/SSE
┌──────▼──────┐
│   FastAPI   │ (Backend)
│  (Port 8000)│
├─────────────┤
│  LangGraph  │ Agent orchestration
│   Agent     │
├─────────────┤
│   Tools:    │
│ - Search    │
│ - Sandbox   │ ◄──── Docker containers for code execution
└──────┬──────┘
       │
   ┌───▼───┬────────────┐
   │       │            │
┌──▼───┐  ┌▼─────────┐ ┌▼────────┐
│ PG   │  │ LangGraph│ │Blobstore│
│ DB   │  │Checkpoint│ │(Files)  │
└──────┘  └──────────┘ └─────────┘
```

### Storage Strategy

- **PostgreSQL**: Chat threads, messages, configs, artifact metadata
- **LangGraph SQLite**: Ephemeral conversation state (summaries, control flow)
- **Filesystem Blobstore**: Content-addressed artifact storage (`blobstore/<sha256>`)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 16

### Setup

1. **Clone and navigate:**
```bash
cd ~/LG-Urban
```

2. **Install dependencies:**
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

3. **Configure environment:**
```bash
cp backend/env.template .env
# Edit .env with your API keys and database credentials
```

4. **Start infrastructure:**
```bash
docker-compose -f infra/docker-compose.yml up -d
```

5. **Run migrations:**
```bash
alembic upgrade head
```

6. **Build sandbox image:**
```bash
docker build -f Dockerfile.sandbox -t sandbox:latest .
```

7. **Start backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

8. **Start frontend:**
```bash
cd frontend
npm run dev
```

9. **Open browser:** http://localhost:5173

## Development

See [PLAN.md](PLAN.md) for detailed implementation plan and architecture decisions.

## Project Status

🚧 **In Development** - Currently implementing Phase 1-2 (see PLAN.md)

## License

MIT

## Credits

Fused from:
- [LG-App-Template](../LG-App-Template) - Chat application foundation
- [LangGraph-Sandbox](../LangGraph-Sandbox) - Sandboxed code execution
