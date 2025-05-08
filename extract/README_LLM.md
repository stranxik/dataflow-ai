# Enrichissement LLM avec Outlines pour Llamendex

## Aperçu

Ce module intègre les capacités d'enrichissement LLM via deux mécanismes principaux :

1. **Outlines Framework** : Utilisation du framework Outlines pour l'extraction structurée et la génération contrôlée
2. **Implémentation personnalisée** : Notre propre implémentation d'enrichissement LLM

Ces enrichissements permettent de transformer les données brutes de JIRA et Confluence en données plus riches pour Llamendex.

## Enrichissements effectués

Pour chaque document (ticket JIRA ou page Confluence), nous réalisons les enrichissements suivants :

1. **Résumé automatique** (`llm_summary`) : Génération d'un résumé concis et informatif
2. **Extraction de mots-clés** (`llm_keywords`) : Identification des termes et concepts clés  
3. **Reconnaissance d'entités** (`llm_entities`) :
   - Personnes
   - Organisations
   - Lieux
   - Termes techniques
4. **Analyse de sentiment** (`llm_sentiment`) : Classification en "positive", "neutral", "negative"

## Architecture technique

### Intégration Outlines

Le module `outlines_integration.py` fournit :

- Une détection automatique d'Outlines avec installation fallback
- Une intégration avec le modèle `OpenAI` d'Outlines
- Des grammmaires personnalisées pour l'extraction structurée
- Des fallbacks robustes en cas d'échec

### Generic JSON Processor

Le `GenericJsonProcessor` utilise le LLM pour :

- Réparer des JSON mal formés (`use_llm_fallback`)
- Enrichir les données avec des analyses additionnelles
- Extraire des mots-clés et des méta-informations

### Utilisation dans Llamendex

Les enrichissements LLM préparent les données pour Llamendex en :

1. **Améliorant la recherche** : Les résumés et mots-clés permettent de meilleures correspondances sémantiques
2. **Facilitant le filtrage** : Les entités et sentiments permettent un filtrage avancé
3. **Optimisant les résultats** : Les résumés générés par LLM donnent un aperçu concis sans lecture complète

## Modèles utilisés

- **OpenAI GPT-4** : Modèle principal pour l'enrichissement
- **OpenAI GPT-3.5-Turbo** : Fallback pour les tâches moins complexes (optionnel)

## Configuration

La configuration des modèles LLM se fait via :

1. Le fichier `.env` qui définit :
   - `OPENAI_API_KEY` : Clé API OpenAI
   - `DEFAULT_LLM_MODEL` : Modèle par défaut (gpt-4.1)
   - `LLM_MODELS` : Liste des modèles disponibles

2. Options CLI (activées par défaut) :
   - `--with-openai` : Active l'enrichissement LLM (défaut: ON)
   - `--no-openai` : Désactive l'enrichissement LLM
   - `--model` : Spécifie un modèle particulier

## Artefacts générés

Plusieurs fichiers sont générés lors de l'utilisation du LLM :

1. **Fichiers enrichis** :
   - `enriched_jira.json`
   - `enriched_confluence.json`

2. **Résumés d'enrichissement** :
   - `llm_enrichment_summary.md` : Résumé des enrichissements et statistiques

## Exemples d'utilisation

### Commande CLI avec enrichissement LLM

L'enrichissement LLM est activé par défaut dans la commande unifiée :

```bash
python -m cli.cli unified --jira-files CARTAN_jira.json --confluence-files hollard_confluence.json
```

Pour le désactiver explicitement :

```bash
python -m cli.cli unified --jira-files CARTAN_jira.json --confluence-files hollard_confluence.json --no-llm
```

### Format d'enrichissement JSON

```json
{
  "id": "TICKET-123",
  "title": "Problème avec l'API de paiement",
  "content": "...",
  "analysis": {
    "llm_summary": "Problème d'intégration avec l'API de paiement Stripe causant des échecs de transaction pour certains clients.",
    "llm_keywords": ["API", "paiement", "Stripe", "échec", "transaction", "intégration"],
    "llm_entities": {
      "people": ["John Smith"],
      "organizations": ["Stripe"],
      "technical_terms": ["API", "webhook", "authentication"]
    },
    "llm_sentiment": "negative"
  }
}
```
