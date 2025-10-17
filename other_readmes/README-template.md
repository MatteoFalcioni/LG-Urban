# LG-APP-TEMPLATE

A simple implementation of a self-contained app that handles conversation storage and a simple chat UI

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL (via Docker)

### 1. Database Setup

```bash
# Start PostgreSQL + Adminer
cd infra
docker-compose up -d

# Verify database is running
docker ps  # Should see chat_pg running on port 5432
```

### 2. Backend Setup

```bash
# Create .env from template
cp backend/env.template backend/.env

# Edit backend/.env - add your OpenAI API key:
# OPENAI_API_KEY=sk-...

# Install dependencies
pip install -r requirements.txt

# Run migrations
cd backend
alembic upgrade head

# Start backend
cd ..
uvicorn backend.main:app --reload --port 8000
```

**Backend runs on:** `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

**Frontend runs on:** `http://localhost:5173`

### Quick Access

- **App:** http://localhost:5173
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Adminer (DB UI):** http://localhost:8080
  - Server: `db`
  - Username: `postgres`
  - Password: `postgres`
  - Database: `chat`

### Common Commands

```bash
# Stop database
docker-compose -f infra/docker-compose.yml down

# Reset database (warning: deletes all data)
docker-compose -f infra/docker-compose.yml down -v
docker-compose -f infra/docker-compose.yml up -d
alembic -c backend/alembic.ini upgrade head

# Run tests
pytest tests/
```

### Troubleshooting

- **Port 5432 in use:** Stop local PostgreSQL or change port in `infra/docker-compose.yml`
- **Port 8000 in use:** Change uvicorn port: `--port 8001`
- **Frontend won't connect:** Check `CORS_ORIGINS` in `backend/.env` includes your frontend URL
