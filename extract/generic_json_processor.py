#!/usr/bin/env python3
"""
Module de traitement générique des fichiers JSON.
Capable de charger, parser et transformer des données JSON indépendamment de leur structure.
"""

import json
import os
import sys
import logging
import re
import traceback
from typing import Dict, Any, List, Union, Optional, Tuple
from pathlib import Path
from datetime import datetime
import shutil

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("generic_json_processor")

# Ajouter l'import pour le résumé LLM
try:
    from .llm_summary import generate_llm_summary
except ImportError:
    # Si importé depuis un autre répertoire
    try:
        from llm_summary import generate_llm_summary
    except ImportError:
        # Fallback si le module n'est pas trouvé
        generate_llm_summary = None
        print("⚠️ Module llm_summary non trouvé, la génération de résumés LLM est désactivée")

class JsonParsingException(Exception):
    """Exception personnalisée pour les erreurs de parsing JSON"""
    pass

def escape_special_chars_in_strings(content: str) -> str:
    """
    Échapper les caractères spéciaux dans les chaînes de caractères JSON
    
    Args:
        content: Contenu JSON à corriger
    
    Returns:
        Contenu JSON corrigé
    """
    # Motif pour identifier les chaînes de caractères JSON (entre guillemets doubles)
    # Prend en compte les échappements existants
    string_pattern = r'"((?:[^"\\]|\\.)*)"'
    
    def escape_special_chars(match):
        # Récupérer la chaîne entre guillemets
        string = match.group(1)
        
        # Échapper les caractères spéciaux non échappés
        # Nouvelle ligne, tabulation, retour chariot
        string = re.sub(r'(?<!\\)\n', '\\n', string)
        string = re.sub(r'(?<!\\)\t', '\\t', string)
        string = re.sub(r'(?<!\\)\r', '\\r', string)
        
        # Retourner la chaîne corrigée entre guillemets
        return f'"{string}"'
    
    # Remplacer toutes les occurrences dans le contenu
    return re.sub(string_pattern, escape_special_chars, content)

def fix_unclosed_strings(content: str) -> str:
    """
    Corriger les chaînes non fermées dans le JSON
    
    Args:
        content: Contenu JSON à corriger
    
    Returns:
        Contenu JSON corrigé
    """
    # Motif pour identifier les lignes avec des chaînes non fermées
    # Une chaîne commence par un guillemet et il n'y a pas de guillemet fermant 
    # ou il est précédé d'un antislash
    unclosed_string_pattern = r'("(?:[^"\\]|\\.)*)\s*$'
    
    # Traiter ligne par ligne
    lines = content.split('\n')
    for i in range(len(lines)):
        if re.search(unclosed_string_pattern, lines[i]):
            # Ajouter un guillemet fermant à la fin de la ligne
            lines[i] = lines[i] + '"'
            logger.info(f"Chaîne non fermée corrigée à la ligne {i+1}")
    
    return '\n'.join(lines)

def fix_missing_quotes_around_property_names(content: str) -> str:
    """
    Corriger les noms de propriétés sans guillemets dans le JSON
    
    Args:
        content: Contenu JSON à corriger
    
    Returns:
        Contenu JSON corrigé
    """
    # Motif pour identifier les propriétés sans guillemets
    # Un nom de propriété suivi de deux-points sans être entouré de guillemets
    missing_quotes_pattern = r'(?<=\{|\,)\s*([a-zA-Z0-9_]+)\s*:'
    
    # Remplacer par le nom de propriété entre guillemets
    return re.sub(missing_quotes_pattern, r' "\1":', content)

def fix_trailing_commas(content: str) -> str:
    """
    Corriger les virgules en trop dans le JSON
    
    Args:
        content: Contenu JSON à corriger
    
    Returns:
        Contenu JSON corrigé
    """
    # Motif pour identifier les virgules en trop avant la fermeture d'un objet ou d'un tableau
    trailing_comma_pattern = r',\s*(\}|\])'
    
    # Remplacer par la fermeture sans virgule
    return re.sub(trailing_comma_pattern, r'\1', content)

