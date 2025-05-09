import json
import os
import re
from datetime import datetime
import argparse
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generic_json_processor import safe_json_load, write_tree, write_file_structure

def clean_html_tags(text):
    """Nettoie les balises HTML et Jira du texte"""
    if not text:
        return ""
    
    # Nettoyer les balises Jira wiki style
    text = re.sub(r'!.*?!', '', text)  # Images
    text = re.sub(r'\[.*?\|.*?\]', '', text)  # Liens
    text = re.sub(r'\{.*?\}', '', text)  # Macros
    
    # Nettoyer les balises HTML
    text = re.sub(r'<.*?>', '', text)
    
    return text.strip()

def extract_keywords(text, max_words=10):
    """Extrait des mots-clés du texte"""
    if not text:
        return []
    
    # Nettoyer le texte
    text = clean_html_tags(text)
    
    # Supprimer la ponctuation et convertir en minuscules
    text = re.sub(r'[^\w\s]', '', text.lower())
    
    # Diviser en mots et filtrer les mots courts
    words = [word for word in text.split() if len(word) > 3]
    
    # Retourner les mots les plus fréquents
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Trier par fréquence et prendre les top mots
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_words]]

def extract_entities(text):
    """Extrait les entités comme les noms d'utilisateurs et les URL"""
    if not text:
        return {"users": [], "urls": []}
    
    # Extraire les utilisateurs mentionnés (format Jira [~username])
    users = re.findall(r'\[~(.*?)\]', text)
    
    # Extraire les URLs
    urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', text)
    
    return {
        "users": users,
        "urls": urls
    }

def normalize_date(date_string):
    """Normalise une date au format ISO"""
    if not date_string:
        return None
    
    try:
        # Convertir au format standard ISO
        date_obj = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%f%z")
        return date_obj.isoformat()
    except ValueError:
        try:
            # Essayer un autre format possible
            date_obj = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")
            return date_obj.isoformat()
        except ValueError:
            return date_string

def transform_jira_ticket(ticket):
    """Transforme un ticket JIRA en structure optimisée pour LLM"""
    
    # Extraire les informations de base
    transformed = {
        "id": ticket.get("key", ""),
        "metadata": {
            "project": ticket.get("key", "").split("-")[0] if "-" in ticket.get("key", "") else "",
            "number": ticket.get("key", "").split("-")[1] if "-" in ticket.get("key", "") else "",
            "created_by": ticket.get("reporter", ""),
            "created_at": normalize_date(ticket.get("created", "")),
            "last_updated_at": normalize_date(ticket.get("updated", "")),
            "status": ticket.get("status", ""),
        },
        "content": {
            "title": ticket.get("title", ""),
            "description": clean_html_tags(ticket.get("description", "")),
            "comments": []
        },
        "history": [],
        "analysis": {
            "keywords": extract_keywords(ticket.get("title", "") + " " + ticket.get("description", "")),
            "entities": extract_entities(ticket.get("description", ""))
        }
    }
    
    # Ajouter les commentaires
    if "comments" in ticket and isinstance(ticket["comments"], list):
        for comment in ticket["comments"]:
            if isinstance(comment, str):
                # Si le commentaire est une simple chaîne
                transformed["content"]["comments"].append({
                    "text": clean_html_tags(comment),
                    "entities": extract_entities(comment)
                })
            elif isinstance(comment, dict):
                # Si le commentaire est un objet
                transformed["content"]["comments"].append({
                    "text": clean_html_tags(comment.get("body", "")),
                    "author": comment.get("author", ""),
                    "date": normalize_date(comment.get("created", "")),
                    "entities": extract_entities(comment.get("body", ""))
                })
    
    # Ajouter l'historique
    if "history" in ticket and isinstance(ticket["history"], list):
        for event in ticket["history"]:
            if isinstance(event, dict) and "items" in event and isinstance(event["items"], list):
                for item in event["items"]:
                    transformed["history"].append({
                        "field": item.get("field", ""),
                        "from": item.get("from", ""),
                        "to": item.get("to", ""),
                        "changed_by": event.get("author", ""),
                        "changed_at": normalize_date(event.get("created", ""))
                    })
    
    # Placeholder pour les liens Confluence (à remplir plus tard)
    transformed["confluence_links"] = []
    
    return transformed

