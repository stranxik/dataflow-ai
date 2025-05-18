"""
PDF processing routes for DataFlow AI API.
These endpoints handle PDF file uploads and processing using the existing CLI.
"""
import os
import uuid
import shutil
import zipfile
import logging
import sys
import time
import json
from pathlib import Path
from typing import List, Optional
import threading
import openai
import requests

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Form, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from api.services.subprocess_service import run_cli_command
from api.services.temp_file_service import create_temp_file, cleanup_files

# Configure logging
logger = logging.getLogger("pdf_routes")

router = APIRouter()

# Ce endpoint ne nécessite PAS d'API key - c'est un endpoint de test public
@router.get("/test-no-auth", summary="Test endpoint (no auth)", include_in_schema=True, tags=["Testing"])
async def test_endpoint_public():
    """
    Simple test endpoint to verify API is working correctly.
    This endpoint does not require authentication.
    """
    logger.info("Test endpoint called")
    
    # Print environment information for debugging
    cwd = os.getcwd()
    python_path = sys.executable
    dirs = {
        "cwd": cwd,
        "files": os.path.join(cwd, "files"),
        "results": os.path.join(cwd, "results"),
        "cli": os.path.join(cwd, "cli")
    }
    
    # Check existence of critical directories
    exists = {dir_name: os.path.exists(path) for dir_name, path in dirs.items()}
    
    # Check for OpenAI API key
    api_key_exists = "OPENAI_API_KEY" in os.environ
    
    # Check for commands
    cmd_check = {
        "python": shutil.which("python"),
        "zip": shutil.which("zip"),
        "unzip": shutil.which("unzip")
    }
    
    return {
        "status": "API is working",
        "environment": {
            "python_executable": python_path,
            "directories": dirs,
            "directories_exist": exists,
            "api_key_exists": api_key_exists,
            "commands": cmd_check
        }
    }

@router.get("/test", summary="Test endpoint")
async def test_endpoint():
    """
    Simple test endpoint to verify API is working correctly.
    """
    logger.info("Test endpoint called")
    
    # Print environment information for debugging
    cwd = os.getcwd()
    python_path = sys.executable
    dirs = {
        "cwd": cwd,
        "files": os.path.join(cwd, "files"),
        "results": os.path.join(cwd, "results"),
        "cli": os.path.join(cwd, "cli")
    }
    
    # Check existence of critical directories
    exists = {dir_name: os.path.exists(path) for dir_name, path in dirs.items()}
    
    # Check for OpenAI API key
    api_key_exists = "OPENAI_API_KEY" in os.environ
    
    # Check for commands
    cmd_check = {
        "python": shutil.which("python"),
        "zip": shutil.which("zip"),
        "unzip": shutil.which("unzip")
    }
    
    return {
        "status": "API is working",
        "environment": {
            "python_executable": python_path,
            "directories": dirs,
            "directories_exist": exists,
            "api_key_exists": api_key_exists,
            "commands": cmd_check
        }
    }

# --- Traduction dynamique via translations.json ---
import json as _json
TRANSLATIONS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cli', 'translations.json')
_translations_cache = None
_translations_lock = threading.Lock()
def get_translations(lang='fr'):
    global _translations_cache
    with _translations_lock:
        if _translations_cache is None:
            with open(TRANSLATIONS_PATH, 'r', encoding='utf-8') as f:
                _translations_cache = _json.load(f)
    return _translations_cache.get(lang, _translations_cache.get('fr', {}))
def tr(label, lang='fr', default=None):
    """Accès simplifié aux labels traduits. label = chemin par points (ex: 'llm_summary.llm_summary_title')"""
    d = get_translations(lang)
    for part in label.split('.'):
        if isinstance(d, dict) and part in d:
            d = d[part]
        else:
            return default or label
    return d

# --- Fonction utilitaire pour rendre un JSON en Markdown agnostique ---
def render_json_to_markdown(data, indent=0):
    lines = []
    prefix = "  " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}- {k} :")
                lines.extend(render_json_to_markdown(v, indent+1))
            else:
                lines.append(f"{prefix}- {k} : {v}")
    elif isinstance(data, list):
        for i, v in enumerate(data):
            lines.append(f"{prefix}- [{i}]")
            lines.extend(render_json_to_markdown(v, indent+1))
    else:
        lines.append(f"{prefix}{data}")
    return lines