def repair_json_content(content: str) -> Tuple[bool, str]:
    """
    Tenter de réparer un contenu JSON invalide
    
    Args:
        content: Contenu JSON à réparer
        
    Returns:
        Tuple (succès, contenu réparé)
    """
    # Vérifier si le JSON est déjà valide
    try:
        json.loads(content)
        return True, content
    except json.JSONDecodeError:
        # Appliquer les corrections
        try:
            repaired = escape_special_chars_in_strings(content)
            repaired = fix_unclosed_strings(repaired)
            repaired = fix_missing_quotes_around_property_names(repaired)
            repaired = fix_trailing_commas(repaired)
            
            # Vérifier si le JSON est maintenant valide
            json.loads(repaired)
            return True, repaired
        except json.JSONDecodeError:
            return False, content

def safe_json_load(file_obj, log_prefix="", llm_fallback=False, model=None):
    """
    Charger un fichier JSON avec gestion robuste des erreurs
    
    Args:
        file_obj: Fichier ouvert à charger
        log_prefix: Préfixe pour les messages de log
        llm_fallback: Si True, tenter d'utiliser un LLM pour réparer le JSON
        model: Modèle LLM à utiliser
        
    Returns:
        Données JSON chargées
    """
    try:
        # Lire le contenu du fichier
        content = file_obj.read()
        
        # Tenter de parser directement
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"{log_prefix} Erreur JSON: {str(e)}")
            
            # Tenter de réparer le JSON
            success, repaired = repair_json_content(content)
            if success:
                logger.info(f"{log_prefix} JSON réparé avec succès")
                return json.loads(repaired)
            
            # Tenter d'utiliser un LLM si demandé
            if llm_fallback:
                logger.info(f"{log_prefix} Tentative de réparation avec LLM")
                try:
                    # Importer le module outlines_enhanced_parser seulement si nécessaire
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    try:
                        from extract.outlines_enhanced_parser import repair_json_content as llm_repair
                        
                        # Utiliser Outlines pour réparer
                        repaired_content = llm_repair(content, use_outlines=True)
                        if repaired_content:
                            logger.info(f"{log_prefix} JSON réparé avec LLM")
                            return json.loads(repaired_content)
                    except (ImportError, Exception) as e:
                        logger.error(f"{log_prefix} Échec de l'utilisation d'Outlines pour réparer: {e}")
                except Exception as e:
                    logger.error(f"{log_prefix} Erreur lors de la réparation LLM: {e}")
            
            # Si toutes les tentatives échouent, lever l'exception
            raise JsonParsingException(f"Impossible de parser le JSON: {str(e)}")
    except Exception as e:
        logger.error(f"{log_prefix} Erreur lors du chargement: {str(e)}")
        raise JsonParsingException(f"Erreur de lecture du fichier: {str(e)}")

def detect_json_structure(data):
    """
    Détecte automatiquement la structure du JSON et l'adapte à un format standard
    
    Args:
        data: Données JSON chargées
        
    Returns:
        Données standardisées et informations sur la structure
    """
    structure_info = {
        "original_type": type(data).__name__,
        "is_collection": isinstance(data, list),
        "detected_item_type": None,
        "item_count": 0,
        "data_format": "unknown",
        "has_items_key": False,
        "has_tickets_key": False,
        "has_pages_key": False
    }
    
    standardized_data = {}
    
    # Cas 1: Liste d'objets
    if isinstance(data, list):
        structure_info["is_collection"] = True
        structure_info["item_count"] = len(data)
        structure_info["data_format"] = "array"
        
        # Détecter le type d'éléments si la liste n'est pas vide
        if data and isinstance(data[0], dict):
            # Regarder les clés pour essayer de deviner le type d'élément
            first_item = data[0]
            keys = set(first_item.keys())
            
            if "title" in keys and "markdown" in keys:
                structure_info["detected_item_type"] = "confluence_page"
            elif "key" in keys and "description" in keys:
                structure_info["detected_item_type"] = "jira_ticket"
            else:
                structure_info["detected_item_type"] = "generic_object"
        
        # Standardiser au format {items: [data]}
        standardized_data = {"items": data}
        
    # Cas 2: Objet avec une clé items/tickets/pages
    elif isinstance(data, dict):
        structure_info["is_collection"] = False
        
        # Détecter les clés de collections
        if "items" in data:
            structure_info["has_items_key"] = True
            structure_info["item_count"] = len(data["items"])
            structure_info["data_format"] = "object_with_items"
            standardized_data = data  # Déjà au format standard
            
        elif "tickets" in data:
            structure_info["has_tickets_key"] = True
            structure_info["item_count"] = len(data["tickets"])
            structure_info["data_format"] = "object_with_tickets"
            # Standardiser en renommant tickets en items
            standardized_data = {"items": data["tickets"]}
            if "metadata" in data:
                standardized_data["metadata"] = data["metadata"]
                
        elif "pages" in data:
            structure_info["has_pages_key"] = True
            structure_info["item_count"] = len(data["pages"])
            structure_info["data_format"] = "object_with_pages"
            # Standardiser en renommant pages en items
            standardized_data = {"items": data["pages"]}
            if "metadata" in data:
                standardized_data["metadata"] = data["metadata"]
                
        else:
            # Objet sans clé de collection connue
            structure_info["data_format"] = "object_without_items"
            # Traiter comme un seul élément
            standardized_data = {"items": [data]}
            structure_info["item_count"] = 1
    
    # Autres cas (non gérés)
    else:
        standardized_data = {"items": [data]}
        structure_info["item_count"] = 1
        structure_info["data_format"] = "other"
    
    return standardized_data, structure_info

