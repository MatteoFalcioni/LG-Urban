# LG-Urban Implementation Plan

**Goal:** Fuse LG-App-Template (chat app with PostgreSQL) with LangGraph-Sandbox (Docker-sandboxed code execution) into a production-ready application.

**Source Repositories:**
- `../LG-App-Template` - Chat application with UI, PostgreSQL, chat history
- `../LangGraph-Sandbox` - Sandboxed code executor with artifact management

---

## Architecture Decisions

### 1. Database & Artifact Storage (Hybrid Approach)
- **PostgreSQL**: Store artifact metadata (id, sha256, filename, size, mime, thread_id relationships)
- **Filesystem Blobstore**: Store actual file bytes in content-addressed storage (`./blobstore/<2-char>/<2-char>/<sha256>`)
- **Deduplication**: SHA-256 fingerprinting ensures identical files are stored once
- **Why**: Production-ready pattern (same as GitHub, AWS S3+RDS), transactional integrity, efficient for large files

### 2. Repository Structure
- **Single monorepo** with backend, frontend, infra
- **Copy code directly** (don't install langgraph-sandbox as package)
- **Fresh git history** (no inherited commits from source repos)

### 3. Technology Stack
- **Backend**: FastAPI, SQLAlchemy 2.0, LangGraph, Docker SDK
- **Frontend**: React, TypeScript, Vite, TailwindCSS
- **Database**: PostgreSQL 16 (chat history, artifacts metadata)
- **Sandbox**: Docker containers with tmpfs/bind storage
- **Artifacts**: Filesystem blobstore + FastAPI download API

---

## Phase 1: Repository Setup & File Migration

### 1.1 Initialize Repository Structure
- [✅] Verify current directory: `~/LG-Urban/`
- [✅] Create directory structure:
```bash
mkdir -p backend/{app,db/alembic,graph,sandbox,artifacts,dataset_manager,tool_factory}
mkdir -p frontend infra
```

### 1.2 Copy Core Files from LG-App-Template
- [✅] Copy backend structure:
```bash
cp -r ../LG-App-Template/backend/app ./backend/
cp -r ../LG-App-Template/backend/db ./backend/
cp ../LG-App-Template/backend/config.py ./backend/
cp ../LG-App-Template/backend/main.py ./backend/
cp -r ../LG-App-Template/backend/graph ./backend/
```

- [✅] Copy frontend:
```bash
cp -r ../LG-App-Template/frontend/* ./frontend/
```

- [✅] Copy infrastructure:
```bash
cp -r ../LG-App-Template/infra/* ./infra/
cp ../LG-App-Template/requirements.txt ./
cp ../LG-App-Template/alembic.ini ./
```

### 1.3 Copy Sandbox Components from LangGraph-Sandbox
- [✅] Copy sandbox core:
```bash
cp -r ../LangGraph-Sandbox/langgraph_sandbox/sandbox/* ./backend/sandbox/
```

- [✅] Copy artifacts module (will be refactored):
```bash
cp -r ../LangGraph-Sandbox/langgraph_sandbox/artifacts/* ./backend/artifacts/
```

- [✅] Copy tool factory:
```bash
cp -r ../LangGraph-Sandbox/langgraph_sandbox/tool_factory/* ./backend/tool_factory/
```

- [✅] Copy dataset manager:
```bash
cp -r ../LangGraph-Sandbox/langgraph_sandbox/dataset_manager/* ./backend/dataset_manager/
```

- [✅] Copy config and Docker files:
```bash
cp ../LangGraph-Sandbox/langgraph_sandbox/config.py ./backend/sandbox_config.py
cp ../LangGraph-Sandbox/Dockerfile.sandbox ./
```

### 1.4 Copy Additional Files
- [✅] Create/copy environment templates:
```bash
cp ../LG-App-Template/backend/env.template ./backend/env.template
cp ../LangGraph-Sandbox/sandbox.env.example ./sandbox.env.example
```

- [✅] Copy documentation:
```bash
cp ../LG-App-Template/README.md ./README-template.md
cp ../LangGraph-Sandbox/README.md ./README-sandbox.md
```

### 1.5 Initialize Git
- [✅] Initialize fresh git repository:
```bash
git init
echo "# LG-Urban - LangGraph Chat with Sandboxed Code Execution" > README.md
```

- [✅] Create `.gitignore`:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/

# Database
*.db
*.sqlite
*.sqlite-shm
*.sqlite-wal
*.db-journal

# Environment
.env
*.env
!*.env.example
!env.template

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Node
node_modules/
dist/
.DS_Store

# Artifacts & Blobstore
blobstore/
sessions/
exports/
artifact_logs/

# Docker
docker-compose.override.yml
```

- [✅] Initial commit:
```bash
git add .
git commit -m "Initial commit: fused LG-App-Template + LangGraph-Sandbox"
```

---

## Phase 2: Database Schema Migration

### 2.1 Update Artifact Model
- [✅] Edit `backend/db/models.py` - update `Artifact` class:
```python
class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), 
        nullable=False, index=True
    )
    
    # Deduplication via SHA-256 fingerprint
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # File metadata
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(nullable=False)
    
    # Session/run tracking for sandbox artifacts
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    run_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # Arbitrary metadata (e.g., original container path, etc.)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relationships
    thread: Mapped[Thread] = relationship(back_populates="artifacts")
    
    __table_args__ = (
        Index("ix_artifacts_thread_created", "thread_id", "created_at"),
        Index("ix_artifacts_sha256", "sha256"),
    )
