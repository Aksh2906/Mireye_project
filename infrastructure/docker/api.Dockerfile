FROM python:3.12-slim
WORKDIR /app
COPY apps/api /app
RUN pip install --no-cache-dir .
COPY infrastructure/migrations /app/migrations
ENV PYTHONPATH=/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
