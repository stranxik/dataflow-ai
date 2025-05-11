# Étape de build de l'application React
FROM node:20-alpine as build

WORKDIR /app

# Copier les fichiers package.json et installer les dépendances
COPY package*.json ./
RUN npm install

# Copier le reste des fichiers du frontend
COPY . ./

# Récupérer la clé API depuis les variables d'environnement lors du build
ARG VITE_API_KEY
ARG VITE_API_URL
ENV VITE_API_KEY=${VITE_API_KEY}
ENV VITE_API_URL=${VITE_API_URL}

# Construire l'application pour la production
RUN npm run build

# Étape de production avec Nginx
FROM nginx:alpine

# Copier les fichiers de build depuis l'étape précédente
COPY --from=build /app/dist /app/dist

# Copier la configuration nginx personnalisée
COPY nginx.conf /etc/nginx/conf.d/default.conf

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

# Exposer le port pour le frontend
EXPOSE 80

# Lancer nginx avec le script d'entrypoint pour les variables d'environnement
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"] 