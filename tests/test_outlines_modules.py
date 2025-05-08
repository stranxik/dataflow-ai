#!/usr/bin/env python3
"""
Script de test pour vérifier les modules spécifiques d'Outlines 0.2.3
"""

import sys

print(f"Python version: {sys.version}")

print("\n=== Test d'importation d'Outlines 0.2.3 ===")
try:
    import outlines
    print(f"Version d'Outlines: {outlines.__version__ if hasattr(outlines, '__version__') else 'Non disponible'}")
    print(f"Chemin: {outlines.__file__}")
    print(f"Contenu du module principal: {sorted(dir(outlines))}")
except ImportError as e:
    print(f"Erreur lors de l'import d'Outlines: {e}")

# Testons l'import des modules utilisés dans notre code selon la nouvelle API
print("\n=== Test des modules spécifiques ===")

# Test pour generate
print("\n1. Test d'import: outlines.generate")
try:
    import outlines.generate
    print(f"Module generate trouvé: {outlines.generate}")
    print(f"Attributs: {dir(outlines.generate)}")
    
    # Vérifier si les fonctions importantes existent
    for func in ['text', 'regex', 'json', 'choice', 'cfg', 'format']:
        if hasattr(outlines.generate, func):
            print(f"La fonction '{func}' existe dans outlines.generate")
        else:
            print(f"La fonction '{func}' n'existe PAS dans outlines.generate")
except ImportError as e:
    print(f"Erreur lors de l'import de outlines.generate: {e}")

# Test pour models
print("\n2. Test d'import: outlines.models")
try:
    from outlines import models
    print(f"Module models trouvé: {models}")
    print(f"Attributs: {dir(models)}")
    
    # Vérifier si les fonctions importantes existent
    for func in ['openai', 'transformers']:
        if hasattr(models, func):
            print(f"La fonction '{func}' existe dans models")
        else:
            print(f"La fonction '{func}' n'existe PAS dans models")
except ImportError as e:
    print(f"Erreur lors de l'import de models: {e}")

# Test pour samplers
print("\n3. Test d'import: outlines.samplers")
try:
    from outlines import samplers
    print(f"Module samplers trouvé: {samplers}")
    print(f"Attributs: {dir(samplers)}")
    
    # Vérifier les samplers importants
    for sampler in ['greedy', 'multinomial']:
        if hasattr(samplers, sampler):
            print(f"Le sampler '{sampler}' existe dans samplers")
        else:
            print(f"Le sampler '{sampler}' n'existe PAS dans samplers")
except ImportError as e:
    print(f"Erreur lors de l'import de samplers: {e}")

# Test pour Template
print("\n4. Test d'import: outlines.Template")
try:
    from outlines import Template
    print(f"Classe Template trouvée: {Template}")
    print(f"Attributs: {dir(Template)}")
    
    # Vérifier si la méthode from_file existe
    if hasattr(Template, 'from_file'):
        print("La méthode 'from_file' existe dans Template")
    else:
        print("La méthode 'from_file' n'existe PAS dans Template")
except ImportError as e:
    print(f"Erreur lors de l'import de Template: {e}")

print("\n=== Résumé ===")
print("Vérification des imports nécessaires pour notre implémentation d'Outlines 0.2.3 terminée.") 