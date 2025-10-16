# LG-Urban

A production-ready LangGraph chat application with sandboxed Python code execution capabilities.

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

## Quick Start with Docker Compose

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (required)
- Tavily API key (optional, for internet search)

### Setup

1. **Clone and navigate:**
```bash
cd ~/LG-Urban
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

3. **Build the sandbox image:**
```bash
docker build -f Dockerfile.sandbox -t sandbox:latest .
```

4. **Start everything with Docker Compose:**
```bash
docker compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Backend API (port 8000)
- Frontend web app (port 80)
- Adminer database UI (port 8080)

5. **Open your browser:**
```
http://localhost
```

### Stopping the Application

```bash
docker compose down
```

To also remove volumes (database data, artifacts):
```bash
docker compose down -v
```

## Development Setup

For local development without Docker:

### Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Start PostgreSQL
docker compose up -d db

# Run migrations
alembic upgrade head

# Start backend (from project root)
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Architecture

```
┌─────────────┐
│   Frontend  │ (React + TypeScript)
│  (Port 80)  │
└──────┬──────┘
       │ HTTP/SSE
┌──────▼──────┐
│   FastAPI   │ (Backend API)
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

## Usage

1. Open the app at `http://localhost`
2. Start a new conversation
3. Ask the AI to run Python code, for example:
   - "Create a plot of sin(x) from 0 to 2π"
   - "Generate a random dataset and show me summary statistics"
   - "Create a bar chart comparing these values: [10, 25, 17, 42]"
4. Download generated files (plots, CSVs, etc.) directly from the chat

## Available Python Libraries in Sandbox

The code execution sandbox includes:
- numpy, pandas, matplotlib, seaborn
- scikit-learn, scikit-image
- scipy, statsmodels
- geopandas, shapely, folium
- pyarrow (Parquet support)

## Project Structure

```
LG-Urban/
├── backend/              # FastAPI backend
│   ├── app/             # API routes
│   ├── db/              # Database models & migrations
│   ├── graph/           # LangGraph agent
│   ├── sandbox/         # Docker sandbox manager
│   ├── artifacts/       # Artifact storage
│   └── tool_factory/    # LangChain tools
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── hooks/       # React hooks (SSE, etc.)
│   │   ├── store/       # Zustand state
│   │   └── types/       # TypeScript types
├── infra/               # Infrastructure configs
├── Dockerfile.backend   # Backend Docker image
├── Dockerfile.frontend  # Frontend Docker image
├── Dockerfile.sandbox   # Sandbox Docker image
└── docker-compose.yml   # Full stack orchestration
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `TAVILY_API_KEY`: Tavily search API key (optional)
- `DEFAULT_MODEL`: LLM model to use (default: gpt-4o)
- `SANDBOX_IMAGE`: Docker image for code execution (default: sandbox:latest)
- `SESSION_STORAGE`: TMPFS (RAM) or BIND (disk) for sandbox sessions

## Troubleshooting

### Backend can't spawn sandbox containers

Make sure the backend container has access to the Docker socket:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

### "Network langgraph-network not found"

Create the network manually:
```bash
docker network create langgraph-network
```

### Frontend can't connect to backend

Check CORS configuration in `.env`:
```bash
CORS_ORIGINS=http://localhost,http://localhost:80
```

## Development

See [PLAN.md](PLAN.md) for detailed implementation plan and architecture decisions.

## Project Status

✅ **Production Ready** - All phases complete (see PLAN.md)

## License

MIT

## Credits

Fused from:
- [LG-App-Template](../LG-App-Template) - Chat application foundation
- [LangGraph-Sandbox](../LangGraph-Sandbox) - Sandboxed code execution
