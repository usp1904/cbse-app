FROM python:3.11-slim

WORKDIR /app

COPY *.py requirements.txt /app/
COPY templates/ /app/templates/
COPY content/ /app/content/
COPY run.sh /app/

RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

EXPOSE 9090

CMD ["bash", "run.sh", "app"]
