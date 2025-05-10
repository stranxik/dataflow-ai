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
COPY .env.example ./.env
COPY run_api.py .
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
COPY .env.example ./.env
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
FROM nginx:alpine AS frontend
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 