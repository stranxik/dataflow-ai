#!/usr/bin/env python3
"""
Module d'enrichissement LLM spécifique pour JIRA et Confluence
Ce module utilise Outlines 0.2.3 pour enrichir les données JSON
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import traceback
from cli.lang_utils import get_current_language

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("outlines_enricher")

# Variable globale pour Outlines
outlines_available = False

def check_outlines():
    """Vérifie si Outlines est disponible et configuré correctement"""
    global outlines_available
    
    try:
        import outlines
        from outlines import Template, models
        outlines_available = True
        logger.info(f"✅ Outlines importé avec succès")
        return True
    except ImportError as e:
        logger.warning(f"❌ Outlines non disponible: {e}")
        outlines_available = False
        return False

# Charger la clé API depuis le fichier .env si dotenv est disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Variables d'environnement chargées depuis .env")
except ImportError:
    logger.warning("⚠️ python-dotenv non disponible, impossible de charger automatiquement .env")

# Vérifier l'import d'Outlines
outlines_available = check_outlines()

def enrich_with_llm(item_data: Dict[str, Any], model_name: str = "gpt-4-0125-preview", language: str = None) -> Dict[str, Any]:
    """
    Enrichit un élément (ticket JIRA ou page Confluence) avec des analyses LLM
    
    Args:
        item_data: Données de l'élément à enrichir
        model_name: Nom du modèle LLM à utiliser (doit supporter les sorties JSON structurées)
        language: Langue à utiliser pour le prompt (par défaut: la langue courante)
    
    Returns:
        Élément enrichi avec des analyses LLM
    """
    global outlines_available
    
    # Vérifier si Outlines est disponible
    if not outlines_available and not check_outlines():
        logger.warning("Outlines n'est pas disponible, impossible d'enrichir les données")
        return item_data
    
    # Importer les modules nécessaires
    try:
        import outlines
        from outlines import Template, models
        import outlines.generate as generate
        from openai import OpenAI
    except ImportError:
        logger.error("Échec de l'import d'Outlines, impossible d'enrichir les données")
        return item_data
    
    # Vérifier la clé API
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("Aucune clé API OpenAI trouvée, impossible d'enrichir les données")
        return item_data
    
    # Extraire le contenu à analyser
    content = extract_content_from_item(item_data)
    if not content:
        logger.warning("Aucun contenu trouvé dans l'élément, impossible d'enrichir")
        return item_data
    
    try:
        # Utiliser directement l'API OpenAI
        client = OpenAI(api_key=api_key)
        
        # Prompt dynamique selon la langue
        lang = language or get_current_language() or "fr"
        if lang == "en":
            prompt_text = f"""
            You are an expert in technical document analysis.
            Analyze the following content and return ONLY a structured JSON object with the following fields:

            1. \"summary\": a concise summary of the content (max 150 words)
            2. \"keywords\": an array of 5-10 important keywords extracted from the content
            3. \"entities\": an object containing:
               - \"people\": an array of mentioned people
               - \"organizations\": an array of mentioned organizations
               - \"technical_terms\": an array of mentioned technical terms
            4. \"sentiment\": the overall sentiment (\"positive\", \"neutral\" or \"negative\" only)

            Content to analyze:
            {content}

            Respond ONLY with a valid JSON object and no additional text.
            """
            system_prompt = "You are a technical assistant who only returns structured JSON."
        else:
            prompt_text = f"""
            Tu es un expert en analyse de documents techniques.
            Analyse le contenu suivant et retourne UNIQUEMENT un objet JSON structuré contenant les champs suivants:

            1. \"summary\": un résumé concis du contenu (150 mots maximum)
            2. \"keywords\": un tableau de 5-10 mots-clés importants extraits du contenu
            3. \"entities\": un objet contenant:
               - \"people\": un tableau des personnes mentionnées
               - \"organizations\": un tableau des organisations mentionnées
               - \"technical_terms\": un tableau des termes techniques mentionnées
            4. \"sentiment\": le sentiment général (uniquement \"positive\", \"neutral\" ou \"negative\")

            Contenu à analyser:
            {content}

            Réponds UNIQUEMENT avec un objet JSON valide sans aucun texte additionnel.
            """
            system_prompt = "Tu es un assistant technique qui retourne uniquement du JSON structuré."
        
        # Appeler l'API
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.0
        )
        
        # Extraire la réponse JSON
        result_json = response.choices[0].message.content
        
        # Nettoyer le JSON si nécessaire (enlever les blocs de code markdown)
        if "```json" in result_json:
            result_json = result_json.split("```json")[1].split("```")[0].strip()
        elif "```" in result_json:
            result_json = result_json.split("```")[1].split("```")[0].strip()
        
        # Analyser le JSON
        result = json.loads(result_json)
        
        # Copier l'élément original pour préserver sa structure
        enriched_item = item_data.copy()
        
        # Ajouter ou mettre à jour l'analyse
        if "analysis" not in enriched_item:
            enriched_item["analysis"] = {}
        
        # Ajouter les enrichissements
        enriched_item["analysis"]["llm_summary"] = result.get("summary", "")
        enriched_item["analysis"]["llm_keywords"] = result.get("keywords", [])
        enriched_item["analysis"]["llm_entities"] = result.get("entities", {})
        enriched_item["analysis"]["llm_sentiment"] = result.get("sentiment", "neutral")
        
        logger.info(f"✅ Élément enrichi avec succès")
        return enriched_item
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'enrichissement LLM: {e}")
        logger.error(traceback.format_exc())
        return item_data

def extract_content_from_item(item: Dict[str, Any]) -> str:
    """
    Extrait le contenu textuel d'un élément (ticket JIRA ou page Confluence)
    
    Args:
        item: Données de l'élément
    
    Returns:
        Contenu textuel extrait
    """
    content = ""
    
    # Extraire le titre
    if "title" in item:
        content += f"Titre: {item.get('title', '')}\n\n"
    
    # Extraire la description
    if "description" in item:
        content += f"Description: {item.get('description', '')}\n\n"
    
    # Extraire le contenu structuré
    if "content" in item:
        if isinstance(item["content"], dict):
            for key, value in item["content"].items():
                if isinstance(value, str) and value.strip():
                    content += f"{key}: {value}\n\n"
        elif isinstance(item["content"], str):
            content += item["content"]
    
    # Extraire les commentaires
    if "comments" in item:
        if isinstance(item["comments"], list):
            for i, comment in enumerate(item["comments"]):
                if isinstance(comment, dict) and "text" in comment:
                    content += f"Commentaire {i+1}: {comment['text']}\n\n"
                elif isinstance(comment, str):
                    content += f"Commentaire {i+1}: {comment}\n\n"
    
    # Limiter la taille du contenu pour éviter des problèmes d'API
    max_len = 8000
    if len(content) > max_len:
        content = content[:max_len] + "..."
    
    return content

def enrich_data_file(input_file: str, output_file: str, model_name: str = "gpt-4-0125-preview", language: str = None) -> bool:
    """
    Enrichit un fichier de données JSON avec des analyses LLM
    
    Args:
        input_file: Chemin vers le fichier d'entrée
        output_file: Chemin vers le fichier de sortie
        model_name: Nom du modèle LLM à utiliser
        language: Langue à utiliser pour le prompt (par défaut: la langue courante)
    
    Returns:
        True si l'enrichissement a réussi, False sinon
    """
    try:
        # Charger les données
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Adapter le format si nécessaire
        data = adapt_data_format(data)
        
        # Vérifier si les données sont au bon format
        if "items" not in data or not isinstance(data["items"], list):
            logger.error("Format de données invalide, 'items' doit être une liste")
            return False
        
        # Enrichir chaque élément
        enriched_items = []
        total_items = len(data["items"])
        
        for i, item in enumerate(data["items"]):
            logger.info(f"Enrichissement de l'élément {i+1}/{total_items}")
            enriched_item = enrich_with_llm(item, model_name, language=language)
            enriched_items.append(enriched_item)
        
        # Mettre à jour les données
        data["items"] = enriched_items
        
        # Ajouter des métadonnées d'enrichissement
        if "metadata" not in data:
            data["metadata"] = {}
        
        data["metadata"]["llm_enrichment"] = {
            "model": model_name,
            "enrichment_date": datetime.now().isoformat(),
            "enriched_items_count": len(enriched_items)
        }
        
        # Sauvegarder les données enrichies
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Données enrichies sauvegardées dans {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'enrichissement du fichier: {e}")
        logger.error(traceback.format_exc())
        return False

# Fonction pour adapter le format des données
def adapt_data_format(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapte le format des données pour s'assurer qu'il y a une liste "items"
    
    Args:
        data: Les données à adapter
        
    Returns:
        Le dictionnaire avec une structure "items" correcte
    """
    # Si les données ont déjà une structure "items" correcte
    if "items" in data and isinstance(data["items"], list):
        return data
    
    # Si les données sont directement une liste
    if isinstance(data, list):
        return {"items": data, "metadata": {}}
    
    # Si les données contiennent une autre structure de liste
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 0:
            logger.info(f"Structure de liste trouvée sous la clé '{key}', utilisation comme 'items'")
            new_data = {
                "items": value,
                "metadata": {key: f"Converti depuis {key}"}
            }
            # Copier les autres métadonnées
            for k, v in data.items():
                if k != key and not isinstance(v, list):
                    new_data["metadata"][k] = v
            return new_data
    
    # Cas où aucune structure de liste n'est trouvée, mais il y a au moins un objet
    logger.warning("Aucune liste d'éléments trouvée, création d'une liste avec l'objet unique")
    return {
        "items": [data],
        "metadata": {"original_format": "single_object"}
    }

if __name__ == "__main__":
    # Test du module avec des fichiers spécifiés en arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrichir des données JSON avec des analyses LLM")
    parser.add_argument("--input", "-i", required=True, help="Fichier JSON d'entrée")
    parser.add_argument("--output", "-o", help="Fichier JSON de sortie (par défaut: enriched_[input])")
    parser.add_argument("--model", "-m", default="gpt-4-0125-preview", help="Modèle LLM à utiliser")
    parser.add_argument("--language", "-l", help="Langue à utiliser pour le prompt")
    
    args = parser.parse_args()
    
    # Déterminer le fichier de sortie
    output_file = args.output
    if not output_file:
        input_path = Path(args.input)
        output_file = str(input_path.parent / f"enriched_{input_path.name}")
    
    # Enrichir les données
    success = enrich_data_file(args.input, output_file, args.model, args.language)
    
    if success:
        print(f"✅ Enrichissement terminé avec succès: {output_file}")
    else:
        print("❌ Échec de l'enrichissement")
        sys.exit(1) 