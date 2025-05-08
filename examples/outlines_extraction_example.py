#!/usr/bin/env python3
"""
Exemple d'utilisation d'Outlines pour l'extraction structurée d'informations
à partir de tickets JIRA et pages Confluence.

Ce script démontre comment utiliser la bibliothèque Outlines pour :
1. Extraire des informations précises de tickets JIRA
2. Extraire des résumés et entités de pages Confluence
3. Comparer les résultats avec l'approche standard
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Ajouter le répertoire parent au chemin d'importation
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Importer les modules d'extraction
try:
    from extract.outlines_enhanced_parser import outlines_robust_json_parser
    from extract.outlines_extractor import process_jira_data, process_confluence_data
    from extract.generic_json_processor import GenericJsonProcessor
    OUTLINES_AVAILABLE = True
except ImportError:
    print("⚠️ Module Outlines non disponible. Installation avec: pip install outlines")
    OUTLINES_AVAILABLE = False
    sys.exit(1)

# Chargement des variables d'environnement
load_dotenv()

def get_timestamp():
    """Retourne un timestamp pour les noms de fichiers"""
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

def compare_extraction_methods(file_path, output_dir, file_type=None, model="gpt-4.1"):
    """
    Compare l'extraction d'informations entre Outlines et l'approche standard
    
    Args:
        file_path: Chemin du fichier JSON à traiter
        output_dir: Répertoire de sortie pour les résultats
        file_type: Type de fichier (jira ou confluence)
        model: Modèle LLM à utiliser
    """
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Charger les données
    print(f"🔄 Chargement du fichier: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Le fichier JSON contient des erreurs. Tentative de réparation avec le parser robuste...")
        data = outlines_robust_json_parser(file_path, llm_fallback=True, model=model)
    
    # Déterminer le type de fichier si non spécifié
    if not file_type:
        # Détection basique basée sur les clés
        if isinstance(data, dict) and "issues" in data:
            file_type = "jira"
        elif isinstance(data, list) and len(data) > 0 and "title" in data[0] and "space" in data[0]:
            file_type = "confluence"
        elif isinstance(data, dict) and "items" in data:
            items = data["items"]
            if len(items) > 0:
                if "summary" in items[0] or "issuetype" in items[0]:
                    file_type = "jira"
                elif "title" in items[0] and ("space" in items[0] or "content" in items[0]):
                    file_type = "confluence"
        
        if not file_type:
            print("❌ Impossible de déterminer le type de fichier. Spécifiez-le avec --type.")
            return
    
    # Extraction avec Outlines
    print(f"🧠 Extraction avec Outlines (type: {file_type})...")
    timestamp = get_timestamp()
    outlines_output_file = os.path.join(output_dir, f"{Path(file_path).stem}_outlines_{timestamp}.json")
    
    if file_type == "jira":
        result_outlines = process_jira_data(data, model=model)
    else:  # confluence
        result_outlines = process_confluence_data(data, model=model)
    
    # Sauvegarder le résultat Outlines
    with open(outlines_output_file, 'w', encoding='utf-8') as f:
        json.dump(result_outlines, f, indent=2, ensure_ascii=False)
    
    # Extraction avec l'approche standard
    print("📊 Extraction avec l'approche standard...")
    standard_output_file = os.path.join(output_dir, f"{Path(file_path).stem}_standard_{timestamp}.json")
    
    processor = GenericJsonProcessor(
        detect_fields=True,
        extract_keywords=True,
        llm_enrichment=True,
        llm_model=model
    )
    
    processor.process_file(file_path, standard_output_file)
    
    # Générer un rapport de comparaison
    print("📝 Génération du rapport de comparaison...")
    report_file = os.path.join(output_dir, f"{Path(file_path).stem}_comparison_{timestamp}.md")
    
    with open(outlines_output_file, 'r', encoding='utf-8') as f:
        outlines_result = json.load(f)
    
    with open(standard_output_file, 'r', encoding='utf-8') as f:
        standard_result = json.load(f)
    
    # Analyser et comparer les résultats
    outlines_items = outlines_result.get("items", [])
    standard_items = standard_result.get("items", [])
    
    num_outlines_items = len(outlines_items)
    num_standard_items = len(standard_items)
    
    # Calculer les différences
    # 1. Nombre de champs extraits
    outlines_fields = set()
    for item in outlines_items[:5]:  # Analyser les 5 premiers éléments
        outlines_fields.update(item.keys())
    
    standard_fields = set()
    for item in standard_items[:5]:  # Analyser les 5 premiers éléments
        standard_fields.update(item.keys())
    
    # 2. Compter les entités et mots-clés extraits
    outlines_entities = 0
    outlines_keywords = 0
    for item in outlines_items[:20]:  # Analyser les 20 premiers éléments
        if "entities" in item:
            for entity_type, entities in item["entities"].items():
                outlines_entities += len(entities)
        if "keywords" in item:
            outlines_keywords += len(item["keywords"])
    
    standard_entities = 0
    standard_keywords = 0
    for item in standard_items[:20]:  # Analyser les 20 premiers éléments
        if "entities" in item:
            for entity_type, entities in item["entities"].items():
                standard_entities += len(entities)
        if "keywords" in item:
            standard_keywords += len(item["keywords"])
        elif "analysis" in item and "keywords" in item["analysis"]:
            standard_keywords += len(item["analysis"]["keywords"])
    
    # Générer le rapport markdown
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Rapport de comparaison: Outlines vs. Standard\n\n")
        f.write(f"Fichier source: `{file_path}`  \n")
        f.write(f"Type de fichier: `{file_type}`  \n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
        
        f.write("## Statistiques générales\n\n")
        f.write("| Métrique | Outlines | Standard | Différence |\n")
        f.write("|----------|----------|----------|------------|\n")
        f.write(f"| Nombre d'éléments | {num_outlines_items} | {num_standard_items} | {num_outlines_items - num_standard_items} |\n")
        f.write(f"| Champs extraits | {len(outlines_fields)} | {len(standard_fields)} | {len(outlines_fields) - len(standard_fields)} |\n")
        f.write(f"| Entités extraites | {outlines_entities} | {standard_entities} | {outlines_entities - standard_entities} |\n")
        f.write(f"| Mots-clés extraits | {outlines_keywords} | {standard_keywords} | {outlines_keywords - standard_keywords} |\n\n")
        
        f.write("## Champs uniques à chaque méthode\n\n")
        f.write("### Champs uniquement dans Outlines\n")
        for field in sorted(outlines_fields - standard_fields):
            f.write(f"- `{field}`\n")
        
        f.write("\n### Champs uniquement dans Standard\n")
        for field in sorted(standard_fields - outlines_fields):
            f.write(f"- `{field}`\n")
        
        # Ajouter des exemples comparatifs
        if num_outlines_items > 0 and num_standard_items > 0:
            f.write("\n## Exemple comparatif\n\n")
            f.write("### Premier élément avec Outlines\n")
            f.write("```json\n")
            f.write(json.dumps(outlines_items[0], indent=2, ensure_ascii=False))
            f.write("\n```\n\n")
            
            f.write("### Premier élément avec Standard\n")
            f.write("```json\n")
            f.write(json.dumps(standard_items[0], indent=2, ensure_ascii=False))
            f.write("\n```\n")
    
    print(f"✅ Comparaison terminée!\n")
    print(f"📄 Résultats Outlines: {outlines_output_file}")
    print(f"📄 Résultats Standard: {standard_output_file}")
    print(f"📄 Rapport de comparaison: {report_file}")
    
    return {
        "outlines_output": outlines_output_file,
        "standard_output": standard_output_file,
        "comparison_report": report_file
    }

def main():
    parser = argparse.ArgumentParser(description="Exemple d'extraction structurée avec Outlines")
    parser.add_argument("--file", "-f", required=True, help="Fichier JSON à traiter")
    parser.add_argument("--output", "-o", default="results/outlines_examples", help="Dossier de sortie")
    parser.add_argument("--type", "-t", choices=["jira", "confluence"], help="Type de fichier (jira ou confluence)")
    parser.add_argument("--model", "-m", default="gpt-4.1", help="Modèle LLM à utiliser")
    
    args = parser.parse_args()
    
    # Vérifier que le fichier existe
    if not os.path.exists(args.file):
        print(f"❌ Le fichier {args.file} n'existe pas.")
        sys.exit(1)
    
    # Exécuter la comparaison
    results = compare_extraction_methods(
        file_path=args.file,
        output_dir=args.output,
        file_type=args.type,
        model=args.model
    )
    
    if results:
        print("\n🔍 Principaux avantages d'Outlines:")
        print("1. Extraction plus précise et structurée des entités nommées")
        print("2. Génération de résumés et analyse sémantique avancée")
        print("3. Schémas JSON typés pour une extraction cohérente")
        print("4. Meilleure détection des relations entre éléments")
        print("5. Parsing JSON robuste avec contraintes grammaticales")

if __name__ == "__main__":
    main() 