def process_jira_file(file_path, max_tickets=None):
    """Traite un fichier JSON JIRA et retourne la structure transformée"""
    
    print(f"Traitement du fichier {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            jira_data = safe_json_load(f, log_prefix=file_path)
        
        if not isinstance(jira_data, list):
            print(f"Erreur: Le fichier {file_path} ne contient pas un tableau JSON.")
            return []
        
        # Limiter le nombre de tickets si nécessaire
        if max_tickets:
            jira_data = jira_data[:min(max_tickets, len(jira_data))]
        
        # Transformer chaque ticket
        print(f"Transformation de {len(jira_data)} tickets...")
        transformed_tickets = [transform_jira_ticket(ticket) for ticket in jira_data]
        
        return transformed_tickets
    
    except json.JSONDecodeError as e:
        print(f"Erreur de décodage JSON dans {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Erreur lors du traitement de {file_path}: {e}")
        return []

def save_results(transformed_data, output_file):
    """Sauvegarde les données transformées dans un fichier JSON"""
    try:
        # S'assurer que le dossier de destination existe
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transformed_data, f, indent=2, ensure_ascii=False)
        print(f"Données transformées sauvegardées dans {output_file}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des résultats: {e}")

def main():
    parser = argparse.ArgumentParser(description="Transforme des exports JIRA en format optimisé pour LLM")
    parser.add_argument("--files", nargs="+", default=[],
                       help="Fichiers JSON JIRA à traiter (ancien format)")
    parser.add_argument("--input", 
                       help="Fichier JSON d'entrée à traiter (nouveau format)")
    parser.add_argument("--output", default="llm_ready_tickets.json", 
                       help="Fichier de sortie")
    parser.add_argument("--type", default="jira", choices=["jira", "confluence"],
                       help="Type de fichier à traiter (jira ou confluence)")
    parser.add_argument("--max", type=int, default=None, 
                       help="Nombre maximum de tickets à traiter par fichier")
    parser.add_argument("--generate-arborescence", action="store_true",
                       help="Générer un fichier d'arborescence pour chaque fichier traité")
    parser.add_argument("--output-dir", default="results",
                       help="Dossier de sortie pour tous les fichiers générés")
    
    args = parser.parse_args()
    
    # S'assurer que le dossier de sortie existe
    output_dir = args.output_dir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Vérifier si le chemin de sortie est absolu ou relatif
    if os.path.isabs(args.output):
        output_file = args.output
    else:
        # Si le chemin est relatif mais contient déjà 'results/', ne pas ajouter le préfixe
        if args.output.startswith(f"{output_dir}/"):
            output_file = args.output
        else:
            output_file = os.path.join(output_dir, args.output)
    
    all_tickets = []
    processed_files = []
    
    # Utiliser --input s'il est fourni (nouveau format)
    if args.input:
        files_to_process = [args.input]
    # Sinon utiliser --files (ancien format)
    elif args.files:
        files_to_process = args.files
    else:
        print("Erreur: Aucun fichier spécifié. Utilisez --input ou --files.")
        sys.exit(1)
    
    for file_path in files_to_process:
        if not os.path.exists(file_path):
            print(f"Erreur: Le fichier {file_path} n'existe pas.")
            continue
        
        # Traiter différemment selon le type de fichier
        if args.type == "confluence":
            # TODO: Ajouter le traitement des fichiers Confluence
            print(f"Traitement du fichier Confluence {file_path}...")
            # Pour l'instant, nous utilisons la même fonction
            tickets = process_jira_file(file_path, args.max)
        else:
            tickets = process_jira_file(file_path, args.max)
        
        all_tickets.extend(tickets)
        processed_files.append(file_path)
    
    # Créer la structure finale
    final_structure = {
        "tickets": all_tickets,
        "metadata": {
            "total_tickets": len(all_tickets),
            "source_files": args.files,
            "created_at": datetime.now().isoformat(),
            "structure_version": "1.0"
        }
    }
    
    save_results(final_structure, output_file)
    
    print(f"\nTraitement terminé. {len(all_tickets)} tickets transformés.")
    print(f"Fichier de sortie: {output_file}")
    
    # Générer les arborescences des fichiers si demandé
    if args.generate_arborescence:
        # Générer une arborescence globale des fichiers LLM-ready
        arborescence_file = os.path.join(output_dir, "llm_ready_arborescence.txt")
        write_tree(output_dir, os.path.basename(arborescence_file))
        print(f"Arborescence globale générée dans {arborescence_file}")
        
        # Générer une arborescence pour chaque fichier traité
        for file_path in processed_files:
            file_base_name = os.path.splitext(os.path.basename(file_path))[0]
            arborescence_file = f"{file_base_name}_arborescence.txt"
            output_arborescence = os.path.join(output_dir, arborescence_file)
            write_file_structure(file_path, output_dir, arborescence_file)
            print(f"Structure du fichier {file_path} générée dans {output_arborescence}")
    
if __name__ == "__main__":
    main() 