#!/usr/bin/env python3
"""
Script principal pour analyser les fichiers d'export JIRA et les préparer pour
le matching avec Confluence via un LLM.

Ce script coordonne l'exécution des différentes étapes :
1. Extraction de la structure des fichiers JSON
2. Traitement/division des fichiers volumineux si nécessaire
3. Transformation des données pour LLM
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime

# Ajouter l'import pour le résumé LLM
try:
    from llm_summary import generate_llm_summary
except ImportError:
    try:
        from extract.llm_summary import generate_llm_summary 
    except ImportError:
        generate_llm_summary = None
        print("⚠️ Module llm_summary non trouvé, la génération de résumés LLM est désactivée")

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

def main():
    parser = argparse.ArgumentParser(description="Analyse complète des fichiers d'export JIRA pour matching avec Confluence")
    parser.add_argument("--files", nargs="+", default=["CARTAN (1).json", "CASM.json"], 
                       help="Fichiers JSON JIRA à analyser")
    parser.add_argument("--output-dir", default="jira_analysis", 
                       help="Répertoire de sortie pour tous les fichiers générés")
    parser.add_argument("--max-items", type=int, default=1000,
                       help="Nombre maximum d'items à traiter par fichier (pour les tests)")
    parser.add_argument("--with-openai", action="store_true",
                       help="Utiliser OpenAI pour analyser la structure (nécessite une clé API)")
    parser.add_argument("--split-only", action="store_true",
                       help="Uniquement diviser les fichiers volumineux sans faire d'analyse")
    parser.add_argument("--api-key", 
                       help="Clé API OpenAI à utiliser")
    
    args = parser.parse_args()
    
    # S'assurer que les dépendances sont installées
    ensure_deps()
    
    # Créer le répertoire de sortie
    create_output_dir(args.output_dir)
    
    # Journal d'exécution
    log_file = os.path.join(args.output_dir, "execution_log.txt")
    with open(log_file, 'w') as log:
        log.write(f"Exécution démarrée le {datetime.now().isoformat()}\n")
        log.write(f"Fichiers à analyser: {', '.join(args.files)}\n")
    
    # Étape 1: Extraction de la structure basique
    structure_output = os.path.join(args.output_dir, "jira_structure.json")
    run_step(
        [sys.executable, "extract_jira_structure.py"] + args.files,
        "Extraction de la structure de base des fichiers"
    )
    
    # Étape 2: Si les fichiers sont volumineux, les diviser en morceaux
    split_dir = os.path.join(args.output_dir, "split_files")
    create_output_dir(split_dir)
    
    for file in args.files:
        # Vérifier si le fichier est volumineux (> 10 Mo)
        if os.path.getsize(file) > 10 * 1024 * 1024:
            print(f"\nLe fichier {file} est volumineux, division en morceaux...")
            file_split_dir = os.path.join(split_dir, os.path.splitext(os.path.basename(file))[0])
            create_output_dir(file_split_dir)
            
            run_step(
                [sys.executable, "process_by_chunks.py", "split", 
                 "--input", file, 
                 "--output-dir", file_split_dir,
                 "--items-per-file", "500"],
                f"Division du fichier {file} en morceaux"
            )
    
    if args.split_only:
        print("\nMode split-only activé, fin de l'exécution.")
        with open(log_file, 'a') as log:
            log.write(f"Exécution terminée en mode split-only le {datetime.now().isoformat()}\n")
        return
    
    # Étape 3: Transformation pour LLM
    transform_output = os.path.join(args.output_dir, "llm_ready_tickets.json")
    
    # Si les fichiers sont trop volumineux, utiliser seulement un échantillon
    files_to_transform = []
    for file in args.files:
        if os.path.getsize(file) > 50 * 1024 * 1024:  # > 50 Mo
            # Utiliser le premier morceau du fichier divisé
            file_split_dir = os.path.join(split_dir, os.path.splitext(os.path.basename(file))[0])
            if os.path.exists(file_split_dir):
                parts = [f for f in os.listdir(file_split_dir) if f.endswith('.json')]
                if parts:
                    files_to_transform.append(os.path.join(file_split_dir, parts[0]))
                    print(f"Fichier {file} trop volumineux, utilisation de {parts[0]}")
        else:
            files_to_transform.append(file)
    
    transform_cmd = [
        sys.executable, "transform_for_llm.py",
        "--files"
    ] + files_to_transform + [
        "--output", transform_output,
        "--max", str(args.max_items)
    ]
    
    run_step(
        transform_cmd,
        "Transformation des données pour LLM"
    )
    
    # Étape 4: Analyse avec OpenAI si demandé
    if args.with_openai:
        if not args.api_key:
            print("\nErreur: Aucune clé API OpenAI fournie. Utilisez --api-key pour spécifier votre clé.")
        else:
            # Modification temporaire du script analyze_jira_export.py pour utiliser la clé API fournie
            api_key_line = f"client = OpenAI(api_key='{args.api_key}')  # Clé API fournie en argument"
            
            # Lire le fichier
            with open("analyze_jira_export.py", 'r') as f:
                content = f.read()
            
            # Remplacer la ligne de la clé API
            content = content.replace("client = OpenAI(api_key='ta-clé-api')", api_key_line)
            
            # Écrire dans un fichier temporaire
            temp_file = os.path.join(args.output_dir, "temp_analyze.py")
            with open(temp_file, 'w') as f:
                f.write(content)
            
            # Exécuter l'analyse avec OpenAI
            run_step(
                [sys.executable, temp_file],
                "Analyse avec OpenAI"
            )
            
            # Générer un résumé des enrichissements LLM si disponible
            if generate_llm_summary is not None:
                try:
                    # Charger les données transformées
                    with open(transform_output, 'r', encoding='utf-8') as f:
                        processed_data = json.load(f)
                    
                    # Générer le résumé
                    summary_file = generate_llm_summary(
                        args.output_dir,
                        data=processed_data,
                        filename="jira_llm_enrichment_summary.md"
                    )
                    print(f"✅ Résumé de l'enrichissement LLM généré: {summary_file}")
                except Exception as e:
                    print(f"⚠️ Impossible de générer le résumé LLM: {e}")
    
    # Fin de l'exécution
    with open(log_file, 'a') as log:
        log.write(f"Exécution terminée le {datetime.now().isoformat()}\n")
    
    print("\n== Récapitulatif ==")
    print(f"Fichiers analysés: {', '.join(args.files)}")
    print(f"Répertoire de sortie: {args.output_dir}")
    print(f"Structure extraite: {structure_output}")
    print(f"Données transformées pour LLM: {transform_output}")
    if args.with_openai:
        print(f"Analyse OpenAI: {os.path.join(os.getcwd(), 'jira_structure_analysis.txt')}")
        if generate_llm_summary is not None:
            print(f"Résumé de l'enrichissement LLM: {os.path.join(args.output_dir, 'jira_llm_enrichment_summary.md')}")

if __name__ == "__main__":
    main() 