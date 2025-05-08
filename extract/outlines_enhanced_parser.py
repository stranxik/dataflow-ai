#!/usr/bin/env python3
# pyright: reportGeneralTypeIssues=false
"""
Module de parsing JSON amélioré utilisant Outlines pour une génération structurée
et une extraction robuste des données JSON.

Ce module remplace/complète robust_json_parser.py en utilisant les capacités
de génération contrainte et de parsing structuré d'Outlines.
"""

import json
import os
import re
import logging
import sys
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
import traceback
from dotenv import load_dotenv

# Import d'Outlines 0.2.3 avec gestion des erreurs
try:
    import outlines
    from outlines import models
    from outlines import Template
    from outlines import samplers
    import outlines.generate as generate
    
    # Vérifier la version d'Outlines si possible
    if hasattr(outlines, '__version__'):
        logger = logging.getLogger("outlines_parser")
        logger.info(f"Utilisation d'Outlines version {outlines.__version__}")
    
    # Indiquer que nous utilisons la vraie bibliothèque
    USING_STUB = False
        
except ImportError:
    logging.warning("Modules Outlines non disponibles. Utilisation des stubs internes.")
    # Utiliser notre version stub complète
    try:
        from extract.outlines_stub import models, generate, Template, samplers, IS_STUB
        USING_STUB = True
        logging.info("Utilisation des stubs d'Outlines (fonctionnalités limitées)")
    except ImportError:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from extract.outlines_stub import models, generate, Template, samplers, IS_STUB
        USING_STUB = True
        logging.info("Utilisation des stubs d'Outlines (fonctionnalités limitées)")

# Import des modules existants
try:
    from extract.robust_json_parser import JsonParsingException, escape_special_chars_in_strings
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extract.robust_json_parser import JsonParsingException, escape_special_chars_in_strings

# Chargement des variables d'environnement
load_dotenv()

# Configuration de l'API OpenAI
openai_api_key = os.getenv("OPENAI_API_KEY")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4.1")

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("outlines_enhanced_parser")

