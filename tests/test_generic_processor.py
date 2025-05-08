#!/usr/bin/env python3
"""
Script de test pour notre processeur JSON générique.
Teste la capacité à charger et analyser différents formats JSON.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_generic_processor")

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Importer notre processeur générique
    from extract.generic_json_processor import GenericJsonProcessor, detect_json_structure
except ImportError:
    print("Erreur d'importation du module. Tentative alternative...")
    # Essayer un chemin alternatif
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract"))
    from generic_json_processor import GenericJsonProcessor, detect_json_structure

def test_file_loading(file_path):
    """Tester le chargement d'un fichier JSON"""
    print(f"\n==== Test de chargement: {os.path.basename(file_path)} ====")
    processor = GenericJsonProcessor(use_llm_fallback=True)
    
    try:
        data = processor.load_file(file_path)
        if data:
            print(f"✅ Fichier chargé avec succès")
            
            # Extraire les éléments
            items = processor.extract_items(data)
            print(f"✅ {len(items)} éléments trouvés")
            
            # Afficher un échantillon du premier élément
            if items:
                print(f"\nPremier élément (échantillon):")
                if isinstance(items[0], dict):
                    sample = {k: items[0][k] for k in list(items[0].keys())[:5]}
                    print(json.dumps(sample, indent=2, ensure_ascii=False)[:500] + "...")
                else:
                    print(f"Type: {type(items[0])}")
            
            return True
        else:
            print(f"❌ Échec du chargement")
            return False
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_structure_detection(file_path):
    """Tester la détection de structure JSON"""
    print(f"\n==== Test de détection de structure: {os.path.basename(file_path)} ====")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        standardized, info = detect_json_structure(data)
        
        print(f"✅ Structure détectée: {info['data_format']}")
        print(f"✅ Type original: {info['original_type']}")
        print(f"✅ Nombre d'éléments: {info['item_count']}")
        if info['detected_item_type']:
            print(f"✅ Type d'élément détecté: {info['detected_item_type']}")
        
        # Vérifier que les éléments ont été correctement extraits
        items = standardized.get("items", [])
        print(f"✅ {len(items)} éléments extraits après standardisation")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Fichiers à tester
    test_files = [
        "files/CARTAN_jira.json",
        "files/hollard_confluence.json"
    ]
    
    # Résultats des tests
    results = {}
    
    # Tester chaque fichier
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"❌ Le fichier n'existe pas: {file_path}")
            results[file_path] = False
            continue
        
        # Tester le chargement
        load_result = test_file_loading(file_path)
        
        # Si le chargement a réussi, tester la détection de structure
        structure_result = False
        if load_result:
            structure_result = test_structure_detection(file_path)
        
        # Enregistrer les résultats
        results[file_path] = load_result and structure_result
    
    # Afficher le résumé
    print("\n==== RÉSUMÉ DES TESTS ====")
    for file_path, success in results.items():
        status = "✅ RÉUSSI" if success else "❌ ÉCHOUÉ"
        print(f"{status}: {file_path}")
    
    # Retourner le statut global
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 