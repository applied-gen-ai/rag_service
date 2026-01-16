# Use Python slim image for smaller size
FROM public.ecr.aws/docker/library/python:3.10-slim

# Install system dependencies for sentence-transformers and gRPC
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model during build (so it's baked into the image)
# This prevents download on every container start
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('infly/inf-retriever-v1-1.5b')"

# ============================================================================
# GENERATE gRPC FILES INSIDE DOCKER with FIXED IMPORTS
# ============================================================================
# Copy ONLY the proto file (not the generated Python files)
COPY llm_grpc/llm.proto ./llm_grpc/

# Generate gRPC Python files
RUN python -m grpc_tools.protoc \
    -I./llm_grpc \
    --python_out=./llm_grpc \
    --grpc_python_out=./llm_grpc \
    --pyi_out=./llm_grpc \
    ./llm_grpc/llm.proto

# FIX IMPORTS: Change "import llm_pb2" to "from . import llm_pb2" in generated files
RUN sed -i 's/^import llm_pb2/from . import llm_pb2/g' llm_grpc/llm_pb2_grpc.py

# Create __init__.py for the package
RUN echo "from . import llm_pb2\nfrom . import llm_pb2_grpc" > llm_grpc/__init__.py

# Copy application code
COPY *.py ./

# Expose WebSocket port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]