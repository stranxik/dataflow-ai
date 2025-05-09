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
import time
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generic_json_processor import write_tree, write_file_structure
from llm_summary import generate_llm_summary

SCRIPTS_DIR = os.path.dirname(__file__)

# Ajouter le répertoire parent au chemin de recherche
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Importer le module lang_utils si disponible
try:
    from cli.lang_utils import t, get_current_language
    TRANSLATIONS_LOADED = True
except ImportError:
    # Fallback si le module de traduction n'est pas disponible
    def t(key, category=None, lang=None):
        return key
    def get_current_language():
        return "fr"
    TRANSLATIONS_LOADED = False

# Importer le module de compression si disponible
try:
    from extract.compress_utils import compress_json, compress_results_directory
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False
    print("⚠️ Module de compression non disponible. Installez les packages requis:")
    print("   pip install zstandard orjson")

def combine_json_files(input_files, output_file):
    """
    Combine plusieurs fichiers JSON en un seul.
    
    Args:
        input_files (list): Liste des chemins des fichiers JSON à combiner
        output_file (str): Chemin du fichier de sortie combiné
    
    Returns:
        bool: True si la combinaison a réussi, False sinon
    """
    try:
        combined_data = {"items": []}
        
        # Extraire les métadonnées du premier fichier
        if input_files and os.path.exists(input_files[0]):
            with open(input_files[0], 'r', encoding='utf-8') as f:
                first_file = json.load(f)
                if "metadata" in first_file:
                    combined_data["metadata"] = first_file["metadata"].copy()
                    # Mettre à jour les métadonnées
                    combined_data["metadata"]["source_files"] = []
                    combined_data["metadata"]["processed_at"] = datetime.now().isoformat()
                    combined_data["metadata"]["combined"] = True
        
        # Parcourir tous les fichiers et combiner leurs items
        for file_path in input_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # Ajouter le fichier source aux métadonnées
                        if "metadata" in combined_data:
                            combined_data["metadata"]["source_files"].append(os.path.basename(file_path))
                        
                        # Ajouter les items
                        if "items" in data and isinstance(data["items"], list):
                            combined_data["items"].extend(data["items"])
                except Exception as e:
                    print(f"⚠️ Erreur lors de la lecture du fichier {file_path}: {e}")
        
        # Ajouter des statistiques aux métadonnées
        if "metadata" in combined_data:
            combined_data["metadata"]["stats"] = {
                "total_items": len(combined_data["items"]),
                "combined_files": len(input_files)
            }
        
        # Écrire le fichier combiné
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Combinaison réussie: {len(combined_data['items'])} éléments de {len(input_files)} fichiers")
        return True
    
    except Exception as e:
        print(f"❌ Erreur lors de la combinaison des fichiers: {e}")
        traceback.print_exc()
        return False

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
    
    # Arguments relatifs aux fichiers
    parser.add_argument('--jira-files', nargs='+', required=True, help='Chemins des fichiers JIRA à analyser')
    parser.add_argument('--confluence-files', nargs='+', default=[], help='Chemins des fichiers Confluence à analyser')
    parser.add_argument('--output-dir', default='output', help='Répertoire de sortie')
    
    # Arguments relatifs au matching
    parser.add_argument('--min-match-score', type=float, default=0.5, help='Score minimum pour les correspondances entre JIRA et Confluence')
    parser.add_argument('--skip-matching', action='store_true', help='Ne pas effectuer le matching entre JIRA et Confluence')
    
    # Arguments relatifs au traitement
    parser.add_argument('--api-key', help='Clé API OpenAI')
    parser.add_argument('--with-openai', action='store_true', default=True, help='Utiliser OpenAI pour enrichir les données')
    parser.add_argument('--no-openai', action='store_true', help='Ne pas utiliser OpenAI')
    parser.add_argument('--max-items', type=int, help='Nombre maximum d\'éléments à traiter par fichier')
    parser.add_argument('--language', help='Langue à utiliser (fr/en)')
    
    # Arguments relatifs à la compression
    if COMPRESSION_AVAILABLE:
        parser.add_argument('--compress', action='store_true', help='Compresser les fichiers de sortie avec zstd et orjson')
        parser.add_argument('--compress-level', type=int, default=19, help='Niveau de compression zstd (1-22)')
        parser.add_argument('--keep-originals', action='store_true', default=True, help='Conserver les fichiers JSON originaux en plus des compressés')
    
    args = parser.parse_args()
    
    # Configuration de la langue
    if args.language and TRANSLATIONS_LOADED:
        from cli.lang_utils import set_language
        set_language(args.language)
        print(f"🌐 Langue configurée: {args.language}")
    
    # Résolution des chemins des fichiers d'entrée
    jira_files = [resolve_input_path(f) for f in args.jira_files]
    confluence_files = [resolve_input_path(f) for f in args.confluence_files] if args.confluence_files else []
    
    # Création du répertoire de sortie
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    
    # Configuration de l'API OpenAI
    use_openai = args.with_openai and not args.no_openai
    api_key = args.api_key
    if use_openai and not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    if use_openai and api_key:
        check_outlines()
    
    # Création des répertoires
    jira_dir = os.path.join(output_dir, "jira")
    jira_structure_file = os.path.join(output_dir, "jira_structure.json")
    jira_arbo_file = os.path.join(output_dir, "jira_arborescence.txt")
    
    confluence_dir = os.path.join(output_dir, "confluence")
    confluence_structure_file = os.path.join(output_dir, "confluence_structure.json")
    confluence_arbo_file = os.path.join(output_dir, "confluence_arborescence.txt")
    
    matches_dir = os.path.join(output_dir, "matches")
    
    jira_splits_dir = os.path.join(output_dir, "split_jira_files")
    confluence_splits_dir = os.path.join(output_dir, "split_confluence_files")
    
    llm_dir = os.path.join(output_dir, "llm_ready")
    
    for d in [jira_dir, confluence_dir, matches_dir, jira_splits_dir, confluence_splits_dir, llm_dir]:
        os.makedirs(d, exist_ok=True)
    
    # Traitement des fichiers JIRA
    jira_processed_files = []
    for jira_file in jira_files:
        try:
            jira_output = os.path.join(jira_dir, f"{os.path.splitext(os.path.basename(jira_file))[0]}_processed.json")
            
            # 1. Extraire la structure
            run_step([
                sys.executable, os.path.join(SCRIPTS_DIR, "extract_jira_structure.py"),
                jira_file,
                "--output", jira_structure_file
            ], "Extraction de la structure JIRA")
            
            # 2. Découper le fichier si nécessaire
            jira_to_process = jira_file
            if args.max_items:
                print(f"\n== Découpage du fichier JIRA ({args.max_items} éléments par fichier) ==")
                run_step([
                    sys.executable, os.path.join(SCRIPTS_DIR, "process_by_chunks.py"),
                    "split",
                    "--input", jira_file,
                    "--output-dir", jira_splits_dir,
                    "--items-per-file", str(args.max_items)
                ], "Découpage du fichier JIRA en morceaux")
                
                # Utiliser le premier fichier découpé
                split_files = glob.glob(os.path.join(jira_splits_dir, "*.json"))
                if split_files:
                    jira_to_process = split_files[0]
                    print(f"Utilisation du fichier découpé: {jira_to_process}")
            
            # 3. Transformer les données
            cmd = [
                sys.executable, os.path.join(SCRIPTS_DIR, "transform_for_llm.py"),
                "--input", jira_to_process,
                "--output", jira_output
            ]
            
            run_step(cmd, "Transformation des données JIRA")
            
            # 4. Générer une arborescence du fichier
            file_structure = write_file_structure(jira_output, jira_arbo_file, max_items=10, max_depth=4)
            
            jira_processed_files.append(jira_output)
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement du fichier JIRA {jira_file}: {e}")
            traceback.print_exc()
    
    # Traitement des fichiers Confluence
    confluence_processed_files = []
    for confluence_file in confluence_files:
        try:
            confluence_output = os.path.join(confluence_dir, f"{os.path.splitext(os.path.basename(confluence_file))[0]}_processed.json")
            
            # 1. Extraire la structure
            run_step([
                sys.executable, os.path.join(SCRIPTS_DIR, "extract_confluence_structure.py"),
                confluence_file,
                "--output", confluence_structure_file
            ], "Extraction de la structure Confluence")
            
            # 2. Découper le fichier si nécessaire
            confluence_to_process = confluence_file
            if args.max_items:
                print(f"\n== Découpage du fichier Confluence ({args.max_items} éléments par fichier) ==")
                run_step([
                    sys.executable, os.path.join(SCRIPTS_DIR, "process_by_chunks.py"),
                    "split",
                    "--input", confluence_file,
                    "--output-dir", confluence_splits_dir,
                    "--items-per-file", str(args.max_items)
                ], "Découpage du fichier Confluence en morceaux")
                
                # Utiliser le premier fichier découpé
                split_files = glob.glob(os.path.join(confluence_splits_dir, "*.json"))
                if split_files:
                    confluence_to_process = split_files[0]
                    print(f"Utilisation du fichier découpé: {confluence_to_process}")
            
            # 3. Transformer les données
            cmd = [
                sys.executable, os.path.join(SCRIPTS_DIR, "transform_for_llm.py"),
                "--input", confluence_to_process,
                "--output", confluence_output,
                "--type", "confluence"
            ]
            
            run_step(cmd, "Transformation des données Confluence")
            
            # 4. Générer une arborescence du fichier
            file_structure = write_file_structure(confluence_output, confluence_arbo_file, max_items=10, max_depth=4)
            
            confluence_processed_files.append(confluence_output)
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement du fichier Confluence {confluence_file}: {e}")
            traceback.print_exc()
    
    # Matching JIRA et Confluence
    if jira_processed_files and confluence_processed_files and not args.skip_matching:
        print("\n== Matching JIRA et Confluence ==")
        for jira_file in jira_processed_files:
            for confluence_file in confluence_processed_files:
                jira_base = os.path.splitext(os.path.basename(jira_file))[0]
                confluence_base = os.path.splitext(os.path.basename(confluence_file))[0]
                matches_output = os.path.join(matches_dir, f"{jira_base}_{confluence_base}_matches.json")
                
                cmd = [
                    sys.executable, os.path.join(SCRIPTS_DIR, "match_jira_confluence.py"),
                    "--jira", jira_file,
                    "--confluence", confluence_file,
                    "--output", matches_output,
                    "--updated-jira", jira_file,
                    "--updated-confluence", confluence_file,
                    "--min-score", str(args.min_match_score)
                ]
                
                run_step(cmd, f"Matching {jira_base} avec {confluence_base}")
    
    # Préparation pour LLM
    if jira_processed_files or confluence_processed_files:
        print("\n== Préparation des données pour LLM ==")
        
        # Créer les fichiers combinés pour LLM
        jira_llm_file = os.path.join(llm_dir, "enriched_jira.json")
        confluence_llm_file = os.path.join(llm_dir, "enriched_confluence.json")
        
        # Combiner tous les fichiers JIRA
        if jira_processed_files:
            combine_json_files(jira_processed_files, jira_llm_file)
            print(f"✅ Fichier JIRA combiné pour LLM: {jira_llm_file}")
        
        # Combiner tous les fichiers Confluence
        if confluence_processed_files:
            combine_json_files(confluence_processed_files, confluence_llm_file)
            print(f"✅ Fichier Confluence combiné pour LLM: {confluence_llm_file}")
        
        # Enrichissement LLM si demandé
        if use_openai and api_key:
            print("\n== Enrichissement des données avec LLM ==")
            
            # Importer le modèle d'enrichissement
            import sys
            sys.path.append(SCRIPTS_DIR)
            from outlines_enricher import enrich_data_file
            
            if os.path.exists(jira_llm_file):
                try:
                    print(f"🔄 Enrichissement JIRA...")
                    jira_enriched = enrich_data_file(jira_llm_file, jira_llm_file)
                    if jira_enriched:
                        print(f"✅ Enrichissement JIRA réussi")
                    else:
                        print(f"⚠️ Enrichissement JIRA incomplet")
                except Exception as e:
                    print(f"❌ Erreur lors de l'enrichissement JIRA: {e}")
                    traceback.print_exc()
            
            if os.path.exists(confluence_llm_file):
                try:
                    print(f"🔄 Enrichissement Confluence...")
                    confluence_enriched = enrich_data_file(confluence_llm_file, confluence_llm_file)
                    if confluence_enriched:
                        print(f"✅ Enrichissement Confluence réussi")
                    else:
                        print(f"⚠️ Enrichissement Confluence incomplet")
                except Exception as e:
                    print(f"❌ Erreur lors de l'enrichissement Confluence: {e}")
                    traceback.print_exc()
        
        # Générer les résumés LLM
        if generate_llm_summary:
            try:
                # Récupérer la langue si disponible
                current_language = None
                if TRANSLATIONS_LOADED:
                    current_language = get_current_language()
                    print(f"🌐 Génération des résumés LLM en langue: {current_language}")
                
                # Générer des résumés pour JIRA et Confluence
                if os.path.exists(jira_llm_file):
                    with open(jira_llm_file, 'r', encoding='utf-8') as f:
                        jira_data = json.load(f)
                    
                    jira_summary_file = generate_llm_summary(
                        output_dir=llm_dir,
                        jira_data=jira_data,
                        filename="jira_llm_enrichment_summary.md",
                        language=current_language
                    )
                    print(f"📝 Résumé JIRA généré: {jira_summary_file}")
                
                if os.path.exists(confluence_llm_file):
                    with open(confluence_llm_file, 'r', encoding='utf-8') as f:
                        confluence_data = json.load(f)
                    
                    confluence_summary_file = generate_llm_summary(
                        output_dir=llm_dir,
                        confluence_data=confluence_data,
                        filename="confluence_llm_enrichment_summary.md",
                        language=current_language
                    )
                    print(f"📝 Résumé Confluence généré: {confluence_summary_file}")
            except Exception as e:
                print(f"⚠️ Erreur lors de la génération des résumés LLM: {e}")
                traceback.print_exc()
    
    # Compression des fichiers si demandée
    if COMPRESSION_AVAILABLE and hasattr(args, 'compress') and args.compress:
        print(f"\n🗜️ {t('compressing_files', 'compression')} {output_dir}...")
        try:
            count, compression_report = compress_results_directory(
                output_dir, 
                compression_level=args.compress_level,
                keep_originals=args.keep_originals,
                generate_report=True
            )
            current_lang = get_current_language()
            report_path = os.path.join(output_dir, f"compression_report_{current_lang}.txt")
            print(f"✅ {count} {t('files_compressed_success', 'compression')}")
            print(f"   {t('report_available', 'compression')}: {report_path}")
        except Exception as e:
            print(f"⚠️ Erreur lors de la compression: {e}")
            traceback.print_exc()
    
    print(f"\n✨ Analyse unifiée terminée avec succès!")
    print(f"📁 Tous les résultats sont dans: {output_dir}")
    if jira_processed_files:
        print(f"📄 Fichiers JIRA traités: {', '.join(os.path.basename(f) for f in jira_processed_files)}")
    if confluence_processed_files:
        print(f"📄 Fichiers Confluence traités: {', '.join(os.path.basename(f) for f in confluence_processed_files)}")
    if COMPRESSION_AVAILABLE and hasattr(args, 'compress') and args.compress:
        print(f"🗜️ Fichiers compressés avec zstd et orjson pour optimiser le stockage")

if __name__ == "__main__":
    main() 