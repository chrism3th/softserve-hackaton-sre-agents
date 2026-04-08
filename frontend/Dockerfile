# syntax=docker/dockerfile:1.7
# Build context: repo root (see docker-compose.prod.yml).
# ---------- builder ----------
FROM node:20-alpine AS builder

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

COPY frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src

RUN npm run build

# ---------- runtime: nginx serving static assets ----------
FROM nginx:1.27-alpine AS runtime

RUN rm /etc/nginx/conf.d/default.conf
COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