def load_and_standardize_json(file_path, llm_fallback=False, model=None):
    """
    Charger un fichier JSON et le convertir dans un format standard
    
    Args:
        file_path: Chemin du fichier à charger
        llm_fallback: Si True, utiliser un LLM pour réparer le JSON en cas d'erreur
        model: Modèle LLM à utiliser (si applicable)
        
    Returns:
        Tuple (données standardisées, info structure)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = safe_json_load(f, log_prefix=file_path, llm_fallback=llm_fallback, model=model)
        
        # Détecter la structure et standardiser
        standardized, structure_info = detect_json_structure(data)
        
        logger.info(f"Fichier chargé: {file_path}")
        logger.info(f"Structure détectée: {structure_info['data_format']}")
        logger.info(f"Nombre d'éléments: {structure_info['item_count']}")
        
        return standardized, structure_info
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement de {file_path}: {str(e)}")
        logger.error(traceback.format_exc())
        return None, None

def get_items_from_data(data, original_format=None):
    """
    Extraire les éléments d'un objet JSON standardisé ou non
    
    Args:
        data: Données JSON
        original_format: Format d'origine pour savoir comment extraire les éléments
        
    Returns:
        Liste d'éléments
    """
    if data is None:
        return []
        
    # Si c'est déjà une liste, la retourner directement
    if isinstance(data, list):
        return data
        
    # Si c'est un objet avec une clé connue pour les éléments
    if isinstance(data, dict):
        # Tenter avec les clés connues
        for key in ["items", "tickets", "pages"]:
            if key in data and isinstance(data[key], list):
                return data[key]
        
        # Si le format original est spécifié, essayer de l'utiliser
        if original_format:
            if original_format == "array":
                return data.get("items", [])
            elif original_format == "object_with_tickets":
                return data.get("tickets", [])
            elif original_format == "object_with_pages":
                return data.get("pages", [])
    
    # Si aucun cas ne correspond, retourner une liste vide
    return []

def write_tree(directory, output_filename="arborescence.txt"):
    """
    Générer un fichier texte avec l'arborescence d'un répertoire et analyser les fichiers JSON
    
    Args:
        directory: Répertoire à analyser
        output_filename: Nom du fichier de sortie
    
    Returns:
        True si réussi
    """
    output_path = os.path.join(directory, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Arborescence des fichiers traités dans {os.path.basename(directory)}\n")
        f.write(f"# Généré le {datetime.now().isoformat()}\n")
        f.write("="*80 + "\n\n")
        
        # Parcourir les fichiers JSON et les analyser
        for root, dirs, files in os.walk(directory):
            # Ignorer le fichier d'arborescence lui-même
            files = [f for f in files if f != output_filename]
            
            json_files = [f for f in files if f.endswith('.json')]
            subdirs = []
            
            # Analyser les fichiers JSON
            for json_file in json_files:
                file_path = os.path.join(root, json_file)
                rel_path = os.path.relpath(file_path, directory)
                
                f.write(f"## {rel_path}\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as jf:
                        data = json.load(jf)
                    
                    # Analyser la structure
                    if isinstance(data, dict):
                        f.write(f"- Type: Object avec {len(data)} clés\n")
                        f.write(f"- Clés principales: {', '.join(data.keys())}\n")
                        
                        # Afficher plus de détails sur chaque clé principale
                        for key, value in data.items():
                            if isinstance(value, dict):
                                f.write(f"  - {key}: Object avec {len(value)} clés\n")
                            elif isinstance(value, list):
                                f.write(f"  - {key}: Array avec {len(value)} éléments\n")
                            else:
                                f.write(f"  - {key}: {type(value).__name__}\n")
                    
                    elif isinstance(data, list):
                        f.write(f"- Type: Array avec {len(data)} éléments\n")
                        if data and isinstance(data[0], dict):
                            f.write(f"- Premier élément contient: {', '.join(data[0].keys())}\n")
                    
                    else:
                        f.write(f"- Type: {type(data).__name__}\n")
                
                except json.JSONDecodeError as e:
                    f.write(f"- Erreur de parsing JSON: {str(e)}\n")
                except Exception as e:
                    f.write(f"- Erreur lors de l'analyse: {str(e)}\n")
                
                f.write("\n")
            
            # Collecter les sous-répertoires pour l'arborescence
            for d in dirs:
                dir_path = os.path.join(root, d)
                rel_dir = os.path.relpath(dir_path, directory)
                dir_files = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
                subdirs.append(f"- {rel_dir}/ ({dir_files} fichiers)")
        
        # Afficher les sous-répertoires à la fin
        if subdirs:
            f.write("## Sous-dossiers:\n")
            for subdir in subdirs:
                f.write(f"{subdir}\n")
    
    return True

def write_file_structure(file_path, output_dir, output_filename=None, max_nodes=None, max_depth=None):
    """
    Analyser et générer un rapport sur la structure d'un fichier JSON
    
    Args:
        file_path: Chemin du fichier à analyser
        output_dir: Répertoire pour le fichier de sortie
        output_filename: Nom du fichier de sortie (optionnel)
        max_nodes: Nombre maximum de nœuds à afficher par niveau (optionnel)
        max_depth: Profondeur maximale d'exploration (optionnel)
    
    Returns:
        Chemin du fichier de sortie
    """
    # Déterminer le nom du fichier de sortie s'il n'est pas fourni
    if output_filename is None:
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        output_filename = f"{name_without_ext}_structure.txt"
    
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Structure et contenu du fichier: {os.path.basename(file_path)}\n")
        f.write("=" * 50 + "\n\n")
        
        # Informations sur le fichier
        f.write(f"Nom: {os.path.basename(file_path)}\n")
        f.write(f"Chemin: {file_path}\n")
        f.write(f"Taille: {os.path.getsize(file_path)} octets\n")
        f.write(f"Date de traitement: {datetime.now().isoformat()}\n\n")
        
        # Analyser la structure interne
        f.write("Structure interne:\n")
        f.write("-" * 17 + "\n")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
            
            # Détecter la structure
            standardized, structure_info = detect_json_structure(data)
            
            f.write(f"Type: {structure_info['original_type']}\n")
            f.write(f"Format: {structure_info['data_format']}\n")
            f.write(f"Nombre d'éléments: {structure_info['item_count']}\n")
            
            if structure_info['detected_item_type']:
                f.write(f"Type d'éléments détecté: {structure_info['detected_item_type']}\n")
            
            # Arborescence du contenu
            f.write("\nArborescence du contenu:\n")
            f.write("-" * 23 + "\n")
            
            # Respecter les limites max_nodes et max_depth si spécifiées
            current_depth = 0
            max_depth = max_depth if max_depth is not None else float('inf')
            max_nodes = max_nodes if max_nodes is not None else float('inf')
            
            # Pour un dictionnaire, afficher les clés de premier niveau
            if isinstance(data, dict):
                for i, (key, value) in enumerate(data.items()):
                    if i >= max_nodes:
                        f.write(f"- ... ({len(data) - max_nodes} autres clés non affichées)\n")
                        break
                        
                    if isinstance(value, dict):
                        f.write(f"- {key}: Object avec {len(value)} clés\n")
                        # Afficher quelques clés du niveau suivant si la profondeur le permet
                        if current_depth + 1 < max_depth:
                            subkeys_to_show = min(max_nodes, len(value)) if max_nodes else 5
                            for j, subkey in enumerate(list(value.keys())[:subkeys_to_show]):
                                f.write(f"  - {subkey}: {type(value[subkey]).__name__}\n")
                            if len(value) > subkeys_to_show:
                                f.write(f"  - ... ({len(value) - subkeys_to_show} autres clés)\n")
                    
                    elif isinstance(value, list):
                        f.write(f"- {key}: Array avec {len(value)} éléments\n")
                        # Afficher le type du premier élément si la liste n'est pas vide
                        if value:
                            f.write(f"  - Type d'élément: {type(value[0]).__name__}\n")
                    
                    else:
                        f.write(f"- {key}: {type(value).__name__}\n")
            
            # Pour une liste, afficher des informations sur les premiers éléments
            elif isinstance(data, list):
                f.write(f"- Liste de {len(data)} éléments\n")
                
                if data:
                    # Afficher les clés du premier élément si c'est un dict
                    if isinstance(data[0], dict):
                        keys = list(data[0].keys())
                        keys_to_show = min(max_nodes, len(keys)) if max_nodes else 10
                        f.write(f"- Clés du premier élément: {', '.join(keys[:keys_to_show])}")
                        if len(keys) > keys_to_show:
                            f.write(f" ... ({len(keys) - keys_to_show} autres)\n")
                        else:
                            f.write("\n")
            
        except json.JSONDecodeError as e:
            f.write(f"Type: Inconnu - Erreur de parsing\n\n")
            f.write(f"Erreur lors de l'analyse: {str(e)}\n\n")
            f.write("Arborescence du contenu:\n")
            f.write("-" * 23 + "\n")
            f.write(f"Impossible de générer l'arborescence: {str(e)}\n")
            
        except Exception as e:
            f.write(f"Erreur lors de l'analyse: {str(e)}\n")
    
    return output_path

# Ajout de la classe principale pour traitement générique
class GenericJsonProcessor:
    """Classe pour traiter génériquement des fichiers JSON indépendamment de leur structure"""
    
    def __init__(self, field_mappings=None, detect_fields=True, extract_keywords=False, 
                 use_llm_fallback=False, llm_model=None, preserve_source=True, generate_llm_reports=True):
        """
        Initialiser le processeur JSON générique
        
        Args:
            field_mappings: Dictionnaire de mappings de champs pour la transformation
            detect_fields: Si True, tente de détecter les champs clés 
            extract_keywords: Si True, extrait des mots-clés du contenu
            use_llm_fallback: Si True, utiliser un LLM pour réparer les JSON invalides
            llm_model: Modèle LLM à utiliser
            preserve_source: Si True, ne modifie jamais les fichiers sources
            generate_llm_reports: Si True, génère des rapports d'enrichissement LLM
        """
        self.field_mappings = field_mappings
        self.detect_fields = detect_fields
        self.extract_keywords = extract_keywords
        self.use_llm_fallback = use_llm_fallback
        self.llm_model = llm_model
        self.preserve_source = preserve_source
        self.generate_llm_reports = generate_llm_reports and generate_llm_summary is not None
    
    def load_file(self, file_path):
        """
        Charger un fichier JSON et le convertir en format standard
        
        Args:
            file_path: Chemin du fichier à charger
            
        Returns:
            Données standardisées
        """
        standardized, info = load_and_standardize_json(
            file_path, 
            llm_fallback=self.use_llm_fallback, 
            model=self.llm_model
        )
        
        return standardized
    
    def extract_items(self, data):
        """
        Extraire les éléments d'un objet JSON
        
        Args:
            data: Données JSON (standardisées ou non)
            
        Returns:
            Liste des éléments
        """
        return get_items_from_data(data)
    
    def transform_to_standard_format(self, data):
        """
        Transformer des données en format standard
        
        Args:
            data: Données à standardiser
            
        Returns:
            Données au format standard
        """
        standardized, _ = detect_json_structure(data)
        return standardized
    
    def save_as_json(self, data, output_path):
        """
        Sauvegarder des données au format JSON
        
        Args:
            data: Données à sauvegarder
            output_path: Chemin de sortie
            
        Returns:
            True si réussi
        """
        try:
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Données sauvegardées dans {output_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde dans {output_path}: {e}")
            return False
    
    def process_file(self, input_file, output_file=None, max_items=None, root_key="items", **kwargs):
        """
        Traite un fichier JSON en utilisant le mapper spécifié.
        
        Args:
            input_file: Chemin vers le fichier JSON d'entrée
            output_file: Chemin vers le fichier JSON de sortie (optionnel)
            max_items: Nombre maximum d'éléments à traiter
            root_key: Clé racine pour les éléments dans le JSON de sortie
            **kwargs: Arguments supplémentaires pour le processing
            
        Returns:
            bool: True si le traitement a réussi, False sinon
        """
        # Générer un output_file par défaut si non spécifié
        if output_file is None:
            base_name = os.path.basename(input_file)
            name, ext = os.path.splitext(base_name)
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            output_file = f"{name}_processed_{timestamp}{ext}"
        
        # Vérifier que le fichier d'entrée existe
        if not os.path.exists(input_file):
            print(f"Erreur: le fichier {input_file} n'existe pas.")
            return False
        
        # Vérifier la validité du fichier JSON
        try:
            # Essayer d'importer les outils de validation
            try:
                from tools import validate_file
                is_valid, error_msg = validate_file(input_file)
                if not is_valid:
                    print(f"Attention: Le fichier JSON n'est pas valide: {error_msg}")
                    print("Utilisation du parser robuste pour tenter de récupérer les données...")
            except ImportError:
                # Si tools n'est pas disponible, continuer sans vérification
                pass
        except Exception as e:
            print(f"Erreur lors de la vérification du fichier: {e}")
            # Continuer malgré l'erreur
        
        # Sauvegarde du fichier original si nécessaire
        if self.preserve_source and input_file != output_file:
            backup_dir = os.path.join(os.path.dirname(output_file), "source_backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, os.path.basename(input_file))
            try:
                # Vérifier si le fichier contient des données sensibles
                try:
                    from tools import clean_json_file
                    # Nettoyage avant la sauvegarde pour éviter les fuites de données sensibles
                    print("Nettoyage des données sensibles avant sauvegarde...")
                    clean_json_file(input_file, backup_file)
                    print(f"✅ Sauvegarde nettoyée créée: {backup_file}")
                except ImportError:
                    # Si le module de nettoyage n'est pas disponible, faire une copie simple
                    shutil.copy2(input_file, backup_file)
                    print(f"✅ Sauvegarde créée: {backup_file}")
            except Exception as e:
                print(f"⚠️ Erreur lors de la sauvegarde du fichier source: {e}")
        
        try:
            # Essai avec le parser robuste
            data = self.load_file(input_file)
            if not data:
                return False
            
            # Traiter les données
            processed_data = self.process_data(data, max_items=max_items, root_key=root_key)
            
            # Sauvegarder les données traitées
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Fichier traité et sauvegardé: {output_file}")
            
            # Générer un résumé LLM si demandé et si l'enrichissement LLM a été utilisé
            if self.generate_llm_reports and self.use_llm_fallback:
                try:
                    # Déterminer le répertoire de sortie
                    output_dir = os.path.dirname(output_file)
                    if not output_dir:
                        output_dir = "."
                    
                    # Nom du fichier de résumé basé sur le fichier de sortie
                    summary_filename = f"{os.path.splitext(os.path.basename(output_file))[0]}_llm_summary.md"
                    
                    # Générer le résumé
                    summary_file = generate_llm_summary(
                        output_dir, 
                        data=processed_data, 
                        filename=summary_filename
                    )
                    print(f"✅ Résumé LLM généré: {summary_file}")
                except Exception as e:
                    print(f"⚠️ Impossible de générer le résumé LLM: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_data(self, data, max_items=None, root_key="items"):
        """
        Traite les données JSON pour les standardiser et les enrichir
        
        Args:
            data: Données JSON à traiter
            max_items: Nombre maximum d'éléments à traiter
            root_key: Clé racine pour les éléments dans le JSON de sortie
            
        Returns:
            dict: Données traitées
        """
        items = self.extract_items(data)
        
        # Limiter le nombre d'éléments si demandé
        if max_items and len(items) > max_items:
            logger.info(f"Limitation à {max_items} éléments (sur {len(items)})")
            items = items[:max_items]
        
        # Transformer les éléments si des mappings sont définis
        processed_items = items
        if self.field_mappings:
            processed_items = self._transform_items(items)
        
        # Extraire des mots-clés si demandé
        if self.extract_keywords:
            processed_items = self._extract_keywords_from_items(processed_items)
        
        # Créer les métadonnées
        metadata = {
            "source_file": data.get("metadata", {}).get("source_file", "unknown"),
            "processed_at": datetime.now().isoformat(),
            "processor_version": "1.0",
            "items_count": len(processed_items),
            "stats": {
                "total_items": len(items),
                "processed_items": len(processed_items)
            }
        }
        
        # Assembler les données finales
        result = {
            root_key: processed_items,
            "metadata": metadata
        }
        
        return result
    
    def _transform_items(self, items):
        """
        Transforme les éléments selon les mappings définis
        
        Args:
            items: Liste d'éléments à transformer
            
        Returns:
            Liste d'éléments transformés
        """
        # Simple implémentation, à compléter selon les besoins spécifiques
        transformed = []
        for item in items:
            new_item = {}
            for target_key, source_path in self.field_mappings.items():
                # Gestion simple des chemins plats
                if isinstance(source_path, str) and source_path in item:
                    new_item[target_key] = item[source_path]
                # Gestion des objets imbriqués
                elif isinstance(source_path, dict) and "field" in source_path:
                    field = source_path["field"]
                    if field in item:
                        # Appliquer une transformation si spécifiée
                        if "transform" in source_path:
                            transform = source_path["transform"]
                            if transform == "clean_text":
                                new_item[target_key] = self._clean_text(item[field])
                            # Ajouter d'autres transformations selon les besoins
                        else:
                            new_item[target_key] = item[field]
            
            # Si aucun mapping n'a été appliqué, conserver l'élément original
            if not new_item and self.detect_fields:
                new_item = self._detect_and_map_fields(item)
            elif not new_item:
                new_item = item
            
            transformed.append(new_item)
        
        return transformed
    
    def _detect_and_map_fields(self, item):
        """
        Détecte et mappe automatiquement les champs communs
        
        Args:
            item: Élément à analyser
            
        Returns:
            Élément avec champs mappés
        """
        result = {}
        
        # Détecter le champ ID (key, id, _id, etc.)
        for id_field in ["key", "id", "_id", "uuid", "identifier"]:
            if id_field in item:
                result["id"] = item[id_field]
                break
        
        # Détecter le champ titre (title, summary, name, etc.)
        for title_field in ["title", "summary", "name", "header", "subject"]:
            if title_field in item:
                result["title"] = item[title_field]
                break
        
        # Détecter le contenu (content, body, text, description, etc.)
        content = {}
        for content_field in ["content", "body", "text", "description", "markdown"]:
            if content_field in item:
                if isinstance(item[content_field], dict):
                    content = item[content_field]
                else:
                    content["text"] = item[content_field]
                break
        
        if content:
            result["content"] = content
        
        # Détecter les métadonnées (created_at, updated_at, author, etc.)
        metadata = {}
        date_fields = {
            "created_at": ["created", "created_at", "createdAt", "date_created"],
            "updated_at": ["updated", "updated_at", "updatedAt", "modified", "lastModified"]
        }
        
        author_fields = ["author", "creator", "created_by", "createdBy", "reporter"]
        
        for meta_key, field_names in date_fields.items():
            for field in field_names:
                if field in item:
                    metadata[meta_key] = item[field]
                    break
        
        for field in author_fields:
            if field in item:
                metadata["created_by"] = item[field]
                break
        
        if metadata:
            result["metadata"] = metadata
        
        # Si aucun champ clé n'a été trouvé, retourner l'élément original
        if not result or (len(result) == 1 and "metadata" in result):
            return item
        
        # Copier les champs restants qui n'ont pas été mappés
        for key, value in item.items():
            if key not in ["key", "id", "_id", "uuid", "identifier", 
                          "title", "summary", "name", "header", "subject",
                          "content", "body", "text", "description", "markdown"] + \
                         date_fields["created_at"] + date_fields["updated_at"] + author_fields:
                if key not in result:
                    result[key] = value
        
        return result
    
    def _extract_keywords_from_items(self, items):
        """
        Extrait des mots-clés du contenu des éléments
        
        Args:
            items: Liste d'éléments
            
        Returns:
            Liste d'éléments enrichis avec des mots-clés
        """
        import re
        from collections import Counter
        
        # Liste des mots vides (stop words) en français
        stop_words = set([
            "le", "la", "les", "un", "une", "des", "et", "est", "il", "elle", "nous", "vous", 
            "ils", "elles", "son", "sa", "ses", "leur", "leurs", "ce", "cette", "ces", "que", 
            "qui", "quoi", "dont", "où", "quand", "comment", "pourquoi", "avec", "sans", "pour", 
            "par", "dans", "sur", "sous", "de", "du", "au", "aux", "à", "en", "vers", "chez"
        ])
        
        enhanced_items = []
        for item in items:
            # Récupérer le texte depuis différents champs possibles
            text = ""
            if "content" in item:
                if isinstance(item["content"], dict):
                    for k, v in item["content"].items():
                        if isinstance(v, str):
                            text += v + " "
                elif isinstance(item["content"], str):
                    text += item["content"] + " "
            
            if "title" in item and isinstance(item["title"], str):
                text += item["title"] + " "
            
            if "description" in item and isinstance(item["description"], str):
                text += item["description"] + " "
            
            # Extraire les mots
            words = re.findall(r'\b\w{3,}\b', text.lower())
            
            # Filtrer les mots vides
            filtered_words = [w for w in words if w not in stop_words]
            
            # Compter les occurrences
            word_counts = Counter(filtered_words)
            
            # Sélectionner les mots-clés les plus fréquents (max 10)
            keywords = [word for word, count in word_counts.most_common(10)]
            
            # Ajouter les mots-clés à l'élément
            if "analysis" not in item:
                item["analysis"] = {}
            
            item["analysis"]["keywords"] = keywords
            enhanced_items.append(item)
        
        return enhanced_items
    
    def _clean_text(self, text):
        """
        Nettoie le texte (supprime les balises HTML, etc.)
        
        Args:
            text: Texte à nettoyer
            
        Returns:
            Texte nettoyé
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Supprimer les balises HTML (implémentation simple)
        import re
        clean = re.sub(r'<[^>]+>', '', text)
        
        # Normaliser les espaces
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        return clean
    
    def analyze_structure(self, file_path, output_dir, output_filename=None):
        """
        Analyser la structure d'un fichier JSON
        
        Args:
            file_path: Chemin du fichier à analyser
            output_dir: Répertoire pour le rapport
            output_filename: Nom du fichier de rapport (optionnel)
            
        Returns:
            Chemin du rapport généré
        """
        return write_file_structure(file_path, output_dir, output_filename)
    
    def generate_directory_tree(self, directory, output_filename="arborescence.txt"):
        """
        Générer l'arborescence d'un répertoire
        
        Args:
            directory: Répertoire à analyser
            output_filename: Nom du fichier d'arborescence
            
        Returns:
            True si réussi
        """
        return write_tree(directory, output_filename)

