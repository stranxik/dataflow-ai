#!/usr/bin/env python3
"""
Module utilitaire pour générer des résumés des enrichissements LLM
"""

import os
import json
from datetime import datetime

def generate_llm_summary(output_dir, jira_data=None, confluence_data=None, data=None, filename="llm_enrichment_summary.md"):
    """
    Génère un fichier résumé des enrichissements LLM effectués.
    Ce fichier sert de preuve de l'utilisation des capacités LLM et résume
    les types d'analyses effectuées.
    
    Args:
        output_dir: Répertoire de sortie
        jira_data: Données JIRA enrichies (optionnel)
        confluence_data: Données Confluence enrichies (optionnel)
        data: Données génériques enrichies si jira/confluence non fournies (optionnel)
        filename: Nom du fichier de sortie (par défaut: llm_enrichment_summary.md)
    
    Returns:
        Le chemin du fichier résumé généré
    """
    summary_file = os.path.join(output_dir, filename)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Vérifier si nous avons au moins une source de données
    if not jira_data and not confluence_data and not data:
        content = f"""# Résumé de l'enrichissement LLM

## Informations générales
- Date de l'analyse: {timestamp}
- AUCUNE DONNÉE ENRICHIE TROUVÉE

⚠️ Aucune donnée enrichie par LLM n'a été trouvée. Vérifiez que:
1. L'option d'enrichissement LLM est activée (--with-openai ou --llm)
2. Une clé API OpenAI valide est disponible
3. Les fichiers d'entrée contiennent des données valides
"""
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return summary_file
    
    # Traitement des données génériques si fournies à la place de jira/confluence
    if data and not jira_data and not confluence_data:
        return _generate_generic_summary(output_dir, data, summary_file, timestamp)
    
    # Extraire des statistiques
    jira_items_count = len(jira_data.get("items", [])) if jira_data else 0
    confluence_items_count = len(confluence_data.get("items", [])) if confluence_data else 0
    
    # Exemples d'enrichissement
    jira_example = None
    jira_keywords = []
    jira_sentiment = {}
    
    confluence_example = None
    confluence_keywords = []
    confluence_sentiment = {}
    
    # Collecter des statistiques sur les tickets JIRA
    if jira_data:
        for item in jira_data.get("items", [])[:20]:  # Limiter à 20 pour l'analyse
            if "analysis" in item:
                # Vérifier si nous avons des enrichissements LLM (deux formats possibles)
                llm_data = None
                if "llm" in item["analysis"]:
                    llm_data = item["analysis"]["llm"]
                elif any(k.startswith("llm_") for k in item["analysis"].keys()):
                    llm_data = {k.replace("llm_", ""): v for k, v in item["analysis"].items() if k.startswith("llm_")}
                
                if llm_data:
                    if not jira_example and "summary" in llm_data:
                        jira_example = {
                            "id": item.get("id", "Unknown"),
                            "title": item.get("title", "No title"),
                            "summary": llm_data["summary"]
                        }
                    
                    # Collecter les mots-clés uniques
                    if "keywords" in llm_data:
                        jira_keywords.extend(llm_data["keywords"])
                    
                    # Compter les sentiments
                    if "sentiment" in llm_data:
                        sentiment = llm_data["sentiment"]
                        jira_sentiment[sentiment] = jira_sentiment.get(sentiment, 0) + 1
    
    # Collecter des statistiques sur les pages Confluence
    if confluence_data:
        for item in confluence_data.get("items", [])[:20]:  # Limiter à 20 pour l'analyse
            if "analysis" in item:
                # Vérifier si nous avons des enrichissements LLM (deux formats possibles)
                llm_data = None
                if "llm" in item["analysis"]:
                    llm_data = item["analysis"]["llm"]
                elif any(k.startswith("llm_") for k in item["analysis"].keys()):
                    llm_data = {k.replace("llm_", ""): v for k, v in item["analysis"].items() if k.startswith("llm_")}
                
                if llm_data:
                    if not confluence_example and "summary" in llm_data:
                        confluence_example = {
                            "id": item.get("id", "Unknown"),
                            "title": item.get("title", "No title"),
                            "summary": llm_data["summary"]
                        }
                    
                    # Collecter les mots-clés uniques
                    if "keywords" in llm_data:
                        confluence_keywords.extend(llm_data["keywords"])
                    
                    # Compter les sentiments
                    if "sentiment" in llm_data:
                        sentiment = llm_data["sentiment"]
                        confluence_sentiment[sentiment] = confluence_sentiment.get(sentiment, 0) + 1
    
    # Limiter et dédupliquer les mots-clés
    jira_keywords = list(set(jira_keywords))[:15]  # Top 15 mots-clés uniques
    confluence_keywords = list(set(confluence_keywords))[:15]  # Top 15 mots-clés uniques
    
    # Déterminer le modèle utilisé
    model_used = "inconnu"
    if jira_data and "metadata" in jira_data and "llm_enrichment" in jira_data["metadata"]:
        model_used = jira_data["metadata"]["llm_enrichment"].get("model", "inconnu")
    elif confluence_data and "metadata" in confluence_data and "llm_enrichment" in confluence_data["metadata"]:
        model_used = confluence_data["metadata"]["llm_enrichment"].get("model", "inconnu")
    
    # Créer le contenu du fichier
    content = f"""# Résumé de l'enrichissement LLM

## Informations générales
- Date d'analyse: {timestamp}
- Nombre total de tickets JIRA analysés: {jira_items_count}
- Nombre total de pages Confluence analysées: {confluence_items_count}
- Modèle LLM utilisé: {model_used}
"""
    
    if jira_items_count > 0:
        content += """
## Analyse JIRA

### Mots-clés principaux extraits
"""
        content += f"{', '.join(jira_keywords) if jira_keywords else 'Aucun mot-clé extrait'}\n"
        
        content += """
### Distribution des sentiments
"""
        content += f"{str(jira_sentiment) if jira_sentiment else 'Aucune analyse de sentiment'}\n"
        
        content += """
### Exemple d'enrichissement
"""
        
        if jira_example:
            content += f"""
**Ticket**: {jira_example['id']} - {jira_example['title']}
**Résumé LLM**: {jira_example['summary']}
"""
        else:
            content += "Aucun exemple disponible\n"
    
    if confluence_items_count > 0:
        content += """
## Analyse Confluence

### Mots-clés principaux extraits
"""
        content += f"{', '.join(confluence_keywords) if confluence_keywords else 'Aucun mot-clé extrait'}\n"
        
        content += """
### Distribution des sentiments
"""
        content += f"{str(confluence_sentiment) if confluence_sentiment else 'Aucune analyse de sentiment'}\n"
        
        content += """
### Exemple d'enrichissement
"""
        
        if confluence_example:
            content += f"""
**Page**: {confluence_example['id']} - {confluence_example['title']}
**Résumé LLM**: {confluence_example['summary']}
"""
        else:
            content += "Aucun exemple disponible\n"
    
    content += """
## Utilisation pour Llamendex

Les données enrichies par LLM sont prêtes pour ingestion dans Llamendex avec:
1. Des résumés concis du contenu
2. Des mots-clés thématiques
3. Des entités extraites (personnes, organisations)
4. Une analyse de sentiment

Ces enrichissements améliorent considérablement la qualité des résultats de recherche
et permettent des fonctionnalités avancées comme le filtrage par sentiment ou 
la recherche par entités.
"""
    
    # Écrire le contenu dans le fichier
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Résumé de l'enrichissement LLM généré dans {summary_file}")
    return summary_file

