#!/usr/bin/env python3
"""
Script utilitaire pour corriger les problèmes de chemins et de structure JSON.
Ce script:
1. Ne modifie JAMAIS les fichiers sources originaux
2. Crée des copies corrigées des fichiers dans le dossier de résultats
3. Corrige les chemins en double dans les résultats
4. Analyse et répare les fichiers JSON invalides
"""

import os
import sys
import glob
import shutil
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_paths")

def fix_duplicate_paths(base_dir="results"):
    """
    Corriger les chemins en double (results/results/) dans les dossiers de résultats
    
    Args:
        base_dir: Répertoire de base à analyser
        
    Returns:
        Nombre de fichiers déplacés
    """
    # Motif de recherche pour les dossiers avec double chemin
    pattern = os.path.join(base_dir, "results", "**")
    duplicate_dirs = glob.glob(pattern, recursive=False)
    
    moved_count = 0
    
    for dup_dir in duplicate_dirs:
        # Extraire le nom du dossier
        dir_name = os.path.basename(dup_dir)
        
        # Créer le chemin de destination correct
        correct_path = os.path.join(base_dir, dir_name)
        
        logger.info(f"Correction du chemin en double: {dup_dir} -> {correct_path}")
        
        # Si le dossier de destination existe déjà, fusionner
        if os.path.exists(correct_path):
            logger.info(f"Le dossier de destination existe déjà: {correct_path}, fusion...")
            
            # Déplacer tous les fichiers du dossier en double
            for root, dirs, files in os.walk(dup_dir):
                # Calculer le chemin relatif à partir du dossier en double
                rel_path = os.path.relpath(root, dup_dir)
                
                # Créer le dossier de destination s'il n'existe pas
                dest_dir = os.path.join(correct_path, rel_path)
                os.makedirs(dest_dir, exist_ok=True)
                
                # Déplacer tous les fichiers
                for file in files:
                    src_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_dir, file)
                    
                    # Si le fichier existe déjà, ajouter un suffixe
                    if os.path.exists(dest_file):
                        base, ext = os.path.splitext(dest_file)
                        dest_file = f"{base}_dup{ext}"
                    
                    # Déplacer le fichier
                    shutil.move(src_file, dest_file)
                    moved_count += 1
            
            # Supprimer le dossier en double
            shutil.rmtree(dup_dir, ignore_errors=True)
        else:
            # Si le dossier de destination n'existe pas, simplement déplacer
            shutil.move(dup_dir, correct_path)
            moved_count += 1
    
    return moved_count

def process_source_files(source_dir, target_dir, use_llm=False):
    """
    Copie et traite les fichiers sources sans les modifier directement
    
    Args:
        source_dir: Répertoire contenant les fichiers sources
        target_dir: Répertoire où stocker les copies corrigées
        use_llm: Si True, utilise un LLM pour aider à réparer les fichiers
        
    Returns:
        Tuple (copied_count, fixed_count)
    """
    # Créer le répertoire cible s'il n'existe pas
    os.makedirs(target_dir, exist_ok=True)
    
    # Importer notre processeur JSON générique
    try:
        from extract.generic_json_processor import GenericJsonProcessor
    except ImportError:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        try:
            from extract.generic_json_processor import GenericJsonProcessor
        except ImportError:
            logger.error("Module generic_json_processor non trouvé")
            return 0, 0
    
    processor = GenericJsonProcessor(use_llm_fallback=use_llm)
    
    copied_count = 0
    fixed_count = 0
    
    # Explorer le répertoire source à la recherche de fichiers JSON
    for root, dirs, files in os.walk(source_dir):
        # Ignorer les répertoires cachés comme .git
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # Filtrer les fichiers JSON
        json_files = [f for f in files if f.endswith('.json')]
        
        for json_file in json_files:
            source_path = os.path.join(root, json_file)
            
            # Calculer le chemin relatif par rapport au répertoire source
            rel_path = os.path.relpath(source_path, source_dir)
            target_path = os.path.join(target_dir, rel_path)
            
            # Créer le répertoire de destination s'il n'existe pas
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Tenter de charger et standardiser le fichier
            try:
                data = processor.load_file(source_path)
                if data:
                    # Sauvegarder la version standardisée
                    processor.save_as_json(data, target_path)
                    logger.info(f"Fichier traité: {rel_path}")
                    fixed_count += 1
                else:
                    # En cas d'échec, simplement copier le fichier
                    shutil.copy2(source_path, target_path)
                    logger.warning(f"Impossible de traiter, copié tel quel: {rel_path}")
                
                copied_count += 1
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement de {source_path}: {e}")
                # Copier le fichier original en cas d'erreur
                shutil.copy2(source_path, target_path)
                copied_count += 1
    
    return copied_count, fixed_count

