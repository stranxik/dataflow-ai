import json
import os
import sys
import re
from datetime import datetime
import argparse
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generic_json_processor import safe_json_load, write_tree, write_file_structure

def extract_structure_from_first_object(json_file_path):
    """
    Extraire la structure du premier objet d'un fichier JSON Confluence
    sans charger l'intégralité du fichier
    """
    with open(json_file_path, 'r', encoding='utf-8') as file:
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

def extract_markdown_keywords(markdown_text, max_keywords=10):
    """
    Extraire des mots-clés pertinents d'un texte markdown
    """
    if not markdown_text:
        return []
    
    # Nettoyer le texte markdown
    # Supprimer les liens, images, et autres syntaxes markdown
    cleaned_text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)  # Images
    cleaned_text = re.sub(r'\[.*?\]\(.*?\)', '', cleaned_text)    # Liens
    cleaned_text = re.sub(r'`.*?`', '', cleaned_text)             # Code inline
    cleaned_text = re.sub(r'```.*?```', '', cleaned_text, flags=re.DOTALL)  # Blocs de code
    cleaned_text = re.sub(r'[#*_~|]', '', cleaned_text)           # Caractères markdown
    
    # Supprimer la ponctuation et convertir en minuscules
    cleaned_text = re.sub(r'[^\w\s]', ' ', cleaned_text.lower())
    
    # Diviser en mots et filtrer les mots courts
    words = [word for word in cleaned_text.split() if len(word) > 3]
    
    # Compter la fréquence des mots
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Trier par fréquence et prendre les top mots
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_keywords]]

def transform_confluence_page(page):
    """
    Transformer une page Confluence en structure optimisée pour LLM
    """
    # Extraire les informations de base
    transformed = {
        "id": page.get("id", ""),
        "title": page.get("title", ""),
        "content": {
            "markdown": page.get("markdown", ""),
            "text": re.sub(r'[#*_~|`]', '', page.get("markdown", "")),  # Version texte simple
            "comments": []
        },
        "metadata": {
            "created_at": page.get("created", ""),
            "updated_at": page.get("updated", ""),
            "created_by": page.get("author", ""),
            "space": page.get("space", {}).get("name", "") if isinstance(page.get("space"), dict) else ""
        },
        "analysis": {
            "keywords": extract_markdown_keywords(page.get("markdown", "")),
            "length": len(page.get("markdown", ""))
        },
        "relationships": {
            "children": [child.get("id", "") for child in page.get("children", [])],
            "parent": page.get("parent", {}).get("id", "") if isinstance(page.get("parent"), dict) else "",
            "jira_tickets": []  # À remplir lors du matching
        }
    }
    
    # Ajouter les commentaires
    if "comments" in page and isinstance(page["comments"], list):
        for comment in page["comments"]:
            if isinstance(comment, dict):
                transformed["content"]["comments"].append({
                    "text": comment.get("body", ""),
                    "author": comment.get("author", ""),
                    "date": comment.get("created", "")
                })
            elif isinstance(comment, str):
                transformed["content"]["comments"].append({
                    "text": comment
                })
    
    return transformed

