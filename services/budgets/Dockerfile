# syntax=docker/dockerfile:1
# The recipe for the Budgets & Alerts service's image. Build it from this folder:
#   docker build -t subtrack-budgets services/budgets
FROM python:3.12-slim

# Do not write .pyc files, and print log lines straight away (no waiting in a buffer).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: Docker reuses this step until requirements.txt changes,
# so changing only the code rebuilds in seconds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the code the service runs (never COPY . .): no tests, no .env, no data files.
COPY app.py auth.py db.py subscriptions_client.py ./
COPY budgets/ budgets/
COPY migrations/ migrations/

# Which commit this image was built from. GET /health shows it; CI passes the real SHA.
ARG GIT_SHA=dev
ENV GIT_SHA=$GIT_SHA

# Run as a normal user, not as root (the all-powerful admin user).
RUN useradd --system --no-create-home appuser
USER appuser

# The port to listen on. gunicorn reads PORT by itself (0.0.0.0:$PORT), like app.py does.
ENV PORT=8000
EXPOSE 8000

# gunicorn is a production web server (Flask's own server is only for development).
# --preload: build the app (and run the migrations) once, before serving any request.
# 1 worker with 4 threads: up to 4 requests at the same time in one process.
# --no-control-socket: we do not use gunicorn's remote-control feature (it needs a home folder).
CMD ["gunicorn", "--preload", "--workers", "1", "--threads", "4", "--no-control-socket", "app:create_app()"]
