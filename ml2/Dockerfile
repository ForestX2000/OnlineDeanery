FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# ML2 лёгкий — только FastAPI + pydantic
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.30.0" \
        "pydantic>=2.9.0"

COPY ml2/ ./ml2/

EXPOSE 8003

CMD ["python", "-m", "ml2.main"]