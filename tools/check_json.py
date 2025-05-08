#!/usr/bin/env python3
"""
Utilitaire pour vérifier la validité des fichiers JSON.
Peut être utilisé en ligne de commande ou comme module.
"""

import json
import sys
import os
import glob

def validate_file(file_path, silent=True):
    """
    Vérifier si un fichier JSON est valide sans affichage.
    
    Args:
        file_path: Chemin vers le fichier JSON à vérifier
        silent: Si True, ne pas afficher de messages
        
    Returns:
        (bool, str): (valide, message d'erreur si invalide)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Erreur JSON: {e}"
    except Exception as e:
        return False, f"Erreur: {e}"

def check_json_file(file_path):
    """
    Vérifier si un fichier JSON est valide avec affichage.
    
    Args:
        file_path: Chemin vers le fichier JSON à vérifier
        
    Returns:
        bool: True si le fichier est valide, False sinon
    """
    print(f"Vérification de {file_path}...")
    valid, error = validate_file(file_path, silent=True)
    
    if valid:
        print(f"✅ Fichier valide: {file_path}")
        return True
    else:
        print(f"❌ {error} dans {file_path}")
        return False

def check_directory(directory, recursive=True):
    """
    Vérifier tous les fichiers JSON d'un répertoire.
    
    Args:
        directory: Chemin vers le répertoire à vérifier
        recursive: Si True, chercher récursivement dans les sous-répertoires
        
    Returns:
        (int, int): (nombre de fichiers valides, nombre total de fichiers)
    """
    json_files = glob.glob(os.path.join(directory, "**", "*.json"), recursive=recursive)
    valid_count = 0
    
    for file_path in json_files:
        if check_json_file(file_path):
            valid_count += 1
            
    return valid_count, len(json_files)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Vérifier un seul fichier ou un dossier spécifique
        path = sys.argv[1]
        if os.path.isdir(path):
            # C'est un dossier, trouver tous les fichiers JSON
            valid_count, total_count = check_directory(path)
            print(f"\nBilan: {valid_count}/{total_count} fichiers valides")
        else:
            # C'est un fichier unique
            check_json_file(path)
    else:
        print("Usage: python check_json.py <path_to_json_file_or_directory>") 