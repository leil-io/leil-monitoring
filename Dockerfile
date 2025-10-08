FROM python:3.14.0-alpine3.21

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV PYTHONPATH="/app/src"

CMD ["/app/src/saunafs_monitoring/main.py"]