@router.post("/extract-images", summary="Extract and analyze images from PDF")
async def extract_images_from_pdf(
    file: UploadFile = File(...),
    max_images: Optional[int] = Form(int(os.environ.get("DEFAULT_IMAGES_ANALYSIS", 10)), description="Maximum number of images to extract and analyze"),
    format: Optional[str] = Form("json", description="Output format: 'json' for single JSON file or 'zip' for complete folder, or 'rasterize' for page rasterization"),
    dpi: Optional[int] = Form(300, description="DPI for rasterization (if rasterize mode)"),
    pages: Optional[str] = Form(None, description="Pages to rasterize (if rasterize mode, ex: 1,3,5-7)"),
    language: Optional[str] = Form(None, description="Language for the report and AI analysis ('fr' or 'en')"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Extract text and analyze images from a PDF file using OpenAI Vision.
    
    - **file**: PDF file to process
    - **max_images**: Maximum number of images to extract and analyze
    - **format**: Output format: 'json' or 'zip' or 'rasterize'
    """
    logger.info(f"Receiving PDF extraction request - File: {file.filename}, Size: {file.size}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Requested format: {format}")
    
    # Generate a unique ID for this job
    job_id = str(uuid.uuid4())
    logger.info(f"Generated job ID: {job_id}")
    
    # Determine the base path for files
    base_path = os.environ.get("BASE_PATH", os.getcwd())
    logger.info(f"Base path: {base_path}")
    
    # Create temp directory for input file
    temp_dir = os.path.join(base_path, "files", f"temp_{job_id}")
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"Created temp directory: {temp_dir}")
    
    # Create output directory for results
    output_dir = os.path.join(base_path, "results", f"pdf_extraction_{job_id}")
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    
    # Save the uploaded PDF file
    input_file_path = os.path.join(temp_dir, "input.pdf")
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    logger.info(f"File saved to {input_file_path}, size: {os.path.getsize(input_file_path)} bytes")
    
    # Process the PDF
    try:
        logger.info(f"Processing PDF: {file.filename}, job_id: {job_id}, format: {format}")
        logger.info(f"Using max_images: {max_images}")
        
        # Check if OpenAI API key is available
        if "OPENAI_API_KEY" in os.environ:
            logger.info("OPENAI_API_KEY found in environment variables")
        else:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        
        # Check if output directory has proper permissions
        logger.info(f"Checking permissions for {output_dir}")
        
        # Get python executable
        python_executable = sys.executable
        logger.info(f"Using Python executable: {python_executable}")
        
        # Priorité : paramètre explicite > .language > fr
        lang = language
        if not lang:
            language_file = os.path.join(base_path, ".language")
            if os.path.exists(language_file):
                try:
                    with open(language_file, "r") as f:
                        lang_file = f.read().strip()
                        if lang_file in ["fr", "en"]:
                            lang = lang_file
                except Exception as e:
                    logger.error(f"Error reading .language file: {e}")
        if lang not in ["fr", "en"]:
            lang = "fr"
        logger.info(f"Language for extraction/report: {lang}")
        
        # Use extract/pdf_complete_extractor.py first in any case for text and embedded images
        extract_script = os.path.join(base_path, "extract", "pdf_complete_extractor.py")
        
        if not os.path.exists(extract_script):
            logger.error(f"Extract script not found at {extract_script}")
            raise HTTPException(status_code=500, detail=f"Extract script not found at {extract_script}")
                
        cmd = [
            python_executable,
            extract_script,
            input_file_path,
            "--output", output_dir,
            "--max-images", str(max_images),
            "--language", lang
        ]
        
        logger.info(f"Running extract command: {' '.join(cmd)}")
        
        # Execute the command
        result = await run_cli_command(cmd, timeout=300)
        
        if result["return_code"] != 0:
            logger.error(f"Extract command failed: {result}")
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {result['stderr']}")
        
        logger.info(f"Extract command completed successfully")
        
        # Additional rasterization if requested
        if format and format.lower() == "rasterize":
            # Also run the rasterizer to get full page images analyzed
            logger.info(f"Entering rasterize mode. Parameters: dpi={dpi}, pages={pages}")
            
            # Utiliser le script pdf_rasterizer.py
            rasterizer_script = os.path.join(base_path, "extract", "pdf_rasterizer.py")
            
            if not os.path.exists(rasterizer_script):
                logger.error(f"Rasterizer script not found at {rasterizer_script}")
                raise HTTPException(status_code=500, detail=f"Rasterizer script not found at {rasterizer_script}")
            
            cmd = [python_executable, rasterizer_script, input_file_path, "--output", output_dir, "--dpi", str(dpi)]
            if pages:
                cmd += ["--pages", pages]
            
            logger.info(f"Running rasterizer command: {' '.join(cmd)}")
            result = await run_cli_command(cmd, timeout=600)
            
            if result["return_code"] != 0:
                logger.error(f"Rasterization command failed: {result}")
                raise HTTPException(status_code=500, detail=f"PDF rasterization failed: {result['stderr']}")
            
            logger.info(f"Rasterization command completed successfully")
            
            # Après les deux traitements (classique et raster), tenter de générer le fichier combiné
            try:
                # Initialisation sécurisée de combined_json pour éviter UnboundLocalError
                combined_json = {
                    "file": file.filename,
                    "date": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "classic": None,
                    "raster": None,
                    "summary": {},
                }
                # Chercher les fichiers nécessaires
                standard_json_files = list(Path(output_dir).glob("classic/*_unified.json"))
                raster_json = Path(output_dir) / "raster" / "rasterized_images_analysis.json"
                standard_reports = list(Path(output_dir).glob("classic/*_report.md"))
                raster_report = Path(output_dir) / "raster" / "rasterized_report.md"
                if not standard_json_files:
                    logger.warning(f"Fichier JSON classique manquant dans {output_dir}/classic")
                if not raster_json.exists():
                    logger.warning(f"Fichier JSON rasterisé manquant dans {output_dir}/raster")
                if not standard_reports:
                    logger.warning(f"Rapport Markdown classique manquant dans {output_dir}/classic")
                if not raster_report.exists():
                    logger.warning(f"Rapport Markdown rasterisé manquant dans {output_dir}/raster")
                if standard_json_files and raster_json.exists() and standard_reports and raster_report.exists():
                    # Générer le résumé IA naturel à partir du JSON structuré du raster
                    ia_summary_natural_language = None
                    cotes_principales = None
                    cotes_comment = ""
                    ia_structured = None
                    try:
                        with open(raster_json, "r", encoding="utf-8") as f:
                            raster_data = json.load(f)
                        if raster_data and isinstance(raster_data, list) and len(raster_data) > 0:
                            desc = raster_data[0].get("description_ai")
                            if desc and desc.strip().startswith('{') and desc.strip().endswith('}'):
                                try:
                                    desc_json = json.loads(desc)
                                    ia_structured = desc_json
                                    # Générer un résumé naturel robuste
                                    type_doc = desc_json.get("type")
                                    surface = desc_json.get("data", {}).get("surface_habitable", {})
                                    # Recherche robuste des pièces
                                    pieces = desc_json.get("data", {}).get("pièces")
                                    if not pieces:
                                        pieces = desc_json.get("data", {}).get("zones_fonctionnelles")
                                    if not pieces:
                                        niveaux = desc_json.get("data", {}).get("niveaux")
                                        if niveaux and isinstance(niveaux, list) and len(niveaux) > 0:
                                            pieces = niveaux[0].get("pièces")
                                    if not pieces:
                                        pieces = []
                                    echelle = desc_json.get("data", {}).get("échelle")
                                    dimensions = desc_json.get("data", {}).get("dimensions_extérieures") or desc_json.get("data", {}).get("dimensions_extérieures_principales")
                                    cotes = desc_json.get("data", {}).get("cotes_principales") or desc_json.get("data", {}).get("références_cadastrales")
                                    # Gérer plusieurs niveaux
                                    niveaux = desc_json.get("data", {}).get("niveaux")
                                    resume = []
                                    if type_doc:
                                        resume.append(f"Type de document : {type_doc}.")
                                    if surface:
                                        resume.append(f"Surface habitable : {surface.get('value')} {surface.get('unit')}.")
                                    if pieces and isinstance(pieces, list):
                                        resume.append(f"Nombre de pièces : {len(pieces)} (" + ", ".join([p.get('nom') for p in pieces if 'nom' in p]) + ").")
                                    if niveaux and isinstance(niveaux, list):
                                        for niveau in niveaux:
                                            if niveau.get("niveau"):
                                                resume.append(f"Niveau : {niveau['niveau']}")
                                            if niveau.get("pièces") and isinstance(niveau["pièces"], list):
                                                resume.append(f"  Pièces ({len(niveau['pièces'])}) : " + ", ".join([p.get('nom') for p in niveau['pièces'] if 'nom' in p]))
                                    if echelle:
                                        resume.append(f"Échelle : {echelle.get('value')}:{echelle.get('unit')}.")
                                    if dimensions:
                                        dims = []
                                        for k, v in dimensions.items():
                                            dims.append(f"{k} : {v.get('value')} {v.get('unit')}")
                                        resume.append("Dimensions extérieures : " + ", ".join(dims) + ".")
                                    if cotes:
                                        cotes_principales = cotes
                                        cotes_comment = "Côtes principales détectées, non associées à une pièce précise."
                                        resume.append(f"Côtes principales détectées : {', '.join(str(x) for x in cotes)}.")
                                    ia_summary_natural_language = " ".join(resume)
                                except Exception as e:
                                    ia_summary_natural_language = None
                    except Exception as e:
                        ia_summary_natural_language = None
                    # Générer le rapport Markdown combiné
                    combined_report_path = Path(output_dir) / "combined_analysis_report.md"
                    summary_lines = []
                    try:
                        with open(standard_json_files[0], "r", encoding="utf-8") as f:
                            classic_data = json.load(f)
                        with open(raster_json, "r", encoding="utf-8") as f:
                            raster_data = json.load(f)
                        # Remplir explicitement les champs classic et raster dans le JSON combiné
                        combined_json["classic"] = classic_data
                        combined_json["raster"] = raster_data
                        # Correction du parsing IA
                        # 1. Analyse classique (images intégrées)
                        classic_ia = None
                        for page in classic_data.get("pages", []):
                            for el in page.get("elements", []):
                                desc = el.get("description_ai")
                                if desc and desc.strip().startswith('{') and desc.strip().endswith('}'):
                                    try:
                                        classic_ia = json.loads(desc)
                                        break
                                    except Exception:
                                        continue
                            if classic_ia:
                                break
                        # 2. Analyse rasterisée
                        raster_ia = None
                        if raster_data and isinstance(raster_data, list) and len(raster_data) > 0:
                            desc = raster_data[0].get("description_ai")
                            if desc:
                                # Nettoyer le code block éventuel
                                desc_clean = desc.strip()
                                if desc_clean.startswith('```json'):
                                    desc_clean = desc_clean[len('```json'):].strip()
                                if desc_clean.startswith('```'):
                                    desc_clean = desc_clean[len('```'):].strip()
                                if desc_clean.endswith('```'):
                                    desc_clean = desc_clean[:-3].strip()
                                try:
                                    raster_ia = json.loads(desc_clean)
                                except Exception:
                                    raster_ia = None
                        nb_pages = len(classic_data.get("pages", []))
                        nb_images = classic_data.get("stats", {}).get("images_detected", 0) or classic_data.get("nb_images_detectees", 0)
                        nb_raster_pages = len(raster_data)
                        summary_lines.append(f"# Rapport d'analyse complet du PDF\n")
                        summary_lines.append(f"Fichier: {file.filename}")
                        summary_lines.append(f"Date d'analyse: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        summary_lines.append(f"Ce document contient {nb_pages} page(s), {nb_images} image(s) intégrée(s), {nb_raster_pages} page(s) rasterisée(s) (images rasterisées générées : {nb_raster_pages}).\n")
                        # Résumé IA naturel
                        if ia_summary_natural_language:
                            summary_lines.append("## Résumé IA en langage naturel\n")
                            summary_lines.append(ia_summary_natural_language + "\n")
                        # Détail structuré IA (Markdown lisible, agnostique)
                        if isinstance(ia_structured, dict):
                            summary_lines.append("## Détail structuré de l'analyse IA (agnostique)\n")
                            summary_lines.extend(render_json_to_markdown(ia_structured))
                            data = ia_structured.get("data")
                            if isinstance(data, dict):
                                # Type, domaine, complexité
                                surface = data.get("surface_habitable")
                                if isinstance(surface, dict):
                                    summary_lines.append(f"- Surface habitable : {surface.get('value')} {surface.get('unit')}")
                                # Échelle
                                echelle = data.get("échelle")
                                if isinstance(echelle, dict):
                                    summary_lines.append(f"- Échelle : {echelle.get('value')}:{echelle.get('unit')}")
                                # Dimensions
                                dimensions = data.get("dimensions_extérieures") or data.get("dimensions_extérieures_principales")
                                if isinstance(dimensions, dict):
                                    dims = []
                                    for k, v in dimensions.items():
                                        if isinstance(v, dict):
                                            dims.append(f"{k} : {v.get('value')} {v.get('unit')}")
                                    summary_lines.append("- Dimensions extérieures : " + ", ".join(dims))
                                # Niveaux et pièces
                                niveaux = data.get("niveaux")
                                if isinstance(niveaux, list):
                                    for niveau in niveaux:
                                        summary_lines.append(f"- Niveau : {niveau.get('niveau','')}")
                                        if isinstance(niveau.get("pièces"), list):
                                            for p in niveau["pièces"]:
                                                if isinstance(p, dict):
                                                    summary_lines.append(f"    - {p.get('nom','')} : {p.get('surface',{}).get('value','')} {p.get('surface',{}).get('unit','')}")
                                else:
                                    # fallback pièces
                                    pieces = data.get("pièces")
                                    if not pieces:
                                        pieces = data.get("zones_fonctionnelles")
                                    if isinstance(pieces, list):
                                        for p in pieces:
                                            if isinstance(p, dict):
                                                summary_lines.append(f"- {p.get('nom','')} : {p.get('surface',{}).get('value','')} {p.get('surface',{}).get('unit','')}")
                                # Côtes principales
                                cotes = data.get("cotes_principales") or data.get("références_cadastrales")
                                if cotes:
                                    summary_lines.append(f"- Côtes principales : {', '.join(str(x) for x in cotes)}")
                            # Post-analyse structurante
                            post_analysis = ia_structured.get("post_analysis")
                            if post_analysis:
                                summary_lines.append("- Post-analyse structurante :")
                                if isinstance(post_analysis, str):
                                    summary_lines.append(f"    {post_analysis}")
                                else:
                                    summary_lines.append(f"    {json.dumps(post_analysis, ensure_ascii=False, indent=2)}")
                            # Insights
                            insights = ia_structured.get("insights")
                            if insights:
                                summary_lines.append(f"- Insights : {insights}")
                            # Erreurs
                            errors = ia_structured.get("errors")
                            if errors:
                                summary_lines.append(f"- Erreurs détectées : {errors}")
                        else:
                            summary_lines.append("[Aucune donnée structurée IA disponible pour ce document.]")
                    except Exception as e:
                        summary_lines.append(f"[Erreur lors de la génération du résumé global: {e}]\n")
                    summary_lines.append("## 1. Analyse du contenu textuel et images intégrées\n\n")
                    with open(standard_reports[0], "r", encoding="utf-8") as f:
                        content = f.read()
                        lines = content.split("\n")
                        skip_lines = 0
                        for i, line in enumerate(lines):
                            if line.startswith("## "):
                                skip_lines = i
                                break
                        summary_lines.append("\n".join(lines[skip_lines:]))
                        summary_lines.append("\n\n")
                    summary_lines.append("## 2. Analyse des pages rasterisées\n\n")
                    with open(raster_report, "r", encoding="utf-8") as f:
                        content = f.read()
                        lines = content.split("\n")
                        skip_lines = 0
                        for i, line in enumerate(lines):
                            if line.startswith("## "):
                                skip_lines = i
                                break
                        summary_lines.append("\n".join(lines[skip_lines:]))
                    if cotes_principales:
                        summary_lines.append(f"\nCôtes principales détectées : {', '.join(str(x) for x in cotes_principales)}.")
                        summary_lines.append(f"\n{cotes_comment}\n")
                    # --- Comparaison détaillée des analyses IA (dynamique et agnostique) ---
                    def extract_facts_dynamic(ia):
                        if not ia or "data" not in ia:
                            return {}
                        return ia["data"]
                    facts_classic = extract_facts_dynamic(classic_ia)
                    facts_raster = extract_facts_dynamic(raster_ia)
                    all_keys = set(facts_classic.keys()) | set(facts_raster.keys())
                    diffs = []
                    alerts = []
                    score = 0
                    total = len(all_keys)
                    comparison_md = [f"## {tr('llm_summary.ia_comparison_title', lang)}\n"]
                    comparison_json = {}
                    for key in sorted(all_keys):
                        v1 = facts_classic.get(key)
                        v2 = facts_raster.get(key)
                        comparison_json[key] = {"classique": v1, "raster": v2}
                        if v1 == v2:
                            score += 1
                            diffs.append(f"- {key} : identique ({v1})")
                        elif v1 is None:
                            diffs.append(f"- {key} : manquant en classique, valeur rasterisée = {v2}")
                            alerts.append(f"Champ '{key}' manquant en classique.")
                        elif v2 is None:
                            diffs.append(f"- {key} : manquant en rasterisé, valeur classique = {v1}")
                            alerts.append(f"Champ '{key}' manquant en rasterisé.")
                        else:
                            diffs.append(f"- {key} : classique = {v1}, rasterisé = {v2}")
                            alerts.append(f"Champ '{key}' différent entre classique et rasterisé.")
                    coherence = round(100 * score / total) if total > 0 else 100
                    comparison_md.extend(diffs)
                    comparison_md.append(f"\n**Score de cohérence : {coherence}%**")
                    if alerts:
                        comparison_md.append("\n**Alertes :**")
                        for alert in alerts:
                            comparison_md.append(f"- {alert}")
                    else:
                        comparison_md.append("\nAucune divergence détectée entre les deux analyses.")
                    # Pour le JSON
                    comparison_json["coherence_score"] = coherence
                    comparison_json["alerts"] = alerts
                    # --- (suite du code de génération du rapport)
                    # Ajouter la section de comparaison dans le Markdown
                    # Double synthèse en haut du rapport
                    synthese_brute = [
                        f"# {tr('llm_summary.llm_summary_title', lang)}\n",
                        f"## {tr('llm_summary.general_info_title', lang)}\n",
                        f"- {tr('llm_summary.analysis_date', lang)} : {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
                        f"\n## {tr('llm_summary.data_analysis_title', lang)}\n",
                    ]
                    synthese_brute.extend(comparison_md)
                    synthese_brute.append("\n---\n")
                    # Synthèse naturelle (OpenAI)
                    synthese_naturelle = [f"### {tr('llm_summary.llm_summary', lang)}\n"]
                    natural_summary = await generate_natural_summary("\n".join(comparison_md), lang)
                    if natural_summary:
                        synthese_naturelle.append(natural_summary + "\n")
                    else:
                        synthese_naturelle.append(f"[{tr('llm_summary.no_data_found', lang)}]\n")
                    synthese_naturelle.append("\n---\n")
                    # On insère les deux synthèses AVANT le reste du rapport
                    summary_lines = synthese_brute + synthese_naturelle + summary_lines
                    # Ajouter la comparaison dans le JSON combiné
                    # ... (après la génération de combined_json["summary"])
                    combined_json["summary"]["comparison"] = comparison_json
                    # Générer le rapport Markdown combiné
                    combined_report_path = Path(output_dir) / "combined_analysis_report.md"
                    with open(combined_report_path, "w", encoding="utf-8") as combined_f:
                        combined_f.write("\n".join(summary_lines))
                    logger.info(f"Created combined analysis report at {combined_report_path}")
                    # Générer le JSON combiné
                    combined_json_path = Path(output_dir) / "combined_analysis.json"
                    with open(combined_json_path, "w", encoding="utf-8") as f:
                        json.dump(combined_json, f, ensure_ascii=False, indent=2)
                    logger.info(f"Created combined analysis JSON at {combined_json_path}")
                    # Pour le JSON combiné, ajouter la structure brute IA pour chaque mode
                    combined_json["summary"]["ia_structured"] = {
                        "classique": classic_ia,
                        "raster": raster_ia
                    }
                else:
                    logger.warning(f"Impossible de générer le rapport/JSON combiné : fichiers manquants (classique ou raster)")
            except Exception as e:
                logger.error(f"Erreur lors de la génération du rapport/JSON combiné : {e}")
                # Initialisation fallback si combined_json n'existe pas (sécurité extrême)
                if 'combined_json' not in locals():
                    combined_json = {"file": file.filename, "date": time.strftime('%Y-%m-%d %H:%M:%S'), "classic": None, "raster": None, "summary": {}}
                if "summary" not in combined_json:
                    combined_json["summary"] = {}
                combined_json["summary"]["error"] = str(e) if 'e' in locals() else "Erreur inconnue lors de la génération du rapport combiné."
                with open(Path(output_dir) / "combined_analysis.json", "w", encoding="utf-8") as f:
                    json.dump(combined_json, f, ensure_ascii=False, indent=2)
                with open(Path(output_dir) / "combined_analysis_report.md", "w", encoding="utf-8") as f:
                    f.write(f"# Erreur lors de la génération du rapport combiné\n\n{str(e) if 'e' in locals() else 'Erreur inconnue lors de la génération du rapport combiné.'}\n")
        
        # Check that output files were generated
        output_files = list(Path(output_dir).glob("**/*"))
        logger.info(f"Generated files: {[str(f) for f in output_files]}")
        
        if not output_files:
            logger.error("No output files were generated")
            raise HTTPException(status_code=500, detail="No output files were generated")
        
        # Handle the requested output format
        if format and format.lower() == "zip":
            # Create a ZIP filename based on the original PDF name
            zip_filename = f"{file.filename.rsplit('.', 1)[0]}_extraction.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            logger.info(f"Creating ZIP file at: {zip_path}")
            
            # Use shutil.make_archive for reliability
            base_name = zip_path.rsplit('.', 1)[0]  # remove .zip extension for make_archive
            logger.info(f"Zipping directory: {output_dir} to {base_name}")
            
            archive_path = shutil.make_archive(base_name, 'zip', output_dir)
            logger.info(f"Created ZIP archive at: {archive_path}")
            
            # Verify the ZIP file was created
            if not os.path.exists(archive_path):
                logger.error(f"Failed to create ZIP file at: {archive_path}")
                raise HTTPException(status_code=500, detail="Failed to create ZIP file")
            
            # Verify the ZIP file is not empty
            zip_size = os.path.getsize(archive_path)
            logger.info(f"ZIP file size: {zip_size} bytes")
            
            if zip_size == 0:
                logger.error("Created ZIP file is empty")
                raise HTTPException(status_code=500, detail="Created ZIP file is empty")
            
            # Return the ZIP file with proper headers
            headers = {
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Type, Content-Length",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate" 
            }
            
            logger.info(f"Returning ZIP file response with headers: {headers}")
            
            # Directement retourner le fichier avec FileResponse plutôt que StreamingResponse
            return FileResponse(
                path=archive_path,
                filename=zip_filename,
                media_type="application/zip",
                headers=headers
            )
            
        elif format and format.lower() == "rasterize":
            # Rasterize mode
            logger.info(f"Entering rasterize mode. Parameters: dpi={dpi}, pages={pages}")
            
            # Utiliser le script pdf_rasterizer.py
            rasterizer_script = os.path.join(base_path, "extract", "pdf_rasterizer.py")
            
            if not os.path.exists(rasterizer_script):
                logger.error(f"Rasterizer script not found at {rasterizer_script}")
                raise HTTPException(status_code=500, detail=f"Rasterizer script not found at {rasterizer_script}")
            
            cmd = [python_executable, rasterizer_script, input_file_path, "--output", output_dir, "--dpi", str(dpi)]
            if pages:
                cmd += ["--pages", pages]
            
            logger.info(f"Running rasterizer command: {' '.join(cmd)}")
            result = await run_cli_command(cmd, timeout=600)
            
            if result["return_code"] != 0:
                logger.error(f"Rasterization command failed: {result}")
                raise HTTPException(status_code=500, detail=f"PDF rasterization failed: {result['stderr']}")
            
            logger.info(f"Rasterization command completed successfully")
            
            # Check that output files were generated
            output_files = list(Path(output_dir).glob("**/*"))
            logger.info(f"Generated files: {[str(f) for f in output_files]}")
            
            if not output_files:
                logger.error("No output files were generated")
                raise HTTPException(status_code=500, detail="No output files were generated")
            
            # Create a ZIP file with the results
            zip_filename = f"{file.filename.rsplit('.', 1)[0]}_rasterized.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            logger.info(f"Creating ZIP file at: {zip_path}")
            
            # Use shutil.make_archive for reliability
            base_name = zip_path.rsplit('.', 1)[0]  # remove .zip extension for make_archive
            logger.info(f"Zipping directory: {output_dir} to {base_name}")
            
            archive_path = shutil.make_archive(base_name, 'zip', output_dir)
            logger.info(f"Created ZIP archive at: {archive_path}")
            
            # Verify the ZIP file was created
            if not os.path.exists(archive_path):
                logger.error(f"Failed to create ZIP file at: {archive_path}")
                raise HTTPException(status_code=500, detail="Failed to create ZIP file")
            
            # Verify the ZIP file is not empty
            zip_size = os.path.getsize(archive_path)
            logger.info(f"ZIP file size: {zip_size} bytes")
            
            if zip_size == 0:
                logger.error("Created ZIP file is empty")
                raise HTTPException(status_code=500, detail="Created ZIP file is empty")
            
            # Return the ZIP file with proper headers
            headers = {
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Type, Content-Length",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate" 
            }
            
            logger.info(f"Returning ZIP file response with headers: {headers}")
            
            # Retourner le fichier ZIP
            return FileResponse(
                path=archive_path,
                filename=zip_filename,
                media_type="application/zip",
                headers=headers
            )
            
        else:  # format.lower() == "json" ou format par défaut
            # Find the JSON result file
            result_files = list(Path(output_dir).glob("*_complete.json"))
            
            if not result_files:
                # Chercher n'importe quel fichier JSON si pas de fichier complet
                result_files = list(Path(output_dir).glob("*.json"))
                
            if not result_files:
                logger.error("No JSON result files found")
                raise HTTPException(status_code=500, detail="No JSON result files found")
            
            result_file = result_files[0]  # Take the first JSON file
            logger.info(f"Returning JSON file: {result_file}")
            
            # Return the JSON file with proper headers
            headers = {
                "Content-Disposition": f"attachment; filename={file.filename.rsplit('.', 1)[0]}_extraction.json",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Type, Content-Length",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate" 
            }
            
            # Directement retourner le fichier avec FileResponse plutôt que StreamingResponse
            return FileResponse(
                path=result_file,
                filename=f"{file.filename.rsplit('.', 1)[0]}_extraction.json",
                media_type="application/json",
                headers=headers
            )
            
    except Exception as e:
        logger.exception(f"Error processing PDF for job_id {job_id}: {str(e)}")
        cleanup_files(temp_dir)
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

@router.post("/extract-text", summary="Extract only text from PDF")
async def extract_text_from_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Extract only text from a PDF file without image analysis.
    
    - **file**: PDF file to process
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input.pdf"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    try:
        # Use extract/pdf_text_extractor.py directly
        extract_script = os.path.join(os.getcwd(), "extract", "pdf_text_extractor.py")
        
        if not os.path.exists(extract_script):
            raise HTTPException(status_code=500, detail=f"Extract script not found at {extract_script}")
            
        result = await run_cli_command(
            [sys.executable, extract_script, str(input_file_path), "--output", str(output_dir)]
        )
        
        # Find the output JSON file
        result_files = list(output_dir.glob("*.json"))
        if not result_files:
            raise HTTPException(status_code=500, detail="Processing completed but no output file was generated")
        
        result_file = result_files[0]
        
        # Return the file to the client
        return FileResponse(
            path=result_file,
            filename=f"text_extraction_{file.filename}.json",
            media_type="application/json",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")

@router.post("/extract-structured", summary="Extract structured data from PDF")
async def extract_structured_from_pdf(
    file: UploadFile = File(...),
    schema: Optional[str] = Form(None, description="JSON schema for structured extraction"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Extract structured data from a PDF file using a specified schema (using Outlines).
    
    - **file**: PDF file to process
    - **schema**: Optional JSON schema for structured extraction
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input.pdf"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    # Save schema if provided
    schema_path = None
    if schema:
        schema_path = temp_dir / "schema.json"
        with open(schema_path, "w") as f:
            f.write(schema)
    
    try:
        # Use extract/pdf_structured_extractor.py directly
        extract_script = os.path.join(os.getcwd(), "extract", "pdf_structured_extractor.py")
        
        if not os.path.exists(extract_script):
            raise HTTPException(status_code=500, detail=f"Extract script not found at {extract_script}")
            
        cmd = [sys.executable, extract_script, str(input_file_path), "--output", str(output_dir)]
        
        if schema_path:
            cmd.extend(["--schema", str(schema_path)])
        
        # Run the command
        result = await run_cli_command(cmd)
        
        # Find the output JSON file
        result_files = list(output_dir.glob("*.json"))
        if not result_files:
            raise HTTPException(status_code=500, detail="Processing completed but no output file was generated")
        
        result_file = result_files[0]
        
        # Return the file to the client
        return FileResponse(
            path=result_file,
            filename=f"structured_extraction_{file.filename}.json",
            media_type="application/json",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error extracting structured data: {str(e)}")

async def generate_natural_summary(comparison_md, lang='fr'):
    """Génère une synthèse naturelle (explication experte) via OpenAI à partir de la comparaison brute, dans la langue demandée."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("VISION_LLM_MODEL") or "gpt-4o"
    api_url = "https://api.openai.com/v1/chat/completions"
    # Ajout d'une consigne sur la possible asymétrie des analyses
    prompt = {
        'fr': (
            "Tu es un expert technique multidomaine, spécialisé dans l'analyse avancée de plans, schémas, documents techniques, graphiques, diagrammes, plans architecturaux, industriels, scientifiques, ou tout autre document visuel complexe. "
            "ATTENTION : Les deux analyses IA (classique et rasterisée) peuvent avoir des structures très différentes, selon le type de document et la méthode d'extraction. Si l'une des analyses ne contient pas de données structurées ou que les champs ne correspondent pas, explique-le et adapte ton jugement de cohérence en conséquence. "
            "À partir de la comparaison suivante entre deux extractions IA d'un même PDF (mode classique vs rasterisé), rédige une synthèse claire, pédagogique et professionnelle en français. "
            "Explique les différences, signale les incohérences, liste les champs manquants, et donne un avis sur la fiabilité globale. Sois synthétique, structuré, et utilise un ton d'expert multidisciplinaire.\n\nComparaison brute :\n" + comparison_md
        ),
        'en': (
            "You are a multi-domain technical expert, specialized in advanced analysis of plans, diagrams, technical documents, scientific or industrial graphics, architectural or engineering drawings, or any other complex visual document. "
            "WARNING: The two AI analyses (classic and rasterized) may have very different structures, depending on the document type and extraction method. If one analysis lacks structured data or the fields do not match, explain this and adapt your coherence judgment accordingly. "
            "Based on the following comparison between two AI extractions of the same PDF (classic vs rasterized mode), write a clear, professional summary in English. "
            "Explain the differences, highlight inconsistencies, list missing fields, and give an opinion on overall reliability. Be concise, structured, and use a multidisciplinary expert tone.\n\nRaw comparison:\n" + comparison_md
        )
    }[lang if lang in ('fr','en') else 'fr']
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    messages = [
        {"role": "system", "content": "Tu es un expert technique multidomaine (You are a multi-domain technical expert)."},
        {"role": "user", "content": prompt}
    ]
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 400,
        "temperature": 0.3,
    }
    import asyncio
    loop = asyncio.get_event_loop()
    def sync_post():
        import time
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if resp.status_code != 200:
                try:
                    err = resp.json()
                    err_msg = err.get('error', {}).get('message', resp.text)
                except Exception:
                    err_msg = resp.text
                return f"[Erreur OpenAI: {resp.status_code} - {err_msg}]"
            data = resp.json()
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'].strip()
            return "[Erreur OpenAI: Réponse inattendue]"
        except Exception as e:
            return f"[Erreur OpenAI: {e}]"
    return await loop.run_in_executor(None, sync_post) 