```

### 2.2 Create Migration
- [✅] Generate Alembic migration:
```bash
cd ~/LG-Urban
# Ensure postgres is running via docker-compose
docker-compose -f infra/docker-compose.yml up -d db
# Generate migration
alembic revision --autogenerate -m "Add artifact deduplication with sha256"
```

- [✅] Review and edit migration file in `backend/db/alembic/versions/`
- [✅] Apply migration:
```bash
alembic upgrade head
```

---

## Phase 3: Refactor Artifact Storage

### 3.1 Create Unified Artifact Store Module
- [✅] Create `backend/artifacts/storage.py`:
```python
"""
Unified artifact storage using PostgreSQL metadata + filesystem blobstore.
Replaces SQLite-based storage from LangGraph-Sandbox.
"""
from pathlib import Path
import hashlib
import mimetypes
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import Artifact

async def ensure_blobstore(base_dir: Path = Path("./blobstore")) -> Path:
    """Create blobstore directory if it doesn't exist."""
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

def _blob_path_for_sha(blob_dir: Path, sha256: str) -> Path:
    """Generate content-addressed path: blobstore/ab/cd/abcdef..."""
    return blob_dir / sha256[:2] / sha256[2:4] / sha256

def _file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 fingerprint of file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

def _sniff_mime(path: Path) -> str:
    """Guess MIME type from filename."""
    mt, _ = mimetypes.guess_type(path.name)
    return mt or "application/octet-stream"

