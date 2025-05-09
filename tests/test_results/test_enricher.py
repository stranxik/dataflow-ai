#!/usr/bin/env python3
"""
Script de test pour le nouveau module d'enrichissement LLM.
"""

import os
import sys
import json
from pathlib import Path

# Ajouter le répertoire parent au chemin Python
current_dir = Path(__file__).parent.absolute()
root_dir = current_dir.parent.parent
sys.path.append(str(root_dir))

# Importer le module à tester
try:
    from extract.outlines_enricher import enrich_with_llm, extract_content_from_item, check_outlines
    print("✅ Module d'enrichissement importé avec succès")
except ImportError as e:
    print(f"❌ Erreur lors de l'import du module d'enrichissement: {e}")
    sys.exit(1)

# Vérifier Outlines
outlines_available = check_outlines()
print(f"Outlines disponible: {outlines_available}")

# Créer des données de test
test_item = {
    "id": "TEST-123",
    "title": "Test d'enrichissement LLM",
    "description": "Ceci est un test d'enrichissement via LLM avec Outlines 0.2.3.",
    "type": "test"
}

# Afficher des informations sur l'environnement
print("\n=== Extraction de contenu ===")
content = extract_content_from_item(test_item)
print(f"Contenu extrait ({len(content)} caractères):")
print(content)

# Vérifier la clé API OpenAI
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("\n❌ Clé API OpenAI non trouvée dans les variables d'environnement")
    print("Définissez OPENAI_API_KEY pour exécuter les tests d'enrichissement")
    sys.exit(1)

# Tester l'enrichissement
print("\n=== Test d'enrichissement LLM ===")
print("Enrichissement en cours...")
enriched_item = enrich_with_llm(test_item, model_name="gpt-4-0125-preview")

# Vérifier que l'enrichissement a fonctionné
if enriched_item and "analysis" in enriched_item and "llm_summary" in enriched_item["analysis"]:
    print("✅ Enrichissement LLM réussi")
    print("\nRésumé généré:")
    print(enriched_item["analysis"]["llm_summary"])
    print("\nMots-clés:")
    print(enriched_item["analysis"]["llm_keywords"])
    print("\nSentiment:")
    print(enriched_item["analysis"]["llm_sentiment"])
else:
    print("❌ L'enrichissement n'a pas généré d'analyse")

print("\n=== Tests terminés ===") 