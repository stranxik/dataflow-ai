import fitz
import os
import json
import argparse
import time
from extract.image_describer import PDFImageDescriber
from rich.console import Console
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed

console = Console()

def get_default_language():
    # Chercher la langue dans le fichier .language à la racine du projet
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    language_file = os.path.join(base_path, ".language")
    if os.path.exists(language_file):
        try:
            with open(language_file, "r") as f:
                lang = f.read().strip()
                if lang in ["fr", "en"]:
                    return lang
        except Exception:
            pass
    return "fr"  # Par défaut

def get_default_model():
    return os.environ.get("VISION_LLM_MODEL") or "gpt-4o"

def create_human_readable_report(images, output_dir, filename="rasterized_report.md", pdf_path=None):
    """
    Crée un rapport lisible pour les humains à partir des résultats d'extraction des images rasterisées.
    
    Args:
        images: Liste des images analysées avec leurs descriptions
        output_dir: Répertoire de sortie
        filename: Nom du fichier de rapport
        pdf_path: Chemin du fichier PDF source
    """
    output_path = os.path.join(output_dir, filename)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # En-tête du rapport
            f.write(f"# Rapport d'analyse des pages rasterisées\n\n")
            
            if pdf_path:
                f.write(f"Fichier: {os.path.basename(pdf_path)}\n")
            
            f.write(f"Date d'extraction: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Nombre de pages rasterisées: {len(images)}\n\n")
            
            # Traiter chaque image rasterisée
            for i, img in enumerate(images):
                f.write(f"## Page {img['page']}\n\n")
                
                # Chemin de l'image
                if 'file_path' in img and img['file_path']:
                    f.write(f"Image: {os.path.basename(img['file_path'])}\n")
                    f.write(f"Dimensions: {img['width']}x{img['height']}\n\n")
                
                # Ajouter l'analyse IA complète
                if 'description_ai' in img and img['description_ai']:
                    f.write("### Analyse IA\n\n")
                    f.write(f"{img['description_ai']}\n\n")
                    # Tenter d'extraire la post-analyse structurante si elle existe dans le JSON
                    try:
                        desc = img['description_ai']
                        if isinstance(desc, str) and desc.strip().startswith('{') and desc.strip().endswith('}'):
                            desc_json = json.loads(desc)
                            post_analysis = desc_json.get('post_analysis', None)
                            post_analysis_attempted = desc_json.get('post_analysis_attempted', False)
                            f.write("### Post-analyse structurante\n\n")
                            if post_analysis_attempted:
                                if post_analysis:
                                    if isinstance(post_analysis, str):
                                        f.write(f"{post_analysis}\n\n")
                                    else:
                                        f.write(f"{json.dumps(post_analysis, ensure_ascii=False, indent=2)}\n\n")
                                else:
                                    f.write("Aucune post-analyse structurante n'a pu être produite ou n'était possible pour cette page.\n\n")
                            else:
                                f.write("Post-analyse structurante non demandée (document non détecté comme plan).\n\n")
                    except Exception as e:
                        f.write(f"[Erreur lors de l'extraction de la post-analyse structurante: {e}]\n\n")
                
                # Ajouter le texte extrait de la page
                if 'surrounding_text' in img and img['surrounding_text']:
                    f.write("### Texte extrait\n\n")
                    f.write(f"{img['surrounding_text']}\n\n")
                
                f.write("---\n\n")
            
            f.write("Fin du rapport\n")
        
        console.print(f"[green]Rapport Markdown créé: {output_path}[/green]")
        return output_path
    
    except Exception as e:
        console.print(f"[bold red]Erreur lors de la création du rapport: {str(e)}[/bold red]")
        return None

