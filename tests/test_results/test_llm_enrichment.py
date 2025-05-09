#!/usr/bin/env python3
"""
Test d'enrichissement LLM avec Outlines.
Ce script vérifie si l'enrichissement LLM fonctionne correctement dans l'application.
"""

import os
import sys
import json
from pathlib import Path

# Ajouter le répertoire parent au chemin Python
current_dir = Path(__file__).parent.absolute()
root_dir = current_dir.parent.parent
sys.path.append(str(root_dir))

print(f"Environnement d'exécution:")
print(f"- Python: {sys.version}")
print(f"- Répertoire courant: {os.getcwd()}")
print(f"- Répertoire racine: {root_dir}")

# Vérifier les imports d'Outlines
print("\n=== Vérification des imports d'Outlines ===")
try:
    import outlines
    print(f"✅ Outlines importé")
    print(f"- Chemin: {outlines.__file__}")
    module_content = dir(outlines)
    print(f"- Contenu: {', '.join(module_content[:10])}...")
    
    # Vérifier la présence de Template
    if 'Template' in module_content:
        from outlines import Template
        print("✅ Template disponible")
    else:
        print("❌ Template non disponible")
    
    # Vérifier models
    if 'models' in module_content:
        from outlines import models
        print("✅ models disponible")
    else:
        print("❌ models non disponible")
        
    # Vérifier generate
    if 'generate' in module_content:
        from outlines import generate
        print("✅ generate disponible")
    else:
        print("❌ generate non disponible")
except ImportError as e:
    print(f"❌ Erreur lors de l'import d'Outlines: {e}")

# Vérifier les imports de notre module extract
print("\n=== Vérification des imports de extract ===")
try:
    from extract import outlines_robust_json_parser, extract_entities, is_using_stub
    print(f"✅ Modules extract importés")
    print(f"- Utilisation des stubs: {is_using_stub()}")
except ImportError as e:
    print(f"❌ Erreur lors de l'import des modules extract: {e}")

# Vérifier la clé API OpenAI
print("\n=== Vérification de la clé API OpenAI ===")
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    print(f"✅ Clé API OpenAI trouvée: {api_key[:8]}...{api_key[-4:]}")
else:
    print("❌ Clé API OpenAI non trouvée")

# Test d'enrichissement LLM avec un exemple simple
print("\n=== Test d'enrichissement LLM ===")
try:
    from extract.outlines_extractor import enrich_with_llm
    
    # Exemple de données à enrichir
    sample_data = {
        "title": "Problème avec l'API de paiement",
        "description": "Lors de l'intégration de l'API de paiement Stripe, les transactions échouent pour certains clients avec une erreur 500."
    }
    
    print(f"Données à enrichir: {json.dumps(sample_data, indent=2)}")
    
    # Tentative d'enrichissement
    try:
        enriched = enrich_with_llm(sample_data, model_name="gpt-4")
        print(f"✅ Enrichissement réussi:")
        print(json.dumps(enriched, indent=2))
    except Exception as e:
        print(f"❌ Erreur lors de l'enrichissement: {e}")
        import traceback
        print(traceback.format_exc())
except ImportError as e:
    print(f"❌ Module d'enrichissement non disponible: {e}")

# Test avec notre implémentation personnalisée
print("\n=== Test avec notre implementation personnalisée ===")
try:
    from extract.llm_summary import generate_llm_summary
    
    # Créer des données de test
    test_data = {
        "items": [
            {
                "id": "TEST-123",
                "title": "Test ticket",
                "content": {"description": "Ceci est un test"},
                "analysis": {
                    "llm_summary": "Résumé de test",
                    "llm_keywords": ["test", "exemple"],
                    "llm_sentiment": "neutral"
                }
            }
        ],
        "metadata": {
            "llm_enrichment": {
                "model": "gpt-4",
                "enrichment_date": "2025-05-10"
            }
        }
    }
    
    # Générer un résumé dans le dossier de test
    summary_file = generate_llm_summary(
        output_dir=str(current_dir),
        data=test_data,
        filename="test_summary.md"
    )
    
    print(f"✅ Résumé généré: {summary_file}")
    
    # Lire le contenu du résumé
    if os.path.exists(summary_file):
        with open(summary_file, "r", encoding="utf-8") as f:
            print(f"Contenu du résumé (extrait):")
            content = f.read()
            print(content[:200] + "...")
    else:
        print(f"❌ Fichier de résumé non trouvé")
    
except Exception as e:
    print(f"❌ Erreur lors du test de génération de résumé: {e}")
    import traceback
    print(traceback.format_exc())

print("\n=== Tests terminés ===") 