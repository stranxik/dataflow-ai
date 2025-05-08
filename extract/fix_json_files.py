#!/usr/bin/env python3
"""
Script de réparation des fichiers JSON erronés dans les résultats.
Ce script parcourt les dossiers de résultats et tente de réparer les fichiers JSON mal formés.
"""

import os
import re
import json
import sys
import glob
import logging
from pathlib import Path
import traceback

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("json_fixer")

def escape_special_chars_in_strings(content):
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

def fix_unclosed_strings(content):
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

def fix_missing_quotes_around_property_names(content):
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

def fix_trailing_commas(content):
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

def repair_json_file(file_path):
    """
    Réparer un fichier JSON
    
    Args:
        file_path: Chemin du fichier à réparer
    
    Returns:
        True si réparé avec succès, False sinon
    """
    logger.info(f"Réparation du fichier JSON: {file_path}")
    
    try:
        # Lire le contenu du fichier
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si le JSON est déjà valide
        try:
            json.loads(content)
            logger.info(f"Le fichier est déjà un JSON valide: {file_path}")
            return True
        except json.JSONDecodeError as e:
            logger.info(f"Erreur JSON détectée: {str(e)}")
        
        # Appliquer les corrections
        content = escape_special_chars_in_strings(content)
        content = fix_unclosed_strings(content)
        content = fix_missing_quotes_around_property_names(content)
        content = fix_trailing_commas(content)
        
        # Vérifier si le JSON est maintenant valide
        try:
            parsed_json = json.loads(content)
            
            # Sauvegarder le fichier réparé
            backup_path = f"{file_path}.backup"
            os.rename(file_path, backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_json, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Fichier réparé avec succès: {file_path}")
            logger.info(f"   Sauvegarde créée: {backup_path}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Échec de la réparation automatique: {str(e)}")
            
            # Sauvegarde du contenu partiellement réparé pour analyse manuelle
            partial_path = f"{file_path}.partial_fix"
            with open(partial_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"   Réparation partielle sauvegardée dans: {partial_path}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la réparation: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def find_and_repair_json_files(results_dir, recursive=True):
    """
    Trouver et réparer tous les fichiers JSON dans un répertoire
    
    Args:
        results_dir: Répertoire à analyser
        recursive: Si True, recherche récursivement dans les sous-répertoires
    
    Returns:
        Tuple (fixed_count, error_count)
    """
    pattern = os.path.join(results_dir, "**", "*.json") if recursive else os.path.join(results_dir, "*.json")
    json_files = glob.glob(pattern, recursive=recursive)
    
    fixed_count = 0
    error_count = 0
    skipped_count = 0
    
    logger.info(f"Fichiers JSON trouvés: {len(json_files)}")
    
    for file_path in json_files:
        # Vérifier si le fichier est lisible (non vide)
        if os.path.getsize(file_path) == 0:
            logger.warning(f"⚠️ Fichier vide ignoré: {file_path}")
            skipped_count += 1
            continue
            
        # Tenter de réparer le fichier
        if repair_json_file(file_path):
            fixed_count += 1
        else:
            error_count += 1
    
    return fixed_count, error_count, skipped_count

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Réparer les fichiers JSON erronés dans les dossiers de résultats")
    parser.add_argument("--dir", default="results", help="Répertoire de résultats à analyser")
    parser.add_argument("--recursive", action="store_true", help="Rechercher récursivement dans les sous-répertoires")
    parser.add_argument("--specific-file", help="Chemin d'un fichier spécifique à réparer")
    
    args = parser.parse_args()
    
    if args.specific_file:
        # Réparer un fichier spécifique
        if repair_json_file(args.specific_file):
            logger.info(f"✅ Fichier réparé avec succès: {args.specific_file}")
        else:
            logger.error(f"❌ Échec de la réparation: {args.specific_file}")
    else:
        # Réparer tous les fichiers dans le répertoire
        fixed_count, error_count, skipped_count = find_and_repair_json_files(args.dir, args.recursive)
        
        logger.info(f"\n=== Résumé de la réparation ===")
        logger.info(f"✅ Fichiers réparés: {fixed_count}")
        logger.info(f"❌ Fichiers avec erreurs: {error_count}")
        logger.info(f"⚠️ Fichiers ignorés: {skipped_count}")
        logger.info(f"Total: {fixed_count + error_count + skipped_count}")

if __name__ == "__main__":
    main() 