# Additional functions to be implemented:
# - ingest_artifact_file(session, thread_id, file_path, ...) -> Artifact
# - get_artifact_blob_path(artifact: Artifact) -> Path
```

### 3.2 Refactor Artifact Ingestion
- [✅] Create `backend/artifacts/ingest.py` (PostgreSQL version):
  - Replace SQLite connection with SQLAlchemy async session
  - Use `Artifact` model instead of raw SQL
  - Implement upsert logic for deduplication
  - Keep filesystem blobstore logic

- [✅] Key functions to implement:
  - `async def ingest_files(session, thread_id, files, session_id, run_id, tool_call_id) -> List[Artifact]`
  - `async def _upsert_artifact(session, sha256, ...) -> Artifact`

### 3.3 Update Artifact API
- [✅] Refactor `backend/artifacts/api.py`:
  - Replace SQLite queries with SQLAlchemy
  - Use PostgreSQL session dependency
  - Update token generation/verification if needed
  - Maintain backward compatibility with download URLs

- [✅] Add artifact API router to `backend/main.py`:
```python
from backend.artifacts.api import router as artifacts_router
app.include_router(artifacts_router, prefix="/api")
```

---

## Phase 4: Integrate Sandbox Tools

### 4.1 Fix Import Paths
- [✅] Update all imports in `backend/sandbox/*`:
  - Change `from ..config import Config` → `from backend.sandbox_config import Config`
  - Change `from ..artifacts import ...` → `from backend.artifacts import ...`

- [✅] Update imports in `backend/tool_factory/*`:
  - Adjust relative imports to absolute imports

### 4.2 Configure Sandbox Settings
- [✅] Create `backend/config.py` (merge both configs):
  - Keep LG-App-Template config (DEFAULT_MODEL, etc.)
  - Add sandbox config (BLOBSTORE_DIR, SANDBOX_IMAGE, etc.)
  - Example:
```python
# LLM Config
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", "30000"))

# Sandbox Config
BLOBSTORE_DIR = Path(os.getenv("BLOBSTORE_DIR", "./blobstore"))
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "sandbox:latest")
TMPFS_SIZE_MB = int(os.getenv("TMPFS_SIZE_MB", "1024"))
SESSION_STORAGE = os.getenv("SESSION_STORAGE", "TMPFS")
```

### 4.3 Add Code Execution Tool
- [✅] Update `backend/graph/tools.py`:
```python
from backend.tool_factory.make_tools import make_code_sandbox_tool
from backend.sandbox.session_manager import SessionManager
from backend.config import SANDBOX_IMAGE, BLOBSTORE_DIR

# Initialize session manager (do this in main.py lifespan)
_session_manager = None

def get_session_manager():
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(
            image=SANDBOX_IMAGE,
            session_storage="TMPFS",
            dataset_access="NONE",  # Start simple
            # ... other config
        )
    return _session_manager

# Create tool
code_sandbox = make_code_sandbox_tool(
    session_manager=get_session_manager(),
    session_key_fn=lambda: "default",  # Will be replaced with thread_id
)
```

- [✅] Update `backend/graph/graph.py` - add `code_sandbox` to agent tools:
```python
agent = create_react_agent(
    model=llm,
    tools=[internet_search, code_sandbox],  # Add sandbox
    prompt=system_message,
    name="agent",
    state_schema=MyState,
)
```

### 4.4 Pass Thread ID to Tools
- [✅] Refactor tool factory to accept thread_id dynamically
- [✅] Update `make_graph()` to inject thread_id into session_key_fn
- [✅] Ensure artifacts are linked to correct thread_id in ingestion
- [✅] Made SessionManager methods async (exec, export_file)
- [✅] Created context module for passing db_session and thread_id
- [✅] Updated API to set context variables before graph invocation

---

## Phase 5: Update Frontend

### 5.1 Add Artifact Display Components
- [✅] Create `frontend/src/components/ArtifactCard.tsx`:
  - Display artifact name, size, MIME type
  - Download button with artifact URL
  - Thumbnail for images

- [✅] Update `frontend/src/components/MessageList.tsx`:
  - Check for artifacts in tool drafts
  - Render artifact cards inline with tool executions

### 5.2 Handle Code Execution Events
- [✅] Update `frontend/src/hooks/useSSE.ts`:
  - Handle `tool_start` events (show "Executing code..." indicator)
  - Handle `tool_end` events (show execution results)
  - Parse artifact data from tool messages

- [✅] Update `frontend/src/components/MessageInput.tsx`:
  - Handle artifacts in tool_end events
  - Update tool drafts with artifact data
  - Display artifacts during streaming

- [✅] Update `frontend/src/store/chatStore.ts`:
  - Add artifact tracking to tool drafts
  - Add updateToolDraft action

### 5.3 Update Types
- [✅] Update `frontend/src/types/api.ts`:
```typescript
export interface Artifact {
  id: string;
  name: string;
  mime: string;
  size: number;
  url: string;
}

export interface ToolMessage {
  type: 'tool_start' | 'tool_end';
  name: string;
  input?: any;
  output?: any;
  artifacts?: Artifact[];
}
```

---

## Phase 6: Docker & Infrastructure

### 6.1 Update Docker Compose
- [ ] Edit `infra/docker-compose.yml`:
  - Keep existing postgres + adminer services
  - Add network configuration for sandbox containers
  - Add volumes for blobstore

```yaml
services:
  db:
    # ... existing postgres config

  adminer:
    # ... existing adminer config

volumes:
  pg_data:

networks:
  default:
    name: langgraph-network
    driver: bridge
```

### 6.2 Build Sandbox Image
- [ ] Ensure `Dockerfile.sandbox` is in root
- [ ] Build image:
```bash
docker build -f Dockerfile.sandbox -t sandbox:latest .
```

### 6.3 Environment Configuration
- [ ] Create `.env` file (based on env.template + sandbox.env.example):
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/chat

# LangGraph Checkpoints
LANGGRAPH_CHECKPOINT_DB=./.lg_checkpoints.sqlite

# LLM
OPENAI_API_KEY=your_key_here
DEFAULT_MODEL=gpt-4o
DEFAULT_TEMPERATURE=0.7
CONTEXT_WINDOW=30000

# Sandbox
BLOBSTORE_DIR=./blobstore
SANDBOX_IMAGE=sandbox:latest
TMPFS_SIZE_MB=1024
SESSION_STORAGE=TMPFS
DATASET_ACCESS=NONE

# CORS
CORS_ORIGINS=http://localhost:5173
```

---

## Phase 7: Testing & Validation

### 7.1 Database Tests
- [ ] Test artifact deduplication:
  - Upload same file twice, verify single blob stored
  - Verify sha256 unique constraint works

- [ ] Test cascade deletes:
  - Delete thread, verify artifacts are deleted
  - Verify blobs remain (for potential cleanup job)

### 7.2 Sandbox Tests
- [ ] Test code execution:
  - Simple print statement
  - File creation in `/session/artifacts/`
  - Artifact ingestion and download

- [ ] Test session persistence:
  - Variables persist between executions in same thread
  - Cleanup on thread deletion

### 7.3 Integration Tests
- [ ] End-to-end flow:
  - Create thread
  - Send message requesting code execution
  - Verify artifact appears in UI
  - Download artifact, verify content
  - Delete thread, verify cleanup

### 7.4 Frontend Tests
- [ ] Artifact card rendering
- [ ] Download links work
- [ ] Code execution indicators show/hide correctly

---

## Phase 8: Documentation & Cleanup

### 8.1 Update README.md
- [ ] Document architecture
- [ ] Setup instructions
- [ ] Environment variables
- [ ] Development workflow

### 8.2 Create API Documentation
- [ ] Document artifact endpoints
- [ ] Document sandbox configuration
- [ ] Document tool usage

### 8.3 Production Considerations
- [ ] Add blob cleanup job (remove orphaned blobs)
- [ ] Add artifact size limits
- [ ] Add rate limiting for code execution
- [ ] Add monitoring/logging
- [ ] Document backup strategy (postgres + blobstore)

---

## Migration Checklist Summary

### Critical Path
1. ✅ Repository structure setup
2. ✅ Copy files from source repos
3. ✅ Update database schema (Artifact model)
4. ✅ Refactor artifact storage (SQLite → PostgreSQL)
5. ✅ Integrate sandbox tools
6. ✅ Update frontend for artifacts
7. ✅ Test end-to-end flow

### Optional Enhancements
- [ ] Dataset management tools (if needed later)
- [ ] Hybrid mode for large datasets
- [ ] Advanced artifact search/filtering
- [ ] Artifact versioning
- [ ] Multi-user sandbox isolation

---

## Notes

- **Start simple**: Begin with TMPFS + NONE dataset mode
- **Iterate**: Get basic code execution working before adding datasets
- **Test incrementally**: Validate each phase before moving to next
- **Keep source repos**: Don't delete LG-App-Template or LangGraph-Sandbox until LG-Urban is fully validated
- **Commit often**: Make atomic commits for each major change

---

## Resources

- LangGraph docs: https://langchain-ai.github.io/langgraph/
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/en/20/
- FastAPI: https://fastapi.tiangolo.com/
- Docker SDK: https://docker-py.readthedocs.io/

