FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY evaluation/results/latest.json ./evaluation/results/latest.json
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
