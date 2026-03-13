FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app ./app
COPY cloud_run_entrypoint.py ./cloud_run_entrypoint.py

EXPOSE 8080

CMD ["python", "cloud_run_entrypoint.py"]
