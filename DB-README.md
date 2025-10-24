# Database Architecture

This app uses a **dual-store design** with PostgreSQL as the primary database and filesystem blob storage for large files.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Application                    │
└─────────────────────────────────────────────────────────────┘
                    │           │
        ┌───────────┘           └───────────┐
        │                                   │
        ▼                                   ▼
┌─────────────────────────────────────────┐ ┌──────────────┐
│              PostgreSQL                 │ │  Blobstore   │
│                                         │ │ (Filesystem) │
│  Main App Tables:                       │ │              │
│  - threads, messages, artifacts         │ │ File Bytes   │
│  - configs, user_api_keys               │ │              │
│                                         │ │              │
│  LangGraph Checkpoint Tables:           │ │              │
│  - checkpoints, checkpoint_writes       │ │              │
│  - checkpoint_blobs                     │ │              │
└─────────────────────────────────────────┘ └──────────────┘
        Single Source of Truth              Content-Addressed
```

### Storage Responsibilities

| Store | What | Why |
|-------|------|-----|
| **PostgreSQL** | All application data + LangGraph checkpoints | Persistent, queryable, relational, concurrent |
| **Blobstore** | Artifact file bytes | Efficient, deduplicated, scalable |

---

## PostgreSQL Schema

### Entity Relationship Diagram

```
┌──────────────────┐
│     threads      │
│──────────────────│
│ id (PK)          │◄─────┐
│ user_id          │      │
│ title            │      │
│ meta (JSONB)     │      │
│ created_at       │      │
│ updated_at       │      │
│ archived_at      │      │
└──────────────────┘      │
         │                │
         │ 1:N            │ 1:1
         │                │
         ├────────────────┴───────────────────┐
         │                                    │
         ▼                                    ▼
