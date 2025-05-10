FROM python:3.12-slim

WORKDIR /app

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installer curl pour le healthcheck
RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copier uniquement les fichiers nécessaires à l'API
COPY requirements.txt .
COPY api/ ./api/
COPY extract/ ./extract/
COPY tools/ ./tools/
COPY run_api.py .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Créer les répertoires pour les volumes et donner les permissions
RUN mkdir -p /app/files /app/results && \
    chmod -R 777 /app/files /app/results

# Exposer le port de l'API
EXPOSE 8000

# Commande pour démarrer l'API
CMD ["python", "run_api.py"] 