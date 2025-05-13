#!/usr/bin/env python
"""
Test pour le nettoyage des données sensibles.
Vérifie que les patterns ajoutés fonctionnent correctement.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Ajouter le répertoire du projet au chemin de recherche Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import direct de la fonction 
from tools.clean_sensitive_data import clean_json_file

def test_sensitive_data_cleaning():
    """Test des fonctionnalités de nettoyage des données sensibles."""
    
    # Créer un fichier JSON de test contenant des données sensibles
    test_data = {
        "stripe": {
            "public_key": "pk_test_FAKE_51LkzZ5IasE7mAY6Jb9jFw2CE2z2fUkhwH1VLzQKuUX4XGBUKHG25hY1RHmQMAKxD05E6UOfYUV1MPyWr0Y4eqR0A00vKfrRaqC",
            "secret_key": "sk_test_FAKE_abcdefghijklmnopqrstuvwx",
            "live_key": "sk_live_FAKE_abcdefghijklmnopqrstuvwx"
        },
        "openai": {
            "api_key": "sk-FAKE_abc1234567890defGHIJKlmnopqRSTUvwxYZ1234abcd"
        },
        "user": {
            "name": "Jean Dupont",
            "email": "jean.dupont@example.com",
            "ip": "192.168.1.1"
        },
        "nested": {
            "data": {
                "user": {
                    "name": "Pierre Martin",
                    "email": "pierre.martin@example.com",
                    "ip": "10.0.0.1"
                }
            }
        },
        "array_data": [
            {
                "name": "Alice Durand",
                "email": "alice.durand@example.com",
                "api_key": "sk-test_FAKE_apikey12345",
                "public_key": "pk_live_FAKE_publickey67890"
            },
            {
                "name": "Bob Lefebvre",
                "email": "bob.lefebvre@example.com",
                "ip": "172.16.0.1"
            }
        ]
    }
    
    # Créer des fichiers temporaires pour les tests
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # Test du mode non-récursif (par défaut)
        input_file = temp_dir_path / "input.json"
        output_file = temp_dir_path / "output_non_recursive.json"
        
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2)
        
        # Nettoyer sans mode récursif
        clean_json_file(input_file, output_file, recursive=False)
        
        # Vérifier que le fichier de sortie existe
        assert output_file.exists(), "Le fichier de sortie n'a pas été créé (mode non-récursif)"
        
        # Test du mode récursif
        output_file_recursive = temp_dir_path / "output_recursive.json"
        clean_json_file(input_file, output_file_recursive, recursive=True)
        
        # Vérifier que le fichier de sortie existe
        assert output_file_recursive.exists(), "Le fichier de sortie n'a pas été créé (mode récursif)"
        
        # Charger les résultats pour vérification
        with open(output_file_recursive, "r", encoding="utf-8") as f:
            cleaned_data = json.load(f)
        
        # Vérifier que les données sensibles ont été nettoyées
        print("\n=== Résultats du nettoyage (mode récursif) ===")
        print(json.dumps(cleaned_data, indent=2))
        
        # Vérifications spécifiques
        assert cleaned_data["stripe"]["public_key"] != test_data["stripe"]["public_key"], "La clé publique Stripe n'a pas été nettoyée"
        assert cleaned_data["stripe"]["secret_key"] != test_data["stripe"]["secret_key"], "La clé secrète Stripe n'a pas été nettoyée"
        assert cleaned_data["openai"]["api_key"] != test_data["openai"]["api_key"], "La clé API OpenAI n'a pas été nettoyée"
        assert cleaned_data["user"]["name"] != test_data["user"]["name"], "Le nom utilisateur n'a pas été nettoyé"
        assert cleaned_data["user"]["email"] != test_data["user"]["email"], "L'email utilisateur n'a pas été nettoyé"
        assert cleaned_data["user"]["ip"] != test_data["user"]["ip"], "L'IP utilisateur n'a pas été nettoyée"
        
        # Vérifier la structure imbriquée
        assert cleaned_data["nested"]["data"]["user"]["name"] != test_data["nested"]["data"]["user"]["name"], "Le nom utilisateur imbriqué n'a pas été nettoyé"
        
        # Vérifier les données dans les tableaux
        assert cleaned_data["array_data"][0]["name"] != test_data["array_data"][0]["name"], "Le nom dans le tableau n'a pas été nettoyé"
        assert cleaned_data["array_data"][0]["api_key"] != test_data["array_data"][0]["api_key"], "La clé API dans le tableau n'a pas été nettoyée"
        
        print("\nTous les tests ont réussi !")
        
if __name__ == "__main__":
    test_sensitive_data_cleaning() 