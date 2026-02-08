# Auth Service Installation & Deployment Guide

## Local Development Setup

### Step 1: Clone/Navigate to Project
```bash
cd microservices/auth-service
```

### Step 2: Create Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Setup Environment Variables
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your values
# Minimum required:
# - SECRET_KEY (generate a secure key)
# - DATABASE_URL (your PostgreSQL connection)
# - GOOGLE_CLIENT_ID (from Google Cloud Console)
# - GOOGLE_CLIENT_SECRET (from Google Cloud Console)
```

### Step 5: Generate Secret Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Copy the output and set as `SECRET_KEY` in `.env`

### Step 6: Initialize Database
```bash
python init_db.py create
```

### Step 7: Run Service
```bash
python main.py
```

Service will start at: `http://localhost:8003`

---

## Docker Deployment

### Build Image
```bash
docker build -t audiobooker-auth-service:1.0 .
```

### Run Container
```bash
docker run \
  -p 8003:8003 \
  --env-file .env \
  --name auth-service \
  audiobooker-auth-service:1.0
```

### View Logs
```bash
docker logs -f auth-service
```

### Stop Container
```bash
docker stop auth-service
docker rm auth-service
```

---

## Docker Compose Setup

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: audiobooker
      POSTGRES_PASSWORD: password
      POSTGRES_DB: audiobooker_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  auth-service:
    build: ./microservices/auth-service
    ports:
      - "8003:8003"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://audiobooker:password@postgres:5432/audiobooker_db
      SECRET_KEY: ${SECRET_KEY}
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      GOOGLE_REDIRECT_URI: ${GOOGLE_REDIRECT_URI}
    volumes:
      - ./microservices/auth-service/logs:/app/logs

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up -d
```

---

## Production Deployment

### Prerequisites
- PostgreSQL 12+ server
- Python 3.11+
- SSL certificate for HTTPS
- Redis server (optional, for caching)

### Step 1: Prepare Server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv postgresql postgresql-contrib redis-server

# Create application user
sudo useradd -m audiobooker
```

### Step 2: Clone Application
```bash
cd /home/audiobooker
git clone <your-repo> Audiobooker
cd Audiobooker/microservices/auth-service
```

### Step 3: Setup Application
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with production values
nano .env
```

### Step 4: Initialize Database
```bash
python init_db.py create
```

### Step 5: Setup Systemd Service
Create `/etc/systemd/system/auth-service.service`:

```ini
[Unit]
Description=Audiobooker Auth Service
After=network.target postgresql.service

[Service]
Type=notify
User=audiobooker
WorkingDirectory=/home/audiobooker/Audiobooker/microservices/auth-service
Environment="PATH=/home/audiobooker/Audiobooker/microservices/auth-service/venv/bin"
ExecStart=/home/audiobooker/Audiobooker/microservices/auth-service/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable auth-service
sudo systemctl start auth-service
```

Check status:
```bash
sudo systemctl status auth-service
```

### Step 6: Setup Nginx Reverse Proxy
Create `/etc/nginx/sites-available/auth-service`:

```nginx
server {
    listen 443 ssl http2;
    server_name auth.yourdomain.com;

    ssl_certificate /path/to/ssl/cert.crt;
    ssl_certificate_key /path/to/ssl/key.key;

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

server {
    listen 80;
    server_name auth.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/auth-service /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Kubernetes Deployment

### Create ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: auth-service-config
  namespace: default
data:
  ENVIRONMENT: "production"
  PORT: "8003"
  LOG_LEVEL: "INFO"
  API_V1_PREFIX: "/api/v1/auth"
```

### Create Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: auth-service-secrets
  namespace: default
type: Opaque
stringData:
  SECRET_KEY: "your-secret-key"
  DATABASE_URL: "postgresql://user:pass@db:5432/audiobooker_db"
  GOOGLE_CLIENT_ID: "your-google-client-id"
  GOOGLE_CLIENT_SECRET: "your-google-client-secret"
```

### Create Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
      - name: auth-service
        image: your-registry/auth-service:1.0
        ports:
        - containerPort: 8003
        envFrom:
        - configMapRef:
            name: auth-service-config
        - secretRef:
            name: auth-service-secrets
        livenessProbe:
          httpGet:
            path: /api/v1/auth/health/live
            port: 8003
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/auth/health/ready
            port: 8003
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

### Create Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: auth-service
  namespace: default
spec:
  selector:
    app: auth-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8003
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

---

## Database Migrations (Future)

When using Alembic:

```bash
# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Monitoring & Maintenance

### Check Service Status
```bash
curl http://localhost:8003/api/v1/auth/health/
```

### View Logs
```bash
# Local
tail -f logs/auth_service.log

# Docker
docker logs -f auth-service

# Systemd
journalctl -u auth-service -f
```

### Database Backup
```bash
pg_dump -U audiobooker -h localhost audiobooker_db > backup.sql
```

### Database Restore
```bash
psql -U audiobooker -h localhost audiobooker_db < backup.sql
```

---

## Troubleshooting

### Service won't start
- Check logs: `tail -f logs/auth_service.log`
- Verify database connection: `psql -U audiobooker -h localhost -d audiobooker_db`
- Check environment variables: `grep -E '^[A-Z]' .env`

### Database connection errors
- Ensure PostgreSQL is running: `systemctl status postgresql`
- Check DATABASE_URL in .env
- Verify user credentials: `psql -U audiobooker`

### Port already in use
- Find process: `lsof -i :8003`
- Kill process: `kill -9 <pid>`
- Or change PORT in .env

### Google OAuth not working
- Verify credentials in Google Cloud Console
- Check redirect URI matches exactly
- Test with `/api/v1/auth/google/auth-url` endpoint

---

## Security Checklist

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Use HTTPS in production
- [ ] Configure firewall rules
- [ ] Setup automated backups
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated: `pip list --outdated`
- [ ] Setup rate limiting (implement in code)
- [ ] Enable database encryption at rest
- [ ] Use secrets management system (Vault, AWS Secrets, etc.)
- [ ] Setup SSL certificates with auto-renewal (Let's Encrypt)

---

## Performance Tuning

### Database
```sql
-- Create indexes for faster queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
```

### Caching (with Redis)
Add to requirements.txt and `.env`:
```
REDIS_HOST=localhost
REDIS_PORT=6379
```

Then implement caching in services for frequently accessed data.

### Connection Pooling
Already configured in SQLAlchemy with `pool_pre_ping=True`

---

## Scaling

### Horizontal Scaling
- Run multiple instances behind load balancer
- Use shared PostgreSQL database
- Implement session persistence with Redis

### Vertical Scaling
- Increase server resources
- Tune database parameters
- Implement caching layer

---

## Support

For issues:
1. Check logs: `logs/auth_service.log`
2. Review API_REFERENCE.md for endpoint details
3. Check FRONTEND_INTEGRATION.md for integration help
4. Verify environment variables are set correctly
