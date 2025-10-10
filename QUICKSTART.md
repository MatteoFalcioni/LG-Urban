# Quick Start Guide

This is a condensed reference for getting started with LG-Urban implementation.

## Key Architecture Decisions (Already Made)

✅ **Database Strategy**: Hybrid approach
- PostgreSQL for artifact metadata (id, sha256, filename, relationships)
- Filesystem blobstore for file bytes
- Deduplication via SHA-256

✅ **Code Integration**: Direct copy, not package install
- Copy code from `../LG-App-Template` and `../LangGraph-Sandbox`
- Refactor into single monorepo
- Fresh git history

✅ **Artifact Flow**:
```
Code execution → File in /session/artifacts/ 
→ Compute SHA-256 → Store blob in ./blobstore/<2-char>/<2-char>/<sha256> 
→ Insert metadata in PostgreSQL → Return download URL
```

## Implementation Order

**Current Phase:** Phase 1 - Repository Setup

### Today's Tasks (Phase 1)

1. **Create directory structure:**
```bash
cd ~/LG-Urban
mkdir -p backend/{app,db/alembic,graph,sandbox,artifacts,dataset_manager,tool_factory}
mkdir -p frontend infra
```

2. **Copy from LG-App-Template:**
```bash
cp -r ../LG-App-Template/backend/app ./backend/
cp -r ../LG-App-Template/backend/db ./backend/
cp ../LG-App-Template/backend/config.py ./backend/
cp ../LG-App-Template/backend/main.py ./backend/
cp -r ../LG-App-Template/backend/graph ./backend/
cp -r ../LG-App-Template/frontend/* ./frontend/
cp -r ../LG-App-Template/infra/* ./infra/
cp ../LG-App-Template/requirements.txt ./
cp ../LG-App-Template/alembic.ini ./
```

3. **Copy from LangGraph-Sandbox:**
```bash
cp -r ../LangGraph-Sandbox/langgraph_sandbox/sandbox/* ./backend/sandbox/
cp -r ../LangGraph-Sandbox/langgraph_sandbox/artifacts/* ./backend/artifacts/
cp -r ../LangGraph-Sandbox/langgraph_sandbox/tool_factory/* ./backend/tool_factory/
cp -r ../LangGraph-Sandbox/langgraph_sandbox/dataset_manager/* ./backend/dataset_manager/
cp ../LangGraph-Sandbox/langgraph_sandbox/config.py ./backend/sandbox_config.py
cp ../LangGraph-Sandbox/Dockerfile.sandbox ./
```

4. **Copy env templates:**
```bash
cp ../LG-App-Template/backend/env.template ./backend/env.template
cp ../LangGraph-Sandbox/sandbox.env.example ./sandbox.env.example
```

5. **Initialize git:**
```bash
git init
git add .
git commit -m "Initial commit: fused LG-App-Template + LangGraph-Sandbox"
```

### Next Sessions

- **Phase 2**: Update database schema (Artifact model with sha256)
- **Phase 3**: Refactor artifact ingestion (SQLite → PostgreSQL)
- **Phase 4**: Integrate sandbox tools into LangGraph agent
- **Phase 5**: Update frontend for artifact display
- **Phase 6**: Docker setup and testing

## Critical Files to Modify

### Phase 2-3 (Database & Artifacts)
- `backend/db/models.py` - Add sha256, dedup fields to Artifact
- `backend/artifacts/ingest.py` - Refactor from SQLite to PostgreSQL
- `backend/artifacts/api.py` - Update to use SQLAlchemy
- `backend/artifacts/storage.py` - New file for unified storage logic

### Phase 4 (Sandbox Integration)
- `backend/graph/tools.py` - Add code_sandbox tool
- `backend/graph/graph.py` - Include sandbox in agent tools
- `backend/config.py` - Merge both configs
- `backend/main.py` - Initialize session manager in lifespan

### Phase 5 (Frontend)
- `frontend/src/components/ArtifactCard.tsx` - New component
- `frontend/src/components/MessageBubble.tsx` - Show artifacts
- `frontend/src/hooks/useSSE.ts` - Handle tool events
- `frontend/src/types/api.ts` - Add Artifact types

## Common Commands

### Development
```bash
# Start database
docker-compose -f infra/docker-compose.yml up -d

# Run migrations
alembic upgrade head

# Start backend
cd backend
uvicorn main:app --reload

# Start frontend
cd frontend
npm run dev
```

### Build sandbox image
```bash
docker build -f Dockerfile.sandbox -t sandbox:latest .
```

### Database migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

## Environment Variables (Template)

Create `.env` in root:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/chat
LANGGRAPH_CHECKPOINT_DB=./.lg_checkpoints.sqlite

# LLM
OPENAI_API_KEY=sk-...
DEFAULT_MODEL=gpt-4o
DEFAULT_TEMPERATURE=0.7
CONTEXT_WINDOW=30000

# Sandbox
BLOBSTORE_DIR=./blobstore
SANDBOX_IMAGE=sandbox:latest
SESSION_STORAGE=TMPFS
DATASET_ACCESS=NONE

# CORS
CORS_ORIGINS=http://localhost:5173
```

## Troubleshooting

### Import errors after copying files
- Update relative imports to absolute imports
- Example: `from ..config import Config` → `from backend.sandbox_config import Config`

### Database connection errors
- Ensure `docker-compose up` is running
- Check DATABASE_URL in `.env`
- Verify postgres is healthy: `docker-compose ps`

### Sandbox container not starting
- Build image: `docker build -f Dockerfile.sandbox -t sandbox:latest .`
- Check Docker daemon is running
- Verify network: `docker network ls | grep langgraph`

## Progress Tracking

Use `PLAN.md` for detailed checklist. Quick status:

- [ ] Phase 1: Repository setup ← **START HERE**
- [ ] Phase 2: Database migration
- [ ] Phase 3: Artifact storage refactor
- [ ] Phase 4: Sandbox integration
- [ ] Phase 5: Frontend updates
- [ ] Phase 6: Docker & testing
- [ ] Phase 7: Testing
- [ ] Phase 8: Documentation

## Reference

- Full plan: `PLAN.md`
- Project overview: `README.md`
- Source repos: `../LG-App-Template`, `../LangGraph-Sandbox`

