# Database Architecture 💾

This app uses a **dual-store design** with PostgreSQL for metadata and AWS S3 for artifact storage.

**Current Deployment**:
- **PostgreSQL**: Managed by [Railway](https://railway.app)
- **AWS S3**: `lg-urban-prod` bucket in `eu-central-1`

**Future Scaling**: AWS RDS (PostgreSQL) ready for production scale-up

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
│              PostgreSQL                 │ │   AWS S3     │
│            (Railway-managed)            │ │              │
│                                         │ │ File Bytes   │
│  Main App Tables:                       │ │ (artifacts)  │
│  - threads, messages, artifacts         │ │              │
│  - configs, user_api_keys               │ │              │
│                                         │ │              │
│  LangGraph Checkpoint Tables:           │ │              │
│  - checkpoints, checkpoint_writes       │ │              │
│  - checkpoint_blobs                     │ │              │
└─────────────────────────────────────────┘ └──────────────┘
        Metadata + Relationships              Content-Addressed
```

### Storage Responsibilities

| Store | What | Why |
|-------|------|-----|
| **PostgreSQL** | Artifact metadata + LangGraph checkpoints | Persistent, queryable, relational, ACID |
| **AWS S3** | Artifact file bytes (plots, CSVs, etc.) | Scalable, durable, content-addressed |

---

## PostgreSQL Schema

### Entity Relationship Diagram

```
                  ┌──────────────────────┐
                  │   user_api_keys      │
                  │──────────────────────│
                  │ user_id (PK)         │
                  │ openai_key (enc)     │
                  │ anthropic_key (enc)  │
                  │ created_at           │
                  │ updated_at           │
                  └──────────────────────┘
                            │
                            │ Logical link by user_id
                            │
┌──────────────────┐        ▼
│     threads      │   (not enforced FK,
│──────────────────│    multi-tenant design)
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
│ sha256           │──► Points to S3 object
│ filename         │
│ mime             │
│ size             │
│ session_id       │
│ run_id           │
│ tool_call_id     │
│ meta (JSONB)     │ ← Contains s3_key, s3_url
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
| `sha256` | String(64) | Content hash (for deduplication & S3 lookup) |
| `filename` | String | Original filename |
| `mime` | String | MIME type (e.g., `image/png`) |
| `size` | Integer | File size in bytes |
| `session_id` | String | Sandbox session that created this artifact |
| `run_id` | String | Graph run identifier |
| `tool_call_id` | String | Specific tool call that generated this |
| `meta` | JSONB | Additional metadata (includes `s3_key` and `s3_url`) |
| `created_at` | Timestamp | Upload time |

**Indexes**: `(thread_id, created_at)`, `sha256`
**Note**: File bytes stored in AWS S3, metadata in PostgreSQL

---

#### **user_api_keys**
Encrypted storage for user-provided API keys (OpenAI, Anthropic).

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | String(255) | Primary key, matches Clerk user ID |
| `openai_key` | Text | Encrypted OpenAI API key (Fernet encryption) |
| `anthropic_key` | Text | Encrypted Anthropic API key (Fernet encryption) |
| `created_at` | Timestamp | Key creation time |
| `updated_at` | Timestamp | Last key update time |

**Indexes**: `user_id`
**Security**: Keys are encrypted at rest using Fernet symmetric encryption
**Note**: No foreign key constraint to threads; `user_id` is a logical link for multi-tenant isolation

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

## AWS S3 Artifact Storage

### Architecture

Artifacts are stored using a **dual-layer approach**:
1. **PostgreSQL**: Metadata (filename, mime, size, sha256, relationships)
2. **AWS S3**: Actual file bytes (plots, CSVs, datasets)

### S3 Structure

```
s3://lg-urban-prod/
└── output/
    └── artifacts/
        ├── ab/
        │   ├── cd/
        │   │   └── abcd1234567890...  ← Full SHA-256 hash
        │   └── ef/
        │       └── abef9876543210...
        └── 12/
            └── 34/
                └── 1234abcdef5678...
```

### How It Works

1. **Upload**: Modal sandbox generates artifacts → uploads to S3 with content-addressed key
2. **Metadata**: Backend ingests S3 key → creates `Artifact` record in PostgreSQL
3. **Download**: Frontend requests artifact → backend generates presigned URL → redirects to S3
4. **Deduplication**: Same file (same SHA-256) uploaded twice = stored once in S3

### Content-Addressed Keys

S3 keys follow a 3-level hierarchy based on SHA-256:
```
output/artifacts/{sha256[:2]}/{sha256[2:4]}/{sha256}
```

**Example**:
```python
# Artifact in PostgreSQL:
sha256 = "abcd1234567890abcdef..."
filename = "analysis.png"
mime = "image/png"
meta = {
    "s3_key": "output/artifacts/ab/cd/abcd1234567890abcdef...",
    "s3_url": "s3://lg-urban-prod/output/artifacts/ab/cd/abcd1234567890..."
}

# Download flow:
# 1. GET /api/artifacts/{artifact_id}/download
# 2. Backend generates presigned URL (valid 24h)
# 3. 307 redirect to presigned S3 URL
# 4. Direct download from S3
```

### Benefits

- ✅ **Scalable**: No size limits, AWS handles infrastructure
- ✅ **Durable**: 99.999999999% durability (11 nines)
- ✅ **Fast**: Direct S3 downloads via presigned URLs
- ✅ **Secure**: Presigned URLs with expiration (default 24h)
- ✅ **Deduplicated**: Content-addressed storage prevents duplication

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

### Why AWS S3 for Artifacts?
- **Performance**: PostgreSQL not optimized for large binary data
- **Deduplication**: Content-addressed storage (same SHA-256 = single S3 object)
- **Scalability**: Unlimited storage, AWS infrastructure
- **Durability**: 99.999999999% durability, automatic replication
- **Cost-effective**: Pay only for storage used
- **Direct Downloads**: Presigned URLs enable direct client → S3 transfers

### Why Encrypted API Keys?
- **Security**: User-provided keys never stored in plaintext
- **Multi-tenant**: Each user brings their own LLM API keys
- **Privacy**: Keys encrypted with Fernet (symmetric encryption)
- **Separation**: Application credentials separate from user credentials

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | PostgreSQL connection string (Railway-provided in prod) |
| `LANGGRAPH_CHECKPOINT_DB_URL` | `postgresql://postgres:postgres@localhost:5432/chat` | PostgreSQL checkpointer connection string |
| `AWS_ACCESS_KEY_ID` | *(required)* | AWS access key for S3 artifact storage |
| `AWS_SECRET_ACCESS_KEY` | *(required)* | AWS secret key for S3 artifact storage |
| `AWS_REGION` | `eu-central-1` | AWS region for S3 bucket |
| `S3_BUCKET` | `lg-urban-prod` | S3 bucket name for artifacts |
| `ENCRYPTION_KEY` | *(required)* | Fernet encryption key for user API keys |

### Deployment-Specific Configuration

**Local Development** (Docker):
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/chat
```

**Railway (Current Production)**:
- `DATABASE_URL` provided automatically by Railway PostgreSQL service
- Managed backups, automatic SSL/TLS
- Suitable for current scale

**AWS RDS (Future Production Scale-up)**:
- Private subnet with bastion access
- Enhanced monitoring and performance insights
- Reserved instances for cost optimization
- See `tests/RDS-CONNECTION-GUIDE.md` for connection details

---

## Troubleshooting

### "Database migration needed"
```bash
alembic upgrade head
```

### "Can't download artifact"
Check that:
1. Artifact metadata exists in PostgreSQL:
   ```sql
   SELECT * FROM artifacts WHERE id = '<uuid>';
   ```
2. S3 object exists:
   ```bash
   aws s3 ls s3://lg-urban-prod/output/artifacts/ab/cd/abcd...
   ```
3. AWS credentials are valid:
   ```bash
   aws s3 ls s3://lg-urban-prod/output/artifacts/ --max-items 5
   ```

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
