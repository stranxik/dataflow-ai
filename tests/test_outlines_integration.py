#!/usr/bin/env python3
"""
Script de test d'intégration d'Outlines dans le système.
Vérifie que tous les composants fonctionnent correctement ensemble.
"""

import os
import sys
import json
from pathlib import Path

# Configurer les chemins
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Importer les modules à tester
try:
    from extract import (
        outlines_robust_json_parser, 
        extract_entities, 
        extract_structured_data,
        is_using_stub,
        get_outlines_status
    )
    
    print("✅ Import des modules réussi")
except ImportError as e:
    print(f"❌ Erreur lors de l'import des modules: {e}")
    sys.exit(1)

# Vérifier le statut d'Outlines
status = get_outlines_status()
print(f"\n=== Statut d'Outlines ===")
for key, value in status.items():
    print(f"- {key}: {value}")

if is_using_stub():
    print("⚠️ Utilisation des stubs Outlines (fonctionnalités limitées)")
else:
    print("✅ Utilisation de la bibliothèque Outlines")

# Exemple d'extraction d'entités
test_text = """
Contactez john.doe@example.com concernant le ticket PROJ-123.
L'entreprise Google travaille avec Microsoft sur ce projet.
"""

print("\n=== Test d'extraction d'entités ===")
try:
    entities = extract_entities(test_text)
    print("Entités extraites:")
    for entity_type, items in entities.items():
        print(f"- {entity_type}: {items}")
    print("✅ Extraction d'entités réussie")
except Exception as e:
    print(f"❌ Erreur lors de l'extraction d'entités: {e}")

# Test de parsing JSON
test_json = """
{
    "name": "Test",
    "items": [1, 2, 3],
    "metadata": {
        "created": "2023-01-01"
    }
}
"""

print("\n=== Test de parsing JSON ===")
try:
    # Sauvegarder dans un fichier temporaire
    temp_file = current_dir / "temp_test.json"
    with open(temp_file, "w") as f:
        f.write(test_json)
    
    # Parser le fichier
    result = outlines_robust_json_parser(str(temp_file), llm_fallback=False)
    print(f"Structure: {type(result)}")
    print(f"Contenu: {json.dumps(result, indent=2)[:100]}...")
    print("✅ Parsing JSON réussi")
    
    # Supprimer le fichier temporaire
    os.remove(temp_file)
except Exception as e:
    print(f"❌ Erreur lors du parsing JSON: {e}")

# Test d'extraction structurée
print("\n=== Test d'extraction structurée ===")
try:
    schema = {
        "type": "object",
        "properties": {
            "extracted_name": {"type": "string"},
            "count": {"type": "integer"}
        }
    }
    
    # Ne pas exécuter l'extraction si nous utilisons les stubs ou si pas de clé API
    if is_using_stub() or not os.environ.get("OPENAI_API_KEY"):
        print("⚠️ Test ignoré (stub ou pas de clé API)")
    else:
        data = extract_structured_data(test_json, schema)
        print(f"Données extraites: {data}")
        print("✅ Extraction structurée réussie")
except Exception as e:
    print(f"❌ Erreur lors de l'extraction structurée: {e}")

print("\n=== Tests terminés ===") 