FROM python:3.12-slim

WORKDIR /app

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copier les fichiers nécessaires pour la CLI
COPY requirements.txt .
COPY api/ ./api/
COPY cli/ ./cli/
COPY extract/ ./extract/
COPY tools/ ./tools/
COPY tests/ ./tests/
COPY documentation/ ./documentation/
COPY README.md README.fr.md ./

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Volume pour les données d'entrée et de sortie
VOLUME ["/app/files", "/app/results"]

# Définir l'entrypoint pour utiliser la CLI
ENTRYPOINT ["python", "-m", "cli.cli"]
CMD ["interactive"] 