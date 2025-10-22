# Deployment Guide

## Development Deployment

The development environment runs locally with:
- Frontend: Vite dev server on port 5173
- Backend: Uvicorn on port 8000
- Database: PostgreSQL in Docker on port 5433

See [Getting Started Guide](./03-getting-started.md) for setup instructions.

## Production Deployment

### Prerequisites

- Docker and Docker Compose
- Domain name (optional)
- SSL certificate (recommended for production)

### Environment Configuration

#### Backend (.env)

```properties
# Production settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-strong-random-key>

# Database
DATABASE_URL=postgresql://audiobooker:<strong-password>@postgres:5432/audiobooker_db

# CORS - Update with your frontend domain
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Cloudflare R2 Storage
R2_ACCOUNT_ID=<your-account-id>
R2_ACCESS_KEY_ID=<your-access-key>
R2_SECRET_ACCESS_KEY=<your-secret-key>
R2_BUCKET_NAME=audiobooker-production
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com

# File Upload
MAX_UPLOAD_SIZE=52428800
ALLOWED_EXTENSIONS=.pdf
```

#### Frontend (.env.production)

```properties
VITE_API_URL=https://api.yourdomain.com
VITE_APP_NAME=Audiobooker
VITE_MAX_FILE_SIZE=52428800
```

### Docker Deployment

#### Update docker-compose.yml for Production

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: audiobooker-postgres
    restart: always
    environment:
      POSTGRES_USER: audiobooker
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: audiobooker_db
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - audiobooker-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U audiobooker"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: audiobooker-backend
    restart: always
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://audiobooker:${POSTGRES_PASSWORD}@postgres:5432/audiobooker_db
    env_file:
      - ./backend/.env
    networks:
      - audiobooker-network
    volumes:
      - ./backend/uploads:/app/uploads

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_URL: https://api.yourdomain.com
    container_name: audiobooker-frontend
    restart: always
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
    networks:
      - audiobooker-network
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl

volumes:
  postgres-data:

networks:
  audiobooker-network:
    driver: bridge
```

#### Backend Dockerfile

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build application
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

#### Nginx Configuration

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Deploy with Docker Compose

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Cloud Deployment Options

#### Option 1: VPS (Digital Ocean, Linode, AWS EC2)

1. **Provision server** (Ubuntu 22.04 recommended)
2. **Install Docker and Docker Compose**
3. **Clone repository**
4. **Configure environment variables**
5. **Run with Docker Compose**
6. **Set up SSL with Let's Encrypt**

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Clone and deploy
git clone https://github.com/andrewdangelo/Audiobooker.git
cd Audiobooker
cp backend/.env.example backend/.env
# Edit backend/.env with production values
docker-compose up -d --build
```

#### Option 2: Platform as a Service

**Frontend (Vercel/Netlify)**:
```bash
# Build command
npm run build

# Output directory
dist

# Environment variables
VITE_API_URL=https://api.yourdomain.com
```

**Backend (Railway/Render)**:
- Set Python version: 3.11
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add environment variables from `.env`

**Database (Managed PostgreSQL)**:
- Use managed PostgreSQL from your provider
- Update `DATABASE_URL` in backend environment

#### Option 3: Kubernetes (Advanced)

Create Kubernetes manifests for:
- PostgreSQL StatefulSet
- Backend Deployment
- Frontend Deployment
- Services and Ingress

### SSL/TLS Configuration

#### Let's Encrypt (Free)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (already configured by certbot)
sudo certbot renew --dry-run
```

### Database Backup

#### Automated Backups

Create `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/audiobooker_$TIMESTAMP.sql"

# Create backup
docker exec audiobooker-postgres pg_dump -U audiobooker audiobooker_db > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

Schedule with cron:
```bash
# Run daily at 2 AM
0 2 * * * /path/to/backup.sh
```

### Monitoring

#### Health Checks

```bash
# Check backend health
curl https://api.yourdomain.com/health

# Check all services
docker-compose ps
```

#### Logging

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 backend
```

### Performance Optimization

#### Backend

```python
# main.py - Increase workers for production
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,  # Number of CPU cores
        log_level="info"
    )
```

#### Frontend

```javascript
// vite.config.ts - Production optimizations
export default defineConfig({
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['@radix-ui/react-slot'],
        },
      },
    },
  },
})
```

### Security Checklist

- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS properly
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Database backups
- [ ] Rate limiting (future)
- [ ] Authentication (future)

### Scaling Considerations

#### Horizontal Scaling

- Load balancer in front of multiple backend instances
- Shared PostgreSQL database
- Centralized file storage (Cloudflare R2)
- Redis for session management (future)

#### Vertical Scaling

- Increase server resources (CPU, RAM)
- Database query optimization
- Connection pooling
- Caching layer (future)

### Rollback Procedure

```bash
# View current version
git log -1

# Rollback to previous version
git log  # Find commit hash
git checkout <previous-commit-hash>

# Rebuild and deploy
docker-compose down
docker-compose up -d --build

# Or restore from backup
docker exec -i audiobooker-postgres psql -U audiobooker -d audiobooker_db < backup.sql
```

### Maintenance Mode

Create a maintenance page and redirect all traffic:

```nginx
# nginx.conf
location / {
    return 503;
}

error_page 503 @maintenance;
location @maintenance {
    root /usr/share/nginx/html;
    rewrite ^(.*)$ /maintenance.html break;
}
```
