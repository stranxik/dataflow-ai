import json
import os
import sys
import argparse
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generic_json_processor import safe_json_load, write_tree, write_file_structure

def extract_structure_from_first_object(json_file_path):
    """
    Extraire la structure du premier objet d'un fichier JSON volumineux
    sans charger l'intégralité du fichier
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
            data = safe_json_load(io.StringIO(content), log_prefix=json_file_path)
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
    # Configuration de l'argument parser
    parser = argparse.ArgumentParser(description="Extraire la structure des fichiers JSON JIRA")
    parser.add_argument("files", nargs="*", help="Fichiers à analyser")
    parser.add_argument("--output", default="jira_structure.json", help="Fichier de sortie")
    args = parser.parse_args()
    
    # Vérifier si des fichiers à analyser ont été spécifiés
    if args.files:
        files_to_analyze = args.files
    else:
        files_to_analyze = ['CARTAN (1).json', 'CASM.json']
    
    print(f"Analyse de {len(files_to_analyze)} fichiers JIRA...")
    
    # Extraire la structure de chaque fichier
    structures = {}
    for file in files_to_analyze:
        if not os.path.exists(file):
            print(f"Erreur: Le fichier {file} n'existe pas.")
            continue
            
        print(f"Analyse de {file}...")
        try:
            structure = extract_structure_from_first_object(file)
            structures[file] = structure
        except Exception as e:
            print(f"Erreur lors de l'analyse de {file}: {e}")
            structures[file] = {
                "filename": os.path.basename(file),
                "error": str(e)
            }
    
    # Sauvegarder les résultats
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(structures, f, indent=2, ensure_ascii=False)
    
    print(f"\nStructure extraite et sauvegardée dans '{args.output}'")
    
    # Afficher un résumé
    print("\nRÉSUMÉ DES STRUCTURES:")
    print("----------------------")
    for filename, structure in structures.items():
        print(f"\n{os.path.basename(filename)}:")
        if "error" in structure:
            print(f"  Erreur: {structure['error']}")
        else:
            print(f"  Clés: {', '.join(structure['structure']['keys'])}")
            print("  Types de données:")
            for key, type_info in structure['structure']['nested_structures'].items():
                print(f"    - {key}: {type_info}")

    # Générer l'arborescence du fichier traité
    output_dir = os.path.dirname(args.output) if os.path.dirname(args.output) else "."
    for file in files_to_analyze:
        if os.path.exists(file):
            file_base_name = os.path.splitext(os.path.basename(file))[0]
            arborescence_file = f"{file_base_name}_arborescence.txt"
            write_file_structure(file, output_dir, arborescence_file)
            print(f"Structure du fichier {file} générée dans {os.path.join(output_dir, arborescence_file)}")

if __name__ == "__main__":
    main() 