def transform_confluence_file(file_path, max_pages=None):
    """
    Traiter un fichier JSON Confluence et retourner la structure transformée
    """
    print(f"Traitement du fichier {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            confluence_data = safe_json_load(f, log_prefix=file_path)
        
        if not isinstance(confluence_data, list):
            print(f"Erreur: Le fichier {file_path} ne contient pas un tableau JSON.")
            return []
        
        # Limiter le nombre de pages si nécessaire
        if max_pages:
            confluence_data = confluence_data[:min(max_pages, len(confluence_data))]
        
        # Transformer chaque page
        print(f"Transformation de {len(confluence_data)} pages...")
        transformed_pages = [transform_confluence_page(page) for page in confluence_data]
        
        return transformed_pages
    
    except json.JSONDecodeError as e:
        print(f"Erreur de décodage JSON dans {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Erreur lors du traitement de {file_path}: {e}")
        return []

def save_results(transformed_data, output_file):
    """
    Sauvegarde les données transformées dans un fichier JSON
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transformed_data, f, indent=2, ensure_ascii=False)
        print(f"Données transformées sauvegardées dans {output_file}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des résultats: {e}")

def main():
    parser = argparse.ArgumentParser(description="Analyse et transformation des fichiers d'export Confluence")
    parser.add_argument("--files", nargs="+", default=["hollard_confluence.json"], 
                       help="Fichiers JSON Confluence à analyser")
    parser.add_argument("--output", default="confluence_structure.json", 
                       help="Fichier de sortie pour la structure")
    parser.add_argument("--transform-output", default="llm_ready_confluence.json", 
                       help="Fichier de sortie pour les données transformées")
    parser.add_argument("--max-pages", type=int, default=None, 
                       help="Nombre maximum de pages à traiter par fichier")
    parser.add_argument("--generate-arborescence", action="store_true",
                       help="Générer un fichier d'arborescence pour chaque fichier traité")
    
    args = parser.parse_args()
    
    print(f"Analyse de {len(args.files)} fichiers Confluence...")
    
    # Extraire la structure de chaque fichier
    structures = {}
    all_pages = []
    processed_files = []
    
    for file in args.files:
        if not os.path.exists(file):
            print(f"Erreur: Le fichier {file} n'existe pas.")
            continue
            
        print(f"Analyse de {file}...")
        try:
            structure = extract_structure_from_first_object(file)
            structures[file] = structure
            
            # Transformer les pages Confluence si nécessaire
            pages = transform_confluence_file(file, args.max_pages)
            all_pages.extend(pages)
            processed_files.append(file)
            
        except Exception as e:
            print(f"Erreur lors de l'analyse de {file}: {e}")
            structures[file] = {
                "filename": os.path.basename(file),
                "error": str(e)
            }
    
    # Sauvegarder les résultats de structure
    output_dir = os.path.dirname(args.output) if os.path.dirname(args.output) else "."
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(structures, f, indent=2, ensure_ascii=False)
    
    print(f"\nStructure extraite et sauvegardée dans '{args.output}'")
    
    # Créer la structure finale pour les pages transformées
    final_structure = {
        "pages": all_pages,
        "metadata": {
            "total_pages": len(all_pages),
            "source_files": args.files,
            "created_at": datetime.now().isoformat(),
            "structure_version": "1.0"
        }
    }
    
    save_results(final_structure, args.transform_output)
    
    print(f"\nTraitement terminé. {len(all_pages)} pages transformées.")
    
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
    
    # Générer les arborescences des fichiers si demandé
    if args.generate_arborescence or True:
        # Générer une arborescence globale des fichiers structure
        struct_dir = os.path.dirname(args.output) if os.path.dirname(args.output) else "."
        write_tree(struct_dir, "confluence_structure_arborescence.txt")
        print(f"Arborescence globale de structure générée dans {os.path.join(struct_dir, 'confluence_structure_arborescence.txt')}")
        
        # Générer une arborescence globale des fichiers transformés
        transform_dir = os.path.dirname(args.transform_output) if os.path.dirname(args.transform_output) else "."
        write_tree(transform_dir, "confluence_transform_arborescence.txt")
        print(f"Arborescence globale de transformation générée dans {os.path.join(transform_dir, 'confluence_transform_arborescence.txt')}")
        
        # Générer une arborescence pour chaque fichier traité
        for file_path in processed_files:
            file_base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Arborescence dans le répertoire de structure
            arborescence_file = f"{file_base_name}_arborescence.txt"
            write_file_structure(file_path, struct_dir, arborescence_file)
            print(f"Structure du fichier {file_path} générée dans {os.path.join(struct_dir, arborescence_file)}")

if __name__ == "__main__":
    main() 