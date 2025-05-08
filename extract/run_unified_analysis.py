#!/usr/bin/env python3
"""
Script principal unifié pour analyser et mettre en correspondance 
les fichiers d'export JIRA et Confluence.

Ce script coordonne l'exécution des différentes étapes :
1. Extraction de la structure des fichiers JSON (JIRA et Confluence)
2. Traitement/division des fichiers volumineux si nécessaire
3. Transformation des données pour optimisation LLM
4. Matching entre tickets JIRA et pages Confluence
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generic_json_processor import write_tree, write_file_structure

SCRIPTS_DIR = os.path.dirname(__file__)

def ensure_deps():
    """S'assurer que toutes les dépendances sont installées"""
    deps = ["ijson", "tqdm", "openai"]
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            print(f"Installation de {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

def create_output_dir(output_dir):
    """Créer le répertoire de sortie s'il n'existe pas"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Répertoire de sortie {output_dir} créé.")

def run_step(cmd, desc):
    """Exécuter une commande et afficher sa description"""
    print(f"\n== {desc} ==")
    print(f"Commande: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erreur: {e}")
        print(e.stdout)
        print(e.stderr)
        return False

def resolve_input_path(path):
    """Résout le chemin absolu d'un fichier d'entrée, en cherchant dans le dossier courant et dans ./files/ si besoin."""
    if os.path.isabs(path):
        return path
    if os.path.exists(path):
        return os.path.abspath(path)
    files_dir = os.path.join(os.getcwd(), 'files')
    candidate = os.path.join(files_dir, path)
    if os.path.exists(candidate):
        return candidate
    return os.path.abspath(path)  # fallback

def main():
    parser = argparse.ArgumentParser(description="Analyse unifiée des fichiers d'export JIRA et Confluence pour matching")
    
    # Fichiers d'entrée
    parser.add_argument("--jira-files", nargs="+", default=["CARTAN (1).json", "CASM.json"], 
                       help="Fichiers JSON JIRA à analyser")
    parser.add_argument("--confluence-files", nargs="+", default=["hollard_confluence.json"], 
                       help="Fichiers JSON Confluence à traiter")
    
    # Options de sortie
    parser.add_argument("--output-dir", default="unified_analysis", 
                       help="Répertoire de sortie pour tous les fichiers générés")
    parser.add_argument("--jira-dir", default=None,
                       help="Sous-répertoire pour les fichiers JIRA traités")
    parser.add_argument("--confluence-dir", default=None,
                       help="Sous-répertoire pour les fichiers Confluence traités")
    parser.add_argument("--matches-dir", default=None,
                       help="Sous-répertoire pour les fichiers de correspondance")
    parser.add_argument("--split-jira-dir", default=None,
                       help="Sous-répertoire pour les fichiers JIRA divisés")
    parser.add_argument("--split-confluence-dir", default=None,
                       help="Sous-répertoire pour les fichiers Confluence divisés")
    parser.add_argument("--llm-ready-dir", default=None,
                       help="Sous-répertoire pour les fichiers prêts pour LLM")
    
    # Options de traitement
    parser.add_argument("--max-items", type=int, default=1000,
                       help="Nombre maximum d'items à traiter par fichier (pour les tests)")
    parser.add_argument("--min-match-score", type=float, default=0.2,
                       help="Score minimum pour considérer une correspondance lors du matching")
    parser.add_argument("--skip-matching", action="store_true",
                       help="Ne pas effectuer le matching entre JIRA et Confluence")
    parser.add_argument("--with-openai", action="store_true",
                       help="Utiliser OpenAI pour analyser la structure (nécessite une clé API)")
    parser.add_argument("--split-only", action="store_true",
                       help="Uniquement diviser les fichiers volumineux sans faire d'analyse")
    parser.add_argument("--api-key", 
                       help="Clé API OpenAI à utiliser")
    
    args = parser.parse_args()
    
    # Initialiser les variables pour éviter UnboundLocalError
    updated_jira_output = None
    updated_confluence_output = None
    matches_output = None
    
    # S'assurer que les dépendances sont installées
    ensure_deps()
    
    # Créer le répertoire de sortie principal
    create_output_dir(args.output_dir)
    
    # Configurer les sous-répertoires
    jira_dir = args.jira_dir or os.path.join(args.output_dir, "jira")
    confluence_dir = args.confluence_dir or os.path.join(args.output_dir, "confluence")
    matches_dir = args.matches_dir or os.path.join(args.output_dir, "matches")
    split_jira_dir = args.split_jira_dir or os.path.join(args.output_dir, "split_jira_files")
    split_confluence_dir = args.split_confluence_dir or os.path.join(args.output_dir, "split_confluence_files")
    llm_ready_dir = args.llm_ready_dir or os.path.join(args.output_dir, "llm_ready")
    
    # Créer tous les sous-répertoires
    for directory in [jira_dir, confluence_dir, matches_dir, split_jira_dir, split_confluence_dir, llm_ready_dir]:
        create_output_dir(directory)
    
    # Résoudre les chemins des fichiers d'entrée
    jira_files_abs = [resolve_input_path(f) for f in args.jira_files]
    confluence_files_abs = [resolve_input_path(f) for f in args.confluence_files]
    
    # Journal d'exécution
    log_file = os.path.join(args.output_dir, "execution_log.txt")
    with open(log_file, 'w') as log:
        log.write(f"Exécution démarrée le {datetime.now().isoformat()}\n")
        log.write(f"Fichiers JIRA à analyser: {', '.join(jira_files_abs)}\n")
        log.write(f"Fichiers Confluence à analyser: {', '.join(confluence_files_abs)}\n")
        log.write(f"Structure des répertoires:\n")
        log.write(f"  - Principal: {args.output_dir}\n")
        log.write(f"  - JIRA: {jira_dir}\n")
        log.write(f"  - Confluence: {confluence_dir}\n")
        log.write(f"  - Correspondances: {matches_dir}\n")
        log.write(f"  - Fichiers JIRA divisés: {split_jira_dir}\n")
        log.write(f"  - Fichiers Confluence divisés: {split_confluence_dir}\n")
        log.write(f"  - Fichiers prêts pour LLM: {llm_ready_dir}\n")
    
    #######################################
    # PARTIE 1: TRAITEMENT DES FICHIERS JIRA
    #######################################
    
    # 1.1 Extraction de la structure basique
    jira_structure_output = os.path.join(jira_dir, "jira_structure.json")
    run_step(
        [sys.executable, os.path.join(SCRIPTS_DIR, "extract_jira_structure.py")] + jira_files_abs + [
            "--output", jira_structure_output
        ],
        "Extraction de la structure de base des fichiers JIRA"
    )
    
    # 1.2 Si les fichiers sont volumineux, les diviser en morceaux
    for file in jira_files_abs:
        # Vérifier si le fichier est volumineux (> 10 Mo)
        if os.path.exists(file) and os.path.getsize(file) > 10 * 1024 * 1024:
            print(f"\nLe fichier {file} est volumineux, division en morceaux...")
            file_base_name = os.path.splitext(os.path.basename(file))[0]
            file_split_dir = os.path.join(split_jira_dir, f"{file_base_name}_jira")
            create_output_dir(file_split_dir)
            
            run_step(
                [sys.executable, os.path.join(SCRIPTS_DIR, "process_by_chunks.py"), "split",
                 "--input", file,
                 "--output-dir", file_split_dir,
                 "--items-per-file", "500"],
                f"Division du fichier {file} en morceaux"
            )
            
            # Générer l'arborescence du répertoire de morceaux
            arborescence_file = os.path.join(file_split_dir, f"{file_base_name}_arborescence.txt")
            write_tree(file_split_dir, os.path.basename(arborescence_file))
            print(f"Arborescence générée dans {arborescence_file}")
    
    if args.split_only:
        print("\nMode split-only activé, fin de l'exécution.")
        with open(log_file, 'a') as log:
            log.write(f"Exécution terminée en mode split-only le {datetime.now().isoformat()}\n")
        return
    
    # 1.3 Transformation pour LLM
    jira_transform_output = os.path.join(llm_ready_dir, "llm_ready_jira.json")
    
    # Si les fichiers sont trop volumineux, utiliser seulement un échantillon
    jira_files_to_transform = []
    for file in jira_files_abs:
        if os.path.exists(file):
            if os.path.getsize(file) > 50 * 1024 * 1024:  # > 50 Mo
                # Utiliser le premier morceau du fichier divisé
                file_base_name = os.path.splitext(os.path.basename(file))[0]
                file_split_dir = os.path.join(split_jira_dir, f"{file_base_name}_jira")
                if os.path.exists(file_split_dir):
                    parts = [f for f in os.listdir(file_split_dir) if f.endswith('.json')]
                    if parts:
                        jira_files_to_transform.append(os.path.join(file_split_dir, parts[0]))
                        print(f"Fichier {file} trop volumineux, utilisation de {parts[0]}")
            else:
                jira_files_to_transform.append(file)
    
    if jira_files_to_transform:
        transform_jira_cmd = [
            sys.executable, os.path.join(SCRIPTS_DIR, "transform_for_llm.py"),
            "--files"
        ] + jira_files_to_transform + [
            "--output", jira_transform_output,
            "--max", str(args.max_items),
            "--generate-arborescence"
        ]
        
        run_step(
            transform_jira_cmd,
            "Transformation des données JIRA pour LLM"
        )
    else:
        print("\nAucun fichier JIRA valide à transformer.")
    
    #######################################
    # PARTIE 2: TRAITEMENT DES FICHIERS CONFLUENCE
    #######################################
    
    # 2.1 Extraction de la structure basique
    confluence_structure_output = os.path.join(confluence_dir, "confluence_structure.json")
    run_step(
        [sys.executable, os.path.join(SCRIPTS_DIR, "extract_confluence_structure.py"), "--files"] + confluence_files_abs + [
            "--output", confluence_structure_output
        ],
        "Extraction de la structure de base des fichiers Confluence"
    )
    
    # 2.2 Si les fichiers sont volumineux, les diviser en morceaux
    for file in confluence_files_abs:
        # Vérifier si le fichier est volumineux (> 10 Mo)
        if os.path.exists(file) and os.path.getsize(file) > 10 * 1024 * 1024:
            print(f"\nLe fichier {file} est volumineux, division en morceaux...")
            file_base_name = os.path.splitext(os.path.basename(file))[0]
            file_split_dir = os.path.join(split_confluence_dir, f"{file_base_name}_confluence")
            create_output_dir(file_split_dir)
            
            run_step(
                [sys.executable, os.path.join(SCRIPTS_DIR, "process_by_chunks.py"), "split",
                 "--input", file,
                 "--output-dir", file_split_dir,
                 "--items-per-file", "500"],
                f"Division du fichier {file} en morceaux"
            )
            
            # Générer l'arborescence du répertoire de morceaux
            arborescence_file = os.path.join(file_split_dir, f"{file_base_name}_arborescence.txt")
            write_tree(file_split_dir, os.path.basename(arborescence_file))
            print(f"Arborescence générée dans {arborescence_file}")
    
    # 2.3 Transformation pour LLM
    confluence_transform_output = os.path.join(llm_ready_dir, "llm_ready_confluence.json")
    
    # Si les fichiers sont trop volumineux, utiliser seulement un échantillon
    confluence_files_to_transform = []
    for file in confluence_files_abs:
        if os.path.exists(file):
            if os.path.getsize(file) > 50 * 1024 * 1024:  # > 50 Mo
                # Utiliser le premier morceau du fichier divisé
                file_base_name = os.path.splitext(os.path.basename(file))[0]
                file_split_dir = os.path.join(split_confluence_dir, f"{file_base_name}_confluence")
                if os.path.exists(file_split_dir):
                    parts = [f for f in os.listdir(file_split_dir) if f.endswith('.json')]
                    if parts:
                        confluence_files_to_transform.append(os.path.join(file_split_dir, parts[0]))
                        print(f"Fichier {file} trop volumineux, utilisation de {parts[0]}")
            else:
                confluence_files_to_transform.append(file)
    
    if confluence_files_to_transform:
        transform_confluence_cmd = [
            sys.executable, os.path.join(SCRIPTS_DIR, "transform_for_llm.py"),
            "--files"
        ] + confluence_files_to_transform + [
            "--output", confluence_transform_output,
            "--max", str(args.max_items),
            "--generate-arborescence"
        ]
        
        run_step(
            transform_confluence_cmd,
            "Transformation des données Confluence pour LLM"
        )
    else:
        print("\nAucun fichier Confluence valide à transformer.")
    
    #######################################
    # PARTIE 3: MATCHING JIRA-CONFLUENCE
    #######################################
    
    # Passer le matching si demandé
    if args.skip_matching:
        print("\nSkipping de la phase de matching JIRA-Confluence.")
    else:
        # Vérifier que les fichiers nécessaires existent
        if not os.path.exists(jira_transform_output):
            print(f"[ERREUR] Fichier JIRA transformé non trouvé: {jira_transform_output}")
        elif not os.path.exists(confluence_transform_output):
            print(f"[ERREUR] Fichier Confluence transformé non trouvé: {confluence_transform_output}")
        else:
            # Exécuter le matching
            matches_output = os.path.join(matches_dir, "jira_confluence_matches.json")
            updated_jira_output = os.path.join(matches_dir, "jira_with_matches.json")
            updated_confluence_output = os.path.join(matches_dir, "confluence_with_matches.json")
            
            match_cmd = [
                sys.executable, os.path.join(SCRIPTS_DIR, "match_jira_confluence.py"),
                "--jira", jira_transform_output,
                "--confluence", confluence_transform_output,
                "--output", matches_output,
                "--updated-jira", updated_jira_output,
                "--updated-confluence", updated_confluence_output,
                "--min-score", str(args.min_match_score)
            ]
            
            run_step(
                match_cmd,
                "Matching entre tickets JIRA et pages Confluence"
            )
            
            # Générer l'arborescence du résultat de matching
            matches_arborescence = os.path.join(matches_dir, "matches_arborescence.txt")
            write_tree(matches_dir, os.path.basename(matches_arborescence))
            print(f"Arborescence des correspondances générée dans {matches_arborescence}")
    
    #######################################
    # PARTIE 4: ANALYSE AVEC OPENAI (optionnel)
    #######################################
    
    if args.with_openai:
        # Vérifier que la clé API est disponible
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("\n[ERREUR] Aucune clé API OpenAI trouvée. L'analyse OpenAI ne sera pas effectuée.")
        else:
            print("\nAnalyse des données avec OpenAI...")
            
            # TODO: Implémentation de l'analyse OpenAI
            # Cette partie pourrait analyser les fichiers traités et les correspondances
            # pour fournir des insights supplémentaires
            
            print("[TODO] L'analyse OpenAI n'est pas encore implémentée.")
    
    # Fin de l'exécution
    with open(log_file, 'a') as log:
        log.write(f"Exécution terminée le {datetime.now().isoformat()}\n")
    
    print("\n== Récapitulatif ==")
    print(f"Fichiers JIRA analysés: {', '.join(args.jira_files)}")
    print(f"Fichiers Confluence analysés: {', '.join(args.confluence_files)}")
    print(f"Répertoire de sortie: {args.output_dir}")
    
    if os.path.exists(jira_transform_output):
        print(f"Données JIRA transformées: {jira_transform_output}")
    
    if os.path.exists(confluence_transform_output):
        print(f"Données Confluence transformées: {confluence_transform_output}")
    
    if (
        not args.skip_matching
        and updated_jira_output is not None
        and updated_confluence_output is not None
        and matches_output is not None
        and os.path.exists(updated_jira_output)
        and os.path.exists(updated_confluence_output)
    ):
        print(f"Correspondances JIRA-Confluence: {matches_output}")
        print(f"Tickets JIRA avec correspondances: {updated_jira_output}")
        print(f"Pages Confluence avec correspondances: {updated_confluence_output}")

    # Générer l'arborescence globale du dossier de sortie
    global_arborescence = os.path.join(args.output_dir, "global_arborescence.txt")
    write_tree(args.output_dir, os.path.basename(global_arborescence))
    print(f"\nArborescence globale du dossier de sortie générée dans {global_arborescence}")
    
    # Générer des arborescences détaillées pour chaque fichier source
    print("\nGénération des arborescences des fichiers source:")
    
    # Arborescences pour les fichiers JIRA
    for file in jira_files_abs:
        if os.path.exists(file):
            file_base_name = os.path.splitext(os.path.basename(file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arborescence_file = f"{file_base_name}_arborescence_{timestamp}.txt"
            write_file_structure(file, args.output_dir, arborescence_file)
            print(f"- Structure du fichier JIRA '{file}' générée dans {os.path.join(args.output_dir, arborescence_file)}")
    
    # Arborescences pour les fichiers Confluence
    for file in confluence_files_abs:
        if os.path.exists(file):
            file_base_name = os.path.splitext(os.path.basename(file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arborescence_file = f"{file_base_name}_arborescence_{timestamp}.txt"
            write_file_structure(file, args.output_dir, arborescence_file)
            print(f"- Structure du fichier Confluence '{file}' générée dans {os.path.join(args.output_dir, arborescence_file)}")
    
    print("\nTraitement terminé avec succès!")

if __name__ == "__main__":
    main() 