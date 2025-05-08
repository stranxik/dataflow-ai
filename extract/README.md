# JSON Processor - Solution générique pour l'analyse et la transformation

## 🎯 Objectif principal

Cette solution a été conçue pour structurer et unifier des sources de données diverses (JIRA, Confluence, Google Drive, Git) pour un système RAG avancé avec **Llamendex**. Chaque source suit un pipeline commun, mais avec une logique d'adaptation spécifique pour maximiser la qualité de l'indexation sémantique et structurelle.

**Le but concret :**
- Extraire les métadonnées structurées de différents formats JSON
- Créer un arbre hiérarchique bien typé pour chaque source
- Établir des correspondances (matching) entre les différentes sources (JIRA ↔ Confluence ↔ Drive ↔ Git)
- Préparer les données au format `NodeWithScore` pour Llamendex, incluant le graphe de relations

## 📂 Contenu du dossier `extract`

Voici les principaux fichiers et leur fonction :

### Script principal générique
- `generic_json_processor.py` : Solution universelle pour traiter n'importe quel JSON

### Scripts spécialisés
- **JIRA** :
  - `extract_jira_structure.py` : Extraction et analyse de structure
  - `transform_for_llm.py` : Transformation de données spécifiques à JIRA
  - `analyze_jira_export.py` : Analyse des exports JIRA

- **Confluence** :
  - `extract_confluence_structure.py` : Extraction et transformation de pages Confluence

### Utilitaires
- `process_by_chunks.py` : Gestion de fichiers JSON volumineux
- `match_jira_confluence.py` : Mise en correspondance JIRA-Confluence
- `run_analysis.py` : Orchestration du flux pour JIRA uniquement
- `run_unified_analysis.py` : Orchestration du flux complet JIRA + Confluence

## 🔍 Approche générique

L'approche adoptée ici permet de traiter n'importe quelle structure JSON, grâce à :

1. **Détection automatique de structure** : Analyse et détection des champs importants
2. **Mappers personnalisables** : Adaptation à n'importe quel format d'entrée
3. **Traitement par morceaux** : Gestion efficace de fichiers volumineux
4. **Transformation flexible** : Structure de sortie adaptable selon les besoins

## 📖 Guide d'utilisation pratique

Voici comment utiliser concrètement cette solution pour vos fichiers JIRA et Confluence.

### 1. Traitement basique

```bash
python generic_json_processor.py --input mon_fichier.json --output resultat.json
```

### 2. Avec un mapping personnalisé

Créez un fichier JSON de mapping (ex: `mapping.json`):
```json
{
  "id": "key",
  "title": ["title", "name", "subject"],
  "content": {
    "field": "description",
    "transform": "clean_text"
  },
  "keywords": {
    "field": "description",
    "transform": "extract_keywords"
  }
}
```

Puis utilisez-le:
```bash
python generic_json_processor.py --input mon_fichier.json --output resultat.json --mapping-file mapping.json
```

### 3. Pour les fichiers volumineux

```bash
python process_by_chunks.py split --input gros_fichier.json --output-dir dossier_morceaux --items-per-file 500
```

Puis traitez chaque morceau:
```bash
for fichier in dossier_morceaux/*.json; do
  python generic_json_processor.py --input "$fichier" --output "$(basename "$fichier" .json)_processed.json"
done
```

### 4. Traitement de plusieurs fichiers d'une même source

Vous pouvez traiter plusieurs fichiers JIRA ou Confluence séquentiellement :

```bash
# Plusieurs fichiers JIRA
for file in jira_*.json; do
  output="${file%.json}_processed.json"
  python generic_json_processor.py --input "$file" --output "$output" --mapping-file mapping_examples/jira_mapping.json
done

# Plusieurs fichiers Confluence
for file in confluence_*.json; do
  output="${file%.json}_processed.json"
  python generic_json_processor.py --input "$file" --output "$output" --mapping-file mapping_examples/confluence_mapping.json
done
```

### 5. Workflow complet JIRA + Confluence

Pour traiter plusieurs fichiers JIRA et Confluence en même temps et établir des correspondances :

```bash
python run_unified_analysis.py --jira-files jira1.json jira2.json --confluence-files confluence1.json confluence2.json --output-dir resultats
```

Cette commande :
- Traite tous les fichiers JIRA spécifiés
- Traite tous les fichiers Confluence spécifiés
- Établit des correspondances entre eux
- Sauvegarde tous les résultats dans le dossier `resultats`

### 6. Établir des correspondances après traitement individuel

Si vous avez déjà traité vos fichiers séparément :

```bash
python match_jira_confluence.py --jira jira_processed.json --confluence confluence_processed.json --output matches.json --updated-jira jira_with_matches.json --updated-confluence confluence_with_matches.json
```

### 7. Scénarios d'utilisation courants

#### Scénario 1 : Extraction et analyse d'un export JIRA

```bash
# Étape 1: Extraction de la structure
python extract_jira_structure.py mon_export_jira.json

# Étape 2: Transformation pour LLM
python transform_for_llm.py --files mon_export_jira.json --output jira_llm_ready.json

# Étape 3 (optionnel): Analyse avec OpenAI
python analyze_jira_export.py --api-key VOTRE_CLE_API
```

#### Scénario 2 : Intégrer un nouveau type de données

```bash
# Étape 1: Créer un fichier de mapping pour la nouvelle source
echo '{
  "id": "issueId", 
  "title": "summary",
  "content": {"field": "description", "transform": "clean_text"},
  "metadata": {
    "created_by": "authorName",
    "created_at": "creationDate"
  }
}' > nouveau_systeme_mapping.json

# Étape 2: Traiter le fichier avec ce mapping
python generic_json_processor.py --input nouveau_systeme.json --output nouveau_traite.json --mapping-file nouveau_systeme_mapping.json
```

## 📊 Structure des résultats générés

Après traitement, votre dossier de résultats contiendra :

- **Fichiers de structure détectée** :
  - `jira_structure.json` : Structure détectée des fichiers JIRA
  - `confluence_structure.json` : Structure détectée des fichiers Confluence

- **Données transformées pour Llamendex** :
  - `llm_ready_jira.json` : Données JIRA transformées
  - `llm_ready_confluence.json` : Données Confluence transformées

- **Correspondances et relations** :
  - `jira_confluence_matches.json` : Correspondances détectées
  - `jira_with_matches.json` : Données JIRA enrichies avec liens
  - `confluence_with_matches.json` : Données Confluence enrichies avec liens

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

## 🔄 Intégration avec Temporal

Pour intégrer cette solution dans vos workflows Temporal :

```javascript
// Exemple simplifié d'activité Temporal en JavaScript
export async function syncJiraAndIndex(ctx) {
  // 1. Exécuter le traitement JIRA
  const processOutput = await executeCommand(
    'python', 
    ['run_analysis.py', '--files', 'export_jira.json', '--output-dir', 'jira_processed']
  );
  
  // 2. Lire les résultats transformés
  const processedData = await fs.readFile('jira_processed/llm_ready_jira.json', 'utf8');
  
  // 3. Mettre à jour l'index Llamendex avec les données transformées
  await llamendexClient.updateIndex('JiraIndex', JSON.parse(processedData));
  
  return { status: 'completed', ticketsProcessed: processedData.items.length };
}
```

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
- dotenv, ijson, openai
- Modules standards (json, os, datetime, etc.) 