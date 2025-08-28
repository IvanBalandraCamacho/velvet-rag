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
