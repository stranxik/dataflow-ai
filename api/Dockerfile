FROM python:3.12-slim

WORKDIR /app

# Configuration des variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer les outils système nécessaires
RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copier les modules nécessaires
COPY api/ ./api/
COPY extract/ ./extract/
COPY cli/ ./cli/
COPY tools/ ./tools/
COPY run_api.py .

# Créer les répertoires pour les fichiers et résultats
RUN mkdir -p /app/files /app/results && chmod -R 777 /app/files /app/results

# Exposer le port de l'API
EXPOSE 8000

# Lancer l'API au démarrage du conteneur
CMD ["python", "run_api.py"] 