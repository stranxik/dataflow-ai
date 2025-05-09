#!/usr/bin/env python3
"""
Module utilitaire pour générer des résumés des enrichissements LLM
"""

import os
import json
import sys
from datetime import datetime

# Importer le module de gestion des langues s'il est disponible
try:
    # Ajouter le chemin du parent au path pour trouver le module cli
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from cli.lang_utils import t, get_current_language
    TRANSLATIONS_LOADED = True
except ImportError:
    # Fallback si le module de traduction n'est pas disponible
    def t(key, category=None, lang=None):
        return key
    def get_current_language():
        return "fr"
    TRANSLATIONS_LOADED = False

def generate_llm_summary(output_dir, jira_data=None, confluence_data=None, data=None, filename="llm_enrichment_summary.md", language=None):
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
        language: Code de langue spécifique à utiliser (fr, en) - si None, utilise la langue active
    
    Returns:
        Le chemin du fichier résumé généré
    """
    summary_file = os.path.join(output_dir, filename)
    
    # Utiliser la langue spécifiée, sinon la langue active
    lang = language if language else get_current_language() if TRANSLATIONS_LOADED else "fr"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Vérifier si nous avons au moins une source de données
    if not jira_data and not confluence_data and not data:
        content = f"""# {t("llm_summary_title", "llm_summary", lang)}

## {t("general_info_title", "llm_summary", lang)}
- {t("analysis_date", "llm_summary", lang)}: {timestamp}
- {t("no_data_found", "llm_summary", lang)}

⚠️ {t("no_data_warning", "llm_summary", lang)}
1. {t("warning_llm_option", "llm_summary", lang)}
2. {t("warning_api_key", "llm_summary", lang)}
3. {t("warning_valid_input", "llm_summary", lang)}
"""
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return summary_file
    
    # Traitement des données génériques si fournies à la place de jira/confluence
    if data and not jira_data and not confluence_data:
        return _generate_generic_summary(output_dir, data, summary_file, timestamp, lang)
    
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
    content = f"""# {t("llm_summary_title", "llm_summary", lang)}

## {t("general_info_title", "llm_summary", lang)}
- {t("analysis_date", "llm_summary", lang)}: {timestamp}
- {t("jira_tickets_count", "llm_summary", lang)}: {jira_items_count}
- {t("confluence_pages_count", "llm_summary", lang)}: {confluence_items_count}
- {t("llm_model_used", "llm_summary", lang)}: {model_used}
"""
    
    if jira_items_count > 0:
        content += f"""
## {t("jira_analysis_title", "llm_summary", lang)}

### {t("main_keywords_title", "llm_summary", lang)}
"""
        content += f"{', '.join(jira_keywords) if jira_keywords else t('no_keywords', 'llm_summary', lang)}\n"
        
        content += f"""
### {t("sentiment_distribution_title", "llm_summary", lang)}
"""
        content += f"{str(jira_sentiment) if jira_sentiment else t('no_sentiment_analysis', 'llm_summary', lang)}\n"
        
        content += f"""
### {t("enrichment_example_title", "llm_summary", lang)}
"""
        
        if jira_example:
            content += f"""
**{t("ticket", "llm_summary", lang)}**: {jira_example['id']} - {jira_example['title']}
**{t("llm_summary", "llm_summary", lang)}**: {jira_example['summary']}
"""
        else:
            content += f"{t('no_example_available', 'llm_summary', lang)}\n"
    
    if confluence_items_count > 0:
        content += f"""
## {t("confluence_analysis_title", "llm_summary", lang)}

### {t("main_keywords_title", "llm_summary", lang)}
"""
        content += f"{', '.join(confluence_keywords) if confluence_keywords else t('no_keywords', 'llm_summary', lang)}\n"
        
        content += f"""
### {t("sentiment_distribution_title", "llm_summary", lang)}
"""
        content += f"{str(confluence_sentiment) if confluence_sentiment else t('no_sentiment_analysis', 'llm_summary', lang)}\n"
        
        content += f"""
### {t("enrichment_example_title", "llm_summary", lang)}
"""
        
        if confluence_example:
            content += f"""
**{t("page", "llm_summary", lang)}**: {confluence_example['id']} - {confluence_example['title']}
**{t("llm_summary", "llm_summary", lang)}**: {confluence_example['summary']}
"""
        else:
            content += f"{t('no_example_available', 'llm_summary', lang)}\n"
    
    content += f"""
## {t("llamendex_usage_title", "llm_summary", lang)}

{t("llamendex_usage_text", "llm_summary", lang)}
"""
    
    # Écrire le contenu dans le fichier
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ {t('llm_summary_generated', 'llm_summary', lang)} {summary_file}")
    return summary_file

def _generate_generic_summary(output_dir, data, summary_file, timestamp, lang="fr"):
    """
    Génère un résumé pour des données génériques (non JIRA/Confluence)
    
    Args:
        output_dir: Répertoire de sortie
        data: Données à analyser
        summary_file: Chemin du fichier de sortie
        timestamp: Horodatage de l'analyse
        lang: Code de langue à utiliser
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
                    sentiment = llm_data["sentiment"]
                    sentiment[sentiment] = sentiment.get(sentiment, 0) + 1
    
    # Limiter et dédupliquer les mots-clés
    keywords = list(set(keywords))[:15]  # Top 15 mots-clés uniques
    
    # Déterminer le modèle utilisé
    model_used = "inconnu"
    if isinstance(data, dict) and "metadata" in data and "llm_enrichment" in data["metadata"]:
        model_used = data["metadata"]["llm_enrichment"].get("model", "inconnu")
    
    # Créer le contenu du fichier
    content = f"""# {t("llm_summary_title", "llm_summary", lang)}

## {t("general_info_title", "llm_summary", lang)}
- {t("analysis_date", "llm_summary", lang)}: {timestamp}
- {t("items_count", "llm_summary", lang)}: {items_count}
- {t("llm_model_used", "llm_summary", lang)}: {model_used}

## {t("data_analysis_title", "llm_summary", lang)}

### {t("main_keywords_title", "llm_summary", lang)}
{', '.join(keywords) if keywords else t('no_keywords', 'llm_summary', lang)}

### {t("sentiment_distribution_title", "llm_summary", lang)}
{str(sentiment) if sentiment else t('no_sentiment_analysis', 'llm_summary', lang)}

### {t("enrichment_example_title", "llm_summary", lang)}
"""
    
    if example:
        content += f"""
**{t("item", "llm_summary", lang)}**: {example['id']} - {example['title']}
**{t("llm_summary", "llm_summary", lang)}**: {example['summary']}
"""
    else:
        content += f"{t('no_example_available', 'llm_summary', lang)}\n"
    
    content += f"""
## {t("llamendex_usage_title", "llm_summary", lang)}

{t("llamendex_usage_text", "llm_summary", lang)}
"""
    
    # Écrire le contenu dans le fichier
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ {t('llm_summary_generated', 'llm_summary', lang)} {summary_file}")
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