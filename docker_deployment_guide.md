# IntelliDoc Docker 이미지 빌드 및 배포 가이드

## 목차
1. [소개](#1-소개)
2. [사전 요구사항](#2-사전-요구사항)
3. [Docker 이미지 빌드](#3-docker-이미지-빌드)
4. [Docker Compose를 사용한 배포](#4-docker-compose를-사용한-배포)
5. [Kubernetes를 사용한 배포](#5-kubernetes를-사용한-배포)
6. [클라우드 환경 배포](#6-클라우드-환경-배포)
7. [환경 변수 관리](#7-환경-변수-관리)
8. [데이터 볼륨 관리](#8-데이터-볼륨-관리)
9. [보안 고려사항](#9-보안-고려사항)
10. [모니터링 및 로깅 설정](#10-모니터링-및-로깅-설정)
11. [배포 자동화](#11-배포-자동화)
12. [문제 해결](#12-문제-해결)

## 1. 소개

이 문서는 IntelliDoc 시스템의 Docker 이미지 빌드 및 다양한 환경에서의 배포 방법을 설명합니다. Docker를 사용하면 개발, 테스트, 운영 환경 간의 일관성을 유지하고, 배포 프로세스를 간소화할 수 있습니다.

IntelliDoc은 다음과 같은 컨테이너로 구성됩니다:
- **intellidoc-backend**: FastAPI 기반 백엔드 API 서버
- **intellidoc-worker**: Celery 워커 (OCR, LLM 처리 등 비동기 작업 수행)
- **intellidoc-frontend**: React 기반 프론트엔드 (Nginx로 서빙)
- **postgres**: PostgreSQL 데이터베이스
- **redis**: Redis 캐시 및 메시지 큐
- **prometheus**: 메트릭 수집 (선택 사항)
- **grafana**: 모니터링 대시보드 (선택 사항)
- **elasticsearch**, **logstash**, **kibana**: 로깅 스택 (선택 사항)

## 2. 사전 요구사항

### 2.1 필수 소프트웨어
- Docker Engine 20.10.0 이상
- Docker Compose 2.0.0 이상 (Docker Compose 배포 시)
- kubectl 1.20.0 이상 (Kubernetes 배포 시)
- Git

### 2.2 하드웨어 요구사항 (최소)
- CPU: 4 코어
- 메모리: 8GB RAM
- 디스크: 50GB 이상 (문서 저장소 크기에 따라 증가)

### 2.3 네트워크 요구사항
- 인터넷 연결 (OCR/LLM API 사용 시)
- 포트 개방:
  - 80/443: 웹 인터페이스
  - 8000: 백엔드 API (개발 환경)
  - 5432: PostgreSQL (내부 네트워크)
  - 6379: Redis (내부 네트워크)

## 3. Docker 이미지 빌드

### 3.1 소스 코드 준비
```bash
# 저장소 클론
git clone https://github.com/yourusername/intellidoc.git
cd intellidoc
```

### 3.2 백엔드 이미지 빌드
```bash
# 백엔드 이미지 빌드
cd backend
docker build -t intellidoc-backend:latest .

# 태그 지정 (선택 사항)
docker tag intellidoc-backend:latest yourdockerhub/intellidoc-backend:latest
```

백엔드 Dockerfile 내용:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PORT=8000

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "web_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.3 워커 이미지 빌드
워커는 백엔드와 동일한 이미지를 사용하지만 다른 명령으로 실행합니다:
```bash
# 백엔드 이미지를 워커로 태그 지정
docker tag intellidoc-backend:latest intellidoc-worker:latest
```

### 3.4 프론트엔드 이미지 빌드
```bash
# 프론트엔드 이미지 빌드
cd ../frontend
docker build -t intellidoc-frontend:latest .

# 태그 지정 (선택 사항)
docker tag intellidoc-frontend:latest yourdockerhub/intellidoc-frontend:latest
```

프론트엔드 Dockerfile 내용:
```dockerfile
# 빌드 단계
FROM node:16-alpine as build

WORKDIR /app

# 의존성 설치
COPY package.json package-lock.json ./
RUN npm ci

# 소스 코드 복사 및 빌드
COPY . .
RUN npm run build

# 실행 단계
FROM nginx:alpine

# Nginx 설정 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 빌드 결과물 복사
COPY --from=build /app/dist /usr/share/nginx/html

# 포트 노출
EXPOSE 80

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]
```

프론트엔드 Nginx 설정 (nginx.conf):
```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # API 프록시 설정
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 정적 파일 서빙
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "public, max-age=3600";
    }

    # 오류 페이지
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
```

### 3.5 이미지 푸시 (선택 사항)
```bash
# Docker Hub 또는 프라이빗 레지스트리에 이미지 푸시
docker login
docker push yourdockerhub/intellidoc-backend:latest
docker push yourdockerhub/intellidoc-frontend:latest
```

## 4. Docker Compose를 사용한 배포

Docker Compose는 개발 환경이나 소규모 배포에 적합한 방법입니다.

### 4.1 docker-compose.yml 파일
프로젝트 루트 디렉토리에 다음 내용의 `docker-compose.yml` 파일을 생성합니다:

```yaml
version: '3.8'

services:
  # PostgreSQL 데이터베이스
  postgres:
    image: postgres:13-alpine
    container_name: intellidoc-postgres
    environment:
      POSTGRES_USER: ${DB_USERNAME:-intellidoc}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-password}
      POSTGRES_DB: ${DB_NAME:-intellidoc}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init-scripts:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USERNAME:-intellidoc}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis 캐시 및 메시지 큐
  redis:
    image: redis:6-alpine
    container_name: intellidoc-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # 백엔드 API 서버
  backend:
    image: intellidoc-backend:latest
    container_name: intellidoc-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://${DB_USERNAME:-intellidoc}:${DB_PASSWORD:-password}@postgres:5432/${DB_NAME:-intellidoc}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY:-your-secret-key}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:3000,http://localhost}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - GOOGLE_VISION_API_KEY=${GOOGLE_VISION_API_KEY:-}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - document_storage:/app/storage
    restart: unless-stopped

  # Celery 워커
  worker:
    image: intellidoc-worker:latest
    container_name: intellidoc-worker
    command: celery -A celery_app worker --loglevel=info
    depends_on:
      - backend
      - redis
    environment:
      - DATABASE_URL=postgresql://${DB_USERNAME:-intellidoc}:${DB_PASSWORD:-password}@postgres:5432/${DB_NAME:-intellidoc}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY:-your-secret-key}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - GOOGLE_VISION_API_KEY=${GOOGLE_VISION_API_KEY:-}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./backend:/app
      - document_storage:/app/storage
    restart: unless-stopped

  # 프론트엔드 웹 서버
  frontend:
    image: intellidoc-frontend:latest
    container_name: intellidoc-frontend
    depends_on:
      - backend
    ports:
      - "80:80"
    restart: unless-stopped

  # Prometheus (선택 사항)
  prometheus:
    image: prom/prometheus:latest
    container_name: intellidoc-prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    restart: unless-stopped

  # Grafana (선택 사항)
  grafana:
    image: grafana/grafana:latest
    container_name: intellidoc-grafana
    depends_on:
      - prometheus
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  document_storage:
  prometheus_data:
  grafana_data:
```

### 4.2 환경 변수 설정
`.env` 파일을 생성하여 환경 변수를 설정합니다:

```
# 데이터베이스 설정
DB_USERNAME=intellidoc
DB_PASSWORD=your-secure-password
DB_NAME=intellidoc

# 보안 설정
SECRET_KEY=your-very-secure-secret-key

# API 키
OPENAI_API_KEY=your-openai-api-key
GOOGLE_VISION_API_KEY=your-google-vision-api-key

# CORS 설정
ALLOWED_ORIGINS=http://localhost:3000,http://localhost,https://yourdomain.com

# 로깅 설정
LOG_LEVEL=INFO

# Grafana 설정 (선택 사항)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-grafana-password
```

### 4.3 배포 실행
```bash
# 환경 변수 파일 생성
cp .env.example .env
# .env 파일 편집

# 컨테이너 빌드 및 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그 확인
docker-compose logs -f backend
```

### 4.4 데이터베이스 마이그레이션
```bash
# 백엔드 컨테이너에서 마이그레이션 실행
docker-compose exec backend alembic upgrade head
```

### 4.5 배포 중지 및 제거
```bash
# 컨테이너 중지
docker-compose stop

# 컨테이너 및 네트워크 제거 (볼륨 유지)
docker-compose down

# 컨테이너, 네트워크 및 볼륨 모두 제거
docker-compose down -v
```

## 5. Kubernetes를 사용한 배포

Kubernetes는 대규모 환경이나 고가용성이 필요한 경우에 적합한 배포 방법입니다.

### 5.1 Kubernetes 매니페스트 파일 준비

#### 5.1.1 네임스페이스 (namespace.yaml)
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: intellidoc
```

#### 5.1.2 시크릿 (secrets.yaml)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: intellidoc-secrets
  namespace: intellidoc
type: Opaque
data:
  db-password: base64-encoded-password
  secret-key: base64-encoded-secret-key
  openai-api-key: base64-encoded-openai-key
  google-vision-api-key: base64-encoded-google-key
```

#### 5.1.3 ConfigMap (configmap.yaml)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: intellidoc-config
  namespace: intellidoc
data:
  DB_USERNAME: "intellidoc"
  DB_NAME: "intellidoc"
  ALLOWED_ORIGINS: "https://yourdomain.com"
  LOG_LEVEL: "INFO"
```

#### 5.1.4 PostgreSQL (postgres.yaml)
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: intellidoc
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:13-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: DB_USERNAME
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: db-password
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: DB_NAME
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: intellidoc
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None
```

#### 5.1.5 Redis (redis.yaml)
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: intellidoc
spec:
  serviceName: redis
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:6-alpine
        command: ["redis-server", "--appendonly", "yes"]
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 5Gi
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: intellidoc
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  clusterIP: None
```

#### 5.1.6 백엔드 (backend.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: intellidoc
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: yourdockerhub/intellidoc-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql://$(DB_USERNAME):$(DB_PASSWORD)@postgres:5432/$(DB_NAME)"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: DB_USERNAME
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: DB_USERNAME
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: db-password
        - name: DB_NAME
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: DB_NAME
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: secret-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: openai-api-key
        - name: GOOGLE_VISION_API_KEY
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: google-vision-api-key
        - name: ALLOWED_ORIGINS
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: ALLOWED_ORIGINS
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: LOG_LEVEL
        volumeMounts:
        - name: document-storage
          mountPath: /app/storage
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 15
      volumes:
      - name: document-storage
        persistentVolumeClaim:
          claimName: document-storage-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: intellidoc
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: document-storage-pvc
  namespace: intellidoc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 20Gi
```

#### 5.1.7 워커 (worker.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker
  namespace: intellidoc
spec:
  replicas: 2
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
    spec:
      containers:
      - name: worker
        image: yourdockerhub/intellidoc-backend:latest
        command: ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
        env:
        - name: DATABASE_URL
          value: "postgresql://$(DB_USERNAME):$(DB_PASSWORD)@postgres:5432/$(DB_NAME)"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: DB_USERNAME
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: DB_USERNAME
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: db-password
        - name: DB_NAME
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: DB_NAME
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: secret-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: openai-api-key
        - name: GOOGLE_VISION_API_KEY
          valueFrom:
            secretKeyRef:
              name: intellidoc-secrets
              key: google-vision-api-key
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: intellidoc-config
              key: LOG_LEVEL
        volumeMounts:
        - name: document-storage
          mountPath: /app/storage
      volumes:
      - name: document-storage
        persistentVolumeClaim:
          claimName: document-storage-pvc
```

#### 5.1.8 프론트엔드 (frontend.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: intellidoc
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: yourdockerhub/intellidoc-frontend:latest
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 15
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: intellidoc
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

#### 5.1.9 인그레스 (ingress.yaml)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: intellidoc-ingress
  namespace: intellidoc
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - yourdomain.com
    secretName: intellidoc-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
```

### 5.2 Kubernetes 배포 실행
```bash
# 네임스페이스 생성
kubectl apply -f kubernetes/namespace.yaml

# 시크릿 및 ConfigMap 생성
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/configmap.yaml

# 데이터베이스 및 Redis 배포
kubectl apply -f kubernetes/postgres.yaml
kubectl apply -f kubernetes/redis.yaml

# 백엔드 및 워커 배포
kubectl apply -f kubernetes/backend.yaml
kubectl apply -f kubernetes/worker.yaml

# 프론트엔드 배포
kubectl apply -f kubernetes/frontend.yaml

# 인그레스 배포
kubectl apply -f kubernetes/ingress.yaml

# 배포 상태 확인
kubectl get all -n intellidoc
```

### 5.3 데이터베이스 마이그레이션
```bash
# 백엔드 파드 이름 가져오기
BACKEND_POD=$(kubectl get pods -n intellidoc -l app=backend -o jsonpath="{.items[0].metadata.name}")

# 마이그레이션 실행
kubectl exec -it $BACKEND_POD -n intellidoc -- alembic upgrade head
```

## 6. 클라우드 환경 배포

### 6.1 AWS ECS (Elastic Container Service)

#### 6.1.1 사전 요구사항
- AWS CLI 설치 및 구성
- ECR (Elastic Container Registry) 리포지토리 생성
- ECS 클러스터 생성
- RDS PostgreSQL 인스턴스 생성
- ElastiCache Redis 인스턴스 생성

#### 6.1.2 이미지 빌드 및 푸시
```bash
# AWS ECR 로그인
aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin your-account-id.dkr.ecr.your-region.amazonaws.com

# 이미지 태그 지정
docker tag intellidoc-backend:latest your-account-id.dkr.ecr.your-region.amazonaws.com/intellidoc-backend:latest
docker tag intellidoc-frontend:latest your-account-id.dkr.ecr.your-region.amazonaws.com/intellidoc-frontend:latest

# 이미지 푸시
docker push your-account-id.dkr.ecr.your-region.amazonaws.com/intellidoc-backend:latest
docker push your-account-id.dkr.ecr.your-region.amazonaws.com/intellidoc-frontend:latest
```

#### 6.1.3 작업 정의 (Task Definition) 생성
AWS 콘솔 또는 CLI를 사용하여 ECS 작업 정의를 생성합니다. 다음 정보를 포함해야 합니다:
- 컨테이너 이미지 URI
- 환경 변수 (RDS 및 ElastiCache 연결 정보 등)
- 포트 매핑
- 로그 구성 (CloudWatch Logs)
- 작업 실행 역할 (Task Execution Role)
- 작업 역할 (Task Role)

#### 6.1.4 서비스 생성
작업 정의를 기반으로 ECS 서비스를 생성합니다:
- 원하는 작업 수 (Desired Tasks)
- 로드 밸런서 구성
- 자동 확장 정책 (선택 사항)
- 서비스 검색 (Service Discovery) 구성 (선택 사항)

### 6.2 Google Cloud Run

#### 6.2.1 사전 요구사항
- Google Cloud SDK 설치 및 구성
- Google Container Registry 또는 Artifact Registry 액세스
- Cloud SQL PostgreSQL 인스턴스 생성
- Memorystore Redis 인스턴스 생성

#### 6.2.2 이미지 빌드 및 푸시
```bash
# Google Container Registry 로그인
gcloud auth configure-docker

# 이미지 태그 지정
docker tag intellidoc-backend:latest gcr.io/your-project-id/intellidoc-backend:latest
docker tag intellidoc-frontend:latest gcr.io/your-project-id/intellidoc-frontend:latest

# 이미지 푸시
docker push gcr.io/your-project-id/intellidoc-backend:latest
docker push gcr.io/your-project-id/intellidoc-frontend:latest
```

#### 6.2.3 Cloud Run 서비스 배포
```bash
# 백엔드 서비스 배포
gcloud run deploy intellidoc-backend \
  --image gcr.io/your-project-id/intellidoc-backend:latest \
  --platform managed \
  --region your-region \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql://user:password@/dbname?host=/cloudsql/your-project-id:your-region:your-instance-name,REDIS_URL=redis://your-redis-ip:6379/0" \
  --add-cloudsql-instances your-project-id:your-region:your-instance-name

# 프론트엔드 서비스 배포
gcloud run deploy intellidoc-frontend \
  --image gcr.io/your-project-id/intellidoc-frontend:latest \
  --platform managed \
  --region your-region \
  --allow-unauthenticated
```

## 7. 환경 변수 관리

### 7.1 환경 변수 파일 (.env)
개발 및 테스트 환경에서는 `.env` 파일을 사용하여 환경 변수를 관리합니다:
```
# 데이터베이스 설정
DB_USERNAME=intellidoc
DB_PASSWORD=your-secure-password
DB_NAME=intellidoc
DATABASE_URL=postgresql://intellidoc:your-secure-password@postgres:5432/intellidoc

# Redis 설정
REDIS_URL=redis://redis:6379/0

# 보안 설정
SECRET_KEY=your-very-secure-secret-key
JWT_EXPIRATION=3600

# API 키
OPENAI_API_KEY=your-openai-api-key
GOOGLE_VISION_API_KEY=your-google-vision-api-key

# CORS 설정
ALLOWED_ORIGINS=http://localhost:3000,http://localhost,https://yourdomain.com

# 로깅 설정
LOG_LEVEL=INFO

# 스토리지 설정
STORAGE_PATH=/app/storage
MAX_UPLOAD_SIZE=100000000  # 100MB
```

### 7.2 운영 환경에서의 환경 변수 관리
운영 환경에서는 다음과 같은 방법으로 환경 변수를 관리합니다:

#### 7.2.1 Docker Compose
```yaml
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://${DB_USERNAME}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      # 기타 환경 변수...
```

#### 7.2.2 Kubernetes
```yaml
containers:
- name: backend
  env:
  - name: DATABASE_URL
    value: "postgresql://$(DB_USERNAME):$(DB_PASSWORD)@postgres:5432/$(DB_NAME)"
  # 기타 환경 변수...
```

#### 7.2.3 클라우드 서비스
- AWS: AWS Systems Manager Parameter Store 또는 AWS Secrets Manager
- GCP: Secret Manager
- Azure: Key Vault

## 8. 데이터 볼륨 관리

### 8.1 Docker Compose 볼륨
```yaml
volumes:
  postgres_data:  # PostgreSQL 데이터
  redis_data:     # Redis 데이터
  document_storage:  # 업로드된 문서 저장
```

### 8.2 Kubernetes 영구 볼륨
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: document-storage-pvc
  namespace: intellidoc
spec:
  accessModes:
    - ReadWriteMany  # 여러 파드에서 읽기/쓰기 가능
  resources:
    requests:
      storage: 20Gi
```

### 8.3 클라우드 스토리지 연동
대규모 환경에서는 클라우드 스토리지 서비스를 사용하는 것이 좋습니다:
- AWS: S3
- GCP: Cloud Storage
- Azure: Blob Storage

#### 8.3.1 AWS S3 연동 예시
```python
# backend/shared/config.py
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")  # local 또는 s3
S3_BUCKET = os.getenv("S3_BUCKET", "intellidoc-documents")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
```

```python
# backend/file_manager/service.py
import boto3
from shared.config import STORAGE_TYPE, S3_BUCKET, S3_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

def save_file(file_data, filename):
    if STORAGE_TYPE == "s3":
        s3_client = boto3.client(
            's3',
            region_name=S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        s3_client.upload_fileobj(file_data, S3_BUCKET, filename)
        return f"s3://{S3_BUCKET}/{filename}"
    else:
        # 로컬 스토리지 저장 로직
        # ...
```

## 9. 보안 고려사항

### 9.1 환경 변수 보안
- 민감한 정보(API 키, 비밀번호 등)는 환경 변수로 관리
- `.env` 파일은 버전 관리 시스템에 포함하지 않음
- 운영 환경에서는 시크릿 관리 서비스 사용

### 9.2 네트워크 보안
- 백엔드 API는 HTTPS를 통해서만 접근 가능하도록 설정
- 내부 서비스(Redis, PostgreSQL)는 외부에 노출하지 않음
- 필요한 포트만 개방

### 9.3 컨테이너 보안
- 최소 권한 원칙 적용 (루트가 아닌 사용자로 실행)
- 컨테이너 이미지 정기적 업데이트
- 취약점 스캔 도구 사용 (예: Docker Scout, Trivy)

### 9.4 데이터 보안
- 데이터베이스 암호화 (저장 데이터 암호화)
- 민감한 문서 데이터 암호화
- 정기적인 백업 및 복구 테스트

## 10. 모니터링 및 로깅 설정

### 10.1 Prometheus/Grafana 설정
`monitoring/prometheus.yml` 파일:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'intellidoc-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 10.2 ELK 스택 설정
`docker-compose.yml`에 ELK 스택 추가:
```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.14.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:7.14.0
    volumes:
      - ./logging/logstash/pipeline:/usr/share/logstash/pipeline
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:7.14.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

### 10.3 로그 수집 설정
백엔드 로깅 설정 (`backend/shared/logger.py`):
```python
import logging
import json
import sys
from logging.handlers import RotatingFileHandler
from shared.config import LOG_LEVEL, LOG_FILE

def setup_logger():
    logger = logging.getLogger("intellidoc")
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # JSON 형식 로그 포맷터
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            if hasattr(record, "request_id"):
                log_record["request_id"] = record.request_id
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_record)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JsonFormatter())
    logger.addHandler(console_handler)

    # 파일 핸들러 (선택 사항)
    if LOG_FILE:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)

    return logger
```

## 11. 배포 자동화

### 11.1 GitHub Actions 워크플로우
`.github/workflows/deploy.yml` 파일:
```yaml
name: Deploy IntelliDoc

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v1

      - name: Login to DockerHub
        uses: docker/login-action@v1
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v2
        with:
          context: ./backend
          push: true
          tags: yourdockerhub/intellidoc-backend:latest

      - name: Build and push frontend
        uses: docker/build-push-action@v2
        with:
          context: ./frontend
          push: true
          tags: yourdockerhub/intellidoc-frontend:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      # Docker Compose 배포 예시
      - name: Copy files to server
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USERNAME }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          source: "docker-compose.yml,.env.example"
          target: "/opt/intellidoc"

      - name: Deploy with Docker Compose
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USERNAME }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/intellidoc
            cp .env.example .env
            # 환경 변수 설정
            sed -i 's/DB_PASSWORD=.*/DB_PASSWORD=${{ secrets.DB_PASSWORD }}/' .env
            sed -i 's/SECRET_KEY=.*/SECRET_KEY=${{ secrets.SECRET_KEY }}/' .env
            sed -i 's/OPENAI_API_KEY=.*/OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}/' .env
            # 이미지 풀 및 컨테이너 재시작
            docker-compose pull
            docker-compose up -d
            # 데이터베이스 마이그레이션
            docker-compose exec -T backend alembic upgrade head
```

### 11.2 GitLab CI/CD 파이프라인
`.gitlab-ci.yml` 파일:
```yaml
stages:
  - test
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: ""

test:
  stage: test
  image: python:3.9
  script:
    - cd backend
    - pip install -r requirements.txt
    - pytest

build-backend:
  stage: build
  image: docker:20.10.12
  services:
    - docker:20.10.12-dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA -t $CI_REGISTRY_IMAGE/backend:latest ./backend
    - docker push $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE/backend:latest

build-frontend:
  stage: build
  image: docker:20.10.12
  services:
    - docker:20.10.12-dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA -t $CI_REGISTRY_IMAGE/frontend:latest ./frontend
    - docker push $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE/frontend:latest

deploy:
  stage: deploy
  image: alpine:latest
  script:
    - apk add --no-cache openssh-client
    - mkdir -p ~/.ssh
    - echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - echo -e "Host *\n\tStrictHostKeyChecking no\n\n" > ~/.ssh/config
    - scp docker-compose.yml .env.example $SERVER_USER@$SERVER_HOST:/opt/intellidoc/
    - ssh $SERVER_USER@$SERVER_HOST "cd /opt/intellidoc && docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY && docker-compose pull && docker-compose up -d && docker-compose exec -T backend alembic upgrade head"
  only:
    - main
```

## 12. 문제 해결

### 12.1 일반적인 문제 및 해결 방법

#### 12.1.1 컨테이너가 시작되지 않는 경우
- 로그 확인: `docker-compose logs <service_name>`
- 환경 변수 확인: `.env` 파일이 올바르게 설정되었는지 확인
- 볼륨 권한 확인: `ls -la` 명령으로 볼륨 디렉토리 권한 확인

#### 12.1.2 데이터베이스 연결 오류
- 데이터베이스 서비스 실행 확인: `docker-compose ps postgres`
- 연결 문자열 확인: `DATABASE_URL` 환경 변수가 올바른지 확인
- 네트워크 확인: `docker network inspect intellidoc_default`

#### 12.1.3 API 요청 실패
- 백엔드 로그 확인: `docker-compose logs backend`
- CORS 설정 확인: `ALLOWED_ORIGINS` 환경 변수가 올바른지 확인
- API 엔드포인트 확인: 요청 URL이 올바른지 확인

#### 12.1.4 OCR/LLM 처리 실패
- 워커 로그 확인: `docker-compose logs worker`
- API 키 확인: `OPENAI_API_KEY`, `GOOGLE_VISION_API_KEY` 등이 올바른지 확인
- Redis 연결 확인: `docker-compose exec redis redis-cli ping`

### 12.2 로그 확인 및 디버깅
```bash
# 모든 서비스 로그 확인
docker-compose logs

# 특정 서비스 로그 확인
docker-compose logs backend

# 실시간 로그 확인
docker-compose logs -f backend

# 컨테이너 내부 접속
docker-compose exec backend bash

# 데이터베이스 접속
docker-compose exec postgres psql -U intellidoc -d intellidoc
```

### 12.3 성능 문제 해결
- 리소스 사용량 모니터링: `docker stats`
- 데이터베이스 쿼리 최적화: 인덱스 추가, 쿼리 개선
- 캐싱 활용: Redis 캐시 설정 확인
- 워커 수 조정: Celery 워커 수 증가

---

이 문서에 대한 문의사항이나 개선 제안이 있다면 프로젝트 관리자에게 연락하거나 이슈 트래커에 등록해 주세요.

© 2025 IntelliDoc. All rights reserved.