class OutlinesJsonParser:
    """
    Parser JSON amélioré utilisant Outlines pour une extraction robuste
    et structurée des données JSON.
    """
    
    def __init__(self, llm_model: str = DEFAULT_LLM_MODEL):
        """
        Initialiser le parser JSON Outlines
        
        Args:
            llm_model: Modèle LLM à utiliser pour les réparations
        """
        self.llm_model = llm_model
        
        # Initialiser le modèle Outlines
        if openai_api_key:
            try:
                # Dans Outlines 0.2.3, models.openai prend un nom de modèle et une clé API
                # Nous n'utilisons pas le paramètre temperature car il n'est pas supporté
                self.model = models.openai(llm_model, api_key=openai_api_key)
                logger.info(f"Modèle {llm_model} initialisé avec succès")
            except Exception as e:
                logger.warning(f"Erreur lors de l'initialisation du modèle Outlines: {e}")
                self.model = None
        else:
            logger.warning("Clé API OpenAI non disponible. Certaines fonctionnalités LLM seront désactivées.")
            self.model = None
    
    def repair_json_with_outlines(self, content: str) -> str:
        """
        Répare un JSON mal formé en utilisant Outlines
        
        Args:
            content: Contenu JSON potentiellement mal formé
            
        Returns:
            Contenu JSON réparé
        """
        if not self.model:
            raise ValueError("Modèle LLM non disponible. Vérifiez votre clé API.")
        
        # Préparer un prompt pour réparer le JSON
        prompt_template = """
        Vous êtes un expert en réparation de fichiers JSON. 
        Votre tâche est de transformer des textes JSON non valides en JSON valides sans perdre d'information.
        
        Ce texte est supposé être du JSON valide, mais il contient des erreurs. Réparez-le pour 
        produire un JSON valide selon la spécification standard.
        
        JSON à réparer:
        ```
        {{ json_text }}
        ```
        
        JSON réparé:
        """
        
        # Créer un template et le rendre avec les variables
        template = Template.from_string(prompt_template)
        prompt = template(json_text=content)
        
        # Générer un JSON valide en utilisant Outlines
        # Utiliser le parser JSON pour contraindre le format de sortie
        json_regex_pattern = r'\{(?:[^{}]|(?R))*\}|\[(?:[^\[\]]|(?R))*\]'
        
        # Dans Outlines 0.2.3, generate est un module avec des fonctions
        generator = generate.regex(self.model, json_regex_pattern)
        result = generator(prompt)
        
        return result
    
    def parse_json_with_schema(self, content: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse un JSON en utilisant un schéma JSON comme guide
        
        Args:
            content: Contenu JSON à parser
            schema: Schéma JSON décrivant la structure attendue
            
        Returns:
            Données JSON structurées selon le schéma
        """
        if not self.model:
            raise ValueError("Modèle LLM non disponible. Vérifiez votre clé API.")
        
        # Configuration du prompt
        prompt_template = """
        Vous êtes un expert en extraction de données structurées à partir de JSON.
        
        Extrayez les données structurées du texte JSON suivant selon le schéma fourni:
        
        ```
        {{ json_text }}
        ```
        """
        
        # Créer un template et le rendre avec les variables
        template = Template.from_string(prompt_template)
        prompt = template(json_text=content)
        
        try:
            # Convertir le dictionnaire de schéma en chaîne JSON
            schema_str = json.dumps(schema)
            
            # Utiliser le parser de schéma JSON d'Outlines 0.2.3
            generator = generate.json(self.model, schema_str)
            result = generator(prompt)
            
            return result
        except Exception as e:
            logger.error(f"Erreur lors du parsing avec schéma: {e}")
            # Retourner un dictionnaire vide en cas d'erreur
            return {}
    
    def extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """
        Extrait des entités nommées d'un texte en utilisant Outlines
        
        Args:
            text: Texte à analyser
            
        Returns:
            Dictionnaire avec des listes d'entités détectées
        """
        if not self.model or not text:
            return {"ids": [], "emails": [], "urls": [], "persons": [], "organizations": []}
        
        # Définir les expressions régulières pour chaque type d'entité
        regex_patterns = {
            "ids": r'([A-Z]+-\d+)',  # IDs de tickets (ex: PROJ-123)
            "emails": r'[\w\.-]+@[\w\.-]+\.\w+',  # Adresses email
            "urls": r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+/?[\w\-.~:/?#[\]@!$&\'()*+,;=]*',  # URLs
        }
        
        # Extraire les entités via regex
        entities = {}
        for entity_type, pattern in regex_patterns.items():
            matches = re.findall(pattern, text)
            entities[entity_type] = list(set(matches))
        
        # Pour les personnes et organisations, utiliser Outlines avec un schéma
        ner_schema = {
            "type": "object",
            "properties": {
                "persons": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste des noms de personnes mentionnées dans le texte"
                },
                "organizations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste des organisations mentionnées dans le texte"
                }
            }
        }
        
        # Configuration du prompt pour NER avec Template
        ner_prompt_template = """
        Vous êtes un expert en extraction d'entités nommées (personnes et organisations). 
        Votre tâche est d'identifier toutes les personnes et organisations mentionnées dans le texte.
        
        Extrayez les noms de personnes et d'organisations du texte suivant:
        
        {{ text }}
        """
        
        try:
            # Créer un template et le rendre avec les variables
            template = Template.from_string(ner_prompt_template)
            prompt = template(text=text[:2000])  # Limiter à 2000 caractères
            
            # Convertir le schéma en JSON
            ner_schema_str = json.dumps(ner_schema)
            
            # Utiliser le parser JSON d'Outlines 0.2.3
            generator = generate.json(self.model, ner_schema_str)
            ner_result = generator(prompt)
            
            # Ajouter les entités extraites par LLM
            entities["persons"] = ner_result.get("persons", [])
            entities["organizations"] = ner_result.get("organizations", [])
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction d'entités: {str(e)}")
            entities["persons"] = []
            entities["organizations"] = []
        
        return entities
    
    def parse_json_file(self, file_path: str, llm_fallback: bool = False) -> Dict[str, Any]:
        """
        Parse un fichier JSON avec gestion robuste des erreurs
        
        Args:
            file_path: Chemin vers le fichier JSON
            llm_fallback: Si True, utilise LLM en cas d'échec
            
        Returns:
            Données JSON parsées
        """
        try:
            # Lecture du fichier
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Tentative de parsing standard
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"Erreur standard JSON: {str(e)}")
                
                # Tentative avec correction des erreurs courantes
                try:
                    # Appliquer des corrections simples
                    corrected_content = escape_special_chars_in_strings(content)
                    return json.loads(corrected_content)
                except json.JSONDecodeError:
                    # Si le fallback LLM est activé, utiliser Outlines
                    if llm_fallback and self.model:
                        logger.info("Tentative de réparation avec Outlines")
                        repaired_json = self.repair_json_with_outlines(content)
                        
                        # Sauvegarder le JSON réparé
                        repaired_path = f"{os.path.splitext(file_path)[0]}_repaired.json"
                        with open(repaired_path, 'w', encoding='utf-8') as f:
                            f.write(repaired_json)
                            
                        logger.info(f"JSON réparé sauvegardé dans {repaired_path}")
                        return json.loads(repaired_json)
                    else:
                        raise
        except Exception as e:
            logger.error(f"Erreur lors du parsing du fichier {file_path}: {str(e)}")
            raise JsonParsingException(f"Impossible de parser {file_path}: {str(e)}")

def outlines_robust_json_parser(file_path: str, llm_fallback: bool = False, model: str = DEFAULT_LLM_MODEL) -> Dict[str, Any]:
    """
    Fonction principale de parsing JSON robuste utilisant Outlines
    
    Args:
        file_path: Chemin du fichier JSON à parser
        llm_fallback: Activer le fallback LLM en cas d'échec
        model: Modèle LLM à utiliser si fallback activé
        
    Returns:
        Dictionnaire contenant les données JSON parsées
    """
    parser = OutlinesJsonParser(llm_model=model)
    return parser.parse_json_file(file_path, llm_fallback=llm_fallback)

def extract_entities(text: str, model: str = DEFAULT_LLM_MODEL) -> Dict[str, List[str]]:
    """
    Fonction d'extraction d'entités améliorée utilisant Outlines
    
    Args:
        text: Texte à analyser
        model: Modèle LLM à utiliser
        
    Returns:
        Dictionnaire avec des listes d'entités détectées
    """
    parser = OutlinesJsonParser(llm_model=model)
    return parser.extract_entities_from_text(text)

def extract_structured_data(content: str, schema: Dict[str, Any], model: str = DEFAULT_LLM_MODEL) -> Dict[str, Any]:
    """
    Extrait des données structurées d'un texte selon un schéma JSON
    
    Args:
        content: Contenu à analyser
        schema: Schéma JSON décrivant la structure attendue
        model: Modèle LLM à utiliser
        
    Returns:
        Données structurées selon le schéma fourni
    """
    parser = OutlinesJsonParser(llm_model=model)
    return parser.parse_json_with_schema(content, schema)

def is_using_stub() -> bool:
    """
    Vérifie si nous utilisons les stubs Outlines ou la vraie bibliothèque
    
    Returns:
        True si les stubs sont utilisés, False sinon
    """
    return USING_STUB

def get_outlines_status() -> Dict[str, Any]:
    """
    Renvoie le statut d'Outlines (version, utilisation des stubs, etc.)
    
    Returns:
        Dictionnaire contenant des informations sur le statut d'Outlines
    """
    status = {
        "using_stub": USING_STUB,
        "available": True
    }
    
    # Ajouter des informations supplémentaires si disponibles
    try:
        if not USING_STUB and hasattr(outlines, '__version__'):
            status["version"] = outlines.__version__
        
        if USING_STUB:
            status["features"] = "limited"
        else:
            status["features"] = "full"
    except Exception:
        pass
        
    return status

if __name__ == "__main__":
    # Test du parser avec un fichier spécifié en argument
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        use_llm = "--llm" in sys.argv
        
        try:
            result = outlines_robust_json_parser(input_file, llm_fallback=use_llm)
            print(f"Parsing réussi! Structure racine: {type(result)}")
            if isinstance(result, dict):
                print(f"Clés: {list(result.keys())}")
            elif isinstance(result, list):
                print(f"Nombre d'éléments: {len(result)}")
                
            # Tester l'extraction d'entités
            if isinstance(result, dict) and "content" in result:
                text = result.get("content", {}).get("description", "")
                if text:
                    print("\nExtraction d'entités:")
                    entities = extract_entities(text)
                    for entity_type, items in entities.items():
                        if items:
                            print(f"{entity_type}: {items}")
        except JsonParsingException as e:
            print(f"Échec final: {e}")
    else:
        print("Usage: python outlines_enhanced_parser.py <fichier_json> [--llm]") 