#!/usr/bin/env python3
"""
Script de test pour l'extraction de PDF en ligne de commande.
Ce script teste directement la commande CLI pour identifier les problèmes.
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Test PDF extraction")
    parser.add_argument("pdf_file", help="Path to the PDF file to process")
    parser.add_argument("--max-images", type=int, default=10, help="Maximum number of images to extract")
    parser.add_argument("--create-zip", action="store_true", help="Create a ZIP of the output")
    
    args = parser.parse_args()
    
    # Obtenir les chemins absolus
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Vérifier que le fichier PDF existe
    pdf_path = os.path.abspath(args.pdf_file)
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        return 1
    
    print(f"Testing PDF extraction with file: {pdf_path}")
    print(f"Base directory: {base_dir}")
    
    # Créer un répertoire de sortie
    timestamp = Path(pdf_path).stem + "_test"
    output_dir = os.path.join(base_dir, "results", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    
    # Construire la commande CLI
    python_exec = sys.executable
    cmd = [
        python_exec, "-m", "cli.cli", "extract-images", "complete",
        pdf_path,
        "--output", output_dir,
        "--max-images", str(args.max_images)
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Exécuter la commande
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            env=os.environ.copy()
        )
        
        print("Command successful")
        print(f"Output: {result.stdout[:500]}..." if len(result.stdout) > 500 else f"Output: {result.stdout}")
        
        # Lister les fichiers générés
        print("\nFiles generated:")
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                print(f" - {os.path.join(root, file)}")
        
        # Créer un ZIP si demandé
        if args.create_zip:
            zip_path = output_dir + ".zip"
            print(f"\nCreating ZIP archive: {zip_path}")
            
            # S'assurer que le fichier ZIP n'existe pas déjà
            if os.path.exists(zip_path):
                os.remove(zip_path)
            
            # Créer le ZIP
            shutil.make_archive(
                base_name=os.path.splitext(zip_path)[0],
                format='zip',
                root_dir=os.path.dirname(output_dir),
                base_dir=os.path.basename(output_dir)
            )
            
            print(f"ZIP archive created: {zip_path}")
            print(f"ZIP size: {os.path.getsize(zip_path)} bytes")
        
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        print(f"Error output: {e.stderr}")
        return e.returncode
    except Exception as e:
        print(f"Error running command: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 