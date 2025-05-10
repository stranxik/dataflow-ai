# DataFlow AI – Pipeline intelligent, CLI avancée & outils pour la préparation, la transformation, la sécurisation et l'enrichissement des données JSON & PDF pour l'IA et le RAG

![Version](https://img.shields.io/badge/version-1.0-blue) ![Python](https://img.shields.io/badge/Python-3.8%2B-green) ![License](https://img.shields.io/badge/license-MIT-orange)

> 🇬🇧 [English version available here](README.md)
> 📚 **Toute la documentation (FR/EN) est désormais centralisée dans le dossier [`/documentation`](documentation/).**
> Vous y trouverez tous les guides (CLI, Extract, LLM, Outlines, Sécurité, API, Frontend) en français et en anglais dans les sous-dossiers correspondants.

## 📑 Sommaire

- [Introduction](#-introduction)
- [Vue d'ensemble](#-vue-densemble)
- [Guide de référence rapide](#-guide-de-référence-rapide)
- [Fonctionnalités principales](#-fonctionnalités-principales)
- [Installation](#️-installation)
- [Guide d'utilisation rapide](#-guide-dutilisation-rapide)
- [Organisation des résultats](#-organisation-des-résultats)
- [Résumés LLM automatiques](#-résumés-llm-automatiques)
- [Approche flexible et générique](#-approche-flexible-et-générique)
- [Système de fallback robuste](#-système-de-fallback-robuste)
- [Utilitaires](#️-utilitaires)
- [Extension du système](#-extension-du-système)
- [Intégration avec Temporal et Llamendex](#-intégration-avec-temporal-et-llamendex)
- [Format pour Llamendex](#-format-pour-llamendex)
- [Analyse de documents PDF](#-analyse-de-documents-pdf)
- [API](#-api)
- [Frontend](#-frontend)
- [Sécurité](#-sécurité)
- [Dépendances](#️-dépendances)
- [Licence](#-licence)

## 🔍 Introduction

Ce projet est une solution complète pour traiter, analyser et transformer des fichiers JSON et des documents PDF provenant de différentes sources (JIRA, Confluence, GitHub, etc.) en préparation pour l'indexation dans Llamendex ou tout autre système RAG moderne.

La particularité de cette solution réside dans sa capacité à **s'adapter automatiquement à n'importe quelle structure JSON et extraire intelligemment le contenu des PDF** et à garantir un traitement robuste des fichiers, même en présence d'erreurs ou d'incohérences. Contrairement aux outils génériques de traitement JSON, notre solution allie:

- **Détection intelligente** de la structure des données
- **Préservation des fichiers sources** (jamais modifiés directement)
- **Enrichissement sémantique par LLM** avec Outlines
- **Extraction intelligente de PDF** (texte natif + images analysées par IA)
- **Rapports détaillés** générés automatiquement
- **Correction automatique** des erreurs de syntaxe JSON
- **Interface CLI interactive** et accessible

> 💡 **NOUVEAU!** Intégration complète des outils de sécurité et de nettoyage des données sensibles directement dans l'interface CLI et dans les processeurs JSON.
> 💡 **NOUVEAU!** Traitement avancé des PDF avec extraction intelligente du texte et analyse des images par IA grâce à GPT-4o.

### Pourquoi cette solution ?

Dans le développement de systèmes RAG (Retrieval Augmented Generation) comme Llamendex, l'ingestion de données de qualité est cruciale. Pourtant, nous faisons face à plusieurs défis concrets :

1. **Hétérogénéité des sources** : Chaque système (JIRA, Confluence, GitHub) exporte des structures JSON différentes
2. **Fichiers mal formés** : Les exports contiennent souvent des erreurs syntaxiques ou structurelles
3. **Volumes importants** : Les exports peuvent atteindre plusieurs gigaoctets, dépassant les capacités de traitement standard
4. **Perte de contexte** : L'enrichissement manuel des données est chronophage et inconsistant
5. **Complexité des PDF** : Les extracteurs standards perdent la structure ou convertissent tout en images
6. **Absence de correspondances** : Les liens entre tickets JIRA et pages Confluence sont souvent perdus

Notre solution répond à ces défis en proposant un pipeline complet et robuste qui :
- Détecte et répare automatiquement les problèmes de structure
- Standardise les données dans un format optimal pour les systèmes RAG
- Enrichit le contenu grâce à des LLM pour améliorer la recherche sémantique
- Extrait intelligemment le texte et les images des PDF avec analyse IA
- Établit des correspondances entre différentes sources de données
- Génère automatiquement des résumés et analyses pour faciliter l'ingestion

De plus, contrairement aux outils ETL génériques ou aux solutions de traitement tabulaire comme pandas, notre solution est spécifiquement conçue pour préparer des données textuelles riches pour les systèmes de RAG, avec une attention particulière à la préservation du contexte et à l'enrichissement sémantique.

## 🎯 Vue d'ensemble

Le projet se compose de trois modules principaux :
- **CLI** : Interface en ligne de commande interactive et puissante pour toutes les opérations
- **Extract** : Moteur de traitement flexible pour l'analyse et la transformation des données
- **Tools** : Utilitaires pour résoudre des problèmes spécifiques (nettoyage, validation)

<!-- DÉBUT ENCART DE RÉFÉRENCE RAPIDE -->
<div align="center">

## 📋 Guide de référence rapide

</div>

| Commande | Description | Exemple |
|---------|-------------|---------|
| `interactive` | **Mode interactif** avec assistant guidé | `python -m cli.cli interactive` |
| `process` | **Traiter** un fichier JSON | `python -m cli.cli process fichier.json --llm` |
| `chunks` | **Découper** un fichier volumineux | `python -m cli.cli chunks gros_fichier.json --items-per-file 500` |
| `match` | **Correspondances** JIRA-Confluence | `python -m cli.cli match jira.json confluence.json` |
| `unified` | **Flux complet** de traitement | `python -m cli.cli unified jira1.json jira2.json --confluence conf1.json` |
| `extract-images` | **Extraire & analyser** le contenu PDF | `python -m cli.cli extract-images complete fichier.pdf --max-images 10` |
| `clean` | **Nettoyer** les données sensibles | `python -m cli.cli clean fichier.json --recursive` |
| `compress` | **Compresser & optimiser** des fichiers JSON | `python -m cli.cli compress repertoire --level 19` |

<div align="center">

### 🛠️ Outils indépendants

</div>

| Outil | Description | Exemple |
|-------|-------------|---------|
| `check_json.py` | **Vérifier** la validité des fichiers JSON | `python -m tools.check_json fichier.json` |
| `clean_sensitive_data.py` | **Nettoyer** les données sensibles | `python -m tools.clean_sensitive_data fichier.json` |
| `fix_paths.py` | **Réparer** les chemins et les fichiers | `python -m tools.fix_paths --all --source-dir=files` |

<!-- FIN ENCART DE RÉFÉRENCE RAPIDE -->

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

### ⚠️ Exigences Python pour Outlines

**IMPORTANT**: Outlines 0.2.3 requiert **Python 3.12** spécifiquement. Il est fortement recommandé de créer un environnement virtuel dédié:

```bash
# Créer un environnement virtuel avec Python 3.12
python3.12 -m venv venv_outlines

# Activer l'environnement
source venv_outlines/bin/activate  # Linux/Mac
venv_outlines\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

Les versions plus récentes de Python (3.13+) ne sont pas compatibles avec Outlines 0.2.3, et les fonctionnalités LLM ne fonctionneront pas correctement sans cet environnement spécifique.

### Configuration d'Outlines (optionnelle)

Le système utilise la bibliothèque [Outlines](https://github.com/dottxt/outlines) (v0.2.3) pour l'extraction structurée de données. Deux modes de fonctionnement sont disponibles :

1. **Mode complet** : Avec la bibliothèque Outlines installée et une clé API OpenAI
2. **Mode stub** : Fonctionnement dégradé sans Outlines ou sans clé API

Le système détecte automatiquement la configuration disponible et s'adapte en conséquence. Pour vérifier votre installation :

```bash
python -m tests.test_outlines_integration
```

## 📖 Guide d'utilisation rapide

<div class="command-box">

### 🔍 Mode interactif (recommandé)

Lancez l'assistant complet qui vous guide étape par étape :

```bash
python -m cli.cli interactive
```

</div>

<div class="command-box">

### 📄 Traitement de fichiers JSON

```bash
python -m cli.cli process mon_fichier.json --output resultat.json
```

#### Avec enrichissement LLM et préservation des sources

```bash
python -m cli.cli process mon_fichier.json --llm --preserve-source
```

</div>

<div class="command-box">

### 🔪 Découpage de fichiers volumineux

```bash
python -m cli.cli chunks mon_gros_fichier.json --output-dir dossier_morceaux --items-per-file 500
```

</div>

<div class="command-box">

### 🔗 Correspondances entre JIRA et Confluence

```bash
python -m cli.cli match jira_processed.json confluence_processed.json --output-dir resultats_match
```

</div>

<div class="command-box">

### 🚀 Flux de traitement complet

```bash
python -m cli.cli unified jira1.json jira2.json --confluence conf1.json conf2.json --output-dir resultats_complets
```

</div>

<div class="command-box">

### 🧹 Nettoyage des données sensibles

```bash
python -m cli.cli clean fichier.json --output fichier_propre.json
```

</div>

<div class="command-box">

### 📦 Compression et optimisation des fichiers JSON

```bash
# Compresser un répertoire spécifique de fichiers JSON
python -m cli.cli compress results/mes_donnees --level 19 --keep-originals

# Compression avec le traitement unifié
python -m cli.cli unified jira1.json --output-dir dossier_resultats --compress
```

Le système de compression utilise orjson et zstd pour obtenir des économies d'espace considérables (jusqu'à 90%) tout en préservant l'intégrité des données.

</div>

<div class="command-box">

### 📄 Extraction de texte et d'images PDF

```bash
# Extraire le texte et analyser les images d'un fichier PDF
python -m cli.cli extract-images complete chemin/vers/fichier.pdf --max-images 10

# Sauvegarder le contenu extrait dans un répertoire spécifique
python -m cli.cli extract-images complete chemin/vers/fichier.pdf --output-dir analyse_pdf
```

</div>

## 📊 Organisation des résultats

Tous les résultats sont organisés dans le dossier `results/` avec une structure claire :

```
results/
├── demo_test/                             # Exemple de dossier de notre dernier test
│   ├── jira/                               # Sous-dossier pour les fichiers JIRA
│   │   ├── demo_NEXUS_jira_processed.json  # Fichier JIRA traité
│   ├── confluence/                         # Sous-dossier pour les fichiers Confluence
│   ├── matches/                            # Sous-dossier pour les correspondances
│   ├── split_jira_files/                   # Fichiers JIRA découpés
│   ├── split_confluence_files/             # Fichiers Confluence découpés
│   ├── llm_ready/                          # Fichiers prêts pour LLM
│   │   ├── enriched_jira.json              # JIRA enrichi avec LLM
│   │   ├── enriched_jira.json.zst          # Version compressée (si activée)
│   │   ├── enriched_confluence.json        # Confluence enrichi avec LLM
│   │   ├── enriched_confluence.json.zst    # Version compressée (si activée)
│   │   ├── jira_llm_enrichment_summary.md  # Résumé LLM pour JIRA
│   │   └── confluence_llm_enrichment_summary.md # Résumé LLM pour Confluence
│   ├── compression_report_fr.txt           # Statistiques de compression (si activée)
│   ├── global_arborescence.txt             # Arborescence globale
│   └── ...
```

## 🧠 Résumés LLM automatiques

> 📝 **Fonctionnalité avancée**: Pour chaque traitement utilisant un LLM, un rapport de résumé est automatiquement généré au format Markdown.

> 💡 **NOUVEAU!** Notre module `outlines_enricher.py` enrichit désormais chaque élément JSON (tickets JIRA/pages Confluence) avec des analyses LLM avancées. Pour chaque élément, il extrait le contenu textuel (titre, description, commentaires), l'envoie à l'API OpenAI (GPT-4-0125-preview), et récupère une analyse structurée contenant: un résumé concis (150 mots max), 5-10 mots-clés importants, les entités identifiées (personnes, organisations, termes techniques) et le sentiment général. Ces données sont ajoutées sous la clé `analysis` avec les sous-champs `llm_summary`, `llm_keywords`, `llm_entities` et `llm_sentiment`. Le module adapte automatiquement différentes structures JSON pour assurer une liste `items` correcte avant traitement.

Exemple de résumé généré:

<details>
<summary>👉 Voir un exemple de résumé LLM (cliquez pour développer)</summary>

```markdown
# Résumé de l'enrichissement LLM

## Informations générales
- Date d'analyse: 2023-05-08 23:34:37
- Nombre total d'éléments analysés: 42
- Modèle LLM utilisé: gpt-4

## Analyse
### Mots-clés principaux extraits
projet, développement, API, backend, utilisateur, interface, base de données

### Distribution des sentiments
{'positive': 12, 'neutral': 25, 'negative': 5}

### Exemple d'enrichissement
**Ticket**: NEXUS-123 - Implémentation de l'authentification OAuth2
**Résumé LLM**: Ce ticket concerne l'intégration du protocole OAuth2 pour sécuriser l'API. L'implémentation comprend l'enregistrement des clients, la gestion des tokens et la gestion des périmètres d'accès. L'équipe a noté des défis avec la persistance des tokens de rafraîchissement, mais les a résolus grâce à une table de base de données dédiée. Les tests montrent une intégration réussie avec l'application frontend. Prêt pour révision par l'équipe de sécurité avant le déploiement final en production.
**Mots-clés**: OAuth2, authentification, sécurité API, tokens, enregistrement client
**Entités**: Jean Dupont (développeur), Équipe de Sécurité, protocole OAuth2, JWT
**Sentiment**: Positif
```

</details>

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

| Niveau | Configuration | Fonctionnalités |
|--------|--------------|-----------------|
| **1** | Outlines + OpenAI | Extraction structurée complète, réparation automatique |
| **2** | Sans OpenAI | Mode dégradé d'Outlines, certaines fonctionnalités désactivées |
| **3** | Sans Outlines | Utilisation de stubs internes imitant l'API d'Outlines |
| **4** | Fallback standard | Parseur JSON standard en dernier recours |

Cette architecture garantit que le système reste opérationnel même sans connexion internet ou clé API.

## 🔄 Traitement JSON robuste

Le système inclut des capacités avancées de traitement JSON pour gérer les fichiers JSON malformés ou invalides :

- **Parsing robuste** : Multiples mécanismes de fallback pour gérer les fichiers JSON malformés
- **Réparation intelligente** : Capacité à récupérer des erreurs de format JSON courantes
- **Réparation assistée par LLM** : Utilisation optionnelle de LLM pour corriger des problèmes structurels complexes
- **Parsing progressif** : Peut traiter des fichiers extrêmement volumineux en les lisant par morceaux
- **Tolérance aux pannes** : Le système continue le traitement même si certains fichiers contiennent des erreurs

Dans nos derniers tests, le système a traité avec succès les fichiers de démonstration du projet NEXUS qui contenaient plusieurs incohérences de formatage, sans nécessiter d'intervention manuelle.

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

3. **clean_sensitive_data.py** : Nettoyer les données sensibles (clés API, emails, etc.)
   ```bash
   python -m tools.clean_sensitive_data fichier.json --output fichier_clean.json
   ```

4. **compress_utils.py** : Compresser et optimiser les fichiers JSON avec zstd et orjson
   ```bash
   python -m extract.compress_utils --directory results/mes_donnees --level 19
   ```

### Utilisation des outils dans le CLI

Les outils sont intégrés au CLI principal et peuvent être utilisés de manière interactive :

```bash
# Lancer le nettoyage des données sensibles via le CLI
python -m cli.cli clean fichier.json --output fichier_clean.json

# Compresser des fichiers JSON via le CLI
python -m cli.cli compress results/mes_donnees --level 19

# Utiliser le mode interactif
python -m cli.cli interactive
# Puis sélectionner "Nettoyer les données sensibles (clean)" ou "Compresser et optimiser des fichiers JSON"
```

### Intégration programmatique

Les outils peuvent également être importés et utilisés directement dans votre code :

```python
# Vérifier la validité d'un fichier JSON
from tools import validate_file
is_valid, error_msg = validate_file("mon_fichier.json")
if not is_valid:
    print(f"Erreur dans le fichier: {error_msg}")

# Nettoyer les données sensibles
from tools import clean_json_file
clean_json_file("fichier_avec_api_keys.json", "fichier_securise.json")

# Corriger les chemins dupliqués
from tools import fix_duplicate_paths
fix_duplicate_paths("dossier_résultats")
```

Le traitement principal via `GenericJsonProcessor` intègre automatiquement ces outils pour vérifier la validité des fichiers JSON et nettoyer les données sensibles avant sauvegarde.

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
      "model": "gpt-4o",
      "enrichment_date": "DATE_ENRICHISSEMENT"
    }
  }
}
```

## 📄 Analyse de documents PDF

> 🔍 **NOUVEAU!** Le système inclut désormais un extracteur PDF intelligent qui combine extraction native de texte et analyse IA des images.

### Fonctionnalités de l'extracteur PDF

L'Extracteur PDF Complet est un module spécialisé conçu pour extraire et analyser intelligemment le contenu des documents PDF. Contrairement aux extracteurs PDF traditionnels, ce module:

1. **Extrait nativement** le texte brut du PDF, préservant sa structure originale
2. **Détecte et extrait** uniquement les images intégrées dans le document
3. **Analyse avec IA** exclusivement les images pour une compréhension enrichie 
4. **Génère un JSON unifié** combinant le texte extrait et les analyses d'images

Cette approche ciblée évite de transformer toutes les pages en images, ce qui préserve la qualité du texte natif tout en permettant une compréhension améliorée par IA des éléments visuels.

### Utilisation via CLI

```bash
# Mode interactif
python -m cli.cli interactive
# Puis sélectionner "Extraction complète d'un PDF (texte + images analysées)"

# OU commande directe
python -m cli.cli extract-images complete chemin/vers/fichier.pdf --max-images 10
```

### Structure du JSON unifié

Pour chaque PDF traité, vous obtiendrez un JSON structuré contenant:

- Métadonnées du document (nom, timestamp, langue)
- Texte brut de chaque page
- Éléments structurés par page (texte et images)
- Descriptions IA pour chaque image avec contexte
- Statistiques générales (pages, images détectées, images analysées)

### Exemples d'applications

- **Analyse de documents techniques**: Extraction du contenu textuel avec enrichissement IA des diagrammes et figures
- **Documentation juridique**: Préservation de la structure exacte du texte avec analyse des signatures et tampons
- **Rapports financiers**: Extraction des données textuelles avec compréhension IA des graphiques et tableaux
- **Publications scientifiques**: Conservation du texte structuré avec analyse des formules et illustrations

### Documentation complète

Une documentation détaillée est disponible dans le dossier [`/documentation/pdf/`](documentation/pdf/) avec:

- Guide d'utilisation complet en français et anglais
- Exemples de commandes avancées
- Description détaillée de la structure de sortie
- Guide de dépannage

## 🚀 API

DataFlow AI inclut une API RESTful robuste construite avec FastAPI qui fournit un accès programmatique à toutes les fonctionnalités de traitement et d'analyse de données.

### Fonctionnalités clés de l'API

- **Architecture RESTful** - Méthodes HTTP standards avec réponses JSON cohérentes
- **Documentation interactive** - Interface Swagger générée automatiquement à `/docs`
- **Endpoints flexibles** - Accès complet à toutes les fonctionnalités de traitement
- **Téléversements sécurisés** - Validation des fichiers et stockage temporaire sécurisé
- **Support Cross-Origin** - CORS configuré pour les applications web
- **Traitement asynchrone** - Opérations non bloquantes pour de meilleures performances

### Endpoints principaux

- **Traitement PDF** - Extraction de texte et analyse d'images des documents PDF
- **Traitement JSON** - Nettoyage, compression et transformation des données JSON
- **Traitement unifié** - Traitement et correspondance des données JIRA et Confluence

Pour la documentation complète, consultez le dossier [Documentation API](documentation/api/).

## 💻 Frontend

DataFlow AI inclut une interface web moderne construite avec React et TypeScript qui fournit un moyen convivial d'accéder à toutes les fonctionnalités du système.

### Fonctionnalités du Frontend

- **Interface moderne** - Interface propre et responsive utilisant React et Tailwind CSS
- **Multilingue** - Support complet pour le français et l'anglais
- **Modes clair/sombre** - Personnalisation du thème selon les préférences de l'utilisateur
- **Glisser-déposer** - Téléversement et traitement intuitifs des fichiers
- **Workflow interactif** - Guidage étape par étape à travers les options de traitement
- **Visualisation des résultats** - Présentation claire des résultats de traitement

### Écrans principaux

- **Analyse PDF** - Téléversement et traitement de documents PDF avec analyse d'images par IA
- **Traitement JSON** - Nettoyage, compression et découpage de fichiers JSON
- **Traitement unifié** - Correspondance et traitement des données JIRA et Confluence

Pour la documentation complète, consultez le dossier [Documentation Frontend](documentation/frontend/).

## 🔒 Sécurité

### Bonnes pratiques de sécurité

Ce projet inclut des mesures de protection pour éviter la fuite de données sensibles :

#### 🚫 Ne jamais commiter de données sensibles
- **Clés API** (AWS, OpenAI, etc.)
- **Informations personnelles** (emails, noms, etc.)
- **Données de test réelles**
- **Tokens d'authentification**
- **Identifiants de connexion**

#### ✅ Manipulation des données sensibles
1. **Variables d'environnement** : Toujours stocker les clés API dans le fichier `.env` (jamais dans le code)
2. **Données de test** : Utiliser uniquement des données synthétiques ou anonymisées
3. **Protection du Git** : Un hook pre-commit détecte automatiquement les fuites potentielles

#### 🧹 Nettoyage des données sensibles
Le projet inclut un outil pour nettoyer les fichiers de test :

```bash
# Nettoyer un fichier spécifique
python -m tools.clean_sensitive_data path/to/file.json

# Nettoyer un dossier
python -m tools.clean_sensitive_data path/to/directory --output path/to/output
```

#### 🚨 En cas de fuite
1. **Éliminer** la donnée sensible de l'historique Git
   ```bash
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch path/to/file" --prune-empty --tag-name-filter cat -- --all
   git push origin --force
   ```
2. **Invalider** les clés ou tokens compromis
3. **Informer** les personnes concernées

Pour plus de détails, consultez le fichier [SECURITY.md](SECURITY.md).

## ⚠️ Dépendances

- Python 3.8+
- typer, rich, inquirer, python-dotenv, ijson
- openai (optionnel, pour les fonctionnalités LLM)
- outlines==0.2.3 (optionnel, pour l'extraction structurée)
- zstandard, orjson (optionnel, pour la compression et l'optimisation JSON)

## 📜 Licence

Ce projet est distribué sous licence MIT. 