def update_progress(progress_path, phase, progress, step, extra=None, status="running"):
    data = {"phase": phase, "progress": progress, "step": step, "status": status}
    if extra:
        data.update(extra)
    lock = threading.Lock()
    with lock:
        # Charger l'historique existant si présent
        if os.path.exists(progress_path):
            try:
                with open(progress_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                history = existing.get("history", [])
            except Exception:
                history = []
        else:
            history = []
        # Ajouter la nouvelle étape à l'historique
        history.append({
            "timestamp": int(time.time()),
            "phase": phase,
            "progress": progress,
            "step": step,
            "status": status
        })
        data["history"] = history
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def process_page(args):
    """
    Fonction indépendante pour traiter une page PDF : rasterisation, analyse IA, etc.
    Args:
        args: tuple (page_num, pdf_path, output_dir, dpi, language, model, raster_timeout)
    Returns:
        dict: résultat pour la page
    """
    page_num, pdf_path, output_dir, dpi, language, model, raster_timeout = args
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_dir = os.path.join(output_dir, "img")
        os.makedirs(img_dir, exist_ok=True)
        img_path = os.path.join(img_dir, f"page_{page_num+1}_raster.png")
        pix.save(img_path)
        # Analyse IA de l'image rasterisée
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("OPENAI_API_KEY")
        describer = PDFImageDescriber(
            openai_api_key=api_key,
            max_images=10000,
            timeout=raster_timeout,
            language=language,
            model=model,
            save_images=True
        )
        img_b64 = describer._encode_image(img_bytes)
        surrounding_text = page.get_text()
        dynamic_timeout = raster_timeout
        if pix.width > 3000 or pix.height > 3000:
            dynamic_timeout = 180
        try:
            description = describer._get_image_description(img_b64, surrounding_text)
        except Exception as e:
            if 'timeout' in str(e).lower() and dynamic_timeout < 180:
                try:
                    description = describer._get_image_description(img_b64, surrounding_text)
                except Exception as e2:
                    description = f"Erreur lors de la description de l'image: timeout API (180s)"
            else:
                description = f"Erreur lors de la description de l'image: {str(e)}"
        return {
            "page": page_num + 1,
            "file_path": img_path,
            "width": pix.width,
            "height": pix.height,
            "description_ai": description,
            "surrounding_text": surrounding_text
        }
    except Exception as e:
        return {"page": page_num + 1, "error": str(e)}

def rasterize_and_analyze_pdf(pdf_path, output_dir, dpi=300, pages=None, language=None, model=None, timeout=30):
    progress_path = os.path.join(output_dir, "progress.json")
    update_progress(progress_path, "raster", 0, "Initialisation rasterisation")
    os.makedirs(output_dir, exist_ok=True)
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print("[bold red]Erreur: Clé API OpenAI non définie. Définissez la variable d'environnement OPENAI_API_KEY.[/bold red]")
        return None
    language = language or get_default_language()
    model = model or get_default_model()
    raster_timeout = 90
    console.print(f"[bold]Configuration rasterisation PDF:[/bold]")
    console.print(f"  • Langue: [bold]{language}[/bold]")
    console.print(f"  • Modèle: [bold]{model}[/bold]")
    console.print(f"  • DPI: [bold]{dpi}[/bold]")
    console.print(f"  • Timeout API: [bold]{raster_timeout}s[/bold]")
    doc = fitz.open(pdf_path)
    page_indices = range(len(doc)) if pages is None else pages
    num_pages = len(page_indices)
    images = []
    resume_path = os.path.join(output_dir, "resume.json")
    if os.path.exists(resume_path):
        with open(resume_path, "r", encoding="utf-8") as f:
            resume = json.load(f)
        done_pages = set(resume.get("ok", []))
        failed_pages = set(resume.get("failed", []))
    else:
        resume = {"ok": [], "failed": []}
        done_pages = set()
        failed_pages = set()
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = []
        for page_num in range(doc.page_count):
            # Vérifier si la page a déjà été traitée
            if str(page_num) in done_pages:
                console.log(f"[RESUME] Page {page_num} déjà traitée, skip.")
                continue
            args = (page_num, pdf_path, output_dir, dpi, language, model, raster_timeout)
            futures.append(executor.submit(process_page, args))
        for future in as_completed(futures):
            result = future.result()
            images.append(result)
            page_num = result.get("page", None)
            error = result.get("error", None)
            if error is None and page_num is not None:
                resume["ok"].append(str(page_num-1))
            elif page_num is not None:
                resume["failed"].append(str(page_num-1))
            with open(resume_path, "w", encoding="utf-8") as f:
                json.dump(resume, f, indent=2)
    # Créer les sous-dossiers
    raster_dir = os.path.join(output_dir, "raster")
    img_dir = os.path.join(output_dir, "img")
    os.makedirs(raster_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)
    # Sauvegarder le JSON de résultat
    result_json = os.path.join(raster_dir, "rasterized_images_analysis.json")
    with open(result_json, "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=2)
    # Créer également un rapport lisible au format Markdown
    create_human_readable_report(images, raster_dir, "rasterized_report.md", pdf_path)
    console.print(f"[green]Rasterisation et analyse IA terminées. {len(images)} images générées et analysées.[/green]")
    console.print(f"JSON de résultat : {result_json}")
    update_progress(progress_path, "raster", 100, "Rasterisation terminée")
    return images

def detect_vector_pages(pdf_path, min_drawings=10, max_text_len=500):
    """
    Détecte les pages contenant beaucoup d'objets vectoriels (plans, schémas) ou peu de texte.
    Args:
        pdf_path: Chemin du PDF
        min_drawings: Nombre minimal d'objets vectoriels pour considérer la page comme un plan
        max_text_len: Longueur maximale du texte pour considérer la page comme graphique
    Returns:
        Liste des indices de pages à rasteriser
    """
    doc = fitz.open(pdf_path)
    selected = []
    for i, page in enumerate(doc):
        drawings = page.get_drawings()
        text = page.get_text()
        if len(drawings) >= min_drawings or len(text) <= max_text_len:
            selected.append(i)
    return selected

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rasteriser chaque page d'un PDF en PNG et analyser avec GPT-4.1.")
    parser.add_argument("pdf_path", help="Chemin du fichier PDF")
    parser.add_argument("--output", required=True, help="Dossier de sortie pour les images")
    parser.add_argument("--dpi", type=int, default=300, help="Résolution en DPI (défaut 300)")
    parser.add_argument("--pages", type=str, default=None, help="Pages à rasteriser (ex: 1,3,5-7)")
    parser.add_argument("--language", type=str, default=None, help="Langue de description IA (fr/en)")
    parser.add_argument("--model", type=str, default=None, help="Modèle OpenAI à utiliser")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout pour l'appel API (secondes)")
    parser.add_argument("--auto-pages", action="store_true", help="Détecte automatiquement les pages à rasteriser (plans, schémas, etc.)")
    args = parser.parse_args()
    # Gérer la sélection de pages
    if args.auto_pages:
        page_indices = detect_vector_pages(args.pdf_path)
        if not page_indices:
            print("Aucune page détectée comme plan/schéma, toutes les pages seront rasterisées.")
            page_indices = None
        else:
            print(f"Pages détectées comme plans/schémas: {[i+1 for i in page_indices]}")
    elif args.pages:
        page_indices = []
        for part in args.pages.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                page_indices.extend(range(start-1, end))
            else:
                page_indices.append(int(part)-1)
    else:
        page_indices = None
    rasterize_and_analyze_pdf(
        args.pdf_path,
        args.output,
        dpi=args.dpi,
        pages=page_indices,
        language=args.language,
        model=args.model,
        timeout=args.timeout
    ) 