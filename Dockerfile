FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py /app/
COPY templates/ /app/templates/
COPY seed_data/ /app/seed_data/

ENV PORT=9090
ENV UVICORN_WORKERS=4
ENV DATABASE_URL=postgresql://user:pass@host:5432/cbse
ENV ALLOWED_HOSTS=*

EXPOSE 9090

CMD ["/bin/sh", "start.sh"]