┌───────────────────┐              ┌──────────────────┐
│    messages       │              │     configs      │
│───────────────────│              │──────────────────│
│ id (PK)           │              │ thread_id (PK,FK)│
│ thread_id (FK)    │              │ model            │
│ message_id        │              │ temperature      │
│ role              │              │ system_prompt    │
│ content (JSONB)   │              │ context_window   │
│ tool_name         │              │ settings (JSONB) │
│ tool_input (JSONB)│              └──────────────────┘
│ tool_output(JSONB)│
│ meta (JSONB)      │
│ created_at        │
└───────────────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐
│    artifacts     │
│──────────────────│
│ id (PK)          │
│ thread_id (FK)   │
│ sha256           │──► Points to blob in filesystem
│ filename         │
│ mime             │
│ size             │
│ session_id       │
│ run_id           │
│ tool_call_id     │
│ meta (JSONB)     │
│ created_at       │
└──────────────────┘
```

### Table Details

#### **threads**
The top-level conversation container.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | String | Multi-tenant identifier (indexed) |
| `title` | String | Optional conversation title |
| `meta` | JSONB | Arbitrary metadata (tags, UI state, etc.) |
| `created_at` | Timestamp | Creation time |
| `updated_at` | Timestamp | Last modification time |
| `archived_at` | Timestamp | Soft delete marker |

**Indexes**: `(user_id, updated_at)` for timeline queries

---

#### **messages**
Chat messages and tool interactions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `thread_id` | UUID | Foreign key → threads (CASCADE delete) |
| `message_id` | String | Client-supplied idempotency key (unique) |
| `role` | String | `user`, `assistant`, `system`, or `tool` |
| `content` | JSONB | Message content (text or structured blocks) |
| `tool_name` | String | Tool name if this is a tool call |
| `tool_input` | JSONB | Tool call parameters |
| `tool_output` | JSONB | Tool execution results |
| `meta` | JSONB | Metadata (tokens, costs, trace IDs) |
| `created_at` | Timestamp | Message timestamp |

**Indexes**: `(thread_id, created_at)` for ordered retrieval  
**Uniqueness**: `message_id` prevents duplicate submissions

---

#### **configs**
Per-thread LLM configuration (1:1 with threads).

| Column | Type | Description |
|--------|------|-------------|
| `thread_id` | UUID | Primary key + foreign key → threads |
| `model` | String | LLM model name (e.g., `gpt-4o`) |
| `temperature` | Float | Sampling temperature |
| `system_prompt` | Text | Custom system prompt |
| `context_window` | Integer | Max tokens for context |
| `settings` | JSONB | Additional model settings |

All fields nullable → falls back to environment defaults if not set.

---

#### **artifacts**
Metadata for files generated/uploaded during conversations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `thread_id` | UUID | Foreign key → threads (CASCADE delete) |
| `sha256` | String(64) | Content hash (for deduplication & blob lookup) |
| `filename` | String | Original filename |
| `mime` | String | MIME type (e.g., `image/png`) |
| `size` | Integer | File size in bytes |
| `session_id` | String | Sandbox session that created this artifact |
| `run_id` | String | Graph run identifier |
| `tool_call_id` | String | Specific tool call that generated this |
| `meta` | JSONB | Additional metadata |
| `created_at` | Timestamp | Upload time |

**Indexes**: `(thread_id, created_at)`, `sha256`  
**Note**: Bytes stored in blobstore, not in database

---

## LangGraph Checkpoint Tables

These tables are automatically created and managed by LangGraph for conversation state management.

#### **checkpoints**
Stores conversation state snapshots at each step.

| Column | Type | Description |
|--------|------|-------------|
| `thread_id` | String | Conversation identifier |
| `checkpoint_id` | String | Unique checkpoint identifier |
| `parent_checkpoint_id` | String | Previous checkpoint (for branching) |
| `checkpoint` | JSONB | Complete state snapshot |
| `metadata` | JSONB | Additional checkpoint metadata |
| `created_at` | Timestamp | Checkpoint creation time |

#### **checkpoint_writes**
Stores atomic updates to checkpoints.

| Column | Type | Description |
|--------|------|-------------|
| `thread_id` | String | Conversation identifier |
| `checkpoint_id` | String | Associated checkpoint |
| `task_id` | String | Task identifier |
| `write` | JSONB | State update data |
| `created_at` | Timestamp | Write creation time |

#### **checkpoint_blobs**
Stores large state objects that don't fit in regular columns.

| Column | Type | Description |
|--------|------|-------------|
| `thread_id` | String | Conversation identifier |
| `checkpoint_id` | String | Associated checkpoint |
| `channel` | String | Channel identifier |
| `version` | String | Version identifier |
| `type` | String | Blob type |
| `blob` | BYTEA | Binary data |
| `created_at` | Timestamp | Blob creation time |

**Note**: These tables are managed entirely by LangGraph and should not be modified directly.

---

## Blobstore (Filesystem)

### Structure
```
blobstore/
├── ab/
│   ├── cd/
│   │   └── abcd1234567890...  ← Full SHA-256 hash as filename
│   └── ef/
│       └── abef9876543210...
└── 12/
    └── 34/
        └── 1234abcdef5678...
```

### How It Works

1. **Content-Addressed Storage**: Files are stored by their SHA-256 hash
2. **3-Level Hierarchy**: `<first-2-chars>/<next-2-chars>/<full-hash>`
   - Prevents too many files in a single directory
3. **Automatic Deduplication**: Same file uploaded twice = only stored once
4. **Lookup**: `sha256` field in `artifacts` table → find blob in filesystem

### Example
```python
# Artifact in database:
sha256 = "abcd1234567890abcdef..."
filename = "report.pdf"

# Actual file location:
# /app/blobstore/ab/cd/abcd1234567890abcdef...
```

---

## LangGraph Checkpointer (PostgreSQL)

**Location**: Same PostgreSQL database as main application data

**Purpose**: Stores LangGraph's internal state:
- Conversation checkpoints
- Agent state between steps
- Graph control flow data

**Important**: All data is now stored in PostgreSQL for unified management. The checkpointer tables are automatically created and managed by LangGraph.

**Benefits of unified PostgreSQL storage**:
- **Concurrency**: Multiple agents can run simultaneously without database locks
- **Scalability**: Better performance with high concurrent user loads
- **Reliability**: ACID transactions and crash recovery
- **Unified Backups**: Single backup strategy for all data
- **Unified Monitoring**: One database to monitor and maintain
- **Data Relationships**: Can correlate checkpoint data with thread data if needed

---

## Working with Alembic

### Inspect Current Database State

```bash
# Show current migration version
docker exec lg_urban_backend alembic current

