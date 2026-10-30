
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5555

CMD ["sh", "-c", "celery --broker=\"$CELERY_BROKER_URL\" flower --address=0.0.0.0 --port=5555 --persistent=True --db=/data/flower"]
