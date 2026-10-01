# Deployment

The reference application is a stateless FastAPI service plus a static frontend.
It is suitable for any container platform.

## Contents

1. [Environment](#environment)
2. [PostgreSQL](#postgresql)
3. [Migrations](#migrations)
4. [Backend](#backend)
5. [Frontend](#frontend)
6. [Reverse proxy and TLS](#reverse-proxy-and-tls)
7. [Production checklist](#production-checklist)
8. [Scaling notes](#scaling-notes)

## Environment

Minimum required variables in production:

```dotenv
APP_ENV=production
LOG_LEVEL=INFO
LOG_MESSAGE_CONTENT=false          # keep false
DATABASE_URL=postgresql+psycopg://user:pass@db:5432/multilingual_assistant
CORS_ORIGINS=https://family.example.org
AI_PROVIDER=openai
OPENAI_API_KEY=...                  # or use a secret manager
DATA_RETENTION_DAYS=30
```

Supply secrets through your platform's secret manager (Kubernetes Secrets, GitHub
Actions secrets, Docker secrets, AWS/GCP parameter store). **Never bake them
into an image or a committed file.**

## PostgreSQL

```sql
CREATE DATABASE multilingual_assistant;
CREATE USER mca WITH PASSWORD '...';
GRANT ALL PRIVILEGES ON DATABASE multilingual_assistant TO mca;
```

Enable `pgcrypto` or generate UUIDs in the application — the current schema
generates UUIDs client-side, so no extension is required.

## Migrations

Run as a release step, before the new version starts serving traffic:

```bash
alembic upgrade head
```

## Backend

```dockerfile
FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Health check:

```bash
curl -fsS http://localhost:8000/api/health
```

Scale on CPU. Each worker holds a connection pool sized by
`DB_POOL_SIZE`; keep `workers × pool_size` below the Postgres
`max_connections` budget for your instance.

## Frontend

Build once, serve as static files:

```bash
cd frontend
VITE_API_BASE_URL=https://api.example.org/api npm run build
```

The output in `frontend/dist/` is a static bundle. Serve it with nginx, Caddy,
or any CDN. The included `frontend/Dockerfile` uses nginx and proxies `/api` to
the backend service so the browser only ever talks to one origin.

## Reverse proxy and TLS

**The reference app ships without authentication.** Terminate TLS and enforce
authentication and rate limits at the edge. A minimal nginx sketch:

```nginx
server {
  listen 443 ssl http2;
  server_name family.example.org;

  ssl_certificate     /etc/letsencrypt/live/family.example.org/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/family.example.org/privkey.pem;

  add_header Strict-Transport-Security "max-age=31536000" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "DENY" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;

  client_max_body_size 1m;

  location /api/ {
    proxy_pass         http://backend:8000;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
    limit_req zone=api burst=20 nodelay;
  }

  location / {
    root  /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
  }
}
```

## Production checklist

- [ ] `APP_ENV=production`
- [ ] `LOG_MESSAGE_CONTENT=false`
- [ ] `CORS_ORIGINS` lists only your real origins
- [ ] `OPENAI_API_KEY` (or local endpoint) supplied via secrets
- [ ] PostgreSQL with TLS and a least-privilege role
- [ ] `alembic upgrade head` runs as a release step
- [ ] TLS terminated at the edge; HSTS enabled
- [ ] Authentication in front of `/api`
- [ ] Rate limiting at the edge **and** a budget on the AI provider
- [ ] `LOG_LEVEL=INFO`, log shipping configured, retention defined
- [ ] Backups for PostgreSQL tested at least once
- [ ] A purge job enforces `DATA_RETENTION_DAYS`
- [ ] `/api/health` wired to your uptime monitor
- [ ] Content security policy reviewed for the frontend origin

## Scaling notes

- The API is stateless; run as many replicas as you like.
- AI calls dominate latency. Cache rewrite and translation results by a hash of
  `(approved text, language, locale, tone)` — the same announcement is often
  drafted repeatedly.
- Verification is pure Python and CPU-cheap. It is not a scaling concern.
- For very long documents, move the pipeline to a queue (Celery / RQ) and have
  the API return a job id.
