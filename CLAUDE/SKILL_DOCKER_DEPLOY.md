```markdown
# Cẩm nang Kỹ năng: Docker & Deployment (SKILL_DOCKER_DEPLOY.md)

**Mục đích:** Hướng dẫn đóng gói toàn bộ hệ thống IDS vào Docker containers để dễ dàng deploy, demo và scale.

## 1. Kiến trúc Multi-container

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   sniffer    │  │   backend    │  │    model     │       │
│  │ (Snort+Parser)│ │  (Node.js)   │  │  (FastAPI)   │       │
│  │  Port: 9000  │─▶│  Port: 3000  │─▶│  Port: 8000  │       │
│  └──────────────┘  └──────┬───────┘  └──────────────┘       │
│                          │                                   │
│                          ▼                                   │
│                   ┌──────────────┐  ┌──────────────┐        │
│                   │   frontend   │  │   postgres   │        │
│                   │   (React)    │  │  (Database)  │        │
│                   │  Port: 80    │  │  Port: 5432  │        │
│                   └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 2. Dockerfile cho từng Service

### 2.1 Sniffer (Snort + Parser)
```dockerfile
# /sniffer/Dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
  snort \
  python3 \
  python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip3 install --no-cache-dir -r parser-requirements.txt

# Chạy Snort logger mode và parser service
CMD ["bash", "-lc", "snort -i ${INTERFACE:-eth0} -A fast -l /var/log/snort -c /etc/snort/snort.conf & python3 parser/stream_parser.py"]
```

### 2.2 Model API (FastAPI + ONNX)
```dockerfile
# /model/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies trước để tận dụng Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port và chạy với nhiều workers
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 2.3 Backend (Node.js)
```dockerfile
# /backend/Dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000
CMD ["node", "server.js"]
```

### 2.4 Frontend (React)
```dockerfile
# /frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage với nginx
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 3. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ids_db
      POSTGRES_USER: ids_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:-secretpassword}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ids_user -d ids_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  model:
    build: ./model
    ports:
      - "8000:8000"
    environment:
      - ONNX_MODEL_PATH=/app/models/autoencoder.onnx
    volumes:
      - ./model/models:/app/models:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  backend:
    build: ./backend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - MODEL_API_URL=http://model:8000
      - DATABASE_URL=postgresql://ids_user:${DB_PASSWORD:-secretpassword}@postgres:5432/ids_db
      - SNIFFER_PORT=9000
    depends_on:
      postgres:
        condition: service_healthy
      model:
        condition: service_healthy

  sniffer:
    build: ./sniffer
    network_mode: host  # Cần để capture traffic thực
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - BACKEND_HOST=127.0.0.1
      - BACKEND_PORT=9000
      - INTERFACE=eth0
    depends_on:
      - backend

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

## 4. Lệnh Deploy thường dùng

### Development (với hot-reload)
```bash
# Build và start tất cả services
docker-compose up --build

# Chỉ start một số services
docker-compose up backend model postgres

# Xem logs của service cụ thể
docker-compose logs -f backend

# Restart một service
docker-compose restart model
```

### Production
```bash
# Build images với tag version
docker-compose build --no-cache
docker tag ids_backend:latest ids_backend:v1.0.0

# Start ở background
docker-compose up -d

# Scale backend (nếu cần)
docker-compose up -d --scale backend=3

# Graceful shutdown
docker-compose down
```

## 5. Xử lý Network cho Sniffer

### Vấn đề
- Container mặc định chạy trong network riêng (bridge), không capture được traffic thật.

### Giải pháp
1. **network_mode: host** - Container dùng chung network stack với host
2. **Capabilities**: Cần `NET_ADMIN` và `NET_RAW` để Snort capture traffic
3. **Promiscuous mode**: Bật trên interface host trước khi start container

```bash
# Bật promiscuous mode trên host
sudo ip link set eth0 promisc on

# Verify
ip link show eth0 | grep PROMISC
```

## 6. Volumes và Persistence

| Volume | Mount Point | Mục đích |
|--------|-------------|----------|
| `postgres_data` | `/var/lib/postgresql/data` | Lưu alerts, không mất khi restart |
| `./model/models` | `/app/models` (read-only) | ONNX model files |
| `./logs` | `/app/logs` | Log files cho debugging |

## 7. Environment Variables

Dùng file `.env` để quản lý secrets:
```bash
# .env (KHÔNG commit vào git!)
DB_PASSWORD=your_secure_password
JWT_SECRET=your_jwt_secret
MODEL_THRESHOLD=0.85
```

## 8. Health Checks & Monitoring

### Kiểm tra health của stack
```bash
# Xem status tất cả containers
docker-compose ps

# Kiểm tra resource usage
docker stats

# Inspect một container
docker inspect ids_backend_1
```

### Endpoints health check
- Model API: `GET http://localhost:8000/health`
- Backend: `GET http://localhost:3000/api/health`
- Frontend: HTTP 200 từ nginx

## 9. Demo Day Checklist

```markdown
### Trước demo 1 ngày:
- [ ] Pull latest code, build images mới
- [ ] Test docker-compose up trên máy demo
- [ ] Verify network connectivity giữa VMs
- [ ] Backup video demo phòng trường hợp fail

### Trước demo 30 phút:
- [ ] Start docker-compose up -d
- [ ] Verify tất cả services healthy
- [ ] Mở sẵn Dashboard trên browser
- [ ] Chuẩn bị terminal Kali Linux với attack scripts

### Khi demo:
- [ ] Chỉ cho hội đồng Dashboard đang chạy
- [ ] Chạy attack từ Kali
- [ ] Highlight real-time alerts xuất hiện
```
```
