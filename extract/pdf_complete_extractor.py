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

console = Console()

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
        # Initialiser le descripteur d'images
        self.image_describer = PDFImageDescriber(
            openai_api_key=openai_api_key,
            max_images=max_images,
            timeout=timeout,
            language=language,
            model=model,
            save_images=save_images
        )
        
        self.max_images = max_images
        self.save_images = save_images
        self.language = language
        self.openai_api_key = openai_api_key
    
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
    
    def _get_surrounding_text(self, page, img_bbox, max_chars=500) -> str:
        """
        Extrait le texte environnant une image dans un document PDF.
        
        Args:
            page: Page du document PDF
            img_bbox: Rectangle délimitant l'image
            max_chars: Nombre maximum de caractères à extraire
            
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
            
            # Prendre les blocs les plus proches jusqu'à atteindre max_chars
            surrounding_text = ""
            chars_count = 0
            for block, _ in blocks_with_distance:
                text = block[4]
                if chars_count + len(text) <= max_chars:
                    surrounding_text += text + " "
                    chars_count += len(text)
                else:
                    # Ajouter une partie du texte pour atteindre max_chars
                    remaining = max_chars - chars_count
                    surrounding_text += text[:remaining] + "..."
                    break
            
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
        
        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)
        
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
            "nb_images_analysees": 0
        }
        
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
                console.print(f"  Traitement de la page {page_num+1}/{len(doc)}")
                
                # Extraire le texte de la page
                page_data = self.extract_text_from_page(page)
                result["pages"].append(page_data)
                
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
                            image_file_path = os.path.join(output_dir, image_filename)
                            with open(image_file_path, "wb") as f:
                                f.write(img_bytes)
                            console.print(f"  [dim]Image sauvegardée: {image_filename}[/dim]")
                        
                        # Encoder l'image en base64 pour l'envoi à l'API
                        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                        
                        # Obtenir la description de l'image via l'API
                        console.print(f"  [bold]Analyse de l'image {img_idx+1} (page {page_num+1})...[/bold]")
                        description = self.image_describer._get_image_description(img_b64, surrounding_text)
                        
                        if description:
                            console.print(f"  [green]✓[/green] Description obtenue")
                            result["nb_images_analysees"] += 1
                        else:
                            console.print(f"  [red]✗[/red] Échec de l'obtention de la description")
                            description = "Erreur lors de la description de l'image"
                        
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
                        continue
            
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
            unified_json_path = os.path.join(output_dir, f"{result_id}_unified.json")
            with open(unified_json_path, 'w', encoding='utf-8') as f:
                json.dump(unified_result, f, ensure_ascii=False, indent=2)
            
            # 4. Sauvegarder aussi le résultat détaillé original
            original_json_path = os.path.join(output_dir, f"{result_id}_complete.json")
            with open(original_json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            console.print(f"\n[bold green]Extraction complète terminée[/bold green]")
            console.print(f"  • Pages extraites: [bold]{len(result['pages'])}[/bold]")
            console.print(f"  • Images détectées: [bold]{result['nb_images_detectees']}[/bold]")
            console.print(f"  • Images analysées: [bold]{result['nb_images_analysees']}[/bold]")
            console.print(f"  • Fichier JSON unifié: [bold]{unified_json_path}[/bold]")
            console.print(f"  • Fichier JSON détaillé: [bold]{original_json_path}[/bold]")
            
            return result
            
        except Exception as e:
            console.print(f"[bold red]Erreur lors de l'extraction complète du document: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
            return result

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    
    # Charger les variables d'environnement
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Extraction complète d'un PDF (texte + images analysées)")
    parser.add_argument("pdf_path", help="Chemin vers le fichier PDF")
    parser.add_argument("--max-images", type=int, default=10, help="Nombre maximum d'images à traiter")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout pour l'appel API (secondes)")
    parser.add_argument("--language", choices=["fr", "en"], default="fr", help="Langue de description")
    parser.add_argument("--output", help="Chemin du répertoire de sortie")
    parser.add_argument("--no-save-images", action="store_true", help="Ne pas sauvegarder les images en fichiers PNG")
    args = parser.parse_args()
    
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