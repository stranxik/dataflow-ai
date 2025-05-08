import json
import os
import ijson
import argparse
from tqdm import tqdm
import sys

def process_json_in_chunks(input_file, output_file, chunk_size=100, max_items=None):
    """
    Traite un fichier JSON par morceaux, sans charger l'intégralité du fichier en mémoire.
    
    Args:
        input_file: Fichier JSON d'entrée (tableau d'objets)
        output_file: Fichier JSON où écrire le résultat
        chunk_size: Nombre d'objets à traiter à la fois
        max_items: Nombre maximum d'objets à traiter au total
    """
    try:
        # Vérifier que le fichier d'entrée existe
        if not os.path.exists(input_file):
            print(f"Erreur: Le fichier {input_file} n'existe pas.")
            return False
        
        # Ouvrir le fichier de sortie en mode écriture
        with open(output_file, 'w', encoding='utf-8') as out_file:
            # Commencer le tableau JSON de sortie
            out_file.write('[\n')
            
            # Ouvrir le fichier d'entrée
            with open(input_file, 'rb') as in_file:
                # Initialiser le parser ijson
                parser = ijson.items(in_file, 'item')
                
                count = 0
                first_item = True
                
                # Traiter le fichier par morceaux
                current_chunk = []
                
                # Utiliser tqdm pour afficher une barre de progression
                for item in tqdm(parser, desc=f"Traitement de {os.path.basename(input_file)}", unit="tickets"):
                    # Ajouter l'objet au morceau courant
                    current_chunk.append(item)
                    count += 1
                    
                    # Si le morceau courant est plein ou si c'est le dernier objet
                    if len(current_chunk) >= chunk_size:
                        # Écrire le morceau dans le fichier de sortie
                        for chunk_item in current_chunk:
                            if not first_item:
                                out_file.write(',\n')
                            else:
                                first_item = False
                            
                            json.dump(chunk_item, out_file, ensure_ascii=False)
                        
                        # Réinitialiser le morceau courant
                        current_chunk = []
                    
                    # Si on a atteint le nombre maximum d'objets, arrêter
                    if max_items and count >= max_items:
                        break
                
                # Traiter le dernier morceau s'il n'est pas vide
                for chunk_item in current_chunk:
                    if not first_item:
                        out_file.write(',\n')
                    else:
                        first_item = False
                    
                    json.dump(chunk_item, out_file, ensure_ascii=False)
            
            # Terminer le tableau JSON de sortie
            out_file.write('\n]')
        
        print(f"\nTraitement terminé. {count} objets traités et sauvegardés dans {output_file}")
        return True
    
    except Exception as e:
        print(f"Erreur lors du traitement du fichier: {e}")
        return False

def split_json_file(input_file, output_dir, items_per_file=1000, max_files=None):
    """
    Divise un fichier JSON volumineux en plusieurs fichiers plus petits.
    
    Args:
        input_file: Fichier JSON d'entrée (tableau d'objets)
        output_dir: Répertoire où écrire les fichiers de sortie
        items_per_file: Nombre d'objets par fichier
        max_files: Nombre maximum de fichiers à créer
    """
    try:
        # Vérifier que le fichier d'entrée existe
        if not os.path.exists(input_file):
            print(f"Erreur: Le fichier {input_file} n'existe pas.")
            return False
        
        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)
        
        # Nom de base pour les fichiers de sortie
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        
        # Ouvrir le fichier d'entrée
        with open(input_file, 'rb') as in_file:
            # Initialiser le parser ijson
            parser = ijson.items(in_file, 'item')
            
            file_count = 0
            item_count = 0
            total_count = 0
            current_items = []
            current_file = None
            
            # Traiter le fichier par morceaux
            for item in tqdm(parser, desc=f"Division de {os.path.basename(input_file)}", unit="tickets"):
                # Si on commence un nouveau fichier
                if item_count == 0:
                    if current_file:
                        current_file.write('\n]')
                        current_file.close()
                    
                    file_count += 1
                    
                    # Si on a atteint le nombre maximum de fichiers, arrêter
                    if max_files and file_count > max_files:
                        break
                    
                    # Créer un nouveau fichier
                    output_file = os.path.join(output_dir, f"{base_name}_part{file_count}.json")
                    current_file = open(output_file, 'w', encoding='utf-8')
                    current_file.write('[\n')
                    first_in_file = True
                
                # Ajouter l'objet au fichier courant
                if not first_in_file:
                    current_file.write(',\n')
                else:
                    first_in_file = False
                
                json.dump(item, current_file, ensure_ascii=False)
                
                item_count += 1
                total_count += 1
                
                # Si le fichier courant est plein, on passe au suivant
                if item_count >= items_per_file:
                    item_count = 0
            
            # Fermer le dernier fichier
            if current_file:
                current_file.write('\n]')
                current_file.close()
        
        print(f"\nDivision terminée. {total_count} objets répartis dans {file_count} fichiers.")
        return True
    
    except Exception as e:
        print(f"Erreur lors de la division du fichier: {e}")
        if current_file:
            current_file.close()
        return False

def main():
    parser = argparse.ArgumentParser(description="Traitement de fichiers JSON volumineux")
    
    # Créer des sous-commandes pour les différentes actions
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")
    
    # Sous-commande pour traiter un fichier par morceaux
    process_parser = subparsers.add_parser("process", help="Traiter un fichier JSON par morceaux")
    process_parser.add_argument("--input", required=True, help="Fichier JSON d'entrée")
    process_parser.add_argument("--output", required=True, help="Fichier JSON de sortie")
    process_parser.add_argument("--chunk-size", type=int, default=100, help="Nombre d'objets à traiter à la fois")
    process_parser.add_argument("--max-items", type=int, default=None, help="Nombre maximum d'objets à traiter")
    
    # Sous-commande pour diviser un fichier en plusieurs fichiers plus petits
    split_parser = subparsers.add_parser("split", help="Diviser un fichier JSON en plusieurs fichiers")
    split_parser.add_argument("--input", required=True, help="Fichier JSON d'entrée")
    split_parser.add_argument("--output-dir", required=True, help="Répertoire de sortie")
    split_parser.add_argument("--items-per-file", type=int, default=1000, help="Nombre d'objets par fichier")
    split_parser.add_argument("--max-files", type=int, default=None, help="Nombre maximum de fichiers à créer")
    
    args = parser.parse_args()
    
    # Installer les dépendances si nécessaire
    try:
        import ijson
        import tqdm
    except ImportError:
        print("Installation des dépendances nécessaires...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ijson", "tqdm"])
        import ijson
        import tqdm
    
    # Exécuter la commande demandée
    if args.command == "process":
        process_json_in_chunks(args.input, args.output, args.chunk_size, args.max_items)
    elif args.command == "split":
        split_json_file(args.input, args.output_dir, args.items_per_file, args.max_files)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 