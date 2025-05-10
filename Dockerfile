# Dockerfile multi-stage et multi-target pour DataFlow AI
# Utilisation: docker build --target [api|frontend|cli] -t dataflow-[target] .

# Base commune pour Python
FROM python:3.12-slim AS python-base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Image API
FROM python-base AS api
COPY api/ ./api/
COPY extract/ ./extract/
COPY tools/ ./tools/
COPY .env* ./
RUN if [ ! -f .env ]; then \
       if [ -f .env.example ]; then \
         cp .env.example .env; \
       else \
         touch .env; \
       fi \
    fi
COPY run_api.py .
RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /app/files /app/results && chmod -R 777 /app/files /app/results
EXPOSE 8000
CMD ["python", "run_api.py"]

# Image CLI
FROM python-base AS cli
COPY api/ ./api/
COPY cli/ ./cli/
COPY extract/ ./extract/
COPY tools/ ./tools/
COPY tests/ ./tests/
COPY documentation/ ./documentation/
COPY README.md README.fr.md ./
COPY .env* ./
RUN if [ ! -f .env ]; then \
       if [ -f .env.example ]; then \
         cp .env.example .env; \
       else \
         touch .env; \
       fi \
    fi
VOLUME ["/app/files", "/app/results"]
ENTRYPOINT ["python", "-m", "cli.cli"]
CMD ["interactive"]

# Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Image frontend
FROM node:20-alpine AS frontend
WORKDIR /app
COPY --from=frontend-build /app/dist ./dist
COPY --from=frontend-build /app/package*.json ./

# Installer un serveur HTTP simple
RUN npm install -g serve

# Créer un script pour injecter les variables d'environnement au runtime
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo 'cat > /app/dist/env-config.js << EOF' >> /docker-entrypoint.sh && \
    echo 'window.env = {' >> /docker-entrypoint.sh && \
    echo '  VITE_API_KEY: "${VITE_API_KEY}",' >> /docker-entrypoint.sh && \
    echo '  VITE_API_URL: "${VITE_API_URL:-/api}"' >> /docker-entrypoint.sh && \
    echo '};' >> /docker-entrypoint.sh && \
    echo 'EOF' >> /docker-entrypoint.sh && \
    echo 'exec "$@"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["serve", "-s", "dist", "-l", "80"] 