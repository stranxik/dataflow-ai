import json
import os
import sys
import argparse
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generic_json_processor import safe_json_load, write_tree, write_file_structure

def extract_structure_from_first_object(json_file_path, llm_fallback=False, model=None):
    """
    Extraire la structure du premier objet d'un fichier JSON volumineux
    sans charger l'intégralité du fichier
    
    Args:
        json_file_path: Chemin du fichier JSON
        llm_fallback: Si True, utilise LLM en cas d'échec de parsing
        model: Modèle LLM à utiliser
        
    Returns:
        Dictionnaire avec la structure du fichier
    """
    with open(json_file_path, 'r') as file:
        # Lire le début du fichier
        content = ""
        brackets_count = 0
        in_first_object = False
        object_complete = False
        
        # Lire caractère par caractère jusqu'à trouver le premier objet complet
        for line in file:
            content += line
            
            # Détecter le début du tableau JSON
            if '[' in line and not in_first_object:
                in_first_object = True
                
            # Compter les accolades pour trouver la fin du premier objet
            if in_first_object and not object_complete:
                for char in line:
                    if char == '{':
                        brackets_count += 1
                    elif char == '}':
                        brackets_count -= 1
                        if brackets_count == 0:
                            object_complete = True
                            break
            
            if object_complete:
                break
        
        # Essayer de parser le premier objet
        try:
            # Ajouter les crochets pour avoir un JSON valide
            if not content.strip().startswith('['):
                content = '[' + content
            if not content.strip().endswith(']'):
                content = content + ']'
                
            # Parser le JSON
            import io
            data = safe_json_load(io.StringIO(content), log_prefix=json_file_path, 
                                 llm_fallback=llm_fallback, model=model)
            if isinstance(data, list) and len(data) > 0:
                return {
                    "filename": os.path.basename(json_file_path),
                    "structure": {
                        "keys": list(data[0].keys()),
                        "nested_structures": {
                            key: type(value).__name__ + 
                                 (" (array)" if isinstance(value, list) else
                                  " (object)" if isinstance(value, dict) else "")
                            for key, value in data[0].items()
                        }
                    },
                    "sample": data[0]
                }
            else:
                return {
                    "filename": os.path.basename(json_file_path),
                    "error": "Aucun objet trouvé dans le fichier"
                }
        except json.JSONDecodeError as e:
            return {
                "filename": os.path.basename(json_file_path),
                "error": f"Erreur de parsing JSON: {str(e)}",
                "content_preview": content[:500] + "..."
            }

def main():
    parser = argparse.ArgumentParser(description='Extrait la structure des fichiers JSON JIRA')
    parser.add_argument('input_files', nargs='+', help='Fichiers JSON JIRA à analyser')
    parser.add_argument('--output-dir', default='results', help='Dossier de sortie')
    parser.add_argument('--output-file', default='jira_structure.json', help='Nom du fichier de sortie')
    parser.add_argument('--llm', action="store_true", help="Activer le fallback LLM pour la correction des fichiers JSON mal formés")
    parser.add_argument('--model', default=None, help="Modèle LLM à utiliser (ex: gpt-4.1, o3)")
    parser.add_argument('--output', default=None, help="Fichier de sortie pour la structure")
    parser.add_argument('--with-openai', action='store_true', help="Utiliser OpenAI pour l'extraction avancée")
    parser.add_argument('--api-key', default=None, help="Clé API OpenAI")
    
    args = parser.parse_args()
    
    # Créer le dossier de sortie s'il n'existe pas
    if args.output_dir and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    all_structures = {}
    
    # Traiter chaque fichier
    for file_path in args.input_files:
        print(f"Analyse de {file_path}...")
        
        # Extraire la structure
        structure = extract_structure_from_first_object(file_path, llm_fallback=args.llm, model=args.model)
        
        # Enregistrer la structure
        all_structures[file_path] = structure
        
        # Générer la visualisation textuelle
        file_name = os.path.basename(file_path)
        output_tree = os.path.join(args.output_dir, f"{os.path.splitext(file_name)[0]}_structure.txt")
        write_file_structure(file_path, args.output_dir)
        
        print(f"Arborescence générée: {output_tree}")

    # Sauvegarder la structure combinée
    output_path = os.path.join(args.output_dir, args.output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_structures, f, indent=2, ensure_ascii=False)
    
    print(f"Structure JSON générée: {output_path}")

if __name__ == "__main__":
    main() 