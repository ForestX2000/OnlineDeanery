FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.30.0" \
        "pydantic>=2.9.0" \
        "python-multipart>=0.0.9" \
        "opencv-python-headless>=4.10.0" \
        "numpy<2" \
        "requests>=2.31.0"

COPY ml1/ ./ml1/

EXPOSE 8001

CMD ["python", "-m", "ml1.main"]