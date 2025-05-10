# Étape unique: Build et serveur de l'application React
FROM node:20-alpine

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

# Installer serve pour servir l'application
RUN npm install -g serve

# Exposer le port pour le frontend
EXPOSE 80

# Lancer le serveur
CMD ["serve", "-s", "dist", "-l", "80"] 