# Pour utilisation en import
if __name__ == "__main__":
    # Si exécuté directement, faire une démonstration
    import argparse
    
    parser = argparse.ArgumentParser(description="Traiter génériquement des fichiers JSON")
    parser.add_argument("--file", "-f", help="Fichier JSON à analyser")
    parser.add_argument("--dir", "-d", help="Répertoire à analyser")
    parser.add_argument("--output", "-o", default="output", help="Répertoire de sortie")
    parser.add_argument("--repair", "-r", action="store_true", help="Tenter de réparer les fichiers JSON invalides")
    
    args = parser.parse_args()
    
    if args.file:
        # Analyser un seul fichier
        processor = GenericJsonProcessor(use_llm_fallback=args.repair)
        
        # Créer le répertoire de sortie si nécessaire
        os.makedirs(args.output, exist_ok=True)
        
        # Générer le rapport de structure
        analysis_path = processor.analyze_structure(args.file, args.output)
        print(f"Rapport de structure généré: {analysis_path}")
        
        # Charger et standardiser le fichier
        data = processor.load_file(args.file)
        if data:
            items = processor.extract_items(data)
            print(f"Nombre d'éléments trouvés: {len(items)}")
            
            # Sauvegarder en format standard
            standardized_path = os.path.join(args.output, "standardized.json")
            processor.save_as_json(data, standardized_path)
            print(f"Format standardisé sauvegardé dans: {standardized_path}")
    
    elif args.dir:
        # Analyser un répertoire
        processor = GenericJsonProcessor()
        tree_path = os.path.join(args.dir, "arborescence.txt")
        processor.generate_directory_tree(args.dir, os.path.basename(tree_path))
        print(f"Arborescence générée: {tree_path}")
    
    else:
        parser.print_help() 