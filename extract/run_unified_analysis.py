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
import glob
import shutil
import traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generic_json_processor import write_tree, write_file_structure
from llm_summary import generate_llm_summary

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

def check_outlines():
    """Vérifie si Outlines est correctement installé et configuré"""
    try:
        import outlines
        print(f"✅ Module Outlines détecté (version: {getattr(outlines, '__version__', 'inconnue')})")
        
        # Vérifier si la clé API est configurée
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("⚠️ Aucune clé API OpenAI trouvée. L'enrichissement LLM ne sera pas disponible.")
            return False
        
        # Essayer d'initialiser un modèle simple
        try:
            model = outlines.models.openai("gpt-3.5-turbo", api_key=api_key)
            print("✅ Connexion à l'API OpenAI établie")
            return True
        except Exception as e:
            print(f"⚠️ Erreur lors de l'initialisation du modèle OpenAI: {e}")
            return False
            
    except ImportError:
        print("⚠️ Module Outlines non détecté. Installation automatique...")
        
        try:
            # Installer Outlines avec pip
            import subprocess
            result = subprocess.run([sys.executable, "-m", "pip", "install", "outlines==0.2.3"], 
                                   capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Outlines installé avec succès")
                # Vérifier l'installation
                try:
                    import outlines
                    print(f"✅ Outlines importé avec succès (version: {getattr(outlines, '__version__', 'inconnue')})")
                    return True
                except ImportError:
                    print("❌ Échec de l'importation d'Outlines après installation")
                    return False
            else:
                print(f"❌ Échec de l'installation d'Outlines: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors de l'installation d'Outlines: {e}")
            return False
    
    return False

def run_llm_enrichment(jira_file, confluence_file, output_dir, api_key, model="gpt-4-0125-preview"):
    """Exécute l'enrichissement par LLM des données JIRA et Confluence"""
    
    # Vérifier que les fichiers existent
    if not os.path.exists(jira_file) or not os.path.exists(confluence_file):
        print("❌ Fichiers d'entrée manquants pour l'enrichissement LLM")
        return False
    
    print("\n== Enrichissement LLM des données ==")
    
    # S'assurer que la clé API est définie
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    # Importer le module d'enrichissement
    try:
        from extract.outlines_enricher import enrich_data_file, check_outlines
        
        # Vérifier que Outlines est disponible
        outlines_available = check_outlines()
        if not outlines_available:
            print("⚠️ Outlines n'est pas disponible, l'enrichissement LLM pourrait être limité")
        
        # Définir les chemins de sortie
        jira_output = os.path.join(output_dir, "enriched_jira.json")
        confluence_output = os.path.join(output_dir, "enriched_confluence.json")
        
        # Enrichir les fichiers JIRA et Confluence
        print(f"🔄 Enrichissement JIRA avec le modèle {model}...")
        jira_success = enrich_data_file(jira_file, jira_output, model)
        
        print(f"🔄 Enrichissement Confluence avec le modèle {model}...")
        confluence_success = enrich_data_file(confluence_file, confluence_output, model)
        
        # Créer les fichiers de résumé
        if jira_success:
            create_jira_summary(jira_output, os.path.join(output_dir, "jira_llm_enrichment_summary.md"))
        
        if confluence_success:
            create_confluence_summary(confluence_output, os.path.join(output_dir, "llm_enrichment_summary.md"))
        
        return jira_success and confluence_success
        
    except ImportError:
        print("❌ Module d'enrichissement non disponible")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'enrichissement LLM: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_jira_summary(jira_file, output_file):
    """
    Crée un résumé des enrichissements JIRA au format Markdown
    
    Args:
        jira_file: Chemin vers le fichier JIRA enrichi
        output_file: Chemin vers le fichier de sortie
    """
    try:
        with open(jira_file, 'r', encoding='utf-8') as f:
            jira_data = json.load(f)
        
        if "items" not in jira_data or not jira_data["items"]:
            print("⚠️ Aucun ticket JIRA trouvé pour générer le résumé")
            return False
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Résumé de l'enrichissement LLM des tickets JIRA\n\n")
            
            # Ajouter les métadonnées
            if "metadata" in jira_data and "llm_enrichment" in jira_data["metadata"]:
                enrichment = jira_data["metadata"]["llm_enrichment"]
                f.write(f"- **Modèle utilisé**: {enrichment.get('model', 'Non spécifié')}\n")
                f.write(f"- **Date d'enrichissement**: {enrichment.get('enrichment_date', 'Non spécifiée')}\n")
                f.write(f"- **Nombre de tickets enrichis**: {enrichment.get('enriched_items_count', 0)}\n\n")
            
            # Créer une table des matières
            f.write("## Table des matières\n\n")
            for i, item in enumerate(jira_data["items"]):
                title = item.get("title", f"Ticket {i+1}")
                key = item.get("key", i+1)
                f.write(f"- [{title} ({key})](#ticket-{i+1})\n")
            f.write("\n")
            
            # Ajouter les résumés de chaque ticket
            for i, item in enumerate(jira_data["items"]):
                title = item.get("title", f"Ticket {i+1}")
                key = item.get("key", i+1)
                f.write(f"## Ticket {i+1}: {title} ({key})\n\n")
                
                if "analysis" in item and "llm_summary" in item["analysis"]:
                    f.write(f"### Résumé\n\n{item['analysis']['llm_summary']}\n\n")
                    
                    if "llm_keywords" in item["analysis"]:
                        keywords = item["analysis"]["llm_keywords"]
                        if keywords:
                            f.write(f"### Mots-clés\n\n")
                            for keyword in keywords:
                                f.write(f"- {keyword}\n")
                            f.write("\n")
                    
                    if "llm_entities" in item["analysis"] and item["analysis"]["llm_entities"]:
                        entities = item["analysis"]["llm_entities"]
                        f.write(f"### Entités\n\n")
                        
                        if "people" in entities and entities["people"]:
                            f.write("#### Personnes\n\n")
                            for person in entities["people"]:
                                f.write(f"- {person}\n")
                            f.write("\n")
                        
                        if "organizations" in entities and entities["organizations"]:
                            f.write("#### Organisations\n\n")
                            for org in entities["organizations"]:
                                f.write(f"- {org}\n")
                            f.write("\n")
                        
                        if "technical_terms" in entities and entities["technical_terms"]:
                            f.write("#### Termes techniques\n\n")
                            for term in entities["technical_terms"]:
                                f.write(f"- {term}\n")
                            f.write("\n")
                    
                    if "llm_sentiment" in item["analysis"]:
                        sentiment = item["analysis"]["llm_sentiment"]
                        f.write(f"### Sentiment\n\n{sentiment}\n\n")
                else:
                    f.write("*Aucune analyse LLM disponible pour ce ticket.*\n\n")
                
                f.write("---\n\n")
        
        print(f"✅ Résumé JIRA généré dans {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du résumé JIRA: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_confluence_summary(confluence_file, output_file):
    """
    Crée un résumé des enrichissements Confluence au format Markdown
    
    Args:
        confluence_file: Chemin vers le fichier Confluence enrichi
        output_file: Chemin vers le fichier de sortie
    """
    try:
        with open(confluence_file, 'r', encoding='utf-8') as f:
            confluence_data = json.load(f)
        
        if "items" not in confluence_data or not confluence_data["items"]:
            print("⚠️ Aucune page Confluence trouvée pour générer le résumé")
            return False
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Résumé de l'enrichissement LLM des pages Confluence\n\n")
            
            # Ajouter les métadonnées
            if "metadata" in confluence_data and "llm_enrichment" in confluence_data["metadata"]:
                enrichment = confluence_data["metadata"]["llm_enrichment"]
                f.write(f"- **Modèle utilisé**: {enrichment.get('model', 'Non spécifié')}\n")
                f.write(f"- **Date d'enrichissement**: {enrichment.get('enrichment_date', 'Non spécifiée')}\n")
                f.write(f"- **Nombre de pages enrichies**: {enrichment.get('enriched_items_count', 0)}\n\n")
            
            # Créer une table des matières
            f.write("## Table des matières\n\n")
            for i, item in enumerate(confluence_data["items"]):
                title = item.get("title", f"Page {i+1}")
                id = item.get("id", i+1)
                f.write(f"- [{title}](#page-{i+1})\n")
            f.write("\n")
            
            # Ajouter les résumés de chaque page
            for i, item in enumerate(confluence_data["items"]):
                title = item.get("title", f"Page {i+1}")
                id = item.get("id", i+1)
                f.write(f"## Page {i+1}: {title}\n\n")
                
                if "analysis" in item and "llm_summary" in item["analysis"]:
                    f.write(f"### Résumé\n\n{item['analysis']['llm_summary']}\n\n")
                    
                    if "llm_keywords" in item["analysis"]:
                        keywords = item["analysis"]["llm_keywords"]
                        if keywords:
                            f.write(f"### Mots-clés\n\n")
                            for keyword in keywords:
                                f.write(f"- {keyword}\n")
                            f.write("\n")
                    
                    if "llm_entities" in item["analysis"] and item["analysis"]["llm_entities"]:
                        entities = item["analysis"]["llm_entities"]
                        f.write(f"### Entités\n\n")
                        
                        if "people" in entities and entities["people"]:
                            f.write("#### Personnes\n\n")
                            for person in entities["people"]:
                                f.write(f"- {person}\n")
                            f.write("\n")
                        
                        if "organizations" in entities and entities["organizations"]:
                            f.write("#### Organisations\n\n")
                            for org in entities["organizations"]:
                                f.write(f"- {org}\n")
                            f.write("\n")
                        
                        if "technical_terms" in entities and entities["technical_terms"]:
                            f.write("#### Termes techniques\n\n")
                            for term in entities["technical_terms"]:
                                f.write(f"- {term}\n")
                            f.write("\n")
                    
                    if "llm_sentiment" in item["analysis"]:
                        sentiment = item["analysis"]["llm_sentiment"]
                        f.write(f"### Sentiment\n\n{sentiment}\n\n")
                else:
                    f.write("*Aucune analyse LLM disponible pour cette page.*\n\n")
                
                f.write("---\n\n")
        
        print(f"✅ Résumé Confluence généré dans {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du résumé Confluence: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Analyse unifiée des fichiers JIRA et Confluence")
    
    # Arguments pour les fichiers d'entrée
    parser.add_argument("--jira-files", "-j", nargs="+", required=True, help="Fichiers JSON JIRA à analyser")
    parser.add_argument("--confluence-files", "-c", nargs="*", default=[], help="Fichiers JSON Confluence à analyser")
    
    # Arguments pour les options de traitement
    parser.add_argument("--output-dir", "-o", default="results", help="Répertoire de sortie")
    parser.add_argument("--min-match-score", "-s", type=float, default=0.2, help="Score minimum pour les correspondances")
    parser.add_argument("--max-items", type=int, help="Nombre maximum d'éléments à traiter par fichier")
    
    # Arguments pour les options LLM
    parser.add_argument("--with-openai", action="store_true", default=True, help="Activer l'analyse avec OpenAI")
    parser.add_argument("--no-openai", action="store_false", dest="with_openai", help="Désactiver l'analyse avec OpenAI")
    parser.add_argument("--api-key", help="Clé API OpenAI (optionnel, sinon utilise OPENAI_API_KEY de l'environnement)")
    parser.add_argument("--model", default="gpt-4", help="Modèle OpenAI à utiliser")
    
    # Options additionnelles
    parser.add_argument("--skip-matching", action="store_true", help="Ne pas effectuer le matching entre JIRA et Confluence")
    parser.add_argument("--install-outlines", action="store_true", help="Installer ou mettre à jour Outlines si nécessaire")
    
    args = parser.parse_args()
    
    # Valider les fichiers d'entrée
    jira_files_abs = [resolve_input_path(f) for f in args.jira_files]
    confluence_files_abs = [resolve_input_path(f) for f in args.confluence_files]
    
    print("\n== Vérification des fichiers d'entrée ==")
    for file in jira_files_abs:
        if os.path.exists(file):
            print(f"✅ Fichier JIRA trouvé: {file}")
        else:
            print(f"❌ Fichier JIRA introuvable: {file}")
    
    for file in confluence_files_abs:
        if os.path.exists(file):
            print(f"✅ Fichier Confluence trouvé: {file}")
        else:
            print(f"❌ Fichier Confluence introuvable: {file}")
    
    # Vérifier si Outlines est disponible si demandé
    if args.with_openai or args.install_outlines:
        print("\n== Vérification de l'installation d'Outlines ==")
        outlines_available = check_outlines()
        if not outlines_available and not args.install_outlines:
            print("⚠️ L'enrichissement par LLM ne sera pas disponible.")
    
    # Si une clé API est fournie, la définir dans les variables d'environnement
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
        print(f"✅ Clé API OpenAI définie à partir des arguments")
    
    # Utiliser directement le répertoire fourni sans ajouter de timestamp supplémentaire
    output_dir = args.output_dir
    create_output_dir(output_dir)
    
    # Créer les sous-répertoires
    jira_dir = os.path.join(output_dir, "jira")
    confluence_dir = os.path.join(output_dir, "confluence")
    matches_dir = os.path.join(output_dir, "matches")
    split_jira_dir = os.path.join(output_dir, "split_jira_files")
    split_confluence_dir = os.path.join(output_dir, "split_confluence_files")
    llm_ready_dir = os.path.join(output_dir, "llm_ready")
    
    # Créer tous les sous-répertoires
    for directory in [jira_dir, confluence_dir, matches_dir, split_jira_dir, split_confluence_dir, llm_ready_dir]:
        create_output_dir(directory)
    
    # Créer aussi les sous-répertoires pour les fichiers LLM ready
    llm_jira_dir = os.path.dirname(os.path.join(llm_ready_dir, "llm_ready_jira.json"))
    llm_confluence_dir = os.path.dirname(os.path.join(llm_ready_dir, "llm_ready_confluence.json"))
    create_output_dir(llm_jira_dir)
    create_output_dir(llm_confluence_dir)
    
    # Résoudre les chemins des fichiers d'entrée
    jira_files_abs = [resolve_input_path(f) for f in args.jira_files]
    confluence_files_abs = [resolve_input_path(f) for f in args.confluence_files]
    
    # Journal d'exécution
    log_file = os.path.join(output_dir, "execution_log.txt")
    with open(log_file, 'w') as log:
        log.write(f"Exécution démarrée le {datetime.now().isoformat()}\n")
        log.write(f"Fichiers JIRA à analyser: {', '.join(jira_files_abs)}\n")
        log.write(f"Fichiers Confluence à analyser: {', '.join(confluence_files_abs)}\n")
        log.write(f"Structure des répertoires:\n")
        log.write(f"  - Principal: {output_dir}\n")
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
    
    # Déplacer les fichiers d'arborescence générés au mauvais endroit
    for file in glob.glob(os.path.join("results", "*_structure.txt")):
        basename = os.path.basename(file)
        new_path = os.path.join(jira_dir, basename)
        shutil.move(file, new_path)
        print(f"Déplacé {file} vers {new_path}")
    
    for file in glob.glob(os.path.join("results", "*_arborescence.txt")):
        basename = os.path.basename(file)
        new_path = os.path.join(jira_dir, basename)
        shutil.move(file, new_path)
        print(f"Déplacé {file} vers {new_path}")
    
    # Déplacer le fichier jira_structure.json s'il a été créé au mauvais endroit
    if os.path.exists(os.path.join("results", "jira_structure.json")) and not os.path.exists(jira_structure_output):
        shutil.move(os.path.join("results", "jira_structure.json"), jira_structure_output)
        print(f"Déplacé results/jira_structure.json vers {jira_structure_output}")
    
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
    
    # Initialiser les variables pour les fichiers de matching
    matches_output = None
    updated_jira_output = None
    updated_confluence_output = None
    
    # Passer le matching si demandé
    if args.skip_matching:
        print("\nSkipping de la phase de matching JIRA-Confluence.")
    else:
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
                "--output", jira_transform_output
            ]
            
            # Ajouter les options supplémentaires
            if args.max_items:
                transform_jira_cmd.extend(["--max", str(args.max_items)])
            
            transform_jira_cmd.append("--generate-arborescence")
            
            run_step(
                transform_jira_cmd,
                "Transformation des données JIRA pour LLM"
            )
            
            # Déplacer les fichiers d'arborescence générés au mauvais endroit pour LLM Ready
            for file in glob.glob(os.path.join("results", "llm_ready_arborescence.txt")):
                new_path = os.path.join(llm_ready_dir, os.path.basename(file))
                shutil.move(file, new_path)
                print(f"Déplacé {file} vers {new_path}")
            
            # Déplacer les fichiers d'arborescence des fichiers sources
            for file in glob.glob(os.path.join("results", "*_jira_arborescence.txt")):
                new_path = os.path.join(jira_dir, os.path.basename(file))
                shutil.move(file, new_path)
                print(f"Déplacé {file} vers {new_path}")
            
            # Déplacer le fichier JSON transformé s'il a été créé au mauvais endroit
            if os.path.exists(os.path.join("results", "llm_ready_jira.json")) and not os.path.exists(jira_transform_output):
                shutil.move(os.path.join("results", "llm_ready_jira.json"), jira_transform_output)
                print(f"Déplacé results/llm_ready_jira.json vers {jira_transform_output}")
        else:
            print("\nAucun fichier JIRA valide à transformer.")
    
    #######################################
    # PARTIE 2: TRAITEMENT DES FICHIERS CONFLUENCE
    #######################################
    
    # 2.1 Extraction de la structure basique
    confluence_structure_output = os.path.join(confluence_dir, "confluence_structure.json")
    run_step(
        [sys.executable, os.path.join(SCRIPTS_DIR, "extract_confluence_structure.py")] + confluence_files_abs + [
            "--output", confluence_structure_output
        ],
        "Extraction de la structure de base des fichiers Confluence"
    )
    
    # Déplacer les fichiers d'arborescence générés au mauvais endroit
    for file in glob.glob(os.path.join("results", "*_confluence_structure.txt")):
        basename = os.path.basename(file)
        new_path = os.path.join(confluence_dir, basename)
        shutil.move(file, new_path)
        print(f"Déplacé {file} vers {new_path}")
    
    for file in glob.glob(os.path.join("results", "*_confluence_arborescence.txt")):
        basename = os.path.basename(file)
        new_path = os.path.join(confluence_dir, basename)
        shutil.move(file, new_path)
        print(f"Déplacé {file} vers {new_path}")
    
    # Déplacer le fichier confluence_structure.json s'il a été créé au mauvais endroit
    if os.path.exists(os.path.join("results", "confluence_structure.json")) and not os.path.exists(confluence_structure_output):
        shutil.move(os.path.join("results", "confluence_structure.json"), confluence_structure_output)
        print(f"Déplacé results/confluence_structure.json vers {confluence_structure_output}")
    
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
            "--output", confluence_transform_output
        ]
        
        # Ajouter les options supplémentaires
        if args.max_items:
            transform_confluence_cmd.extend(["--max", str(args.max_items)])
        
        transform_confluence_cmd.append("--generate-arborescence")
        
        run_step(
            transform_confluence_cmd,
            "Transformation des données Confluence pour LLM"
        )
        
        # Déplacer les fichiers d'arborescence générés au mauvais endroit pour LLM Ready
        for file in glob.glob(os.path.join("results", "llm_ready_arborescence.txt")):
            new_path = os.path.join(llm_ready_dir, os.path.basename(file))
            shutil.move(file, new_path)
            print(f"Déplacé {file} vers {new_path}")
        
        # Déplacer les fichiers d'arborescence des fichiers sources
        for file in glob.glob(os.path.join("results", "*_confluence_arborescence.txt")):
            new_path = os.path.join(confluence_dir, os.path.basename(file))
            shutil.move(file, new_path)
            print(f"Déplacé {file} vers {new_path}")
            
        # Déplacer le fichier JSON transformé s'il a été créé au mauvais endroit
        if os.path.exists(os.path.join("results", "llm_ready_confluence.json")) and not os.path.exists(confluence_transform_output):
            shutil.move(os.path.join("results", "llm_ready_confluence.json"), confluence_transform_output)
            print(f"Déplacé results/llm_ready_confluence.json vers {confluence_transform_output}")
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
            
            # Vérifier si on a les fichiers nécessaires
            if os.path.exists(jira_transform_output) and os.path.exists(confluence_transform_output):
                llm_enrichment = run_llm_enrichment(
                    jira_transform_output,
                    confluence_transform_output,
                    llm_ready_dir,
                    api_key,
                    model=args.model
                )
                
                if llm_enrichment:
                    print("✅ Enrichissement LLM effectué avec succès.")
                else:
                    print("⚠️ L'enrichissement LLM a rencontré des problèmes.")
            else:
                print("[ERREUR] Fichiers transformés non trouvés pour l'enrichissement LLM.")
                print(f"Fichier JIRA: {jira_transform_output} (existe: {os.path.exists(jira_transform_output)})")
                print(f"Fichier Confluence: {confluence_transform_output} (existe: {os.path.exists(confluence_transform_output)})")
    else:
        print("\nL'analyse OpenAI n'a pas été activée. Utilisez --with-openai pour l'activer.")
    
    # Fin de l'exécution
    with open(log_file, 'a') as log:
        log.write(f"Exécution terminée le {datetime.now().isoformat()}\n")
    
    # Générer un résumé LLM même si l'enrichissement n'a pas pu être effectué
    if generate_llm_summary is not None:
        try:
            # Générer le résumé pour JIRA
            if os.path.exists(jira_transform_output):
                try:
                    with open(jira_transform_output, 'r', encoding='utf-8') as f:
                        jira_data = json.load(f)
                    
                    jira_summary_file = generate_llm_summary(
                        llm_ready_dir,
                        data=jira_data,
                        filename="jira_llm_enrichment_summary.md"
                    )
                    print(f"✅ Résumé de l'enrichissement LLM pour JIRA généré: {jira_summary_file}")
                except Exception as e:
                    print(f"⚠️ Impossible de générer le résumé LLM pour JIRA: {e}")
            
            # Générer le résumé pour Confluence si disponible
            if os.path.exists(confluence_transform_output):
                try:
                    with open(confluence_transform_output, 'r', encoding='utf-8') as f:
                        confluence_data = json.load(f)
                    
                    confluence_summary_file = generate_llm_summary(
                        llm_ready_dir,
                        data=confluence_data,
                        filename="confluence_llm_enrichment_summary.md"
                    )
                    print(f"✅ Résumé de l'enrichissement LLM pour Confluence généré: {confluence_summary_file}")
                except Exception as e:
                    print(f"⚠️ Impossible de générer le résumé LLM pour Confluence: {e}")
        except Exception as e:
            print(f"⚠️ Erreur lors de la génération des résumés LLM: {e}")
    
    print("\n== Récapitulatif ==")
    print(f"Fichiers JIRA analysés: {', '.join(args.jira_files)}")
    print(f"Fichiers Confluence analysés: {', '.join(args.confluence_files)}")
    print(f"Répertoire de sortie: {output_dir}")
    
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
    global_arborescence = os.path.join(output_dir, "global_arborescence.txt")
    write_tree(output_dir, os.path.basename(global_arborescence))
    print(f"\nArborescence globale du dossier de sortie générée dans {global_arborescence}")
    
    # Générer des arborescences détaillées pour chaque fichier source
    print("\nGénération des arborescences des fichiers source:")
    
    # Arborescences pour les fichiers JIRA
    for file in jira_files_abs:
        if os.path.exists(file):
            file_base_name = os.path.splitext(os.path.basename(file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arborescence_file = f"{file_base_name}_arborescence_{timestamp}.txt"
            write_file_structure(file, output_dir, arborescence_file)
            print(f"- Structure du fichier JIRA '{file}' générée dans {os.path.join(output_dir, arborescence_file)}")
    
    # Arborescences pour les fichiers Confluence
    for file in confluence_files_abs:
        if os.path.exists(file):
            file_base_name = os.path.splitext(os.path.basename(file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arborescence_file = f"{file_base_name}_arborescence_{timestamp}.txt"
            write_file_structure(file, output_dir, arborescence_file)
            print(f"- Structure du fichier Confluence '{file}' générée dans {os.path.join(output_dir, arborescence_file)}")
    
    print("\nTraitement terminé avec succès!")

if __name__ == "__main__":
    main() 