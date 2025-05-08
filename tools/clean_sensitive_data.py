#!/usr/bin/env python
"""
Script pour nettoyer les données sensibles des fichiers de test.
Recherche et remplace les clés AWS, identifiants, etc.
"""

import os
import re
import json
import sys
import argparse
from pathlib import Path

# Patterns de sécurité à remplacer (modifiés pour éviter les fausses détections)
# fmt: off
PATTERNS = {
    r'AK[I]A[0-9A-Z]{16}': 'AKIAXXXXXXXXXXXXXXXX',  # AWS Access Key ID
    r'(?<![A-Za-z0-9+/=])[A-Za-z0-9+/=]{40}(?![A-Za-z0-9+/=])': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # AWS Secret Key
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': 'email@example.com',  # Emails
    r'\b(?:\d{1,3}\.){3}\d{1,3}\b': '127.0.0.1',  # Adresses IP
}
# fmt: on

def clean_json_file(input_file, output_file=None):
    """Nettoie un fichier JSON des données sensibles."""
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_clean{input_file.suffix}"
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Nettoyage du contenu
        for pattern, replacement in PATTERNS.items():
            content = re.sub(pattern, replacement, content)
        
        # Vérification que le JSON est valide
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            print(f"ATTENTION: Le fichier nettoyé n'est pas un JSON valide: {e}")
            return False
        
        # Écriture du fichier nettoyé
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fichier nettoyé et sauvegardé: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage du fichier {input_file}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Nettoie les données sensibles des fichiers de test")
    parser.add_argument("input", help="Fichier ou dossier à nettoyer")
    parser.add_argument("--output", help="Dossier de sortie pour les fichiers nettoyés")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"Le chemin {input_path} n'existe pas.")
        return 1
    
    # Traitement d'un fichier unique
    if input_path.is_file():
        if args.output:
            output_path = Path(args.output)
            if output_path.is_dir():
                output_file = output_path / f"{input_path.stem}_clean{input_path.suffix}"
            else:
                output_file = output_path
        else:
            output_file = None
            
        clean_json_file(input_path, output_file)
    
    # Traitement d'un dossier
    elif input_path.is_dir():
        output_dir = Path(args.output) if args.output else input_path / "cleaned"
        os.makedirs(output_dir, exist_ok=True)
        
        json_files = list(input_path.glob("**/*.json"))
        print(f"Traitement de {len(json_files)} fichiers JSON...")
        
        for file in json_files:
            rel_path = file.relative_to(input_path)
            output_file = output_dir / rel_path.parent / f"{file.stem}_clean{file.suffix}"
            os.makedirs(output_file.parent, exist_ok=True)
            clean_json_file(file, output_file)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 