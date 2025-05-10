FROM python:3.12-slim

WORKDIR /app

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copier uniquement les fichiers nécessaires à l'API
COPY requirements.txt .
COPY .env.example ./.env
COPY api/ ./api/
COPY extract/ ./extract/
COPY tools/ ./tools/
COPY run_api.py .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Créer un utilisateur non-root pour plus de sécurité
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Exposer le port de l'API
EXPOSE 8000

# Commande pour démarrer l'API
CMD ["python", "run_api.py"] 