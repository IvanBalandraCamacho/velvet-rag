#!/bin/bash

echo "🚀 Creando estructura del proyecto Velvet RAG..."

# Crear directorios principales
mkdir -p backend/{services,models,api}
mkdir -p frontend/{src/{components/{auth,chat,layout,ui,profile,settings},contexts,hooks,types,api},public}
mkdir -p vllm
mkdir -p nginx
mkdir -p monitoring
mkdir -p storage/{files,faiss}

echo "📁 Estructura de directorios creada"

# Backend main.py
cat > backend/main.py << 'EOL'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Velvet RAG API",
    description="API para plataforma RAG con Velvet 14B y datos del BCRP",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "🚀 Velvet RAG API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Velvet RAG API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
EOL

# Backend requirements.txt
cat > backend/requirements.txt << 'EOL'
fastapi==0.104.1
uvicorn[standard]==0.24.0
asyncpg==0.29.0
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
bcrypt==4.0.1
aiohttp==3.9.1
aiofiles==23.2.1
pandas==2.1.4
numpy==1.25.2
openpyxl==3.1.2
PyPDF2==3.0.1
sentence-transformers==2.2.2
faiss-cpu==1.7.4
torch==2.1.1
transformers==4.36.2
boto3==1.34.0
redis==5.0.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
requests==2.31.0
EOL

# Backend Dockerfile
cat > backend/Dockerfile << 'EOL'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/storage/files /app/storage/faiss

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /bin/bash velvet && \
    chown -R velvet:velvet /app
USER velvet

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOL

# vLLM Dockerfile
cat > vllm/Dockerfile << 'EOL'
FROM nvidia/cuda:12.4-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python
RUN python -m pip install --upgrade pip

RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN pip install vllm==0.2.6
RUN pip install transformers>=4.36.0 accelerate fastapi uvicorn requests

WORKDIR /app

COPY start_server.py .
RUN chmod +x start_server.py

ENV MODEL_NAME=Almawave/Velvet-14B \
    TENSOR_PARALLEL_SIZE=1 \
    MAX_MODEL_LEN=32768 \
    GPU_MEMORY_UTILIZATION=0.9 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

CMD ["python", "start_server.py"]
EOL

# vLLM start script
cat > vllm/start_server.py << 'EOL'
#!/usr/bin/env python3
import os
import subprocess
import sys

def main():
    model_name = os.getenv("MODEL_NAME", "Almawave/Velvet-14B")
    tensor_parallel_size = int(os.getenv("TENSOR_PARALLEL_SIZE", "1"))
    max_model_len = int(os.getenv("MAX_MODEL_LEN", "32768"))
    gpu_memory_utilization = float(os.getenv("GPU_MEMORY_UTILIZATION", "0.9"))
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_name,
        "--tensor-parallel-size", str(tensor_parallel_size),
        "--max-model-len", str(max_model_len),
        "--gpu-memory-utilization", str(gpu_memory_utilization),
        "--host", host,
        "--port", str(port),
        "--trust-remote-code",
    ]
    
    print(f"🚀 Starting vLLM server: {model_name}")
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
EOL

# Frontend package.json
cat > frontend/package.json << 'EOL'
{
  "name": "velvet-rag-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.1",
    "axios": "^1.6.2",
    "@tanstack/react-query": "^5.8.4",
    "framer-motion": "^10.16.16",
    "react-hot-toast": "^2.4.1",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "@vitejs/plugin-react": "^4.1.1",
    "vite": "^5.0.0",
    "typescript": "^5.2.2",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}
EOL

# Frontend Dockerfile
cat > frontend/Dockerfile << 'EOL'
FROM node:18-alpine as build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build

FROM nginx:alpine as production

RUN apk add --no-cache curl

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
EOL

# Frontend nginx config
cat > frontend/nginx.conf << 'EOL'
server {
    listen 80;
    server_name localhost;
    
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOL

# Docker Compose
cat > docker-compose.yml << 'EOL'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: velvet-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: velvet_db
      POSTGRES_USER: velvet_user
      POSTGRES_PASSWORD: velvet_password_secure_2024
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - velvet-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U velvet_user -d velvet_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: velvet-redis
    restart: unless-stopped
    command: redis-server --requirepass redis_password_secure_2024
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - velvet-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: velvet-backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://velvet_user:velvet_password_secure_2024@postgres:5432/velvet_db
      REDIS_URL: redis://:redis_password_secure_2024@redis:6379/0
      VLLM_BASE_URL: http://vllm-server:8000
      JWT_SECRET_KEY: your-super-secret-jwt-key-change-this-in-production
    volumes:
      - ./backend:/app
      - backend_storage:/app/storage
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - velvet-network

  vllm-server:
    build:
      context: ./vllm
      dockerfile: Dockerfile
    container_name: velvet-vllm
    restart: unless-stopped
    environment:
      MODEL_NAME: Almawave/Velvet-14B
      TENSOR_PARALLEL_SIZE: 1
      MAX_MODEL_LEN: 32768
      GPU_MEMORY_UTILIZATION: 0.9
    volumes:
      - model_cache:/root/.cache/huggingface
    ports:
      - "8001:8000"
    networks:
      - velvet-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 60s
      timeout: 30s
      retries: 3
      start_period: 600s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: velvet-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - velvet-network

volumes:
  postgres_data:
  redis_data:
  backend_storage:
  model_cache:

networks:
  velvet-network:
    driver: bridge
EOL

# Environment file
cat > .env.example << 'EOL'
# Database
DATABASE_URL=postgresql://velvet_user:velvet_password_secure_2024@postgres:5432/velvet_db

# Redis
REDIS_URL=redis://:redis_password_secure_2024@redis:6379/0

# JWT Secret (CAMBIAR EN PRODUCCIÓN)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# vLLM
VLLM_BASE_URL=http://vllm-server:8000
MODEL_NAME=Almawave/Velvet-14B

# AWS S3
USE_S3=false
S3_BUCKET_NAME=velvet-rag-files
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME="Velvet RAG"
EOL

# README.md
cat > README.md << 'EOL'
# 🚀 Velvet RAG - Plataforma de IA para Análisis Económico del Perú

Una plataforma RAG (Retrieval Augmented Generation) completa que utiliza el modelo **Velvet 14B** para análisis de datos económicos del Perú, integrada con la API del BCRP.

## ✨ Características

- 🤖 **AI Avanzada**: Velvet 14B (14B parámetros)
- 📊 **Datos del BCRP**: Integración en tiempo real con API del Banco Central
- 📁 **Procesamiento de Archivos**: Soporte para PDF, CSV, Excel
- 🔍 **RAG Pipeline**: Búsqueda semántica y generación contextual
- 💬 **Chat Interface**: UI moderna estilo ChatGPT/Claude
- 🌙 **Modo Oscuro**: Tema blanco/rojo/negro personalizable
- 🔐 **Autenticación**: Sistema completo de usuarios
- 📱 **Responsive**: Adaptado para escritorio y móvil

## 🚀 Quick Start

```bash
# Clonar repositorio
git https://github.com/IvanBalandraCamacho/velvet-rag.git
cd velvet-rag

# Configurar environment
cp .env.example .env

# Iniciar servicios
docker-compose up --build -d

# Acceder a la aplicación
open http://localhost:3000
