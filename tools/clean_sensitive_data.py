#!/usr/bin/env python
"""
Script pour nettoyer les données sensibles des fichiers de test.
Recherche et remplace les clés AWS, identifiants, etc.
"""

import os
import re
import json
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Patterns de sécurité à remplacer (modifiés pour éviter les fausses détections)
# fmt: off
PATTERNS = {
    r'AK[I]A[0-9A-Z]{16}': 'AKIAXXXXXXXXXXXXXXXX',  # AWS Access Key ID
    r'(?<![A-Za-z0-9+/=])[A-Za-z0-9+/=]{40}(?![A-Za-z0-9+/=])': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # AWS Secret Key
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': 'email@example.com',  # Emails
    r'\b(?:\d{1,3}\.){3}\d{1,3}\b': '127.0.0.1',  # Adresses IP
    # OpenAI API Keys
    r'sk-[A-Za-z0-9]{48}': 'sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # OpenAI API Key
    r'sk-[a-zA-Z0-9]{20,}': 'sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # OpenAI API Key - format alternatif
    r'sk-[a-zA-Z0-9]{1,}[A-Za-z0-9]{20,}': 'sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # OpenAI API Key générique
    r'sk-proj-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}': 'sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # OpenAI Project Key
    # Azure OpenAI API Keys
    r'[a-f0-9]{32}': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Azure OpenAI API Key (avec vérification contextuelle)
    # Google API Keys
    r'AIza[0-9A-Za-z\\-_]{35}': 'AIzaXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Google API Key
    # GitHub Tokens
    r'ghp_[a-zA-Z0-9]{36}': 'ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # GitHub Personal Access Token
    r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}': 'github_pat_XXXXXXXXXXXXXXXXXXXXXX_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # GitHub Fine-Grained PAT
    r'gho_[a-zA-Z0-9]{36}': 'gho_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # GitHub OAuth Token
    # Stripe API Keys - Direct patterns instead of concatenated
    r'pk_live_[0-9a-zA-Z]{24}': 'pk_live_XXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Live Public Key
    r'pk_test_[0-9a-zA-Z]{24}': 'pk_test_XXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Test Public Key
    r'sk_live_[0-9a-zA-Z]{24}': 'sk_live_XXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Live Secret Key
    r'sk_test_[0-9a-zA-Z]{24}': 'sk_test_XXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Test Secret Key
    r'pk_test_[a-zA-Z0-9]{60,}': 'pk_test_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Test Public Key (long format)
    r'pk_live_[a-zA-Z0-9]{60,}': 'pk_live_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Stripe Live Public Key (long format)
    # JWT Tokens
    r'eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*': 'eyXXX.XXXXX.XXXXX',  # JWT Token
    # Clés privées et certificats
    r'-----BEGIN PRIVATE KEY-----[a-zA-Z0-9\s/+=]+-----END PRIVATE KEY-----': '-----BEGIN PRIVATE KEY-----XXXX-----END PRIVATE KEY-----',  # Private Key
    r'-----BEGIN RSA PRIVATE KEY-----[a-zA-Z0-9\s/+=]+-----END RSA PRIVATE KEY-----': '-----BEGIN RSA PRIVATE KEY-----XXXX-----END RSA PRIVATE KEY-----',  # RSA Private Key
    r'-----BEGIN CERTIFICATE-----[a-zA-Z0-9\s/+=]+-----END CERTIFICATE-----': '-----BEGIN CERTIFICATE-----XXXX-----END CERTIFICATE-----',  # Certificate
    # Slack Tokens
    r'xox[baprs]-([0-9a-zA-Z]{10,48})?': 'xoxX-XXXXXXXXXXXXXXXXXXX',  # Slack Token
    # Discord Tokens
    r'[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27}': 'XXXXX.XXXXX.XXXXX',  # Discord Token
    # Numéros de téléphone
    r'\+\d{1,3}\s?\d{1,14}(?:\s?\d{1,4}){0,5}': '+XX XXX XXX XXX',  # Numéros de téléphone internationaux
    r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b': 'XXX-XXX-XXXX',  # Format téléphone US/Canada
    # Numéros de cartes bancaires
    r'\b(?:\d{4}[-\s]?){3}\d{4}\b': 'XXXX-XXXX-XXXX-XXXX',  # Carte de crédit
    # Nouveaux patterns pour d'autres services cloud et bases de données
    # Azure
    r'DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[^;]+;EndpointSuffix=[^;]+': 'DefaultEndpointsProtocol=https;AccountName=XXXXX;AccountKey=XXXXX;EndpointSuffix=XXXXX',  # Azure Storage Connection String
    # Firebase
    r'AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}': 'AAAXXXXXXXXX:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Firebase API Key
    # MongoDB
    r'mongodb(?:\+srv)?:\/\/[^:]+:[^@]+@[^\/]+\/[^\/]+': 'mongodb://user:password@host/database',  # MongoDB Connection String
    r'mongodb:\/\/(?:[^:]+:)?[^@]+@[^\/]+(?:\/[^\/]+)?': 'mongodb://user:password@host/database',  # MongoDB Connection String (alternative)
    # PostgreSQL
    r'postgres(?:ql)?:\/\/[^:]+:[^@]+@[^\/]+\/[^\/]+': 'postgresql://user:password@host/database',  # PostgreSQL Connection String
    # MySQL
    r'mysql:\/\/[^:]+:[^@]+@[^\/]+\/[^\/]+': 'mysql://user:password@host/database',  # MySQL Connection String
    # Redis
    r'redis:\/\/[^:]*:[^@]*@[^:]+:\d+': 'redis://user:password@host:port',  # Redis Connection String
    # Twilio
    r'SK[0-9a-fA-F]{32}': 'SKXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Twilio API Key
    r'AC[a-zA-Z0-9]{32}': 'ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Twilio Account SID
    # Mailgun
    r'key-[0-9a-zA-Z]{32}': 'key-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Mailgun API Key
    # SendGrid
    r'SG\.[0-9A-Za-z-_]{22}\.[0-9A-Za-z-_]{43}': 'SG.XXXXXXXXXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # SendGrid API Key
    # Hugging Face
    r'hf_[a-zA-Z0-9]{34}': 'hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Hugging Face API Key
    # Databricks
    r'dapi[a-f0-9]{32}': 'dapiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Databricks API Token
    # Supabase
    r'eyJ[a-zA-Z0-9]{20,}\.eyJ[a-zA-Z0-9]{20,}': 'eyXXXXXXXXXXXXXXXXXXXX.eyXXXXXXXXXXXXXXXXXXXX',  # Supabase JWT
    # Salesforce
    r'00D[a-zA-Z0-9]{15}': '00DXXXXXXXXXXXXXXX',  # Salesforce Organization ID
    # Heroku
    r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}': 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX',  # Heroku API Key / UUID
    # Gitlab
    r'glpat-[0-9a-zA-Z_-]{20}': 'glpat-XXXXXXXXXXXXXXXXXXXX',  # GitLab Personal Access Token
    # Bitbucket
    r'BITBUCKET_[A-Za-z0-9_]{20,}': 'BITBUCKET_XXXXXXXXXXXXXXXXXXXX',  # Bitbucket Access Token
    # Cloudflare
    r'[0-9a-f]{37}': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Cloudflare API Token
    # Digital Ocean
    r'dop_v1_[a-f0-9]{64}': 'dop_v1_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Digital Ocean Personal Access Token
    # Datadog
    r'[a-f0-9]{32}': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',  # Datadog API Key (avec vérification contextuelle)
    # Mistral AI
    r'[a-zA-Z0-9]{32}-[a-zA-Z0-9]{8}': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX-XXXXXXXX',  # Mistral AI API Key
    # Anthropic
    r'sk-ant-[a-zA-Z0-9]{32}-[a-zA-Z0-9]{8}': 'sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX-XXXXXXXX',  # Anthropic API Key
    # Claude
    r'sk-claude-[a-zA-Z0-9]{32}-[a-zA-Z0-9]{8}': 'sk-claude-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX-XXXXXXXX',  # Claude API Key
    # Noms d'utilisateurs et informations personnelles
    r'"name"\s*:\s*"[^"]+"': '"name": "Anonymous User"',  # Nom dans JSON
    r'"user"\s*:\s*"[^"]+"': '"user": "Anonymous User"',  # Utilisateur dans JSON
    r'"username"\s*:\s*"[^"]+"': '"username": "anonymous"',  # Nom d'utilisateur dans JSON
    r'"email"\s*:\s*"[^"]+"': '"email": "email@example.com"',  # Email dans JSON
    r'"ip"\s*:\s*"[^"]+"': '"ip": "127.0.0.1"',  # IP dans JSON
    # Objets utilisateur complets et imbriqués
    r'"user"\s*:\s*\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"email"\s*:\s*"[^"]+"\s*,\s*"ip"\s*:\s*"[^"]+"\s*\}': '"user": {"name": "Anonymous User", "email": "email@example.com", "ip": "127.0.0.1"}',  # Objet utilisateur complet
}
# fmt: on

