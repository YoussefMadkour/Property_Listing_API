#!/bin/bash

# Health Check Script for Property Listing API
# This script performs comprehensive health checks on all services

set -e

API_URL="${API_URL:-http://localhost:8000}"
TIMEOUT=10

echo "🏥 Property Listing API Health Check"
echo "=================================="

# Function to check HTTP endpoint
check_endpoint() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $name... "
    
    if response=$(curl -s -w "%{http_code}" -m $TIMEOUT "$url" -o /dev/null); then
        if [ "$response" = "$expected_status" ]; then
            echo "✅ OK ($response)"
            return 0
        else
            echo "❌ FAIL (HTTP $response, expected $expected_status)"
            return 1
        fi
    else
        echo "❌ FAIL (Connection failed)"
        return 1
    fi
}

# Function to check Docker service
check_docker_service() {
    local service=$1
    echo -n "Checking Docker service $service... "
    
    if docker-compose ps "$service" | grep -q "Up"; then
        echo "✅ Running"
        return 0
    else
        echo "❌ Not running"
        return 1
    fi
}

# Check Docker services
echo "🐳 Docker Services:"
check_docker_service "api" || HEALTH_ISSUES=1
check_docker_service "db" || HEALTH_ISSUES=1

echo ""

# Check API endpoints
echo "🌐 API Endpoints:"
check_endpoint "$API_URL/health" "Health endpoint" || HEALTH_ISSUES=1
check_endpoint "$API_URL/health/db" "Database health" || HEALTH_ISSUES=1
check_endpoint "$API_URL/docs" "API documentation" || HEALTH_ISSUES=1

echo ""

# Check database connectivity
echo "🗄️ Database Connectivity:"
echo -n "Checking PostgreSQL connection... "
if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ Connected"
else
    echo "❌ Connection failed"
    HEALTH_ISSUES=1
fi

echo ""

# Check disk space
echo "💾 Disk Space:"
echo -n "Checking available disk space... "
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    echo "✅ OK (${DISK_USAGE}% used)"
else
    echo "⚠️ WARNING (${DISK_USAGE}% used)"
    HEALTH_ISSUES=1
fi

echo ""

# Check memory usage
echo "🧠 Memory Usage:"
echo -n "Checking available memory... "
if command -v free > /dev/null; then
    MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$MEMORY_USAGE" -lt 90 ]; then
        echo "✅ OK (${MEMORY_USAGE}% used)"
    else
        echo "⚠️ WARNING (${MEMORY_USAGE}% used)"
        HEALTH_ISSUES=1
    fi
else
    echo "ℹ️ Memory check not available"
fi

echo ""

# Check log files for errors
echo "📋 Recent Logs:"
echo -n "Checking for recent errors... "
if docker-compose logs --tail=100 api 2>/dev/null | grep -i "error\|exception\|failed" > /dev/null; then
    echo "⚠️ Errors found in logs"
    echo "Recent errors:"
    docker-compose logs --tail=20 api | grep -i "error\|exception\|failed" | tail -5
    HEALTH_ISSUES=1
else
    echo "✅ No recent errors"
fi

echo ""
echo "=================================="

# Summary
if [ "${HEALTH_ISSUES:-0}" = "1" ]; then
    echo "❌ Health check completed with issues"
    echo ""
    echo "🔧 Troubleshooting commands:"
    echo "   View API logs: docker-compose logs -f api"
    echo "   View DB logs: docker-compose logs -f db"
    echo "   Restart services: docker-compose restart"
    echo "   Check service status: docker-compose ps"
    exit 1
else
    echo "✅ All health checks passed!"
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    exit 0
fi