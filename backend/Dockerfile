FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend

EXPOSE 8000 8002

CMD ["sh", "-c", "python -m backend.init_db && python -m backend.seed && exec python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000"]
