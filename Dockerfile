FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY clio ./clio

ENV CLIO_HOST=0.0.0.0 \
    CLIO_PORT=8010 \
    CLIO_DB_PATH=/data/clio.db

VOLUME ["/data"]
EXPOSE 8010

CMD ["python", "-m", "clio"]
