# -------- llama.cpp build stage --------
FROM python:3.12-slim AS llama_builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN git clone https://github.com/ggerganov/llama.cpp.git
WORKDIR /opt/llama.cpp
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF \
 && cmake --build build -j
RUN CMAKE_ARGS="-DLLAMA_CURL=OFF" pip install --no-cache-dir --no-binary llama-cpp-python llama-cpp-python

# -------- Development runtime stage --------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=llama_builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
