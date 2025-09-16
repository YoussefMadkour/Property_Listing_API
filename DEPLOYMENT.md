# Deployment Guide

This guide covers deploying the Property Listing API in different environments using Docker.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Development Deployment](#development-deployment)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment)
- [Database Management](#database-management)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Docker**: 20.10+ with Docker Compose 2.0+
- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2
- **Memory**: Minimum 2GB RAM (4GB+ recommended for production)
- **Storage**: Minimum 10GB free space (50GB+ recommended for production)
- **Network**: Ports 80, 443, 8000, and 5432 available

### Required Tools

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose (if not included)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd property-listing-api
```

### 2. Choose Environment Configuration

Copy the appropriate environment template:

```bash
# For development
cp .env.development .env

# For staging
cp .env.staging .env

# For production
cp .env.production .env
```

### 3. Configure Environment Variables

Edit the `.env` file and update the following critical values:

#### Required Changes for Production

```bash
# Strong database password
POSTGRES_PASSWORD=your-very-strong-database-password

# Strong JWT secret (64+ characters)
JWT_SECRET_KEY=your-very-strong-jwt-secret-key-at-least-64-characters-long

# Your domain(s)
CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com

# Redis password
REDIS_PASSWORD=your-strong-redis-password
```

## Development Deployment

### Quick Start

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose --profile migration up migrate

# Check health
curl http://localhost:8000/health
```

### Development Commands

```bash
# View logs
docker-compose logs -f api

# Restart API service
docker-compose restart api

# Run tests
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Stop all services
docker-compose down
```

## Staging Deployment

### 1. Prepare Environment

```bash
# Copy staging configuration
cp .env.staging .env

# Edit configuration
nano .env
```

### 2. Deploy

```bash
# Use deployment script
./scripts/deploy.sh staging

# Or manually
docker-compose up -d --build
docker-compose --profile migration up migrate
```

### 3. Verify Deployment

```bash
# Run health check
./scripts/health-check.sh

# Check API documentation
curl http://your-staging-domain.com/docs
```

## Production Deployment

### 1. Server Preparation

#### Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git
```

#### Configure Firewall

```bash
# Allow SSH, HTTP, and HTTPS
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### Set up SSL Certificates

```bash
# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Option 1: Let's Encrypt (recommended)
sudo apt install -y certbot
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /etc/nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /etc/nginx/ssl/key.pem

# Option 2: Self-signed (development only)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/key.pem \
  -out /etc/nginx/ssl/cert.pem
```

### 2. Deploy Application

```bash
# Clone repository
git clone <repository-url>
cd property-listing-api

# Configure production environment
cp .env.production .env
nano .env  # Update all CHANGE_ME values

# Deploy using script
./scripts/deploy.sh production
```

### 3. Configure Nginx for HTTPS

Edit `nginx/conf.d/default.conf` and uncomment the HTTPS server block, then update your domain:

```bash
# Update Nginx configuration
sed -i 's/your-domain.com/yourdomain.com/g' nginx/conf.d/default.conf

# Restart Nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### 4. Verify Production Deployment

```bash
# Health check
./scripts/health-check.sh

# Test HTTPS
curl -I https://yourdomain.com/health

# Check SSL rating
curl -I https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

## Database Management

### Migrations

```bash
# Run migrations
docker-compose --profile migration up migrate

# Create new migration
docker-compose run --rm api alembic revision --autogenerate -m "Description"

# Rollback migration
docker-compose run --rm api alembic downgrade -1

# Check migration status
docker-compose run --rm api alembic current
```

### Database Access

```bash
# Connect to database
docker-compose exec db psql -U postgres -d property_listings

# Run SQL file
docker-compose exec -T db psql -U postgres -d property_listings < backup.sql

# Create database dump
docker-compose exec db pg_dump -U postgres property_listings > backup.sql
```

## Monitoring and Health Checks

### Built-in Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# Comprehensive health check
./scripts/health-check.sh
```

### Monitoring Endpoints

- **Health**: `GET /health`
- **Database Health**: `GET /health/db`
- **Metrics**: `GET /metrics` (if enabled)
- **API Documentation**: `GET /docs`

### Log Management

```bash
# View API logs
docker-compose logs -f api

# View database logs
docker-compose logs -f db

# View Nginx logs (production)
docker-compose -f docker-compose.prod.yml logs -f nginx

# Export logs
docker-compose logs api > api.log
```

## Backup and Recovery

### Automated Backups

Backups are configured in production Docker Compose:

```bash
# Enable backup service
docker-compose -f docker-compose.prod.yml --profile backup up -d backup

# Manual backup
./scripts/backup.sh
```

### Backup Configuration

Edit `docker-compose.prod.yml` to configure backup schedule:

```yaml
environment:
  BACKUP_SCHEDULE: "0 2 * * *"  # Daily at 2 AM
```

### Recovery

```bash
# List available backups
ls -la backups/

# Restore from backup
docker-compose exec -T db psql -U postgres -d property_listings < backups/backup_file.sql

# Or using compressed backup
gunzip -c backups/backup_file.sql.gz | docker-compose exec -T db psql -U postgres -d property_listings
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check database status
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec db pg_isready -U postgres
```

#### 2. API Not Responding

```bash
# Check API logs
docker-compose logs api

# Check if port is available
netstat -tlnp | grep :8000

# Restart API service
docker-compose restart api
```

#### 3. Permission Denied Errors

```bash
# Fix upload directory permissions
sudo chown -R 1000:1000 uploads/
chmod 755 uploads/

# Fix script permissions
chmod +x scripts/*.sh
```

#### 4. SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in /etc/nginx/ssl/cert.pem -text -noout

# Renew Let's Encrypt certificate
sudo certbot renew

# Test SSL configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### Performance Issues

#### 1. Slow Database Queries

```bash
# Check database performance
docker-compose exec db psql -U postgres -d property_listings -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"

# Analyze query plans
docker-compose exec db psql -U postgres -d property_listings -c "
EXPLAIN ANALYZE SELECT * FROM properties WHERE location = 'Dubai';"
```

#### 2. High Memory Usage

```bash
# Check container memory usage
docker stats

# Check system memory
free -h

# Restart services to free memory
docker-compose restart
```

### Emergency Procedures

#### 1. Service Outage

```bash
# Quick restart
docker-compose restart

# Full rebuild
docker-compose down
docker-compose up -d --build

# Check all services
./scripts/health-check.sh
```

#### 2. Data Corruption

```bash
# Stop services
docker-compose down

# Restore from backup
gunzip -c backups/latest_backup.sql.gz | docker-compose exec -T db psql -U postgres -d property_listings

# Start services
docker-compose up -d

# Verify data integrity
./scripts/health-check.sh
```

### Getting Help

#### Log Collection

```bash
# Collect all logs
mkdir -p debug_logs
docker-compose logs api > debug_logs/api.log
docker-compose logs db > debug_logs/db.log
docker-compose logs nginx > debug_logs/nginx.log
docker-compose ps > debug_logs/services.txt
./scripts/health-check.sh > debug_logs/health.txt
```

#### System Information

```bash
# System info
uname -a > debug_logs/system.txt
docker version >> debug_logs/system.txt
docker-compose version >> debug_logs/system.txt
df -h >> debug_logs/system.txt
free -h >> debug_logs/system.txt
```

## Security Checklist

### Pre-deployment Security

- [ ] Change all default passwords
- [ ] Use strong JWT secret key (64+ characters)
- [ ] Configure CORS origins properly
- [ ] Set up SSL certificates
- [ ] Configure firewall rules
- [ ] Enable security headers in Nginx
- [ ] Set up rate limiting
- [ ] Configure secure cookie settings

### Post-deployment Security

- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Set up intrusion detection
- [ ] Regular backup testing
- [ ] SSL certificate renewal
- [ ] Security vulnerability scanning
- [ ] Access control review

## Maintenance

### Regular Tasks

#### Daily
- [ ] Check service health
- [ ] Review error logs
- [ ] Monitor disk space

#### Weekly
- [ ] Review performance metrics
- [ ] Check backup integrity
- [ ] Update dependencies

#### Monthly
- [ ] Security updates
- [ ] SSL certificate check
- [ ] Performance optimization review
- [ ] Backup retention cleanup

### Update Procedure

```bash
# 1. Backup current state
./scripts/backup.sh

# 2. Pull latest changes
git pull origin main

# 3. Update dependencies
docker-compose pull

# 4. Deploy updates
./scripts/deploy.sh production

# 5. Verify deployment
./scripts/health-check.sh
```