# Utilisation d'Outlines 0.2.3 dans ce projet

Ce document explique comment le projet utilise la bibliothèque [Outlines](https://github.com/dottxt-ai/outlines) version 0.2.3 pour le traitement et l'extraction robuste de données JSON.

## Présentation d'Outlines

Outlines est une bibliothèque Python qui permet de générer du texte structuré à partir de modèles de langage (LLM). Elle offre des fonctionnalités avancées comme:

- Génération de JSON suivant un schéma précis
- Génération de texte suivant une expression régulière
- Extraction structurée de données
- Support de plusieurs modèles (OpenAI, Transformers, etc.)

## Installation d'Outlines 0.2.3

⚠️ **IMPORTANT**: Outlines 0.2.3 requiert **strictement Python 3.12** (Python 3.13 n'est pas supporté).

```bash
# Installer dans un environnement virtuel avec Python 3.12
python3.12 -m venv venv_outlines
source venv_outlines/bin/activate  # Linux/Mac
# OU
venv_outlines\Scripts\activate     # Windows

# Installer Outlines
pip install outlines==0.2.3

# Installer les dépendances du projet
pip install -r requirements.txt
```

## Sources de données

Les fichiers sources JSON à traiter se trouvent dans le dossier `files` à la racine du projet:
- `CASM_jira.json`: Tickets JIRA du projet CASM
- `CARTAN_jira.json`: Tickets JIRA du projet CARTAN
- `hollard_confluence.json`: Pages Confluence Hollard

Pour traiter ces fichiers, assurez-vous d'activer l'environnement virtuel Python 3.12 avant de lancer les commandes.

## Structure d'intégration dans notre projet

Notre implémentation d'Outlines se compose de deux modules principaux:

1. `extract/outlines_enhanced_parser.py` - Parser JSON robuste utilisant Outlines
2. `extract/outlines_extractor.py` - Extracteur de données structurées

### Architecture du système

```
┌───────────────────┐
│  CLI/Application  │
└─────────┬─────────┘
          │
┌─────────▼─────────┐
│ outlines_extractor │◄─────┐
└─────────┬─────────┘      │
          │                │
┌─────────▼─────────┐      │
│outlines_parser    │      │
└─────────┬─────────┘      │
          │                │
┌─────────▼─────────┐      │
│robust_json_parser │──────┘
└───────────────────┘   (fallback)
```

### Mode de fonctionnement hybride

Notre système utilise une approche hybride:
1. Essaie d'abord de parser avec Outlines
2. Si Outlines n'est pas disponible, utilise des stubs internes
3. En dernier recours, revient au parser JSON robuste standard

## API et utilisation

### Initialisation du modèle

```python
from outlines import models

# Créer un modèle OpenAI - Notez que dans 0.2.3 la signature a changé
# et le paramètre temperature n'est plus supporté avec OpenAI
model = models.openai("gpt-4.1", api_key="votre-clé-api")
```

### Parser JSON avec Outlines

```python
from extract import outlines_robust_json_parser

# Parser un fichier JSON avec fallback LLM si nécessaire
data = outlines_robust_json_parser(
    file_path="data.json", 
    llm_fallback=True,
    model="gpt-4.1"  # Modèle OpenAI à utiliser
)
```

### Extraction structurée avec un schéma

```python
from extract.outlines_enhanced_parser import extract_structured_data

# Définir un schéma pour les données à extraire
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "author": {"type": "string"},
        "tags": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

# Extraire des données selon ce schéma
structured_data = extract_structured_data(
    content=json_content,
    schema=schema,
    model="gpt-4.1"
)
```

### Extraction d'entités nommées

```python
from extract.outlines_enhanced_parser import extract_entities

# Extraire des entités comme des IDs, emails, URLs, personnes et organisations
entities = extract_entities(
    text="Contactez john.doe@example.com concernant le ticket PROJ-123.",
    model="gpt-4.1"
)
# Résultat: {"ids": ["PROJ-123"], "emails": ["john.doe@example.com"], ...}
```

## Utilisation des guides de génération (0.2.3)

Dans Outlines 0.2.3, l'API a changé significativement par rapport aux versions précédentes:

### 1. Guide Regex

```python
# Import du module generate et des modèles
from outlines import models
import outlines.generate as generate

# Créer un modèle
model = models.openai("gpt-4.1", api_key="votre-clé-api")

# Créer un générateur avec contrainte regex
regex_pattern = r'\{(?:[^{}]|(?R))*\}|\[(?:[^\[\]]|(?R))*\]'
generator = generate.regex(model, regex_pattern)

# Générer un texte suivant cette contrainte
result = generator("Génère un objet JSON valide")
```

### 2. Guide par schéma JSON

```python
# Import du module generate
import outlines.generate as generate

# Définir un schéma
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"}
    },
    "required": ["name", "age"]
}

# Créer un générateur avec contrainte de schéma
generator = generate.json(model, schema)

# Générer un JSON suivant ce schéma
result = generator("Génère un objet avec nom et âge")
```

### 3. Prompts avec Template

```python
# Import de Template
from outlines import Template

# Créer un template avec Jinja2
template = Template.from_string("Voici une variable: {{ variable }}")

# Rendre le template avec les variables
prompt = template(variable="valeur")
```

## Limitations et compatibilité

### Notes importantes sur OpenAI

- Avec Outlines 0.2.3, certaines fonctionnalités sont limitées avec les modèles OpenAI:
  - `generate.format(model, int)` ne fonctionne pas avec les modèles OpenAI
  - Certains guides avancés peuvent ne pas être compatibles avec l'API OpenAI
  - Il est préférable d'utiliser `generate.text()` et `generate.json()` avec OpenAI

### Compatibilité générale

- Outlines 0.2.3 n'est pas compatible avec Python 3.13
- Différentes versions d'Outlines peuvent avoir des API légèrement différentes
- Si Outlines n'est pas disponible, notre système continuera à fonctionner avec des fonctionnalités réduites

## Gestion des erreurs et fallbacks

Notre mise en œuvre assure une robustesse maximale en:

1. Détectant automatiquement si Outlines est disponible
2. Fournissant des stubs pour les tests et développement
3. Permettant de revenir au parseur JSON standard si nécessaire
4. Offrant des mécanismes de réparation JSON via LLM

---

Pour plus d'informations sur Outlines, consultez la [documentation officielle](https://dottxt-ai.github.io/outlines/latest/welcome/). 