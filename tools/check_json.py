#!/usr/bin/env python3
import json
import sys
import os
import glob

def check_json_file(file_path):
    """Vérifier si un fichier JSON est valide"""
    print(f"Vérification de {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✅ Fichier valide: {file_path}")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON: {e} dans {file_path}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e} dans {file_path}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Vérifier un seul fichier ou un dossier spécifique
        path = sys.argv[1]
        if os.path.isdir(path):
            # C'est un dossier, trouver tous les fichiers JSON
            json_files = glob.glob(os.path.join(path, "**", "*.json"), recursive=True)
            valid_count = 0
            for file_path in json_files:
                if check_json_file(file_path):
                    valid_count += 1
            print(f"\nBilan: {valid_count}/{len(json_files)} fichiers valides")
        else:
            # C'est un fichier unique
            check_json_file(path)
    else:
        print("Usage: python check_json.py <path_to_json_file_or_directory>") 