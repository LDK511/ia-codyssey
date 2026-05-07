FROM python:3.11-slim

WORKDIR /app

COPY door_hacking.py .
COPY emergency_storage_key.zip .

RUN mkdir -p /output

CMD ["python", "door_hacking.py"]