# Show migration history
docker exec lg_urban_backend alembic history --verbose

# Show pending migrations (not yet applied)
docker exec lg_urban_backend alembic heads
```

### Apply Migrations

```bash
# Upgrade to latest version
docker exec lg_urban_backend alembic upgrade head

# Upgrade to specific revision
docker exec lg_urban_backend alembic upgrade <revision_id>

# Downgrade one step
docker exec lg_urban_backend alembic downgrade -1
```

### Create New Migrations

```bash
# Auto-generate migration from model changes
docker exec lg_urban_backend alembic revision --autogenerate -m "description"

# Create empty migration template (for manual changes)
docker exec lg_urban_backend alembic revision -m "description"
```

### Inspect Tables Directly

```bash
# Connect to PostgreSQL
docker exec -it lg_urban_db psql -U postgres -d chat

# Useful queries:
\dt                          # List all tables
\d threads                   # Describe threads table
\d+ artifacts                # Detailed description with indexes

SELECT * FROM threads LIMIT 5;
SELECT COUNT(*) FROM messages;
```

### Migration Files Location

```
backend/db/alembic/versions/
├── 0001_baseline.py
├── ac00f878b352_rename_message_key_to_message_id.py
├── 58cf9063fe3f_add_context_window_to_config.py
└── 980ae8fe2fe4_add_artifact_deduplication_with_sha256.py
```

### Common Alembic Commands

| Command | Description |
|---------|-------------|
| `alembic current` | Show current revision |
| `alembic history` | Show all revisions |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Rollback last migration |
| `alembic show <revision>` | Show specific migration SQL |
| `alembic stamp head` | Mark database as up-to-date without running migrations |

---

## Key Design Decisions

### Why Unified PostgreSQL Storage?
- **Single Source of Truth**: All data in one database
- **ACID Transactions**: Ensures consistency across app data and checkpoints
- **Unified Operations**: One database to backup, monitor, and maintain
- **Better Concurrency**: PostgreSQL handles multiple agents better than SQLite
- **Production Ready**: No file system dependencies for checkpoints

### Why UUID Primary Keys?
- Enables **client-side generation** (no server roundtrip)
- Avoids coordination issues in distributed systems
- Safe for offline-first applications

### Why JSONB for content/meta?
- **Flexible schema** without migrations
- Supports structured data (nested objects, arrays)
- Still queryable with PostgreSQL JSON operators

### Why Separate Blobstore?
- **Performance**: PostgreSQL not optimized for large binary data
- **Deduplication**: Same file uploaded 10 times = stored once
- **Scalability**: Easy to move to S3/object storage later

### Why SQLite for Checkpoints?
- **Fast**: No network overhead for frequent state updates
- **Disposable**: If deleted, agent continues from message history
- **Lightweight**: No extra infrastructure needed

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | PostgreSQL connection string |
| `LANGGRAPH_CHECKPOINT_DB_URL` | `postgresql://postgres:postgres@localhost:5432/chat` | PostgreSQL checkpointer connection string |
| `BLOBSTORE_DIR` | `/app/blobstore` | Artifact storage directory |
| `MAX_ARTIFACT_SIZE_MB` | `50` | Max file size per artifact |

---

## Troubleshooting

### "Database migration needed"
```bash
docker exec lg_urban_backend alembic upgrade head
```

### "Can't find artifact blob"
Check that:
1. Artifact exists in database: `SELECT * FROM artifacts WHERE id = '<uuid>'`
2. Blob file exists: `ls /app/blobstore/<sha256-prefix>/<sha256>`

### "Checkpointer connection error"
Verify:
```bash
# Check LangGraph checkpoint tables in PostgreSQL
docker exec lg_urban_backend psql postgresql://postgres:postgres@db:5432/chat -c "\dt" | grep checkpoint
# Should show checkpoint tables (checkpoints, checkpoint_writes, checkpoint_blobs)
```

### Reset Everything
```bash
# WARNING: Deletes all data
docker-compose down -v
docker-compose up -d
docker exec lg_urban_backend alembic upgrade head
```

