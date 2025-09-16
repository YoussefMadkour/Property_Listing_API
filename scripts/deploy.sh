#!/bin/bash

# Property Listing API Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Environment: development, staging, production

set -e

ENVIRONMENT=${1:-development}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying Property Listing API to $ENVIRONMENT environment..."

# Validate environment
case $ENVIRONMENT in
    development|staging|production)
        echo "✅ Environment: $ENVIRONMENT"
        ;;
    *)
        echo "❌ Invalid environment: $ENVIRONMENT"
        echo "Valid environments: development, staging, production"
        exit 1
        ;;
esac

# Change to project directory
cd "$PROJECT_DIR"

# Check if required files exist
if [ ! -f ".env.$ENVIRONMENT" ]; then
    echo "❌ Environment file .env.$ENVIRONMENT not found"
    echo "Please create .env.$ENVIRONMENT based on the template"
    exit 1
fi

# Copy environment file
echo "📋 Setting up environment configuration..."
cp ".env.$ENVIRONMENT" .env

# Choose Docker Compose file based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    DOCKERFILE="Dockerfile.prod"
else
    COMPOSE_FILE="docker-compose.yml"
    DOCKERFILE="Dockerfile"
fi

echo "📦 Using Docker Compose file: $COMPOSE_FILE"

# Pull latest images
echo "📥 Pulling latest Docker images..."
docker-compose -f "$COMPOSE_FILE" pull

# Build application image
echo "🔨 Building application image..."
docker-compose -f "$COMPOSE_FILE" build --no-cache

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f "$COMPOSE_FILE" down

# Start database first
echo "🗄️ Starting database..."
docker-compose -f "$COMPOSE_FILE" up -d db

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run database migrations
echo "🔄 Running database migrations..."
docker-compose -f "$COMPOSE_FILE" --profile migration up migrate

# Start all services
echo "🚀 Starting all services..."
docker-compose -f "$COMPOSE_FILE" up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Health check
echo "🏥 Performing health check..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    echo "📋 Checking service logs..."
    docker-compose -f "$COMPOSE_FILE" logs api
    exit 1
fi

# Show running services
echo "📊 Running services:"
docker-compose -f "$COMPOSE_FILE" ps

echo "🎉 Deployment completed successfully!"
echo ""
echo "📍 Service URLs:"
echo "   API: http://localhost:8000"
echo "   Swagger UI: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"

if [ "$ENVIRONMENT" = "production" ]; then
    echo ""
    echo "🔒 Production deployment notes:"
    echo "   - Ensure SSL certificates are configured"
    echo "   - Update DNS records to point to your server"
    echo "   - Configure monitoring and alerting"
    echo "   - Set up automated backups"
fi

echo ""
echo "📝 Useful commands:"
echo "   View logs: docker-compose -f $COMPOSE_FILE logs -f [service]"
echo "   Stop services: docker-compose -f $COMPOSE_FILE down"
echo "   Restart service: docker-compose -f $COMPOSE_FILE restart [service]"