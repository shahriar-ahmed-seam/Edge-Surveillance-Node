# Edge agent image. Multi-arch friendly (linux/arm64 for Pi/Jetson, linux/amd64 for dev).
FROM python:3.11-slim

# OpenCV runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Models are mounted at runtime (-v) or baked in a derived image.
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "src.agent"]
