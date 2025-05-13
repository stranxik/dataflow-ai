#!/usr/bin/env python
"""
Test spécifique des patterns pour les clés Stripe et les informations utilisateur.
"""

import re
import json
import tempfile
from pathlib import Path

# Patterns spécifiques à tester
PATTERNS = {
    # Stripe API Keys - Public and Private
    r'pk_test_[0-9a-zA-Z]{24}': 'pk_test_XXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Test Public Key
    r'pk_live_[0-9a-zA-Z]{24}': 'pk_live_XXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Live Public Key
    r'sk_test_[0-9a-zA-Z]{24}': 'sk_test_XXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Test Secret Key
    r'sk_live_[0-9a-zA-Z]{24}': 'sk_live_XXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Live Secret Key
    r'pk_test_[a-zA-Z0-9]{60,}': 'pk_test_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Test Public Key (long format)
    r'pk_live_[a-zA-Z0-9]{60,}': 'pk_live_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Live Public Key (long format)
    
    # OpenAI API Keys
    r'sk-[A-Za-z0-9]{48}': 'sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # OpenAI API Key standard
    r'sk-[a-zA-Z0-9]{20,}': 'sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # OpenAI API Key alternative
    
    # Utilisateurs et informations personnelles
    r'"name"\s*:\s*"[^"]+"': '"name": "Anonymous User"',  # Nom d'utilisateur dans JSON
    r'"email"\s*:\s*"[^"]+"': '"email": "email@example.com"',  # Email dans JSON
    r'"ip"\s*:\s*"[^"]+"': '"ip": "127.0.0.1"',  # IP dans JSON
    r'"user"\s*:\s*\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"email"\s*:\s*"[^"]+"\s*,\s*"ip"\s*:\s*"[^"]+"\s*\}': '"user": {"name": "Anonymous User", "email": "email@example.com", "ip": "127.0.0.1"}',  # Objet utilisateur complet
}

def test_specific_patterns():
    """Teste les patterns spécifiques mentionnés dans la demande."""
    
    # Test des clés Stripe
    stripe_test_keys = [
        '"public_key": "pk_test_FAKE_51LkzZ5IasE7mAY6Jb9jFw2CE2z2fUkhwH1VLzQKuUX4XGBUKHG25hY1RHmQMAKxD05E6UOfYUV1MPyWr0Y4eqR0A00vKfrRaqC"',
        '"api_key": "sk_test_FAKE_abcdefghijklmnopqrstuvwx"'
    ]
    
    # Test des clés OpenAI
    openai_test_keys = [
        '"api_key": "sk-FAKE_abc1234567890defGHIJKlmnopqRSTUvwxYZ1234abcd"'
    ]
    
    # Test des informations utilisateur
    user_test_data = [
        '"user": {"name": "Jean Dupont", "email": "email@example.com", "ip": "127.0.0.1"}'
    ]
    
    print("=== Test des patterns de clés Stripe ===")
    for test_key in stripe_test_keys:
        print(f"Original: {test_key}")
        cleaned = test_key
        for pattern, replacement in PATTERNS.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        print(f"Nettoyé: {cleaned}")
        print(f"Résultat: {'✅ Nettoyé' if cleaned != test_key else '❌ Non nettoyé'}")
        print()
    
    print("=== Test des patterns de clés OpenAI ===")
    for test_key in openai_test_keys:
        print(f"Original: {test_key}")
        cleaned = test_key
        for pattern, replacement in PATTERNS.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        print(f"Nettoyé: {cleaned}")
        print(f"Résultat: {'✅ Nettoyé' if cleaned != test_key else '❌ Non nettoyé'}")
        print()
    
    print("=== Test des patterns d'informations utilisateur ===")
    for test_data in user_test_data:
        print(f"Original: {test_data}")
        cleaned = test_data
        for pattern, replacement in PATTERNS.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        print(f"Nettoyé: {cleaned}")
        print(f"Résultat: {'✅ Nettoyé' if cleaned != test_data else '❌ Non nettoyé'}")
        print()

if __name__ == "__main__":
    test_specific_patterns() 