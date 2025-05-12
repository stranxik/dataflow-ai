#!/usr/bin/env python3
"""
Script pour tester directement l'API d'extraction PDF
"""

import os
import sys
import requests
import json
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api/pdf/extract-images"
API_KEY = os.getenv("API_KEY")
DEFAULT_PDF = "files/1744005520250-10-11.pdf"  # Chemin par défaut du PDF à tester
OUTPUT_DIR = "test_api_results"  # Répertoire où sauvegarder les résultats

def test_api(pdf_path, format="zip", max_images=10):
    """Tester l'API d'extraction PDF"""
    print(f"Testing API with PDF: {pdf_path}")
    print(f"Format: {format}, Max images: {max_images}")
    
    # Vérifier que le fichier existe
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist")
        return False
    
    # Préparer la requête
    headers = {"X-API-Key": API_KEY}
    data = {"max_images": max_images, "format": format}
    
    # Ouvrir le fichier PDF
    files = {"file": open(pdf_path, "rb")}
    
    try:
        # Envoyer la requête
        print("Sending request to API...")
        response = requests.post(API_URL, headers=headers, data=data, files=files)
        
        # Fermer le fichier
        files["file"].close()
        
        # Vérifier que la requête a réussi
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response content: {response.text}")
            return False
        
        # Créer le répertoire de sortie
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Déterminer le nom du fichier de sortie
        base_name = os.path.basename(pdf_path).rsplit(".", 1)[0]
        output_filename = f"{base_name}_api_test.{format}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Écrire la réponse dans un fichier
        print(f"Writing response to {output_path}")
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        # Afficher la taille du fichier
        file_size = os.path.getsize(output_path)
        print(f"Output file size: {file_size} bytes")
        
        # Vérifier que le fichier n'est pas vide
        if file_size == 0:
            print("Error: Output file is empty")
            return False
        
        # Si c'est un format JSON, afficher une partie du contenu
        if format.lower() == "json":
            try:
                content = json.loads(response.content)
                print(f"JSON content preview: {json.dumps(content, indent=2)[:200]}...")
            except Exception as e:
                print(f"Error parsing JSON: {e}")
        
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Utiliser le PDF spécifié en argument ou le PDF par défaut
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    
    # Tester l'API avec le format JSON
    print("\n=== Testing API with JSON format ===")
    test_api(pdf_path, format="json")
    
    # Tester l'API avec le format ZIP
    print("\n=== Testing API with ZIP format ===")
    test_api(pdf_path, format="zip")
    
    print("\nTest completed!") 