# JSON Processor & CLI pour Llamendex - Extraction et analyse robuste de données structurées

## 🔍 Introduction

Ce projet est une solution complète pour traiter, analyser et transformer des fichiers JSON provenant de différentes sources (JIRA, Confluence, GitHub, etc.) en préparation pour l'indexation dans Llamendex ou tout autre système RAG moderne.

La particularité de cette solution réside dans sa capacité à **s'adapter automatiquement à n'importe quelle structure JSON** et à garantir un traitement robuste des fichiers, même en présence d'erreurs ou d'incohérences. Contrairement aux outils génériques de traitement JSON, notre solution allie:

- **Détection intelligente** de la structure des données
- **Préservation des fichiers sources** (jamais modifiés directement)
- **Enrichissement sémantique par LLM** avec Outlines
- **Rapports détaillés** générés automatiquement
- **Correction automatique** des erreurs de syntaxe JSON
- **Interface CLI interactive** et accessible

### Pourquoi cette solution ?

Dans le développement de systèmes RAG (Retrieval Augmented Generation) comme Llamendex, l'ingestion de données de qualité est cruciale. Pourtant, nous faisons face à plusieurs défis concrets :

1. **Hétérogénéité des sources** : Chaque système (JIRA, Confluence, GitHub) exporte des structures JSON différentes
2. **Fichiers mal formés** : Les exports contiennent souvent des erreurs syntaxiques ou structurelles
3. **Volumes importants** : Les exports peuvent atteindre plusieurs gigaoctets, dépassant les capacités de traitement standard
4. **Perte de contexte** : L'enrichissement manuel des données est chronophage et inconsistant
5. **Absence de correspondances** : Les liens entre tickets JIRA et pages Confluence sont souvent perdus

Notre solution répond à ces défis en proposant un pipeline complet et robuste qui :
- Détecte et répare automatiquement les problèmes de structure
- Standardise les données dans un format optimal pour les systèmes RAG
- Enrichit le contenu grâce à des LLM pour améliorer la recherche sémantique
- Établit des correspondances entre différentes sources de données
- Génère automatiquement des résumés et analyses pour faciliter l'ingestion

De plus, contrairement aux outils ETL génériques ou aux solutions de traitement tabulaire comme pandas, notre solution est spécifiquement conçue pour préparer des données textuelles riches pour les systèmes de RAG, avec une attention particulière à la préservation du contexte et à l'enrichissement sémantique.

## �� Vue d'ensemble

Le projet se compose de trois modules principaux :
- **CLI** : Interface en ligne de commande interactive et puissante pour toutes les opérations
- **Extract** : Moteur de traitement flexible pour l'analyse et la transformation des données
- **Tools** : Utilitaires pour résoudre des problèmes spécifiques (nettoyage, validation)

## 🎯 Fonctionnalités principales

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
- **Résumés LLM générés automatiquement** pour chaque traitement
- **Gestion robuste des erreurs** avec différents niveaux de fallback

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
python -m tests.test_outlines_integration
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

### Avec enrichissement LLM et préservation des sources

```bash
python -m cli.cli process mon_fichier.json --llm --preserve-source
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
│   │   ├── enriched_jira.json              # JIRA enrichi avec LLM
│   │   ├── enriched_confluence.json        # Confluence enrichi avec LLM
│   │   ├── jira_llm_enrichment_summary.md  # Résumé LLM pour JIRA
│   │   └── confluence_llm_enrichment_summary.md # Résumé LLM pour Confluence
│   ├── global_arborescence.txt             # Arborescence globale
│   └── ...
```

## 🧠 Résumés LLM automatiques

Pour chaque traitement utilisant un LLM, un rapport de résumé est automatiquement généré au format Markdown:

```markdown
# Résumé de l'enrichissement LLM

## Informations générales
- Date d'analyse: 2025-05-08 23:34:37
- Nombre total d'éléments analysés: 42
- Modèle LLM utilisé: gpt-4

## Analyse
### Mots-clés principaux extraits
projet, développement, API, backend, utilisateur, interface, base de données

### Distribution des sentiments
{'positive': 12, 'neutral': 25, 'negative': 5}

### Exemple d'enrichissement
**Ticket**: PROJ-123 - Implémentation de l'authentification OAuth2
**Résumé LLM**: Ce ticket concerne l'intégration du protocole OAuth2 pour sécuriser l'API...
```

Ces résumés permettent:
1. Une vue d'ensemble rapide du contenu traité
2. L'extraction des principaux thèmes et sentiments
3. Des exemples concrets d'enrichissement LLM
4. Une préparation optimale pour l'ingestion dans Llamendex

## 🔍 Approche flexible et générique

L'approche adoptée permet de traiter n'importe quelle structure JSON, grâce à :

1. **Détection automatique de structure** : Analyse des champs importants
2. **Mappers personnalisables** : Adaptation à n'importe quel format
3. **Traitement par morceaux** : Gestion efficace de fichiers volumineux
4. **Transformation flexible** : Structure de sortie adaptable
5. **Préservation des sources** : Travail uniquement sur des copies

## 💡 Système de fallback robuste

Notre solution est conçue pour fonctionner dans différents environnements, grâce à un système de fallback à plusieurs niveaux :

1. **Outlines + OpenAI** : Utilisation complète des fonctionnalités d'extraction structurée
2. **Sans OpenAI** : Outlines fonctionne en mode dégradé, certaines fonctionnalités désactivées
3. **Sans Outlines** : Le système utilise des stubs internes qui imitent l'API d'Outlines
4. **Fallback standard** : En dernier recours, utilisation du parseur JSON standard

Cette architecture garantit que le système reste opérationnel même sans connexion internet ou clé API.

## 🛠️ Utilitaires

Le projet inclut des outils pratiques dans le dossier `tools/` :

1. **check_json.py** : Vérifier la validité des fichiers JSON
   ```bash
   python -m tools.check_json chemin/vers/fichier.json
   ```

2. **fix_paths.py** : Corriger les problèmes de chemins et réparer les fichiers JSON
   ```bash
   python -m tools.fix_paths --all --source-dir=files --target-dir=results/fixed
   ```

## 🧩 Extension du système

### Créer vos propres mappers

Pour adapter la solution à de nouvelles sources :

```python
from extract.generic_json_processor import GenericJsonProcessor

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
from extract.outlines_enhanced_parser import outlines_robust_json_parser
from extract.outlines_extractor import extract_structured_data

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

## 🔄 Intégration avec Temporal et Llamendex

Notre solution s'intègre parfaitement avec des workflows Temporal et Llamendex :

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
        "llm_summary": "Résumé concis généré par LLM",
        "llm_keywords": ["MOT1", "MOT2"],
        "llm_entities": {
          "people": ["PERSONNE1", "PERSONNE2"],
          "organizations": ["ORG1", "ORG2"]
        },
        "llm_sentiment": "positive"
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
    "llm_enrichment": {
      "model": "gpt-4",
      "enrichment_date": "DATE_ENRICHISSEMENT"
    }
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