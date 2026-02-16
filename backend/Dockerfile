# Dockerfile for backend service
# - Multi-stage build:
#   * 'llama_builder' compiles the native 'llama.cpp' library and installs the
#     Python wrapper (llama-cpp-python) into site-packages.
#   * Final image is a minimal Python runtime that reuses the compiled extension
#     (avoids compiling at container start and keeps the runtime small).
# - Intended for development/local use (uvicorn with --reload). For production
#   images, remove `--reload` and use an appropriate production server/workers.

# -------- llama.cpp build stage --------
FROM python:3.12-slim AS llama_builder
# Install build tools required to compile llama.cpp (keep packages minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
# Clone and build the native llama.cpp repository
RUN git clone https://github.com/ggerganov/llama.cpp.git
WORKDIR /opt/llama.cpp
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF \
 && cmake --build build -j

# Install the Python wrapper from source so the compiled extension is available
# in site-packages for the final image (no runtime compilation required).
RUN CMAKE_ARGS="-DLLAMA_CURL=OFF" pip install --no-cache-dir --no-binary llama-cpp-python llama-cpp-python

# -------- Development runtime stage --------
FROM python:3.12-slim

# Runtime system libraries (keep image small with --no-install-recommends)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled Python extensions and packages from the build stage.
COPY --from=llama_builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

WORKDIR /app

# Use `requirements.txt` (single source of truth for backend Python deps).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source into the image.
COPY . .

# Development entrypoint: FastAPI via uvicorn with live reload.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
