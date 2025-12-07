#!/bin/bash
set -e

echo "🚀 IPAM Core - Steel Thread MVP"
echo "================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker and try again."
    exit 1
fi

echo "✓ Docker found"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

echo "✓ Docker Compose found"
echo ""

# Build and start
echo "📦 Building services..."
docker-compose up --build

echo ""
echo "✓ IPAM Core is running!"
echo ""
echo "🌐 Access Points:"
echo "  - Frontend:  http://localhost:3000"
echo "  - API Docs:  http://localhost:8000/docs"
echo "  - Database:  localhost:5432"
