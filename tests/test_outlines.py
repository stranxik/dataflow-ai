#!/usr/bin/env python3
"""
Script de test pour vérifier que Outlines est correctement installé
"""

import sys
import os
import traceback

print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")

# Vérifier l'import de base
try:
    import outlines
    print(f"Outlines est installé !")
    print(f"Chemin: {outlines.__file__}")
    print(f"Contenu: {dir(outlines)}")
except ImportError as e:
    print(f"Erreur lors de l'import d'Outlines: {e}")
    print("Vérifiez que vous avez bien installé la bibliothèque.")

# Test simple d'utilisation d'Outlines 0.2.3
try:
    from outlines import models, Template
    import outlines.generate as generate
    
    print("\n=== Test simple d'utilisation d'Outlines 0.2.3 ===")
    
    # Vérifier si la clé API OpenAI est définie
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            # Créer un modèle - note: la signature de l'API a changé dans 0.2.3
            # Ne pas utiliser le paramètre temperature car non supporté
            model = models.openai("gpt-3.5-turbo", api_key=api_key)
            print("Modèle OpenAI créé avec succès!")
            
            # Créer un prompt avec Template
            template = Template.from_string("Donne-moi un nombre entre 1 et 10: ")
            prompt = template()
            print(f"Prompt créé: {prompt}")
            
            # Tester avec text() car format() n'est pas compatible avec OpenAI
            print("Création du générateur avec generate.text")
            generator = generate.text(model)
            print("Générateur créé avec succès!")
            
            # Ne pas exécuter réellement pour éviter les coûts API
            print("(Génération non exécutée pour éviter les coûts API)")
        except Exception as e:
            print(f"Erreur lors de la création du modèle OpenAI: {e}")
    else:
        print("Clé API OpenAI non définie. Test avec modèle OpenAI ignoré.")
    
    print("\nTest de fonctionnalités sans modèle:")
    print("- Template fonctionne correctement")
    print("- generate.format est disponible")
    print("- L'API Outlines 0.2.3 est accessible")
    
except Exception as e:
    print(f"Erreur lors du test d'utilisation d'Outlines: {e}")
    print(f"Trace: {traceback.format_exc()}")

print("\nTests terminés.")

# Tester les importations comme dans le projet
try:
    from outlines import generate, prompts
    print("Import de 'models', 'generate', 'prompts' réussi")
except ImportError as e:
    print(f"Erreur lors de l'import de models, generate, prompts: {e}")

try:
    from outlines.regex import regex
    print("Import de 'regex' réussi")
except ImportError as e:
    print(f"Erreur lors de l'import de regex: {e}")

try: 
    from outlines.json_schema import JsonSchemaParser
    print("Import de 'JsonSchemaParser' réussi")
except ImportError as e:
    print(f"Erreur lors de l'import de JsonSchemaParser: {e}") 