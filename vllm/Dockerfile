FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

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
