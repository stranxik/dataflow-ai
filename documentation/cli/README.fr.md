# CLI pour le traitement et l'analyse de données JSON

Ce CLI offre une interface puissante pour traiter, analyser et transformer des fichiers JSON provenant de différentes sources (JIRA, Confluence, GitHub, etc.), en préparation pour l'indexation dans un système RAG avec Llamendex.

## 🎯 Fonctionnalités principales

- **Mode interactif complet** : Assistant guidé pour toutes les opérations (traitement, découpage, matching, flux unifié)
- **Détection automatique** de type de fichier (JIRA, Confluence, GitHub)
- **Transformation flexible** via des mappings personnalisables
- **Découpage et traitement de fichiers volumineux** (`chunks`)
- **Extraction de métadonnées** structurées
- **Établissement de correspondances** entre différentes sources
- **Enrichissement par LLM** (OpenAI) pour l'analyse sémantique
- **Interface interactive** pour faciliter l'utilisation et la navigation dans les fichiers
- **Organisation des résultats** avec timestamps uniques pour chaque exécution
- **Arborescences détaillées** du contenu de chaque fichier traité
- **Gestion robuste** des fichiers JSON mal formatés ou incomplets
- **Support des variables d'environnement** pour la configuration

## 🚀 Installation

1. Clonez ce dépôt et accédez au dossier
2. Créez un fichier `.env` en copiant `.env.example`
3. Installez les dépendances :

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

Configurez l'outil via le fichier `.env` :

```
# Paramètres généraux
MAPPINGS_DIR=extract/mapping_examples
OUTPUT_DIR=output

# Paramètres LLM
OPENAI_API_KEY=votre_cle_api_openai
DEFAULT_LLM_MODEL=gpt-4.1
LLM_MODELS=gpt-4.1,gpt-3.5-turbo,o3,gpt-4
```

## 📖 Guide d'utilisation

### Mode interactif (recommandé)

Lancez l'assistant complet qui vous guide étape par étape :

```bash
python -m cli.cli interactive
```

Vous pourrez :
- Choisir le type d'opération (traitement, découpage, matching, flux complet)
- Naviguer dans vos dossiers pour sélectionner les fichiers
- Créer ou choisir un mapping
- Définir les options avancées (LLM, limites, etc.)
- Visualiser un récapitulatif avant chaque action
- Recevoir une notification claire à la fin de chaque étape
- Savoir exactement où sont générés les fichiers de résultats

### Commande `chunks` - Découpage et traitement de fichiers volumineux

Découpez un gros fichier JSON en morceaux plus petits, puis traitez chaque morceau automatiquement :

```bash
python -m cli.cli chunks mon_gros_fichier.json --output-dir dossier_morceaux --items-per-file 500 --process --mapping extract/mapping_examples/jira_mapping.json --llm
```

- Les morceaux sont créés dans le dossier `results/dossier_morceaux_YYYY-MM-DD-HH-MM-SS/`
- Les fichiers traités sont placés dans un sous-dossier `processed/`
- Chaque fichier génère sa propre arborescence détaillant sa structure
- Une notification de fin et un récapitulatif sont affichés

### Commande `process` - Traitement de fichiers JSON individuels

```bash
python -m cli.cli process mon_fichier.json --output resultat.json
```

Options principales :

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Fichier de sortie (défaut: `results/{input}_processed_YYYY-MM-DD-HH-MM-SS.json`) |
| `--mapping`, `-m` | Fichier de mapping à utiliser |
| `--detect/--no-detect` | Active/désactive la détection automatique du type de fichier |
| `--llm/--no-llm` | Active/désactive l'enrichissement LLM |
| `--model` | Modèle LLM à utiliser |
| `--interactive`, `-i` | Mode interactif pour les choix |
| `--max` | Nombre maximum d'éléments à traiter |

### Commande `match` - Correspondances JIRA ↔ Confluence

```bash
python -m cli.cli match jira_processed.json confluence_processed.json --output-dir resultats_match
```

Options principales :

| Option | Description |
|--------|-------------|
| `--output-dir`, `-o` | Répertoire de sortie (génère `results/resultats_match_YYYY-MM-DD-HH-MM-SS/`) |
| `--min-score`, `-s` | Score minimum pour les correspondances |
| `--llm-assist` | Utiliser un LLM pour améliorer les correspondances |

### Commande `unified` - Flux complet (JIRA + Confluence + Matching)

```bash
python -m cli.cli unified jira1.json jira2.json --confluence conf1.json conf2.json --output-dir resultats_complets
```

Options principales :

| Option | Description |
|--------|-------------|
| `--confluence`, `-c` | Fichiers Confluence à traiter |
| `--output-dir`, `-o` | Répertoire de sortie (génère `results/resultats_complets_YYYY-MM-DD-HH-MM-SS/`) |
| `--min-score`, `-s` | Score minimum pour les correspondances |
| `--max` | Nombre maximum d'éléments à traiter par fichier |
| `--llm` | Active l'enrichissement LLM |
| `--skip-matching` | Désactive le matching entre JIRA et Confluence |

## 🔍 Navigation interactive et expérience utilisateur

- Sélection des fichiers/dossiers via un navigateur interactif (plus besoin de taper les chemins)
- Création de mapping personnalisé via éditeur intégré
- Récapitulatif avant chaque action
- Notifications de fin de traitement et affichage du dossier de sortie

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
│   ├── jira1_arborescence_20230830_142255.txt  # Arborescence détaillée du fichier jira1.json
│   └── confluence1_arborescence_20230830_142255.txt  # Arborescence détaillée du fichier confluence1.json
├── chunks_fichier1_2023-08-31-09-15-20/    # Dossier d'une exécution chunks
│   ├── part1.json                          # Premier morceau
│   ├── fichier1_arborescence.txt           # Arborescence du fichier source
│   └── ...
└── fichier2_processed_2023-08-31-10-45-30.json  # Résultat d'une exécution process
```

## 📝 Arborescence des fichiers

Pour chaque fichier traité, une arborescence détaillée est générée, montrant :

- Les informations sur le fichier (nom, taille, date de traitement)
- Le type de structure (object ou array)
- Les clés principales pour les objets
- Un aperçu du premier élément pour les tableaux
- La structure complète du contenu avec exemples de valeurs
- Gestion robuste des fichiers partiellement corrompus ou mal formatés

Ces arborescences vous permettent de comprendre rapidement le contenu et la structure des fichiers JSON, ce qui facilite la création de mappings et le débogage.

## 🧩 Extension

Pour ajouter de nouveaux types de fichiers :
1. Créez un fichier de mapping dans `mapping_examples/`
2. Adaptez la détection dans `detect_file_type()`
3. Utilisez la commande `process` ou le mode interactif avec votre nouveau mapping

## ⚠️ Dépendances

- Python 3.8+
- typer, rich, inquirer, python-dotenv, ijson, openai

## 📜 Licence

Ce projet est distribué sous la Polyform Small Business License 1.0.0.

[![License: Polyform-SBL](https://img.shields.io/badge/license-Polyform_SBL-blue.svg)](LICENSE)

Pour les détails complets de la licence, consultez le fichier [LICENSE](LICENSE).