def fix_json_files(directory="results", recursive=True, modify_in_place=False):
    """
    Analyser et réparer les fichiers JSON invalides
    
    Args:
        directory: Répertoire à analyser
        recursive: Si True, recherche récursivement dans les sous-répertoires
        modify_in_place: Si True, modifie les fichiers sur place (sinon crée des copies)
        
    Returns:
        Tuple (fixed_count, error_count, skipped_count)
    """
    # Importer notre module de réparation
    try:
        from extract.generic_json_processor import GenericJsonProcessor
    except ImportError:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        try:
            from extract.generic_json_processor import GenericJsonProcessor
        except ImportError:
            logger.error("Module generic_json_processor non trouvé")
            return 0, 0, 0
    
    processor = GenericJsonProcessor(use_llm_fallback=True)
    
    fixed_count = 0
    error_count = 0
    skipped_count = 0
    
    # Explorer le répertoire à la recherche de fichiers JSON
    for root, dirs, files in os.walk(directory):
        if not recursive:
            # Si non récursif, vider la liste des sous-répertoires
            dirs.clear()
        
        # Ignorer les répertoires cachés comme .git
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # Filtrer les fichiers JSON
        json_files = [f for f in files if f.endswith('.json')]
        
        for json_file in json_files:
            file_path = os.path.join(root, json_file)
            
            try:
                # Tenter de charger et standardiser le fichier
                data = processor.load_file(file_path)
                
                if data:
                    # Déterminer le chemin de sortie
                    if modify_in_place:
                        output_path = file_path
                    else:
                        # Créer un nouveau nom de fichier avec "_fixed" suffixe
                        base, ext = os.path.splitext(file_path)
                        output_path = f"{base}_fixed{ext}"
                    
                    # Sauvegarder la version standardisée
                    processor.save_as_json(data, output_path)
                    fixed_count += 1
                else:
                    error_count += 1
            
            except Exception as e:
                logger.error(f"Erreur lors du traitement de {file_path}: {e}")
                error_count += 1
    
    return fixed_count, error_count, skipped_count

def update_file_structure(directory="results", recursive=True):
    """
    Mettre à jour les fichiers de structure dans les dossiers de résultats
    
    Args:
        directory: Répertoire à analyser
        recursive: Si True, recherche récursivement dans les sous-répertoires
        
    Returns:
        Nombre de fichiers générés
    """
    from extract.generic_json_processor import write_tree, write_file_structure
    
    # Trouver tous les dossiers de résultats
    result_dirs = []
    
    if recursive:
        # Parcourir tous les sous-répertoires
        for root, dirs, files in os.walk(directory):
            # Ignorer les dossiers node_modules et __pycache__
            dirs[:] = [d for d in dirs if d not in ['node_modules', '__pycache__']]
            
            # Si le dossier contient des fichiers JSON, c'est un dossier de résultats
            if any(f.endswith('.json') for f in files):
                result_dirs.append(root)
    else:
        # Uniquement le répertoire spécifié
        if os.path.exists(directory) and os.path.isdir(directory):
            result_dirs.append(directory)
    
    generated_count = 0
    
    # Traiter chaque dossier
    for result_dir in result_dirs:
        logger.info(f"Mise à jour de la structure dans: {result_dir}")
        
        # Générer l'arborescence
        write_tree(result_dir, "arborescence.txt")
        generated_count += 1
        
        # Analyser chaque fichier JSON dans le dossier
        json_files = [f for f in os.listdir(result_dir) if f.endswith('.json')]
        for json_file in json_files:
            file_path = os.path.join(result_dir, json_file)
            
            # Générer le rapport de structure
            base_name = os.path.splitext(json_file)[0]
            output_filename = f"{base_name}_structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            write_file_structure(file_path, result_dir, output_filename)
            generated_count += 1
    
    return generated_count

def main():
    parser = argparse.ArgumentParser(description="Corriger les problèmes de chemins et de structure JSON sans modifier les sources")
    parser.add_argument("--source-dir", "-s", default="files", help="Répertoire contenant les fichiers sources")
    parser.add_argument("--target-dir", "-t", default="results", help="Répertoire où stocker les résultats")
    parser.add_argument("--recursive", "-r", action="store_true", help="Recherche récursive dans les sous-répertoires")
    parser.add_argument("--fix-paths", action="store_true", help="Corriger les chemins en double")
    parser.add_argument("--fix-json", action="store_true", help="Réparer les fichiers JSON invalides (dans le répertoire cible)")
    parser.add_argument("--update-structure", action="store_true", help="Mettre à jour les fichiers de structure")
    parser.add_argument("--process-sources", action="store_true", help="Traiter les fichiers sources et les copier dans le répertoire cible")
    parser.add_argument("--use-llm", action="store_true", help="Utiliser un LLM pour aider à réparer les fichiers")
    parser.add_argument("--all", "-a", action="store_true", help="Exécuter toutes les corrections")
    
    args = parser.parse_args()
    
    # Si aucune action spécifiée, exécuter toutes les corrections
    if not (args.fix_paths or args.fix_json or args.update_structure or args.process_sources or args.all):
        args.all = True
    
    # Exécuter les corrections demandées
    if args.process_sources or args.all:
        copied_count, fixed_count = process_source_files(args.source_dir, args.target_dir, args.use_llm)
        logger.info(f"✅ {copied_count} fichiers sources copiés")
        logger.info(f"✅ {fixed_count} fichiers sources réparés pendant la copie")
    
    if args.fix_paths or args.all:
        moved_count = fix_duplicate_paths(args.target_dir)
        logger.info(f"✅ {moved_count} fichiers déplacés pour corriger les chemins en double")
    
    if args.fix_json or args.all:
        fixed_count, error_count, skipped_count = fix_json_files(args.target_dir, args.recursive, modify_in_place=False)
        logger.info(f"✅ {fixed_count} fichiers JSON réparés")
        logger.info(f"❌ {error_count} fichiers JSON avec erreurs persistantes")
        logger.info(f"⚠️ {skipped_count} fichiers JSON ignorés")
    
    if args.update_structure or args.all:
        generated_count = update_file_structure(args.target_dir, args.recursive)
        logger.info(f"✅ {generated_count} fichiers de structure générés")

if __name__ == "__main__":
    main() 