def _generate_generic_summary(output_dir, data, summary_file, timestamp):
    """
    Génère un résumé pour des données génériques (non JIRA/Confluence)
    """
    # Déterminer le type de données (liste ou dictionnaire avec 'items')
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "items" in data:
        items = data.get("items", [])
    elif isinstance(data, dict) and "tickets" in data:
        items = data.get("tickets", [])
    elif isinstance(data, dict) and "pages" in data:
        items = data.get("pages", [])
    
    # Statistiques de base
    items_count = len(items)
    
    # Exemples d'enrichissement et statistiques
    example = None
    keywords = []
    sentiment = {}
    
    # Collecter des informations sur les éléments enrichis
    for item in items[:20]:  # Limiter à 20 pour l'analyse
        if "analysis" in item:
            # Vérifier si nous avons des enrichissements LLM (deux formats possibles)
            llm_data = None
            if "llm" in item["analysis"]:
                llm_data = item["analysis"]["llm"]
            elif any(k.startswith("llm_") for k in item["analysis"].keys()):
                llm_data = {k.replace("llm_", ""): v for k, v in item["analysis"].items() if k.startswith("llm_")}
            
            if llm_data:
                if not example and "summary" in llm_data:
                    example = {
                        "id": item.get("id", "Unknown"),
                        "title": item.get("title", item.get("name", "No title")),
                        "summary": llm_data["summary"]
                    }
                
                # Collecter les mots-clés uniques
                if "keywords" in llm_data:
                    keywords.extend(llm_data["keywords"])
                
                # Compter les sentiments
                if "sentiment" in llm_data:
                    sentiment_value = llm_data["sentiment"]
                    sentiment[sentiment_value] = sentiment.get(sentiment_value, 0) + 1
    
    # Limiter et dédupliquer les mots-clés
    keywords = list(set(keywords))[:15]  # Top 15 mots-clés uniques
    
    # Déterminer le modèle utilisé
    model_used = "inconnu"
    if isinstance(data, dict) and "metadata" in data and "llm_enrichment" in data["metadata"]:
        model_used = data["metadata"]["llm_enrichment"].get("model", "inconnu")
    
    # Créer le contenu du fichier
    content = f"""# Résumé de l'enrichissement LLM

## Informations générales
- Date d'analyse: {timestamp}
- Nombre total d'éléments analysés: {items_count}
- Modèle LLM utilisé: {model_used}

## Analyse

### Mots-clés principaux extraits
{', '.join(keywords) if keywords else "Aucun mot-clé extrait"}

### Distribution des sentiments
{str(sentiment) if sentiment else "Aucune analyse de sentiment"}

### Exemple d'enrichissement
"""
    
    if example:
        content += f"""
**Élément**: {example['id']} - {example['title']}
**Résumé LLM**: {example['summary']}
"""
    else:
        content += "Aucun exemple disponible\n"
    
    content += """
## Utilisation pour Llamendex

Les données enrichies par LLM sont prêtes pour ingestion dans Llamendex avec:
1. Des résumés concis du contenu
2. Des mots-clés thématiques
3. Des entités extraites (personnes, organisations)
4. Une analyse de sentiment

Ces enrichissements améliorent considérablement la qualité des résultats de recherche
et permettent des fonctionnalités avancées comme le filtrage par sentiment ou 
la recherche par entités.
"""
    
    # Écrire le contenu dans le fichier
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Résumé de l'enrichissement LLM généré dans {summary_file}")
    return summary_file

if __name__ == "__main__":
    # Test simple avec un échantillon de données
    sample_data = {
        "items": [
            {
                "id": "TEST-1",
                "title": "Test item",
                "analysis": {
                    "llm_summary": "This is a test summary",
                    "llm_keywords": ["test", "sample", "example"],
                    "llm_sentiment": "neutral"
                }
            }
        ],
        "metadata": {
            "llm_enrichment": {
                "model": "gpt-4",
                "enrichment_date": "2025-05-08T12:00:00"
            }
        }
    }
    
    if not os.path.exists("test_output"):
        os.makedirs("test_output")
    
    generate_llm_summary("test_output", data=sample_data) 