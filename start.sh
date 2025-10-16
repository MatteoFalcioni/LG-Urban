#!/bin/bash
# Quick start script for LG-Urban

set -e

echo "🚀 Starting LG-Urban..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from template..."
    cp .env.example .env || cp backend/env.template .env
    echo ""
    echo "❗ IMPORTANT: Edit .env and add your OPENAI_API_KEY"
    echo "   Run: nano .env"
    echo ""
    read -p "Press Enter after setting your API key..."
fi

# Check if sandbox image exists
if ! docker images | grep -q "^sandbox.*latest"; then
    echo "🔨 Building sandbox image..."
    docker build -f Dockerfile.sandbox -t sandbox:latest .
fi

# Create network if it doesn't exist
if ! docker network ls | grep -q langgraph-network; then
    echo "🌐 Creating Docker network..."
    docker network create langgraph-network
fi

# Start the application
echo "🐳 Starting Docker Compose..."
docker compose up -d

echo ""
echo "✅ LG-Urban is starting!"
echo ""
echo "📍 Services:"
echo "   - Frontend:  http://localhost"
echo "   - Backend:   http://localhost:8000"
echo "   - Adminer:   http://localhost:8080"
echo ""
echo "📊 Check status: docker compose ps"
echo "📜 View logs:    docker compose logs -f"
echo "🛑 Stop:         docker compose down"
echo ""

