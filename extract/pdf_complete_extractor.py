#!/usr/bin/env python3
import fitz  # PyMuPDF
import os
import json
import time
import base64
import io
from typing import Dict, List, Any, Optional, Tuple
from rich.console import Console
from extract.image_describer import PDFImageDescriber
import threading

console = Console()

def update_progress(progress_path, phase, progress, step, extra=None):
    data = {"phase": phase, "progress": progress, "step": step}
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
            "step": step
        })
        data["history"] = history
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

class PDFCompleteExtractor:
    """
    Extraire le contenu complet d'un PDF : texte et images avec leurs descriptions.
    Génère un JSON unifié contenant le texte et les images analysées.
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        max_images: int = 10,
        timeout: int = 30,
        language: str = "fr",
        model: Optional[str] = None,
        save_images: bool = True,
    ):
        """
        Initialise l'extracteur complet de PDF.
        
        Args:
            openai_api_key: Clé API OpenAI pour les modèles multimodaux
            max_images: Nombre maximum d'images à traiter
            timeout: Timeout en secondes pour l'appel API
            language: Langue de description ('fr' ou 'en')
            model: Modèle OpenAI à utiliser
            save_images: Si True, les images extraites sont sauvegardées en fichiers PNG
        """
        # Essayer d'obtenir la clé API depuis les variables d'environnement si non fournie
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            console.print("[bold yellow]⚠️ Attention: Aucune clé API OpenAI fournie ou trouvée dans les variables d'environnement.[/bold yellow]")
            console.print("[yellow]Les images seront extraites mais pas analysées.[/yellow]")
        else:
            # Masquer la clé dans les logs pour des raisons de sécurité
            visible_part = self.openai_api_key[:5] + "..." + self.openai_api_key[-4:] if self.openai_api_key else "None"
            console.print(f"[green]✓[/green] Clé API OpenAI configurée: {visible_part}")
        
        # Initialiser le descripteur d'images
        self.image_describer = PDFImageDescriber(
            openai_api_key=self.openai_api_key,
            max_images=max_images,
            timeout=timeout,
            language=language,
            model=model,
            save_images=save_images
        )
        
        self.max_images = max_images
        self.save_images = save_images
        self.language = language
        
        # Afficher les informations de configuration
        console.print(f"[bold]Configuration d'extraction PDF:[/bold]")
        console.print(f"  • Langue: [bold]{language}[/bold]")
        console.print(f"  • Modèle: [bold]{self.image_describer.model}[/bold]")
        console.print(f"  • Nombre max. d'images: [bold]{max_images}[/bold]")
        console.print(f"  • Timeout API: [bold]{timeout}s[/bold]")
        console.print(f"  • Sauvegarde des images: [bold]{'Oui' if save_images else 'Non'}[/bold]")
    
    def extract_text_from_page(self, page) -> Dict[str, Any]:
        """
        Extrait le texte d'une page de PDF avec sa structure.
        
        Args:
            page: Page PyMuPDF
        
        Returns:
            Dictionnaire contenant le texte structuré de la page
        """
        # Extraire le texte avec sa structure
        page_dict = page.get_text("dict")
        page_text = page.get_text()
        
        # Structure simplifiée pour le JSON final
        return {
            "page_number": page.number + 1,  # Indexé à partir de 1 pour l'utilisateur
            "text": page_text,
            "blocks": [
                {
                    "type": "text" if block["type"] == 0 else "image",
                    "bbox": block["bbox"],
                    "text": "".join([span["text"] for line in block.get("lines", []) for span in line.get("spans", [])]) if block["type"] == 0 else "",
                }
                for block in page_dict.get("blocks", [])
            ]
        }
    
    def _get_surrounding_text(self, page, img_bbox, max_chars=None) -> str:
        """
        Extrait le texte environnant une image dans un document PDF.
        
        Args:
            page: Page du document PDF
            img_bbox: Rectangle délimitant l'image
            max_chars: Nombre maximum de caractères à extraire (None = pas de limite)
            
        Returns:
            Texte extrait autour de l'image
        """
        try:
            # Obtenir tout le texte de la page
            text_blocks = page.get_text("blocks")
            
            # Calculer les distances entre les blocs de texte et l'image
            # et récupérer les plus proches
            blocks_with_distance = []
            for block in text_blocks:
                # Ignorer les blocs qui ne sont pas du texte
                if block[6] != 0:  # Type 0 = texte
                    continue
                
                block_rect = fitz.Rect(block[:4])
                
                # Calculer la distance entre le bloc de texte et l'image
                # Nous utiliserons la distance entre les centres
                img_center = fitz.Point((img_bbox[0] + img_bbox[2]) / 2, (img_bbox[1] + img_bbox[3]) / 2)
                block_center = fitz.Point((block_rect[0] + block_rect[2]) / 2, (block_rect[1] + block_rect[3]) / 2)
                distance = abs(img_center - block_center)
                
                blocks_with_distance.append((block, distance))
            
            # Trier les blocs par distance
            blocks_with_distance.sort(key=lambda x: x[1])
            
            # Prendre les blocs les plus proches
            surrounding_text = ""
            for block, _ in blocks_with_distance:
                text = block[4]
                surrounding_text += text + " "
            
            return surrounding_text.strip()
        except Exception as e:
            console.print(f"Erreur lors de l'extraction du texte environnant: {e}")
            return ""
    
    def process_pdf(self, pdf_path: str, output_dir: str = None) -> dict:
        """
        Traite un document PDF pour extraire son texte et ses images.
        
        Args:
            pdf_path: Chemin du fichier PDF
            output_dir: Répertoire de sortie (optionnel)
            
        Returns:
            Dictionnaire contenant l'extraction complète
        """
        # Générer un ID unique pour cette exécution
        timestamp = int(time.time() * 1000)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        result_id = f"{pdf_name}_{timestamp}"
        
        # Utiliser le répertoire de sortie spécifié ou créer un sous-répertoire dans results
        if output_dir is None:
            output_dir = os.path.join("results", result_id)
        # Créer les sous-dossiers
        classic_dir = os.path.join(output_dir, "classic")
        img_dir = os.path.join(output_dir, "img")
        os.makedirs(classic_dir, exist_ok=True)
        os.makedirs(img_dir, exist_ok=True)
        
        # Log des informations pour le débogage
        console.print(f"[bold]Configuration:[/bold]")
        console.print(f"  • OpenAI API key présente: [{'green' if self.openai_api_key else 'red'}]{'Oui' if self.openai_api_key else 'Non'}[/{'green' if self.openai_api_key else 'red'}]")
        console.print(f"  • Modèle OpenAI: [bold]{self.image_describer.model}[/bold]")
        console.print(f"  • Nombre maximum d'images: [bold]{self.max_images}[/bold]")
        
        # Initialiser le résultat
        result = {
            "meta": {
                "filename": os.path.basename(pdf_path),
                "timestamp": timestamp,
                "result_id": result_id,
                "language": self.language,
                "model": self.image_describer.model,
                "output_dir": output_dir
            },
            "pages": [],
            "images": [],
            "nb_images_detectees": 0,
            "nb_images_analysees": 0,
            "configuration": {
                "openai_api_key_present": bool(self.openai_api_key),
                "model": self.image_describer.model,
                "max_images": self.max_images
            }
        }
        
        progress_path = os.path.join(output_dir, "progress.json")
        update_progress(progress_path, "init", 0, "Initialisation")
        
        resume_path = os.path.join(output_dir, "resume_classic.json")
        if os.path.exists(resume_path):
            with open(resume_path, "r", encoding="utf-8") as f:
                resume = json.load(f)
            done_pages = set(resume.get("ok", []))
            failed_pages = set(resume.get("failed", []))
        else:
            resume = {"ok": [], "failed": []}
            done_pages = set()
            failed_pages = set()
        
        try:
            console.print(f"\n[bold green]Extraction complète du document[/bold green]: {pdf_path}")
            
            # Vérifier que le fichier existe
            if not os.path.exists(pdf_path):
                console.print(f"[bold red]Erreur[/bold red]: Le fichier {pdf_path} n'existe pas.")
                return result
            
            # Ouvrir le document PDF
            doc = fitz.open(pdf_path)
            console.print(f"[bold]Document ouvert avec succès[/bold]: {len(doc)} pages")
            
            # Compteur pour les images
            processed_images = 0
            
            # 1. Extraire le texte et les images intégrées de chaque page
            console.print("[bold]Phase 1: Extraction du texte et des images intégrées[/bold]")
            
            for page_num, page in enumerate(doc):
                if str(page_num) in done_pages:
                    console.print(f"[RESUME] Page {page_num+1} déjà traitée, skip.")
                    continue
                try:
                    update_progress(progress_path, "classic", int(100 * page_num / len(doc)), f"Traitement de la page {page_num+1}/{len(doc)}")
                    
                    # Extraire le texte de la page
                    page_data = self.extract_text_from_page(page)
                    result["pages"].append(page_data)
                    resume["ok"].append(str(page_num))
                    
                    # Obtenir les images intégrées dans la page
                    image_list = page.get_images(full=True)
                    
                    if not image_list:
                        console.print(f"  [dim]Aucune image intégrée détectée sur la page {page_num+1}[/dim]")
                        continue
                    
                    console.print(f"  [green]{len(image_list)} image(s) intégrée(s) détectée(s) sur la page {page_num+1}[/green]")
                    result["nb_images_detectees"] += len(image_list)
                    
                    # Traiter chaque image intégrée
                    for img_idx, img in enumerate(image_list):
                        # Vérifier si on a atteint le nombre maximum d'images à traiter
                        if processed_images >= self.max_images:
                            console.print(f"[yellow]Nombre maximum d'images atteint ({self.max_images}). Arrêt du traitement.[/yellow]")
                            break
                        try:
                            # Extraire les informations de l'image
                            xref = img[0]  # Référence xref de l'image
                            # Extraire l'image directement du PDF sans rendering la page
                            pix = fitz.Pixmap(doc, xref)
                            # Rechercher la position de l'image sur la page
                            img_bbox = None
                            for item in page.get_text("dict")["blocks"]:
                                if item.get("type") == 1:  # Type 1 = image
                                    # Rechercher par proximité de dimensions
                                    if abs(item.get("width") - pix.width) <= 5 and abs(item.get("height") - pix.height) <= 5:
                                        img_bbox = item["bbox"]
                                        break
                            # Si on n'a pas trouvé de position exacte, utiliser les dimensions de la page
                            if not img_bbox:
                                img_bbox = [0, 0, page.rect.width, page.rect.height]
                            # Extraire le texte environnant
                            surrounding_text = self._get_surrounding_text(page, img_bbox)
                            # Convertir l'image en PNG pour le traitement
                            img_bytes = pix.tobytes("png")
                            # Sauvegarder l'image en tant que fichier PNG si demandé
                            image_file_path = None
                            if self.save_images:
                                image_filename = f"{result_id}_image_p{page_num+1}_i{img_idx+1}.png"
                                image_file_path = os.path.join(img_dir, image_filename)
                                with open(image_file_path, "wb") as f:
                                    f.write(img_bytes)
                                console.print(f"  [dim]Image sauvegardée: {image_filename}[/dim]")
                            # Encoder l'image en base64 pour l'envoi à l'API
                            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                            # Obtenir la description de l'image via l'API
                            console.print(f"  [bold]Analyse de l'image {img_idx+1} (page {page_num+1})...[/bold]")
                            description = None
                            if not self.openai_api_key:
                                console.print(f"  [yellow]⚠️ Pas de clé API OpenAI, l'image ne sera pas analysée[/yellow]")
                                description = "Aucune analyse d'image (clé API non configurée)"
                            else:
                                try:
                                    import signal
                                    class TimeoutException(Exception): pass
                                    def handler(signum, frame):
                                        raise TimeoutException("Timeout sur analyse image OpenAI")
                                    signal.signal(signal.SIGALRM, handler)
                                    signal.alarm(60)  # 60 secondes max par image
                                    try:
                                        console.print(f"  [dim]Envoi à l'API OpenAI - Image {len(img_b64)//1000}K caractères, modèle {self.image_describer.model}[/dim]")
                                        description = self.image_describer._get_image_description(img_b64, surrounding_text)
                                        signal.alarm(0)
                                    except TimeoutException:
                                        description = "Timeout lors de l'analyse de l'image (60s)"
                                        console.print(f"  [red]Timeout lors de l'analyse de l'image {img_idx+1} (page {page_num+1})[/red]")
                                    except Exception as e:
                                        signal.alarm(0)
                                        raise e
                                    if description:
                                        # Déterminer si la description est un message d'erreur
                                        error_prefixes = ["Erreur", "Error", "Aucune analyse", "Timeout"]
                                        is_error = any(description.startswith(prefix) for prefix in error_prefixes)
                                        if is_error:
                                            console.print(f"  [yellow]⚠️ L'analyse a échoué: {description[:100]}...[/yellow]")
                                        else:
                                            console.print(f"  [green]✓[/green] Description obtenue: {len(description)} caractères")
                                            result["nb_images_analysees"] += 1
                                            console.print(f"  [green]✓[/green] Analyse réussie")
                                    else:
                                        console.print(f"  [red]✗[/red] Échec de l'obtention de la description (réponse vide)")
                                        description = "Erreur lors de la description de l'image: réponse vide"
                                except Exception as e:
                                    console.print(f"  [red]✗[/red] Exception lors de l'appel à l'API: {str(e)}")
                                    import traceback
                                    console.print(f"  [red]Détails: {type(e).__name__}[/red]")
                                    console.print(f"  [dim]{traceback.format_exc()}[/dim]")
                                    description = f"Erreur lors de l'analyse: {str(e)}"
                            # Ajouter l'image au résultat
                            image_info = {
                                "page": page_num + 1,
                                "index": img_idx + 1,
                                "width": pix.width,
                                "height": pix.height,
                                "position": img_bbox,
                                "xref": xref,
                                "description_ai": description,
                                "surrounding_text": surrounding_text,
                                "file_path": image_file_path
                            }
                            result["images"].append(image_info)
                            processed_images += 1
                        except Exception as e:
                            console.print(f"  [red]Erreur lors du traitement de l'image {img_idx+1}: {str(e)}[/red]")
                            import traceback
                            console.print(traceback.format_exc())
                            continue
                except Exception as e:
                    resume["failed"].append(str(page_num))
                with open(resume_path, "w", encoding="utf-8") as f:
                    json.dump(resume, f, indent=2)
            
            # Fermer le document
            doc.close()
            
            # 2. Générer un JSON unifié qui combine le texte et les images
            console.print("[bold]Phase 2: Génération du JSON unifié[/bold]")
            
            # Associer chaque image à sa page correspondante dans la structure finale
            # On référence les images par leur chemin de fichier plutôt que de dupliquer le contenu
            unified_result = {
                "meta": result["meta"],
                "pages": [],
                "stats": {
                    "pages_count": len(result["pages"]),
                    "images_detected": result["nb_images_detectees"],
                    "images_analyzed": result["nb_images_analysees"]
                }
            }
            
            # Carte des images par numéro de page
            images_by_page = {}
            for img in result["images"]:
                page_num = img["page"]
                if page_num not in images_by_page:
                    images_by_page[page_num] = []
                images_by_page[page_num].append(img)
            
            # Reconstruire les pages avec les images intégrées
            for page_data in result["pages"]:
                page_num = page_data["page_number"]
                page_images = images_by_page.get(page_num, [])
                
                # Construire une version unifiée de la page
                unified_page = {
                    "page_number": page_num,
                    "text": page_data["text"],
                    "elements": []
                }
                
                # Ajouter les blocs de texte et référencer les images
                for block in page_data["blocks"]:
                    if block["type"] == "text":
                        unified_page["elements"].append({
                            "type": "text",
                            "position": block["bbox"],
                            "content": block["text"]
                        })
                
                # Ajouter les images avec leurs descriptions
                for img in page_images:
                    unified_page["elements"].append({
                        "type": "image",
                        "position": img["position"],
                        "width": img["width"],
                        "height": img["height"],
                        "file_path": os.path.basename(img["file_path"]) if img["file_path"] else None,
                        "description_ai": img["description_ai"],
                        "surrounding_text": img["surrounding_text"]
                    })
                
                unified_result["pages"].append(unified_page)
            
            # 3. Sauvegarder le JSON unifié
            unified_json_path = os.path.join(classic_dir, f"{result_id}_unified.json")
            with open(unified_json_path, 'w', encoding='utf-8') as f:
                json.dump(unified_result, f, ensure_ascii=False, indent=2)
            
            # 4. Sauvegarder aussi le résultat détaillé original
            original_json_path = os.path.join(classic_dir, f"{result_id}_complete.json")
            with open(original_json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # 5. Créer un rapport texte lisible par l'homme
            report_path = os.path.join(classic_dir, f"{result_id}_report.md")
            self._create_human_readable_report(unified_result, report_path)
            
            console.print(f"\n[bold green]Extraction complète terminée[/bold green]")
            console.print(f"  • Pages extraites: [bold]{len(result['pages'])}[/bold]")
            console.print(f"  • Images détectées: [bold]{result['nb_images_detectees']}[/bold]")
            console.print(f"  • Images analysées: [bold]{result['nb_images_analysees']}[/bold]")
            console.print(f"  • Fichier JSON unifié: [bold]{unified_json_path}[/bold]")
            console.print(f"  • Fichier JSON détaillé: [bold]{original_json_path}[/bold]")
            console.print(f"  • Rapport texte lisible: [bold]{report_path}[/bold]")
            
            update_progress(progress_path, "classic", 100, "Extraction classique terminée")
            
            return result
            
        except Exception as e:
            console.print(f"[bold red]Erreur lors de l'extraction complète du document: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
            return result

    def _create_human_readable_report(self, result: dict, output_path: str):
        """
        Crée un rapport lisible pour les humains à partir des résultats d'extraction.
        
        Args:
            result: Résultat unifié de l'extraction
            output_path: Chemin du fichier de sortie
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # En-tête du rapport
                f.write(f"# Rapport d'extraction complète du PDF\n\n")
                f.write(f"Fichier: {result['meta']['filename']}\n")
                f.write(f"Date d'extraction: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['meta']['timestamp']/1000))}\n")
                f.write(f"Langue: {result['meta']['language']}\n")
                f.write(f"Modèle utilisé: {result['meta']['model']}\n\n")
                
                # Statistiques globales
                f.write(f"## Statistiques\n\n")
                f.write(f"Pages: {result['stats']['pages_count']}\n")
                f.write(f"Images détectées: {result['stats']['images_detected']}\n")
                f.write(f"Images analysées: {result['stats']['images_analyzed']}\n\n")
                
                # Contenu de chaque page
                for page in result['pages']:
                    f.write(f"## Page {page['page_number']}\n\n")
                    
                    # Extraire le texte principal de la page SANS LIMITATION
                    f.write(f"### Texte\n\n")
                    f.write(f"{page['text']}\n\n")
                    
                    # Extraire les descriptions d'images pour cette page
                    image_elements = [elem for elem in page['elements'] if elem['type'] == 'image']
                    
                    if image_elements:
                        f.write(f"### Images ({len(image_elements)})\n\n")
                        
                        for i, img in enumerate(image_elements):
                            f.write(f"#### Image {i+1}\n\n")
                            if 'file_path' in img and img['file_path']:
                                f.write(f"Fichier: {img['file_path']}\n")
                            f.write(f"Dimensions: {img['width']}x{img['height']}\n")
                            
                            # Écrire le texte environnant SANS LIMITATION
                            if 'surrounding_text' in img and img['surrounding_text']:
                                surrounding_text = img['surrounding_text']
                                console.print(f"[bold yellow]Longueur du texte environnant: {len(surrounding_text)} caractères[/bold yellow]")
                                f.write(f"Contexte: {surrounding_text}\n\n")
                            
                            if 'description_ai' in img and img['description_ai']:
                                f.write(f"Description: {img['description_ai']}\n\n")
                            
                            f.write("---\n\n")
                    
                    f.write("\n")
                
                f.write("Fin du rapport\n")
                
            return output_path
        except Exception as e:
            console.print(f"[bold red]Erreur lors de la création du rapport: {str(e)}[/bold red]")
            return None

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    
    # Charger les variables d'environnement
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Extraction complète d'un PDF (texte + images analysées)")
    parser.add_argument("pdf_path", help="Chemin vers le fichier PDF")
    parser.add_argument("--output-dir", dest="output", help="Chemin du répertoire de sortie")
    parser.add_argument("--max-images", type=int, default=10, help="Nombre maximum d'images à traiter")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout pour l'appel API (secondes)")
    parser.add_argument("--language", choices=["fr", "en"], default="fr", help="Langue de description")
    parser.add_argument("--no-save-images", action="store_true", help="Ne pas sauvegarder les images en fichiers PNG")
    args = parser.parse_args()
    
    if not args.pdf_path:
        print("Erreur: Aucun fichier PDF spécifié.")
        exit(1)
    
    # Récupérer la clé API et le modèle
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("VISION_LLM_MODEL") or "gpt-4o"
    
    # Si la clé API n'est pas définie, afficher un message et quitter
    if not api_key:
        print("Erreur: Clé API OpenAI non définie. Définissez la variable d'environnement OPENAI_API_KEY.")
        exit(1)
    
    # Créer l'extracteur complet
    extractor = PDFCompleteExtractor(
        openai_api_key=api_key,
        max_images=args.max_images,
        timeout=args.timeout,
        language=args.language,
        model=model,
        save_images=not args.no_save_images
    )
    
    # Traiter le PDF
    result = extractor.process_pdf(args.pdf_path, args.output)
    
    # Afficher un résumé
    print("\nRésumé de l'extraction complète:")
    print(f"  Fichier: {result['meta']['filename']}")
    print(f"  Pages extraites: {len(result['pages'])}")
    print(f"  Images détectées: {result['nb_images_detectees']}")
    print(f"  Images analysées: {result['nb_images_analysees']}")
    print(f"  Résultats sauvegardés dans: {result['meta']['output_dir']}") 