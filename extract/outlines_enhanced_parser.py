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
        
except ImportError as e:
    logging.warning(f"Modules Outlines non disponibles. Utilisation des stubs internes. Erreur: {e}")
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

# Import du module de réparation JSON
try:
    from extract.fix_json_files import repair_json_file, escape_special_chars_in_strings, fix_unclosed_strings, fix_missing_quotes_around_property_names, fix_trailing_commas
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try: 
        from extract.fix_json_files import repair_json_file, escape_special_chars_in_strings, fix_unclosed_strings, fix_missing_quotes_around_property_names, fix_trailing_commas
    except ImportError:
        logger.warning("Module fix_json_files non disponible. Fonctionnalités de réparation JSON limitées.")
        # Définir des fonctions stub si le module n'est pas disponible
        def repair_json_file(file_path):
            return False
            
        from extract.robust_json_parser import escape_special_chars_in_strings  # Fallback
        
        def fix_unclosed_strings(content):
            return content
            
        def fix_missing_quotes_around_property_names(content):
            return content
            
        def fix_trailing_commas(content):
            return content

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
        {content}
        ```
        
        JSON réparé:
        """
        
        # Remplacer la variable content manuellement
        prompt = prompt_template.replace("{content}", content)
        
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
        {content}
        ```
        """
        
        # Remplacer la variable content manuellement
        prompt = prompt_template.replace("{content}", content)
        
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
        
        # Configuration du prompt pour NER
        ner_prompt_template = """
        Vous êtes un expert en extraction d'entités nommées (personnes et organisations). 
        Votre tâche est d'identifier toutes les personnes et organisations mentionnées dans le texte.
        
        Extrayez les noms de personnes et d'organisations du texte suivant:
        
        {text}
        """
        
        try:
            # Remplacer la variable text manuellement
            prompt = ner_prompt_template.replace("{text}", text[:2000])  # Limiter à 2000 caractères
            
            # Convertir le schéma en JSON
            ner_schema_str = json.dumps(ner_schema)
            
            # Utiliser le parser JSON d'Outlines 0.2.3
            generator = generate.json(self.model, ner_schema_str)
            ner_result = generator(prompt)
            
            # Ajouter les entités extraites par LLM
            entities["persons"] = ner_result.get("persons", [])
            entities["organizations"] = ner_result.get("organizations", [])
            
            return entities
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction d'entités: {e}")
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
                
                # Tentative de réparation
                repaired_content = repair_json_content(content, use_outlines=llm_fallback)
                
                if repaired_content:
                    # Sauvegarder le JSON réparé
                    repaired_path = f"{os.path.splitext(file_path)[0]}_repaired.json"
                    with open(repaired_path, 'w', encoding='utf-8') as f:
                        f.write(repaired_content)
                    
                    logger.info(f"JSON réparé sauvegardé dans {repaired_path}")
                    return json.loads(repaired_content)
                else:
                    # Si aucune méthode n'a fonctionné, essayer avec repairer_json_file
                    if repair_json_file(file_path):
                        # Le fichier a été réparé, le charger à nouveau
                        with open(file_path, 'r', encoding='utf-8') as f:
                            return json.loads(f.read())
                    else:
                        raise JsonParsingException(f"Impossible de réparer le fichier JSON {file_path}")
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

# Fonctions simples de test pour vérifier l'installation d'Outlines
def test_outlines_installation():
    """
    Fonction simple pour tester si Outlines est correctement installé et configuré.
    Affiche un diagnostic complet avec suggestions de résolution des problèmes.
    """
    print("=== Test d'installation d'Outlines ===")
    
    # 1. Vérifier si le module outlines est importable
    try:
        import outlines
        print(f"✅ Module Outlines importé avec succès (version: {getattr(outlines, '__version__', 'inconnue')})")
    except ImportError as e:
        print(f"❌ Impossible d'importer Outlines: {e}")
        print("   - Solution: Installez Outlines avec 'pip install outlines==0.2.3'")
        return False
    
    # 2. Vérifier si la clé API est configurée
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✅ Clé API OpenAI trouvée dans les variables d'environnement")
    else:
        print("❌ Aucune clé API OpenAI trouvée")
        print("   - Solution: Définissez la variable d'environnement OPENAI_API_KEY")
        print("   - Ou ajoutez-la dans un fichier .env à la racine du projet")
    
    # 3. Vérifier si on peut initialiser un modèle simple
    try:
        model = outlines.models.openai("gpt-3.5-turbo", api_key=api_key)
        print("✅ Modèle OpenAI initialisé avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation du modèle OpenAI: {e}")
        print("   - Vérifiez que votre clé API est valide")
        print("   - Vérifiez que le modèle spécifié est disponible sur votre compte")
        return False
    
    # 4. Vérifier si on peut créer un template et générer du texte simple
    try:
        # Dans Outlines 0.2.3, Template n'est pas un attribut direct de outlines
        # Utilisons la méthode de création de template via la classe prompts
        prompt = "Dis bonjour en français."
        # Utiliser la fonction text pour générer du texte simple
        generator = outlines.generate.text(model)
        result = generator(prompt)
        print(f"✅ Génération de texte simple réussie: '{result[:30]}...'")
    except Exception as e:
        print(f"❌ Erreur lors de la génération de texte: {e}")
        traceback.print_exc()
        return False
    
    print("\n✅ Outlines est correctement installé et fonctionnel!")
    return True

# Point d'entrée pour tester l'installation
if __name__ == "__main__":
    test_outlines_installation()

# Ajouter une fonction de réparation locale qui utilise d'abord Outlines, puis les méthodes alternatives
def repair_json_content(content, use_outlines=True):
    """
    Réparer un contenu JSON en utilisant plusieurs méthodes
    
    Args:
        content: Contenu JSON à réparer
        use_outlines: Si True, essaie d'abord d'utiliser Outlines
        
    Returns:
        Contenu JSON réparé ou None si échec
    """
    # Vérifier si le JSON est déjà valide
    try:
        json_obj = json.loads(content)
        return content  # Déjà valide
    except json.JSONDecodeError:
        pass
    
    # 1. Essayer avec Outlines si disponible et demandé
    if use_outlines and not USING_STUB and openai_api_key:
        try:
            parser = OutlinesJsonParser()
            if parser.model:
                repaired = parser.repair_json_with_outlines(content)
                try:
                    # Vérifier que le résultat est valide
                    json.loads(repaired)
                    logger.info("JSON réparé avec succès en utilisant Outlines")
                    return repaired
                except json.JSONDecodeError:
                    logger.warning("Échec de la réparation avec Outlines, essai des méthodes alternatives")
        except Exception as e:
            logger.warning(f"Erreur lors de l'utilisation d'Outlines: {e}")
    
    # 2. Essayer avec nos fonctions de réparation
    try:
        # Appliquer les corrections
        fixed_content = content
        fixed_content = escape_special_chars_in_strings(fixed_content)
        fixed_content = fix_unclosed_strings(fixed_content)
        fixed_content = fix_missing_quotes_around_property_names(fixed_content)
        fixed_content = fix_trailing_commas(fixed_content)
        
        # Vérifier que le résultat est valide
        try:
            json.loads(fixed_content)
            logger.info("JSON réparé avec succès en utilisant les méthodes alternatives")
            return fixed_content
        except json.JSONDecodeError as e:
            logger.warning(f"Échec de la réparation avec les méthodes alternatives: {e}")
    except Exception as e:
        logger.warning(f"Erreur lors de la réparation: {e}")
    
    return None  # Échec de toutes les méthodes 