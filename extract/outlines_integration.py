#!/usr/bin/env python3
"""
Module d'intégration entre Outlines et notre processeur JSON générique.
Fournit des fonctions pour utiliser la bibliothèque Outlines avec notre système.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Union, Optional, Tuple

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("outlines_integration")

# Variable globale pour suivre si Outlines est disponible
outlines_available = False

def check_outlines_available():
    """
    Vérifier si la bibliothèque Outlines est disponible
    
    Returns:
        True si disponible, False sinon
    """
    global outlines_available
    
    try:
        import outlines
        logger.info(f"✅ Outlines version {outlines.__version__} est disponible")
        outlines_available = True
        return True
    except ImportError:
        logger.warning("❌ Bibliothèque Outlines non disponible")
        outlines_available = False
        return False

def create_json_grammar():
    """
    Créer une grammaire JSON en utilisant Outlines

    Returns:
        Grammaire JSON ou None si Outlines n'est pas disponible
    """
    if not outlines_available and not check_outlines_available():
        logger.warning("Impossible de créer une grammaire JSON: Outlines non disponible")
        return None
    
    try:
        import outlines.grammars as grammars
        
        # Créer une grammaire JSON avec Outlines
        json_grammar = grammars.json.JSONGrammar()
        
        logger.info("Grammaire JSON créée avec succès")
        return json_grammar
    except Exception as e:
        logger.error(f"Erreur lors de la création de la grammaire JSON: {e}")
        return None

def repair_json_with_outlines(content: str, model_name: str = None) -> Tuple[bool, str]:
    """
    Réparer un contenu JSON invalide en utilisant Outlines

    Args:
        content: Contenu JSON à réparer
        model_name: Nom du modèle à utiliser (ex: 'openai/gpt-4o')

    Returns:
        Tuple (succès, contenu réparé)
    """
    if not outlines_available and not check_outlines_available():
        logger.warning("Impossible de réparer le JSON avec Outlines: bibliothèque non disponible")
        return False, content
    
    try:
        import outlines
        from outlines.models.openai import OpenAI
        
        # Créer la grammaire JSON
        json_grammar = create_json_grammar()
        if not json_grammar:
            return False, content
        
        # Configurer le modèle
        if not model_name:
            # Essayer de détecter automatiquement
            if "OPENAI_API_KEY" in os.environ:
                model_name = "openai/gpt-4o"  # Valeur par défaut pour OpenAI
            else:
                # Essayer de se connecter à un modèle local
                model_name = "local/llama3"
        
        # Créer le modèle
        if model_name.startswith("openai/"):
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("Clé API OpenAI non trouvée dans les variables d'environnement")
                return False, content
            
            model_name_clean = model_name.replace("openai/", "")
            model = OpenAI(model_name_clean)
        else:
            # Supposons un modèle local pour les autres cas
            # (cela devrait être adapté à votre infrastructure)
            from outlines.models.huggingface import HuggingFace
            model_name_clean = model_name.replace("local/", "")
            model = HuggingFace(model_name_clean)
        
        # Instruction pour la réparation
        instruction = f"""
        Le contenu suivant est du JSON mal formé ou non valide.
        Corrige toutes les erreurs de syntaxe pour produire un JSON valide.
        Ne modifie pas les données elles-mêmes, corrige uniquement la syntaxe.
        
        JSON à réparer:
        {content[:2000]}  # Limiter pour éviter les dépassements de contexte
        """
        
        # Générer avec la grammaire JSON
        generator = outlines.generate.text(model, max_tokens=4096)
        fixed_json = generator(instruction, grammar=json_grammar)
        
        # Vérifier que le JSON est valide
        try:
            json.loads(fixed_json)
            logger.info("JSON réparé avec succès via Outlines")
            return True, fixed_json
        except json.JSONDecodeError as e:
            logger.error(f"Le JSON réparé par Outlines est toujours invalide: {e}")
            return False, content
            
    except Exception as e:
        logger.error(f"Erreur lors de la réparation avec Outlines: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, content

def enrich_json_with_outlines(items: List[Dict], instructions: str, model_name: str = None) -> List[Dict]:
    """
    Enrichir des éléments JSON avec Outlines

    Args:
        items: Liste d'éléments à enrichir
        instructions: Instructions pour l'enrichissement
        model_name: Nom du modèle à utiliser

    Returns:
        Liste d'éléments enrichis
    """
    if not outlines_available and not check_outlines_available():
        logger.warning("Impossible d'enrichir le JSON avec Outlines: bibliothèque non disponible")
        return items
    
    try:
        import outlines
        from outlines.models.openai import OpenAI
        
        # Configurer le modèle
        if not model_name:
            # Essayer de détecter automatiquement
            if "OPENAI_API_KEY" in os.environ:
                model_name = "openai/gpt-4o"  # Valeur par défaut pour OpenAI
            else:
                # Essayer de se connecter à un modèle local
                model_name = "local/llama3"
        
        # Créer le modèle
        if model_name.startswith("openai/"):
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("Clé API OpenAI non trouvée dans les variables d'environnement")
                return items
            
            model_name_clean = model_name.replace("openai/", "")
            model = OpenAI(model_name_clean)
        else:
            # Supposons un modèle local pour les autres cas
            from outlines.models.huggingface import HuggingFace
            model_name_clean = model_name.replace("local/", "")
            model = HuggingFace(model_name_clean)
        
        # Créer le générateur
        generator = outlines.generate.text(model, max_tokens=2048)
        
        # Traiter chaque élément
        enriched_items = []
        for i, item in enumerate(items):
            try:
                # Préparer le contexte
                context = json.dumps(item, indent=2, ensure_ascii=False)
                
                # Construire le prompt
                prompt = f"""
                {instructions}
                
                Élément à enrichir:
                {context}
                """
                
                # Générer l'enrichissement
                response = generator(prompt)
                
                # Mettre à jour l'élément
                item["enriched"] = response.strip()
                enriched_items.append(item)
                
                # Log
                if i % 10 == 0:
                    logger.info(f"Enrichi {i+1}/{len(items)} éléments")
                
            except Exception as e:
                logger.error(f"Erreur lors de l'enrichissement de l'élément {i}: {e}")
                enriched_items.append(item)  # Garder l'élément original
        
        logger.info(f"Enrichissement terminé: {len(enriched_items)}/{len(items)} éléments traités")
        return enriched_items
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enrichissement avec Outlines: {e}")
        return items

def create_structured_output_generator(schema_dict):
    """
    Créer un générateur de sortie structurée avec Outlines
    
    Args:
        schema_dict: Dictionnaire JSON Schema
        
    Returns:
        Générateur de sortie structurée ou None si Outlines n'est pas disponible
    """
    if not outlines_available and not check_outlines_available():
        logger.warning("Impossible de créer un générateur structuré: Outlines non disponible")
        return None
        
    try:
        import outlines
        from outlines.models.openai import OpenAI
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("Clé API OpenAI non trouvée dans les variables d'environnement")
            return None
            
        # Créer le modèle
        model = OpenAI("gpt-4o")
        
        # Créer la structure
        structured_generator = outlines.generate.json(model, schema=schema_dict)
        
        return structured_generator
    except Exception as e:
        logger.error(f"Erreur lors de la création du générateur structuré: {e}")
        return None

# Fonctions d'intégration avec notre processeur générique

def process_data_with_outlines(file_path, output_path=None, instructions=None, model_name=None):
    """
    Traiter un fichier JSON avec Outlines
    
    Args:
        file_path: Chemin du fichier à traiter
        output_path: Chemin du fichier de sortie (optionnel)
        instructions: Instructions pour l'enrichissement (optionnel)
        model_name: Nom du modèle à utiliser (optionnel)
        
    Returns:
        Données traitées ou None en cas d'erreur
    """
    # Importer notre processeur (ici pour éviter des dépendances circulaires)
    try:
        from generic_json_processor import GenericJsonProcessor
    except ImportError:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from generic_json_processor import GenericJsonProcessor
    
    # Créer une instance du processeur
    processor = GenericJsonProcessor(use_llm_fallback=True)
    
    try:
        # Charger le fichier
        data = processor.load_file(file_path)
        if not data:
            logger.error(f"Impossible de charger le fichier: {file_path}")
            return None
        
        # Extraire les éléments
        items = processor.extract_items(data)
        logger.info(f"Éléments chargés: {len(items)}")
        
        # Si des instructions sont fournies, enrichir les données
        if instructions:
            enriched_items = enrich_json_with_outlines(items, instructions, model_name)
            
            # Mettre à jour les données
            data["items"] = enriched_items
            
            # Sauvegarder si un chemin de sortie est fourni
            if output_path:
                processor.save_as_json(data, output_path)
                logger.info(f"Données enrichies sauvegardées dans: {output_path}")
        
        return data
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement avec Outlines: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# Test de disponibilité lors de l'import
check_outlines_available()

# Point d'entrée pour les tests directs
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Intégration Outlines pour le traitement JSON")
    parser.add_argument("--file", "-f", required=True, help="Fichier JSON à traiter")
    parser.add_argument("--output", "-o", help="Fichier de sortie enrichi")
    parser.add_argument("--instructions", "-i", help="Instructions pour l'enrichissement")
    parser.add_argument("--model", "-m", help="Nom du modèle à utiliser")
    parser.add_argument("--repair", "-r", action="store_true", help="Réparer le fichier JSON")
    
    args = parser.parse_args()
    
    if args.repair:
        # Mode réparation
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success, repaired = repair_json_with_outlines(content, args.model)
            
            if success:
                output_path = args.output or f"{args.file}.repaired.json"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(repaired)
                
                print(f"✅ Fichier réparé sauvegardé dans: {output_path}")
            else:
                print("❌ La réparation a échoué")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    elif args.instructions:
        # Mode enrichissement
        result = process_data_with_outlines(
            args.file,
            args.output,
            args.instructions,
            args.model
        )
        
        if result:
            print("✅ Traitement réussi")
        else:
            print("❌ Le traitement a échoué") 