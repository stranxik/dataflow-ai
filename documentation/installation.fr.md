# Guide d'installation complet de DataFlow AI

Ce guide détaille les différentes méthodes d'installation et de configuration de DataFlow AI. Choisissez celle qui correspond le mieux à vos besoins.

## Table des matières
- [Prérequis](#prérequis)
- [Installation avec Docker (recommandée)](#installation-avec-docker-recommandée)
- [Installation manuelle](#installation-manuelle)
- [Configuration d'Outlines pour l'extraction structurée](#configuration-doutlines-pour-lextraction-structurée)
- [Configuration de l'API OpenAI](#configuration-de-lapi-openai)
- [Configuration du frontend](#configuration-du-frontend)
- [Vérification de l'installation](#vérification-de-linstallation)
- [Résolution des problèmes courants](#résolution-des-problèmes-courants)

## Prérequis

### Configuration minimale
- Système d'exploitation: Linux, macOS ou Windows
- CPU: 2 cœurs, 4 Go RAM (minimum)
- Espace disque: 1 Go pour l'installation, plus espace pour les fichiers traités

### Logiciels requis
- Docker et Docker Compose (pour l'installation Docker)
- **Python 3.12** spécifiquement (pour l'installation manuelle)
- Node.js 14+ (pour l'installation manuelle du frontend)
- Git

> ⚠️ **IMPORTANT**: DataFlow AI requiert **Python 3.12** spécifiquement en raison de la dépendance avec la bibliothèque Outlines 0.2.3. Les versions antérieures ou plus récentes de Python peuvent ne pas fonctionner correctement.

## Installation avec Docker (recommandée)

L'installation avec Docker est la méthode la plus simple et garantit un environnement cohérent.

### 1. Cloner le dépôt

```bash
git clone https://github.com/stranxik/dataflow-ai.git
cd dataflow-ai
```

### 2. Configurer les variables d'environnement

```bash
# Copier les fichiers d'exemple
cp .env.example .env
cp frontend/.env.example frontend/.env

# Éditer les fichiers selon vos besoins
nano .env  # ou utilisez votre éditeur préféré
nano frontend/.env
```

Variables importantes à configurer dans `.env`:
```
API_KEY=votre_clé_api_sécurisée
OPENAI_API_KEY=votre_clé_api_openai
```

Variables importantes à configurer dans `frontend/.env`:
```
VITE_API_KEY=votre_clé_api_sécurisée  # Doit correspondre à API_KEY dans .env
```

### 3. Construire et démarrer les services

```bash
docker-compose up -d
```

Cela démarrera:
- L'API backend sur http://localhost:8000
- L'interface frontend sur http://localhost:80
- Les conteneurs pour la CLI et autres services

### 4. Vérifier l'installation

```bash
# Vérifier que les conteneurs fonctionnent
docker-compose ps

# Tester la CLI
docker-compose run cli test
```

## Installation manuelle

L'installation manuelle offre plus de contrôle et est recommandée pour les environnements de développement.

### 1. Cloner le dépôt

```bash
git clone https://github.com/stranxik/dataflow-ai.git
cd dataflow-ai
```

### 2. Configurer l'environnement backend

```bash
# Créer un environnement virtuel Python 3.12
python3.12 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env selon vos besoins
```

### 3. Configurer le frontend

```bash
cd frontend

# Installer les dépendances Node.js
npm install

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env selon vos besoins
```

### 4. Démarrer les services

Dans un premier terminal (backend):
```bash
# À la racine du projet, avec l'environnement virtuel activé
python run_api.py
```

Dans un second terminal (frontend):
```bash
cd frontend
npm run dev
```

## Configuration d'Outlines pour l'extraction structurée

DataFlow AI utilise la bibliothèque [Outlines](https://github.com/dottxt/outlines) pour l'extraction structurée depuis les LLMs.

### Exigences spécifiques d'Outlines

**IMPORTANT**: Outlines 0.2.3 requiert **Python 3.12** spécifiquement. Pour cette raison, il est recommandé de créer un environnement virtuel dédié:

```bash
# Créer un environnement virtuel avec Python 3.12
python3.12 -m venv venv_outlines

# Activer l'environnement
source venv_outlines/bin/activate  # Linux/Mac
venv_outlines\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

Les versions plus récentes de Python (3.13+) ne sont pas compatibles avec Outlines 0.2.3.

### Modes de fonctionnement d'Outlines

Deux modes de fonctionnement sont disponibles:

1. **Mode complet**: Avec la bibliothèque Outlines installée et une clé API OpenAI
2. **Mode dégradé**: Fonctionnement sans Outlines ou sans clé API (certaines fonctionnalités désactivées)

Le système détecte automatiquement la configuration disponible et s'adapte en conséquence.

## Configuration de l'API OpenAI

Pour les fonctionnalités d'enrichissement LLM et d'analyse d'images, une clé API OpenAI est nécessaire.

### 1. Obtenir une clé API

1. Créez un compte sur [OpenAI Platform](https://platform.openai.com/)
2. Accédez à la section API Keys
3. Créez une nouvelle clé API

### 2. Configurer la clé dans DataFlow AI

Ajoutez votre clé API dans le fichier `.env`:

```
OPENAI_API_KEY=votre_clé_api_openai
```

### 3. Modèles utilisés

DataFlow AI utilise différents modèles selon les fonctionnalités:
- `gpt-4o` pour l'analyse d'images dans les PDFs
- `gpt-4-turbo` pour l'enrichissement des données JSON
- `gpt-3.5-turbo` comme fallback pour certaines tâches moins complexes

## Configuration du frontend

Le frontend offre une interface utilisateur moderne pour accéder aux fonctionnalités de DataFlow AI.

### Options de configuration

Dans le fichier `frontend/.env`:

```
# Clé API pour se connecter au backend
VITE_API_KEY=votre_clé_api_sécurisée

# URL de l'API (par défaut: /api)
VITE_API_URL=/api

# Limitations pour les fichiers
VITE_MAX_PDF_SIZE_MB=50
VITE_DEFAULT_IMAGES_ANALYSIS=10
```

## Vérification de l'installation

Pour vérifier que tous les composants fonctionnent correctement:

### 1. Tester l'API

```bash
curl http://localhost:8000/api/pdf/test -H "X-API-Key: votre_clé_api_sécurisée"
```

Vous devriez recevoir une réponse JSON indiquant que l'API fonctionne.

### 2. Vérifier l'intégration d'Outlines

```bash
python -m tests.test_outlines_integration
```

### 3. Tester la CLI

```bash
python -m cli.cli test
```

## Résolution des problèmes courants

### L'API ne démarre pas

- Vérifiez que le port 8000 n'est pas déjà utilisé
- Vérifiez que toutes les dépendances sont installées
- Consultez les logs: `docker-compose logs api`

### Erreurs d'authentification

- Vérifiez que la même clé API est configurée dans `.env` et `frontend/.env`
- Assurez-vous que les requêtes incluent bien l'en-tête `X-API-Key`

### Problèmes avec Outlines

- Vérifiez que vous utilisez Python 3.12 spécifiquement
- Si l'installation échoue, essayez: `pip install outlines==0.2.3`

### Erreurs de traitement des fichiers PDF

- Assurez-vous que la clé API OpenAI est valide
- Vérifiez que le fichier PDF n'est pas corrompu ou protégé

### Problèmes Docker

- Essayez de reconstruire les images: `docker-compose build --no-cache`
- Vérifiez l'espace disque disponible
- Consultez les logs: `docker-compose logs` 