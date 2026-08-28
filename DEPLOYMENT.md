# Production Deployment Guide

This guide covers deploying Real-Time Vision System in production environments with security, scalability, and reliability in mind.

## 📋 Pre-Deployment Checklist

### Security
- [ ] Change default ports if exposing publicly
- [ ] Set up firewall rules (UFW, iptables, or cloud security groups)
- [ ] Configure HTTPS/TLS termination
- [ ] Add authentication to dashboard (see Security section)
- [ ] Review and remove debug/logging endpoints
- [ ] Use secrets management for sensitive data
- [ ] Enable automatic security updates
- [ ] Run containers as non-root user (already configured)

### Infrastructure
- [ ] Ensure adequate CPU/RAM resources
- [ ] Set up monitoring (Prometheus, Grafana, CloudWatch)
- [ ] Configure log aggregation (ELK, Loki, CloudWatch Logs)
- [ ] Plan backup strategy for configurations and data
- [ ] Test camera/network connectivity
- [ ] Verify GPU drivers (if using CUDA)

### Application
- [ ] Create production configuration (`configs/production.yaml`)
- [ ] Test with actual camera feeds
- [ ] Validate event detection logic
- [ ] Performance test under load
- [ ] Document rollback procedure

## 🔒 Security Hardening

### 1. Network Isolation

**Firewall Rules (Ubuntu UFW)**:
```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port if needed)
sudo ufw allow 22/tcp

# Allow dashboard only from trusted IPs
sudo ufw allow from 192.168.1.0/24 to any port 5050

# Enable firewall
sudo ufw enable
```

**Docker Network Isolation**:
```yaml
# docker-compose.prod.yml
networks:
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
  backend:
    internal: true  # No external access
```

### 2. HTTPS/TLS Termination

**Option A: Nginx Reverse Proxy**

Create `nginx/nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream vision_backend {
        server vision-system:5050;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        
        # Modern SSL configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        location / {
            proxy_pass http://vision_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_read_timeout 86400s;
            proxy_send_timeout 86400s;
        }
    }
}
```

