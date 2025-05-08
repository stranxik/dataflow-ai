# JSON Processor & CLI - Solution complète pour le traitement et l'analyse de données

## 🚀 Vue d'ensemble

Ce projet fournit une solution complète pour traiter, analyser et transformer des fichiers JSON provenant de différentes sources (JIRA, Confluence, GitHub, etc.), en préparation pour l'indexation dans un système RAG avec Llamendex.

Il se compose de deux modules principaux :
- **CLI** : Interface en ligne de commande interactive et puissante pour toutes les opérations
- **Extract** : Moteur de traitement flexible pour l'analyse et la transformation des données

## 🎯 Objectifs et fonctionnalités principales

- **Détection automatique** de type de fichier (JIRA, Confluence, GitHub)
- **Transformation flexible** via des mappings personnalisables
- **Mode interactif complet** avec assistant guidé pour toutes les opérations
- **Découpage et traitement** de fichiers volumineux
- **Extraction de métadonnées** structurées
- **Établissement de correspondances** entre différentes sources
- **Extraction structurée avec Outlines** pour une génération contrainte par schéma
- **Enrichissement par LLM** (OpenAI) pour l'analyse sémantique
- **Arborescences détaillées** du contenu de chaque fichier traité
- **Organisation automatique** des résultats avec timestamps uniques

## ⚙️ Installation

1. Clonez ce dépôt et accédez au dossier
2. Créez un fichier `.env` en copiant `.env.example`
3. Installez les dépendances :

```bash
pip install -r requirements.txt
```

### Configuration d'Outlines (optionnelle)

Le système utilise la bibliothèque [Outlines](https://github.com/dottxt/outlines) (v0.2.3) pour l'extraction structurée de données. Deux modes de fonctionnement sont disponibles :

1. **Mode complet** : Avec la bibliothèque Outlines installée et une clé API OpenAI
2. **Mode stub** : Fonctionnement dégradé sans Outlines ou sans clé API

Le système détecte automatiquement la configuration disponible et s'adapte en conséquence. Pour vérifier votre installation :

```bash
python test_outlines_integration.py
```

## 📖 Guide d'utilisation rapide

### Mode interactif (recommandé)

Lancez l'assistant complet qui vous guide étape par étape :

```bash
python -m cli.cli interactive
```

### Traitement de fichiers JSON

```bash
python -m cli.cli process mon_fichier.json --output resultat.json
```

### Avec extraction structurée Outlines

```bash
python -m cli.cli process mon_fichier.json --outlines --llm
```

### Découpage de fichiers volumineux

```bash
python -m cli.cli chunks mon_gros_fichier.json --output-dir dossier_morceaux --items-per-file 500
```

### Correspondances entre JIRA et Confluence

```bash
python -m cli.cli match jira_processed.json confluence_processed.json --output-dir resultats_match
```

### Flux de traitement complet

```bash
python -m cli.cli unified jira1.json jira2.json --confluence conf1.json conf2.json --output-dir resultats_complets
```

## 📊 Organisation des résultats

Tous les résultats sont organisés dans le dossier `results/` avec une structure claire :

```
results/
├── jira_confluence_2023-08-30-14-22-55/     # Dossier d'une exécution unified
│   ├── jira/                               # Sous-dossier pour les fichiers JIRA
│   ├── confluence/                         # Sous-dossier pour les fichiers Confluence
│   ├── matches/                            # Sous-dossier pour les correspondances
│   ├── split_jira_files/                   # Fichiers JIRA découpés
│   ├── split_confluence_files/             # Fichiers Confluence découpés
│   ├── llm_ready/                          # Fichiers prêts pour LLM
│   ├── global_arborescence.txt             # Arborescence globale
│   └── ...
```

## 🔍 Approche flexible et générique

L'approche adoptée permet de traiter n'importe quelle structure JSON, grâce à :

1. **Détection automatique de structure** : Analyse des champs importants
2. **Mappers personnalisables** : Adaptation à n'importe quel format
3. **Traitement par morceaux** : Gestion efficace de fichiers volumineux
4. **Transformation flexible** : Structure de sortie adaptable

## 💡 Système de fallback robuste

Notre solution est conçue pour fonctionner dans différents environnements, grâce à un système de fallback à plusieurs niveaux :

1. **Outlines + OpenAI** : Utilisation complète des fonctionnalités d'extraction structurée
2. **Sans OpenAI** : Outlines fonctionne en mode dégradé, certaines fonctionnalités désactivées
3. **Sans Outlines** : Le système utilise des stubs internes qui imitent l'API d'Outlines
4. **Fallback standard** : En dernier recours, utilisation du parseur JSON standard

Cette architecture garantit que le système reste opérationnel même sans connexion internet ou clé API.

## 🧩 Extension du système

### Créer vos propres mappers

Pour adapter la solution à de nouvelles sources :

```python
from generic_json_processor import GenericJsonProcessor

def mon_mapper_personnalise(item):
    # Transformer l'item selon vos besoins
    result = {
        "id": item.get("identifiant", ""),
        "content": {
            "title": item.get("nom", ""),
            "body": item.get("contenu", "")
        },
        "metadata": {
            "created_at": item.get("date_creation", ""),
            "type": item.get("type", "")
        }
    }
    return result

# Créer le processeur avec votre mapper
processor = GenericJsonProcessor(custom_mapper=mon_mapper_personnalise)
processor.process_file("mon_fichier.json", "resultat.json")
```

### Utiliser Outlines pour l'extraction structurée

```python
from extract import outlines_robust_json_parser, extract_structured_data

# Parser un fichier JSON avec Outlines
data = outlines_robust_json_parser("mon_fichier.json", llm_fallback=True)

# Extraire des données structurées selon un schéma
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "categories": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}
result = extract_structured_data(text_content, schema)
```

## 🔄 Intégration avec Temporal

Notre solution s'intègre parfaitement avec des workflows Temporal :

| **Workflow Temporal** | **Index associé** | **Notre solution** |
|------------------------|-------------------|---------------------|
| `SyncJiraAndIndex` | `JiraIndex` | Utilise notre processeur avec mapping JIRA |
| `SyncConfluenceAndIndex` | `ConfluenceIndex` | Utilise notre processeur avec mapping Confluence |
| `HandleUserQueryToAgent` | (tous) | Interroge les données transformées par notre solution |

## 📝 Format pour Llamendex

La structure de sortie est optimisée pour Llamendex, permettant une conversion directe en `NodeWithScore` :

```json
{
  "items": [
    {
      "id": "IDENTIFIANT",
      "title": "TITRE",
      "content": {
        "field1": "CONTENU1",
        "field2": "CONTENU2"
      },
      "metadata": {
        "created_at": "DATE",
        "author": "AUTEUR"
      },
      "analysis": {
        "keywords": ["MOT1", "MOT2"],
        "entities": {
          "ids": ["ID1", "ID2"],
          "urls": ["URL1", "URL2"]
        }
      },
      "relationships": {
        "confluence_links": [],
        "jira_tickets": []
      }
    }
  ],
  "metadata": {
    "source_file": "fichier_source.json",
    "processed_at": "DATE_TRAITEMENT",
    "structure": { ... }
  }
}
```

## ⚠️ Dépendances

- Python 3.8+
- typer, rich, inquirer, python-dotenv, ijson
- openai (optionnel, pour les fonctionnalités LLM)
- outlines==0.2.3 (optionnel, pour l'extraction structurée)

## 📜 Licence

Ce projet est distribué sous licence MIT. 