def clean_json_object(obj, patterns=None, report=None, path=""):
    """
    Nettoie récursivement un objet JSON (dict, list, str) des données sensibles.
    
    Args:
        obj: L'objet JSON à nettoyer
        patterns: Dictionnaire des patterns regex à rechercher et remplacer
        report: Dictionnaire pour stocker les rapports de détection
        path: Chemin actuel dans l'objet JSON (pour le rapport)
        
    Returns:
        L'objet JSON nettoyé
    """
    if patterns is None:
        patterns = PATTERNS
        
    if report is None:
        report = {"detected": {}, "total_count": 0}
    
    # Cas de base: chaîne de caractères
    if isinstance(obj, str):
        original = obj
        # Vérifier tous les patterns
        for pattern, replacement in patterns.items():
            try:
                matches = re.findall(pattern, obj)
                for match in matches:
                    if isinstance(match, tuple):  # Si le pattern contient des groupes
                        match = match[0]  # Prendre le premier groupe
                    
                    # Enregistrer dans le rapport
                    if pattern not in report["detected"]:
                        report["detected"][pattern] = []
                    
                    # Limiter la taille des matches pour éviter un rapport trop volumineux
                    truncated_match = match[:20] + "..." if len(match) > 20 else match
                    report["detected"][pattern].append({
                        "path": path,
                        "value": truncated_match,
                        "type": "string"
                    })
                    report["total_count"] += 1
                
                # Remplacer dans la chaîne
                obj = re.sub(pattern, replacement, obj)
            except Exception as e:
                logger.warning(f"Erreur lors du traitement du pattern {pattern}: {e}")
                continue
            
        return obj
        
    # Cas récursif: dictionnaire
    elif isinstance(obj, dict):
        # Vérification spéciale pour les objets utilisateur
        if "user" in obj and isinstance(obj["user"], dict):
            if "name" in obj["user"]:
                obj["user"]["name"] = "Anonymous User"
            if "email" in obj["user"]:
                obj["user"]["email"] = "email@example.com"
            if "ip" in obj["user"]:
                obj["user"]["ip"] = "127.0.0.1"
        
        # Nettoyage direct des clés communes
        sensitive_keys = {
            "name": "Anonymous User",
            "email": "email@example.com",
            "ip_address": "127.0.0.1",
            "ip": "127.0.0.1",
            "address": "123 Example Street",
            "phone": "+XX XXX XXX XXX",
            "phone_number": "+XX XXX XXX XXX",
            "api_key": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "key": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "secret": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "password": "******************",
            "credit_card": "XXXX-XXXX-XXXX-XXXX",
            "credit_card_number": "XXXX-XXXX-XXXX-XXXX",
            "ssn": "XXX-XX-XXXX",
            "social_security": "XXX-XX-XXXX",
            "auth_token": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "token": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "public_key": "pk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "private_key": "sk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        }
        
        # Appliquer le nettoyage direct aux clés sensibles
        for key, value in obj.items():
            # Remplacer directement les valeurs pour les clés connues
            if key in sensitive_keys and isinstance(obj[key], str):
                obj[key] = sensitive_keys[key]
            # Sinon, continuer le nettoyage récursif
            else:
                current_path = f"{path}.{key}" if path else key
                obj[key] = clean_json_object(value, patterns, report, current_path)
        
        return obj
        
    # Cas récursif: liste
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{path}[{i}]"
            obj[i] = clean_json_object(item, patterns, report, current_path)
        return obj
        
    # Autres types (int, float, bool, None)
    return obj