**Get SSL Certificate (Let's Encrypt)**:
```bash
# Install Certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Certificates will be at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

**Option B: Traefik (Auto-HTTPS)**

```yaml
# docker-compose.traefik.yml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.myresolver.acme.tlschallenge=true"
      - "--certificatesresolvers.myresolver.acme.email=your@email.com"
      - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt
    networks:
      - web

  vision-system:
    # ... your existing config ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.vision.rule=Host(`your-domain.com`)"
      - "traefik.http.routers.vision.entrypoints=websecure"
      - "traefik.http.routers.vision.tls.certresolver=myresolver"
    networks:
      - web

networks:
  web:
    external: true
```

### 3. Authentication

**Basic Auth with Nginx**:
```bash
# Create password file
sudo apt install apache2-utils
htpasswd -c .htpasswd username

# Add to nginx.conf inside server block:
auth_basic "Restricted Access";
auth_basic_user_file /etc/nginx/.htpasswd;
```

**Add to Docker Compose**:
```yaml
volumes:
  - ./nginx/.htpasswd:/etc/nginx/.htpasswd:ro
```

### 4. Environment Variables & Secrets

**Create `.env.production`**:
```bash
# Never commit this file!
LOG_LEVEL=WARNING
DASHBOARD_PORT=5050
API_KEY=your-secret-api-key-here
DATABASE_URL=postgresql://user:password@db:5432/vision
```

**Update docker-compose**:
```yaml
services:
  vision-system:
    env_file:
      - .env.production
    environment:
      - API_KEY=${API_KEY}
```

## 🚀 Deployment Strategies

### Single Server Deployment

**Best for**: Small deployments, single camera, testing

```bash
# 1. Clone and configure
git clone https://github.com/yourusername/real-time-vision-system.git
cd real-time-vision-system
cp configs/default.yaml configs/production.yaml

# 2. Edit production.yaml for your setup
nano configs/production.yaml

# 3. Build and run
docker-compose -f docker-compose.yml up -d --build

# 4. Monitor
docker-compose logs -f
```

### Multi-Camera Deployment

**Best for**: Multiple cameras on one server

**docker-compose.multi.yml**:
```yaml
version: '3.8'

services:
  camera-1:
    build: .
    container_name: vision-cam-1
    restart: unless-stopped
    volumes:
      - ./configs/camera1.yaml:/app/configs/config.yaml:ro
    environment:
      - CAMERA_ID=1
    command: ["python", "main.py", "--config", "configs/config.yaml"]
    networks:
      - vision-network

  camera-2:
    build: .
    container_name: vision-cam-2
    restart: unless-stopped
    volumes:
      - ./configs/camera2.yaml:/app/configs/config.yaml:ro
    environment:
      - CAMERA_ID=2
    command: ["python", "main.py", "--config", "configs/config.yaml"]
    networks:
      - vision-network

  dashboard:
    image: nginx:alpine
    container_name: vision-dashboard
    ports:
      - "80:80"
    volumes:
      - ./nginx/multi.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - camera-1
      - camera-2
    networks:
      - vision-network

networks:
  vision-network:
    driver: bridge
```

### Kubernetes Deployment (Advanced)

**vision-deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vision-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vision-system
  template:
    metadata:
      labels:
        app: vision-system
    spec:
      containers:
      - name: vision-system
        image: your-registry/real-time-vision:latest
        ports:
        - containerPort: 5050
        resources:
          requests:
            memory: "2Gi"
            cpu: "2"
            nvidia.com/gpu: "1"  # If using GPU
          limits:
            memory: "4Gi"
            cpu: "4"
            nvidia.com/gpu: "1"
        volumeMounts:
        - name: config
          mountPath: /app/configs
          readOnly: true
        - name: data
          mountPath: /app/data
        livenessProbe:
          httpGet:
            path: /
            port: 5050
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 5050
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: vision-config
      - name: data
        persistentVolumeClaim:
          claimName: vision-data-pvc
      nodeSelector:
        gpu: "true"  # If using GPU nodes
---
apiVersion: v1
kind: Service
metadata:
  name: vision-service
spec:
  selector:
    app: vision-system
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5050
  type: LoadBalancer  # Or ClusterIP with Ingress
```

## 📊 Monitoring & Observability

### Health Checks

Already configured in Dockerfile and docker-compose.yml:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import socket; s = socket.socket(); s.settimeout(5); result = s.connect_ex(('localhost', 5050)); s.close(); exit(0 if result == 0 else 1)"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging

**Structured Logging** (add to main.py):
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Configure
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

**Log Aggregation** (Docker):
```yaml
services:
  vision-system:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        # Or send to syslog/fluend/elasticsearch
```

### Metrics (Future Enhancement)

Add Prometheus metrics endpoint:
```python
from prometheus_client import Counter, Histogram, generate_latest

DETECTIONS = Counter('detections_total', 'Total detections', ['class'])
PROCESSING_TIME = Histogram('processing_seconds', 'Processing time')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example

**.github/workflows/deploy.yml**:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt pytest
      - name: Run tests
        run: pytest tests/ -v

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t your-registry/real-time-vision:${{ github.sha }} .
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push your-registry/real-time-vision:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/real-time-vision
            docker-compose pull
            docker-compose up -d --remove-orphans
```

## 🛡️ Backup & Recovery

### Configuration Backup

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups/vision-$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup configs
cp -r configs/ $BACKUP_DIR/

# Backup custom models
cp -r data/models/ $BACKUP_DIR/ 2>/dev/null || true

# Backup docker-compose
cp docker-compose.yml $BACKUP_DIR/

# Compress
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Upload to cloud (example with AWS S3)
aws s3 cp $BACKUP_DIR.tar.gz s3://your-bucket/backups/

# Keep only last 7 backups
find /backups -name "vision-*.tar.gz" -mtime +7 -delete
```

### Disaster Recovery

1. **Restore from backup**:
```bash
# Download backup
aws s3 cp s3://your-bucket/backups/vision-20240101-120000.tar.gz .
tar -xzf vision-20240101-120000.tar.gz

# Restore
cp -r vision-20240101-120000/configs/ ./
cp vision-20240101-120000/docker-compose.yml ./

# Restart
docker-compose up -d
```

2. **Rollback to previous version**:
```bash
# List images
docker images your-registry/real-time-vision

# Rollback
docker-compose down
docker tag your-registry/real-time-vision:previous latest
docker-compose up -d
```

## 📈 Performance Tuning

### CPU Optimization

```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
    reservations:
      cpus: '2'
      memory: 2G
```

### GPU Optimization

```yaml
# Ensure NVIDIA runtime
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### Model Selection

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| yolov8n | Fastest | Lower | Edge devices, high FPS |
| yolov8s | Fast | Medium | General purpose |
| yolov8m | Medium | High | Balanced performance |
| yolov8l | Slow | Very High | High accuracy needs |
| yolov8x | Slowest | Highest | Critical applications |

## 🎯 Production Configuration Example

**configs/production.yaml**:
```yaml
source:
  type: "camera"
  camera_index: 0
  width: 1920
  height: 1080
  fps: 30
  reconnect_attempts: 10
  reconnect_delay: 3.0

detector:
  model_path: "yolov8m.pt"
  confidence_threshold: 0.6
  iou_threshold: 0.5
  device: "cuda"  # or "cpu"
  img_size: 640

tracker:
  type: "iou"
  max_lost_frames: 60
  iou_threshold: 0.3

pipeline:
  window_name: "Production Vision System"
  show_fps: true
  save_detections: false  # Disable in production unless needed

events:
  log_events: true
  log_to_file: true
  log_path: "/app/logs/events.log"
  lines:
    - name: "entry_line"
      start: [200, 500]
      end: [1700, 500]
  zones:
    - name: "restricted_area"
      points: [[300,300], [1600,300], [1600,800], [300,800]]
```

## ✅ Post-Deployment Validation

1. **Health Check**:
```bash
curl -f http://localhost:5050/ || echo "Dashboard not responding"
```

2. **Camera Feed**:
```bash
docker-compose logs vision-system | grep -i "frame\|camera"
```

3. **Performance**:
```bash
# Check resource usage
docker stats vision-system

# Check FPS in logs
docker-compose logs vision-system | grep FPS
```

4. **Event Detection**:
```bash
# Walk through zones/lines and verify events are logged
docker-compose logs vision-system | grep -i "event\|zone\|line"
```

## 📞 Support & Maintenance

### Regular Maintenance Tasks

- **Weekly**: Check logs for errors, review disk space
- **Monthly**: Update dependencies, review security advisories
- **Quarterly**: Full system backup, performance review
- **Annually**: Hardware inspection, capacity planning

### Getting Help

- Documentation: See README.md
- Issues: GitHub Issues
- Emergency: On-call contact (configure in your organization)

---

**Remember**: Security is ongoing. Regularly update dependencies, monitor for vulnerabilities, and review access controls.
