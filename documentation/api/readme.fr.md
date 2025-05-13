# API DataFlow AI

## Présentation

L'API DataFlow AI est une interface de programmation RESTful construite avec FastAPI. Elle fournit un ensemble d'endpoints pour traiter les données, analyser les documents et intégrer l'intelligence artificielle dans les workflows de traitement de données.

## Technologies utilisées

- **FastAPI** - Framework web moderne et rapide pour la création d'APIs
- **Python 3.10+** - Langage de programmation principal
- **Uvicorn** - Serveur ASGI performant pour exécuter l'application
- **PyMuPDF (Fitz)** - Bibliothèque pour l'analyse de documents PDF
- **Outlines** - Framework d'intégration LLM avec génération structurée
- **GPT-4.1** - Pour l'analyse avancée des images et du texte
- **Docker** - Conteneurisation (optionnelle)

## Structure du projet

```
api/
├── main.py              # Point d'entrée principal de l'API
├── __init__.py          # Initialisation du package
├── models/              # Modèles de données et schémas Pydantic
├── routes/              # Définitions des endpoints par fonctionnalité
│   ├── __init__.py      # Initialisation du package routes
│   ├── pdf.py           # Routes pour le traitement PDF
│   ├── json.py          # Routes pour le traitement JSON
│   ├── unified.py       # Routes pour le traitement unifié (JIRA/Confluence)
│   └── auth.py          # Middleware d'authentification par API key
└── services/            # Logique métier et services sous-jacents
    ├── __init__.py      # Initialisation du package services
    ├── pdf_service.py   # Service de traitement PDF
    ├── json_service.py  # Service de traitement JSON
    └── unified_service.py # Service de traitement unifié
```

## Authentification API

Tous les endpoints de l'API (à l'exception des endpoints de santé `/api/health` et racine `/`) nécessitent une authentification par API key.

### Configuration de l'API Key

1. Définissez votre clé API dans le fichier `.env` à la racine du projet :
   ```
   API_KEY=votre_clé_api_sécurisée
   ```

2. Pour la production, utilisez une clé forte et aléatoire :
   ```bash
   openssl rand -hex 32
   ```

### Utilisation de l'API Key

Pour chaque requête API, incluez la clé API dans l'en-tête HTTP :

```
X-API-Key: votre_clé_api_sécurisée
```

Exemple avec curl :
```bash
curl -X POST http://localhost:8000/api/json/process \
  -H "X-API-Key: votre_clé_api_sécurisée" \
  -F "file=@mon_fichier.json"
```

Exemple avec JavaScript/Fetch :
```javascript
const response = await fetch('http://localhost:8000/api/json/process', {
  method: 'POST',
  headers: {
    'X-API-Key': 'votre_clé_api_sécurisée'
  },
  body: formData
});
```

## Endpoints principaux

L'API expose les endpoints suivants :

### Traitement PDF
- `POST /api/pdf/process` - Traite un fichier PDF et extrait le texte et les images avec analyse IA

### Traitement JSON
- `POST /api/json/process` - Traite un fichier JSON avec détection de structure
- `POST /api/json/clean` - Nettoie les données sensibles d'un fichier JSON
- `POST /api/json/compress` - Compresse un fichier JSON pour réduire sa taille
- `POST /api/json/split` - Divise un fichier JSON en plusieurs morceaux

### Traitement unifié
- `POST /api/unified/process` - Traite et associe des fichiers JIRA et Confluence

## Installation et démarrage

1. Assurez-vous d'avoir Python 3.10+ installé
2. Créez et activez un environnement virtuel:

```bash
python -m venv venv_outlines
source venv_outlines/bin/activate  # Sur Windows: venv_outlines\\Scripts\\activate
```

3. Installez les dépendances:

```bash
pip install -r requirements.txt
```

4. Créez un fichier `.env` avec vos configurations:

```
API_PORT=8000
API_HOST=localhost
DEBUG=True
MAX_UPLOAD_SIZE=52428800  # 50MB
API_KEY=votre_clé_api_sécurisée
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000
```

5. Lancez le serveur:

```bash
python run_api.py
```

L'API sera accessible à l'adresse `http://localhost:8000`. La documentation interactive est disponible à `http://localhost:8000/docs`.

## Variables d'environnement

Les variables d'environnement peuvent être configurées dans un fichier `.env` à la racine du projet:

```
API_PORT=8000
API_HOST=localhost
DEBUG=True
MAX_UPLOAD_SIZE=52428800  # 50MB
API_KEY=votre_clé_api_sécurisée
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Intégration avec le Frontend

L'API est conçue pour fonctionner avec le frontend DataFlow AI. Le frontend utilise automatiquement la clé API définie dans son fichier `.env` pour toutes les communications avec l'API. Pour configurer le frontend :

1. Assurez-vous que la même clé API est configurée dans `frontend/.env` :
   ```
   VITE_API_KEY=votre_clé_api_sécurisée
   ```

2. La variable `FRONTEND_ORIGINS` dans le fichier `.env` du backend doit inclure l'origine du frontend pour permettre les requêtes CORS.

## Sécurité

- **Authentification API Key** - Toutes les routes sont protégées par une clé API
- **Validation CORS** - Seules les origines autorisées peuvent accéder à l'API
- **Fichiers temporaires** - Tous les fichiers traités sont temporaires et ne sont pas stockés de façon permanente
- **Validation des entrées** - Utilisation de Pydantic pour valider les entrées
- **Limites de taille** - Limites de taille de fichier pour éviter les abus
- **Headers sécurisés** - Headers HTTP configurés pour la sécurité

Pour plus de détails sur la sécurité et l'authentification, consultez le document dédié dans `documentation/security/API_AUTHENTICATION.md`.

## Performances

- Traitement asynchrone pour une meilleure scalabilité
- Optimisations pour le traitement de fichiers volumineux
- Mise en cache configurable pour les opérations fréquentes

## Développement et extension

Pour étendre l'API avec de nouvelles fonctionnalités:

1. Créez un nouveau fichier de routes dans le dossier `routes/`
2. Implémentez les services nécessaires dans `services/`
3. Définissez les modèles de données dans `models/` si nécessaire
4. Enregistrez les nouveaux routes dans `main.py` avec la dépendance d'authentification
   ```python
   app.include_router(ma_nouvelle_route.router, prefix="/api/nouveau", tags=["Nouvelle Fonctionnalité"], dependencies=[require_api_key])
   ``` 