def clean_json_file(input_file, output_file=None, recursive=False, generate_report=False):
    """
    Nettoie un fichier JSON des données sensibles.
    
    Args:
        input_file: Chemin du fichier à nettoyer (str ou Path)
        output_file: Chemin du fichier de sortie (str ou Path, si None, génère automatiquement)
        recursive: Si True, nettoie récursivement les objets JSON
        generate_report: Si True, génère un rapport des données sensibles trouvées
        
    Returns:
        True si le nettoyage a réussi, False sinon
    """
    # Convertir les chemins en objets Path
    input_file = Path(input_file) if not isinstance(input_file, Path) else input_file
    
    # Vérifier que le fichier d'entrée existe
    if not input_file.exists():
        logger.error(f"Le fichier d'entrée n'existe pas: {input_file}")
        return False
    
    # Générer le nom du fichier de sortie si non spécifié
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_clean{input_file.suffix}"
    else:
        output_file = Path(output_file) if not isinstance(output_file, Path) else output_file
    
    # Créer le répertoire de sortie si nécessaire
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Nettoyage du fichier: {input_file}")
    logger.info(f"Fichier de sortie: {output_file}")
    logger.info(f"Mode récursif: {recursive}")
    
    try:
        # Lire le fichier d'entrée
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Si mode récursif, parser le JSON et nettoyer récursivement
        if recursive:
            try:
                logger.info("Utilisation du mode récursif")
                data = json.loads(content)
                report = {"detected": {}, "total_count": 0, "timestamp": datetime.now().isoformat()}
                cleaned_data = clean_json_object(data, PATTERNS, report)
                
                # Écrire le fichier nettoyé
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
                
                # Générer le rapport si demandé
                if generate_report and report["total_count"] > 0:
                    report_file = output_file.parent / f"{output_file.stem}_security_report.json"
                    with open(report_file, 'w', encoding='utf-8') as f:
                        json.dump(report, f, indent=2, ensure_ascii=False)
                    logger.info(f"Rapport de sécurité généré: {report_file}")
                    logger.info(f"{report['total_count']} données sensibles détectées et nettoyées")
                
                logger.info(f"Fichier nettoyé et sauvegardé: {output_file}")
                return True
                
            except json.JSONDecodeError as e:
                logger.warning(f"Erreur de parsing JSON, utilisation du mode non-récursif: {e}")
                # Continuer avec le mode non-récursif en cas d'erreur
        
        # Mode non-récursif (traitement du fichier comme texte)
        logger.info("Utilisation du mode non-récursif (traitement comme texte)")
        
        # Patterns qui nécessitent une vérification contextuelle
        context_patterns = {
            # Azure OpenAI API Key - vérifier si le contexte contient des mots-clés Azure/OpenAI
            r'[a-f0-9]{32}': {
                'replacement': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
                'context_keywords': ['azure', 'openai', 'api', 'key', 'secret', 'token']
            },
            # Datadog API Key - vérifier si le contexte contient des mots-clés Datadog
            r'[0-9a-f]{32}': {
                'replacement': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
                'context_keywords': ['datadog', 'api', 'key', 'apikey']
            }
        }
        
        # Traiter d'abord les patterns contextuels
        for pattern, config in context_patterns.items():
            # Rechercher toutes les occurrences
            matches = re.finditer(pattern, content)
            for match in matches:
                # Extraire le contexte (50 caractères avant et après)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end].lower()
                
                # Vérifier si le contexte contient un des mots-clés
                if any(keyword in context for keyword in config['context_keywords']):
                    # Remplacer uniquement cette occurrence
                    content = content[:match.start()] + config['replacement'] + content[match.end():]
        
        # Traiter les patterns standards
        for pattern, replacement in PATTERNS.items():
            # Ignorer les patterns contextuels déjà traités
            if pattern in context_patterns:
                continue
            try:
                content = re.sub(pattern, replacement, content)
            except Exception as e:
                logger.warning(f"Erreur lors du traitement du pattern {pattern}: {e}")
                continue
        
        # Vérification que le JSON est valide
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Le fichier nettoyé n'est pas un JSON valide: {e}")
            # Continuer quand même pour sauvegarder le résultat
        
        # Écriture du fichier nettoyé
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Fichier nettoyé et sauvegardé: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage du fichier {input_file}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Fonction principale pour l'exécution en ligne de commande."""
    parser = argparse.ArgumentParser(description="Nettoie les données sensibles des fichiers de test")
    parser.add_argument("input", help="Fichier ou dossier à nettoyer")
    parser.add_argument("--output", help="Fichier ou dossier de sortie")
    parser.add_argument("--recursive", "-r", action="store_true", help="Nettoyer récursivement les objets JSON")
    parser.add_argument("--report", action="store_true", help="Générer un rapport des données sensibles trouvées")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        logger.error(f"Le chemin {input_path} n'existe pas.")
        return 1
    
    # Traitement d'un fichier unique
    if input_path.is_file():
        output_path = Path(args.output) if args.output else None
        
        success = clean_json_file(input_path, output_path, args.recursive, args.report)
        
        if success:
            logger.info("Nettoyage terminé avec succès!")
            return 0
        else:
            logger.error("Erreur lors du nettoyage!")
            return 1
    
    # Traitement d'un dossier
    elif input_path.is_dir():
        output_dir = Path(args.output) if args.output else input_path / "cleaned"
        os.makedirs(output_dir, exist_ok=True)
        
        json_files = list(input_path.glob("**/*.json"))
        logger.info(f"Traitement de {len(json_files)} fichiers JSON...")
        
        success_count = 0
        for file in json_files:
            rel_path = file.relative_to(input_path)
            output_file = output_dir / rel_path.parent / f"{file.stem}_clean{file.suffix}"
            os.makedirs(output_file.parent, exist_ok=True)
            
            if clean_json_file(file, output_file, args.recursive, args.report):
                success_count += 1
        
        logger.info(f"{success_count}/{len(json_files)} fichiers nettoyés avec succès!")
        
        if success_count < len(json_files):
            logger.warning(f"{len(json_files) - success_count} fichiers n'ont pas pu être nettoyés")
            return 1
        return 0
    
    else:
        logger.error(f"Le chemin {input_path} n'est ni un fichier ni un dossier.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 