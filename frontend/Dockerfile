# Multilingual Communication Assistant - frontend image.
#
# Stage 1 builds the static bundle with Node. Stage 2 serves it with nginx and
# proxies /api to the backend, so the browser only ever talks to one origin and
# no CORS configuration is needed in production.

# --- Stage 1: build ---------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# The API base URL is baked in at build time. In the compose stack the browser
# reaches the API through this same nginx origin at /api.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Install dependencies from the lockfile for a reproducible build.
COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build

# --- Stage 2: serve ---------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# Replace the stock config so SPA routes fall back to index.html and /api is
# proxied to the backend service.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]