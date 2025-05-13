#!/usr/bin/env python
"""
Test final des patterns spécifiques avec les exemples fournis.
"""

import re
import json

# Exemples spécifiques à tester
TEST_EXAMPLES = {
    "Stripe public key": '"public_key": "pk_test_FAKE_51LkzZ5IasE7mAY6Jb9jFw2CE2z2fUkhwH1VLzQKuUX4XGBUKHG25hY1RHmQMAKxD05E6UOfYUV1MPyWr0Y4eqR0A00vKfrRaqC"',
    "OpenAI API key": '"api_key": "sk-FAKE_abc1234567890defGHIJKlmnopqRSTUvwxYZ1234abcd"',
    "User object": '    "user": {\n      "name": "Jean Dupont",\n      "email": "email@example.com",\n      "ip": "127.0.0.1"\n    },'
}

# Patterns des regex pour les tests
PATTERNS = {
    # Stripe 
    r'pk_test_[a-zA-Z0-9]{60,}': 'pk_test_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Test Public Key (long format)
    
    # OpenAI API Keys
    r'sk-[a-zA-Z0-9]{20,}': 'sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # OpenAI API Key format générique
    
    # Utilisateur
    r'"user"\s*:\s*\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"email"\s*:\s*"[^"]+"\s*,\s*"ip"\s*:\s*"[^"]+"\s*\}': '"user": {"name": "Anonymous User", "email": "email@example.com", "ip": "127.0.0.1"}',  # Objet utilisateur complet
    r'"name"\s*:\s*"[^"]+"': '"name": "Anonymous User"',  # Nom dans JSON
}

def test_examples():
    """Test les patterns avec les exemples fournis."""
    
    print("=== Test des patterns avec les exemples spécifiques ===\n")
    
    for name, example in TEST_EXAMPLES.items():
        print(f"Exemple: {name}")
        print(f"Original: {example}")
        
        # Appliquer tous les patterns
        cleaned = example
        for pattern, replacement in PATTERNS.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        
        print(f"Nettoyé: {cleaned}")
        print(f"Résultat: {'✅ Nettoyé' if cleaned != example else '❌ Non nettoyé'}")
        print()

if __name__ == "__main__":
    test_examples() 