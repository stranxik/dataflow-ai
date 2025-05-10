# API DataFlow AI

## Présentation

L'API DataFlow AI est une interface de programmation RESTful construite avec FastAPI. Elle fournit un ensemble d'endpoints pour traiter les données, analyser les documents et intégrer l'intelligence artificielle dans les workflows de traitement de données.

## Technologies utilisées

- **FastAPI** - Framework web moderne et rapide pour la création d'APIs
- **Python 3.10+** - Langage de programmation principal
- **Uvicorn** - Serveur ASGI performant pour exécuter l'application
- **PyMuPDF (Fitz)** - Bibliothèque pour l'analyse de documents PDF
- **Outlines** - Framework d'intégration LLM avec génération structurée
- **GPT-4o** - Pour l'analyse avancée des images et du texte
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
│   └── unified.py       # Routes pour le traitement unifié (JIRA/Confluence)
└── services/            # Logique métier et services sous-jacents
    ├── __init__.py      # Initialisation du package services
    ├── pdf_service.py   # Service de traitement PDF
    ├── json_service.py  # Service de traitement JSON
    └── unified_service.py # Service de traitement unifié
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

4. Lancez le serveur:

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
```

## Intégration avec le Frontend

L'API est conçue pour fonctionner avec le frontend DataFlow AI, mais peut également être utilisée indépendamment comme service backend. Les réponses sont formatées en JSON et suivent des structures cohérentes.

## Sécurité

- Tous les fichiers traités sont temporaires et ne sont pas stockés de façon permanente
- Validation des entrées via Pydantic
- Limites de taille de fichier pour éviter les abus
- Prise en charge CORS pour les requêtes cross-origin sécurisées

## Performances

- Traitement asynchrone pour une meilleure scalabilité
- Optimisations pour le traitement de fichiers volumineux
- Mise en cache configurable pour les opérations fréquentes

## Développement et extension

Pour étendre l'API avec de nouvelles fonctionnalités:

1. Créez un nouveau fichier de routes dans le dossier `routes/`
2. Implémentez les services nécessaires dans `services/`
3. Définissez les modèles de données dans `models/` si nécessaire
4. Enregistrez les nouveaux routes dans `main.py` 