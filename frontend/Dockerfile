# Étape 1: Build de l'application React
FROM node:20-alpine as build

WORKDIR /app

# Copier les fichiers package.json et installer les dépendances
COPY package*.json ./
RUN npm install

# Copier le reste des fichiers du frontend (local au dossier frontend)
COPY . ./

# Construire l'application pour la production
RUN npm run build

# Étape 2: Servir avec Nginx
FROM nginx:alpine

# Copier les fichiers de build depuis l'étape précédente
COPY --from=build /app/dist /usr/share/nginx/html

# Copier la configuration nginx personnalisée
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Créer un script pour injecter les variables d'environnement au runtime
RUN echo "#!/bin/sh" > /docker-entrypoint.sh && \
    echo "set -e" >> /docker-entrypoint.sh && \
    echo "envsubst '\$VITE_API_KEY \$VITE_API_URL' < /usr/share/nginx/html/env-config.template.js > /usr/share/nginx/html/env-config.js" >> /docker-entrypoint.sh && \
    echo "exec \"\$@\"" >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Créer un template pour les variables d'environnement
COPY --from=build /app/dist /usr/share/nginx/html
RUN echo "window.env = { VITE_API_KEY: '${VITE_API_KEY}', VITE_API_URL: '${VITE_API_URL}' };" > /usr/share/nginx/html/env-config.template.js && \
    echo "" > /usr/share/nginx/html/env-config.js

# Exposer le port pour le frontend
EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"] 