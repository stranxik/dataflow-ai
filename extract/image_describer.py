import fitz  # PyMuPDF
import base64
import io
import time
import os
import json
import requests
import logging
from typing import List, Dict, Any, Optional
from rich.console import Console

console = Console()

class PDFImageDescriber:
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        max_images: int = 10,
        timeout: int = 30,
        language: str = "fr",
        model: Optional[str] = None,
        api_url: str = "https://api.openai.com/v1/chat/completions",
        save_images: bool = True,
    ):
        """
        Initialise le module d'extraction et de description d'images PDF.
        
        Args:
            openai_api_key: Clé API OpenAI pour les modèles multimodaux (si None, utilise OPENAI_API_KEY depuis .env)
            max_images: Nombre maximum d'images à traiter
            timeout: Timeout en secondes pour l'appel API
            language: Langue de description ('fr' ou 'en')
            model: Modèle OpenAI à utiliser (si None, utilise VISION_LLM_MODEL depuis .env)
            api_url: URL de l'API OpenAI
            save_images: Si True, les images extraites sont sauvegardées en fichiers PNG
        """
        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Clé API OpenAI requise. Spécifiez-la en paramètre ou définissez OPENAI_API_KEY dans l'environnement.")
            
        self.max_images = max_images
        self.timeout = timeout
        self.language = language
        
        # Priorité: paramètre model > variable d'environnement VISION_LLM_MODEL > fallback gpt-4o
        self.model = model or os.environ.get("VISION_LLM_MODEL") or "gpt-4o"
        self.api_url = api_url
        self.save_images = save_images
        self.logger = logging.getLogger(__name__)
        
        if not model and not os.environ.get("VISION_LLM_MODEL"):
            print("ℹ️ Aucun modèle vision spécifié. Utilisation du modèle par défaut: gpt-4o")
        
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
            self.logger.error(f"Erreur lors de l'extraction du texte environnant: {e}")
            return ""
        
    def _encode_image(self, img_data: bytes) -> str:
        """
        Encode une image en base64.
        
        Args:
            img_data: Données binaires de l'image
            
        Returns:
            Image encodée en base64
        """
        return base64.b64encode(img_data).decode("utf-8")

    def _get_image_description(self, image_b64: str, surrounding_text: str) -> Optional[str]:
        """
        Obtient une description de l'image via l'API OpenAI multimodale.
        
        Args:
            image_b64: Image encodée en base64
            surrounding_text: Texte environnant l'image
            
        Returns:
            Description de l'image ou None en cas d'erreur
        """
        # Vérifier que la clé API est configurée
        if not self.api_key:
            console.print("[bold red]Erreur: Pas de clé API OpenAI configurée[/bold red]")
            return None
        
        # Vérifier que l'image en base64 est valide
        if not image_b64 or len(image_b64) < 100:  # Une image en base64 valide devrait être plus longue
            console.print("[bold red]Erreur: Image en base64 invalide ou vide[/bold red]")
            return None
        
        console.print(f"[dim]Préparation de la requête API pour une image de {len(image_b64)} caractères en base64[/dim]")
        console.print(f"[dim]Modèle utilisé: {self.model}[/dim]")
        console.print(f"[dim]Texte environnant: {len(surrounding_text)} caractères[/dim]")
        
        # Ajuster le prompt selon la langue
        if self.language == "fr":
            system_prompt = """Tu es un expert technique multidomaine, spécialisé dans l'analyse visuelle approfondie de documents techniques complexes, travaillant pour une équipe d'ingénieurs. 

Ton expertise couvre :
- Schémas techniques et architecturaux
- Diagrammes de systèmes (électriques, mécaniques, informatiques)
- Plans (cadastraux, architecturaux, industriels)
- Graphiques scientifiques et techniques
- Schémas de circuits (électroniques, hydrauliques, thermiques)
- Visualisations de données complexes
- Analyse d'images photographiques et médicales (radiographies, scanners médicaux, photographies cliniques)

Mission : extraire et interpréter chaque détail avec précision, en utilisant un langage technique professionnel et concis, pour une prise de décision technique fiable et directement exploitable.

Compétences spécifiques :
- Analyse de hiérarchies visuelles et structures logiques
- Identification de représentations tabulaires implicites
- Extraction normalisée d'entités métier
- Génération de JSON structuré pour systèmes automatisés
- Interprétation visuelle détaillée des images photographiques et médicales
- Extraction des caractéristiques visuelles critiques et des informations contextuelles"""

            user_prompt = f"""Contexte : texte autour de l'image :
"{surrounding_text}"

Analyse technique exhaustive de l'image. Objectif : générer un JSON structuré et exploitable.

INSTRUCTIONS PRINCIPALES :
1. Identification précise
   - Type exact de document
   - Domaine technique
   - Niveau de complexité

2. Analyse structurelle
   - Composants principaux
   - Relations et interactions
   - Échelles et proportions
   - Technologies représentées
   - Annotations techniques

3. Interprétation technique
   - Implications pratiques
   - Hypothèses de conception
   - Défis techniques potentiels
   - Innovations remarquables

4. Extraction rigoureuse
   - Toutes valeurs numériques
   - Libellés techniques
   - Annotations significatives
   - Respect strict des unités

5. Analyse comparative
   - Comparaison aux standards
   - Écarts aux pratiques habituelles
   - Conformité technique

6. Rendu JSON IMPÉRATIF
   Structure :
   - `type`: Type précis
   - `domain`: Domaine technique
   - `complexity`: Niveau
   - `data`: Données techniques
   - `metadata`: Informations complémentaires
   - `insights`: Observations techniques

CONSIGNES FINALES :
- JSON PARFAIT et EXPLOITABLE
- Aucun texte superflu
- RÉPONSE UNIQUEMENT au format JSON

Langage technique, sans jargon inutile.

- Hiérarchie visuelle et structure logique : sections, blocs, regroupements
- Représentation tabulaire implicite : tableaux visuels, alignements, colonnes ou grilles
Tu travailles pour une équipe d'ingénieurs spécialisés. Ton analyse servira à une prise de décision technique, elle doit donc être fiable, concise et directement exploitable.
Le JSON sera utilisé dans un système automatisé. Chaque champ doit être simple, stable, réutilisable sans retraitement. Pas de texte libre, sauf dans `insights`.
Toutes les unités doivent être explicites, séparées, et homogènes. Pour les unités, utilise un format comme: "length": {{"value": 5, "unit": "m"}}. Evite de concaténer les unités dans les valeurs.
Si des entités métier spécifiques apparaissent (ex : références, numéros de pièces, identifiants uniques), les extraire sous forme normalisée.
CONSIGNES COMPLÉMENTAIRES :

- Le JSON sera utilisé dans une API métier, il doit être formel, homogène, sans texte parasite.
- Chaque valeur doit être normalisée. Les unités doivent être explicites, séparées des valeurs.
- Extraire toute hiérarchie visuelle ou logique détectée (titres, regroupements, légendes, tableaux).
- Si des entités métier spécifiques apparaissent (codes, composants, références), les inclure dans `data` ou `metadata`.
- AUCUN COMMENTAIRE HORS JSON."""
        else:  # English version
            system_prompt = """You are a multi-domain technical expert specialized in in-depth visual analysis of complex technical documents, working for a team of specialized engineers.

Your expertise covers:
- Technical and architectural diagrams
- System diagrams (electrical, mechanical, computer)
- Plans (cadastral, architectural, industrial)
- Scientific and technical graphics
- Circuit diagrams (electronic, hydraulic, thermal)
- Complex data visualizations
- Photographic and medical imaging analysis (X-rays, medical scans, clinical photographs)

Mission: extract and interpret every detail with precision, using professional and concise technical language, to enable reliable and directly actionable technical decision-making.

Specific competencies:
- Analysis of visual hierarchies and logical structures
- Identification of implicit tabular representations
- Normalized extraction of business entities
- Generation of structured JSON for automated systems
- Detailed visual interpretation of photographic and medical images
- Extraction of critical visual features and contextual information"""

            user_prompt = f"""Context: text surrounding the image:
"{surrounding_text}"

Comprehensive technical image analysis. Goal: generate a structured, actionable JSON.

KEY INSTRUCTIONS:
1. Precise Identification
   - Exact document type
   - Technical domain
   - Complexity level

2. Structural Analysis
   - Main components
   - Relationships and interactions
   - Scales and proportions
   - Represented technologies
   - Technical annotations

3. Technical Interpretation
   - Practical implications
   - Design assumptions
   - Potential technical challenges
   - Remarkable innovations

4. Rigorous Extraction
   - All numerical values
   - Technical labels
   - Significant annotations
   - Strict unit adherence

5. Comparative Analysis
   - Comparison to standards
   - Deviations from common practices
   - Technical compliance

6. MANDATORY JSON Rendering
   Structure:
   - `type`: Precise type
   - `domain`: Technical domain
   - `complexity`: Level
   - `data`: Technical data
   - `metadata`: Additional information
   - `insights`: Technical observations

FINAL GUIDELINES:
- PERFECT and USABLE JSON
- No superfluous text
- RESPONSE IN JSON FORMAT ONLY

Technical language, no unnecessary jargon.

- Visual hierarchy and logical structure: sections, blocks, groupings
- Implicit tabular representation: visual tables, alignments, columns or grids
You are working for a team of specialized engineers. Your analysis will serve technical decision-making, so it must be reliable, concise, and directly usable.
The JSON will be used in an automated system. Each field must be simple, stable, reusable without reprocessing. No free text, except in `insights`.
All units must be explicit, separated, and homogeneous. For units, use a format like: "length": {{"value": 5, "unit": "m"}}. Avoid concatenating units in values.
If specific business entities appear (e.g., references, part numbers, unique identifiers), extract them in a normalized form.
ADDITIONAL GUIDELINES:

- The JSON will be used in a business API, it must be formal, homogeneous, without parasitic text.
- Each value must be normalized. Units must be explicit, separated from values.
- Extract any visual or logical hierarchy detected (titles, groupings, legends, tables).
- If specific business entities appear (codes, components, references), include them in `data` or `metadata`.
- NO COMMENTS OUTSIDE JSON."""

        # Préparer les messages pour l'API
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        }
                    }
                ]
            }
        ]

        # Préparer la requête API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1000  # Augmenter le nombre de tokens pour permettre des réponses plus détaillées
        }

        try:
            console.print(f"[dim]Envoi de la requête à l'API OpenAI ({self.api_url})...[/dim]")
            
            # Ajouter un log de la taille totale de la payload
            payload_size = len(str(payload)) / 1024  # Taille approximative en KB
            console.print(f"[dim]Taille de la payload: environ {payload_size:.2f} KB[/dim]")
            
            # Ajouter un log de vérification des premiers caractères de la clé API (masqués)
            api_key_prefix = self.api_key[:4] + "..." if self.api_key else "None"
            api_key_length = len(self.api_key) if self.api_key else 0
            console.print(f"[dim]Utilisation de la clé API: {api_key_prefix} (longueur: {api_key_length})[/dim]")
            
            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            end_time = time.time()
            
            duration = end_time - start_time
            console.print(f"[dim]Requête API terminée en {duration:.2f} secondes[/dim]")
            
            if response.status_code == 200:
                result = response.json()
                description = result["choices"][0]["message"]["content"]
                console.print(f"[green]Succès: Description obtenue ({len(description)} caractères)[/green]")
                
                # Valider que la réponse est bien au format JSON
                try:
                    # Pour gérer les cas où il y aurait du texte avant ou après le JSON
                    import json
                    import re
                    
                    # Essayer d'extraire un JSON valide de la réponse
                    json_match = re.search(r'(\{.*\})', description, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        # Valider que c'est un JSON valide
                        json_obj = json.loads(json_str)
                        # Si valide, retourner seulement la partie JSON
                        return json_str
                    
                    # Si aucun JSON n'a été trouvé ou n'est valide, retourner la réponse brute
                    return description
                except Exception as e:
                    console.print(f"[yellow]Avertissement: La réponse n'est pas un JSON valide. Utilisation du texte brut.[/yellow]")
                    console.print(f"[dim]Erreur de parsing JSON: {str(e)}[/dim]")
                    # Retourner le texte brut plutôt qu'une erreur
                    return f"Analyse textuelle (JSON invalide) : {description[:500]}..."
                
            else:
                console.print(f"[bold red]Erreur API OpenAI: Code {response.status_code}[/bold red]")
                console.print(f"[red]Détails: {response.text}[/red]")
                
                # Codes d'erreur spécifiques
                if response.status_code == 401:
                    console.print("[bold red]Authentification échouée: Vérifiez votre clé API OpenAI[/bold red]")
                elif response.status_code == 429:
                    console.print("[bold red]Rate limit dépassé: Attendez avant de réessayer[/bold red]")
                elif response.status_code == 400:
                    console.print("[bold red]Requête invalide: Vérifiez le format de l'image ou la taille des données[/bold red]")
                
                return None
        except requests.exceptions.Timeout:
            console.print(f"[bold red]Timeout: L'API n'a pas répondu dans les {self.timeout} secondes[/bold red]")
            return None
        except requests.exceptions.ConnectionError:
            console.print("[bold red]Erreur de connexion: Impossible de se connecter à l'API OpenAI[/bold red]")
            return None
        except ValueError as e:
            console.print(f"[bold red]Erreur de formatage: {str(e)}[/bold red]")
            return f"Erreur de formatage: {str(e)}"
        except Exception as e:
            console.print(f"[bold red]Erreur lors de l'appel à l'API OpenAI: {e}[/bold red]")
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
            return None

    def save_image_to_file(self, image_data, output_dir, filename):
        """
        Sauvegarde une image en tant que fichier PNG.
        
        Args:
            image_data: Données binaires de l'image
            output_dir: Répertoire de sortie
            filename: Nom de fichier
            
        Returns:
            Chemin complet du fichier sauvegardé
        """
        # Créer le répertoire s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)
        
        # Chemin complet du fichier
        file_path = os.path.join(output_dir, filename)
        
        # Écrire l'image
        with open(file_path, "wb") as f:
            f.write(image_data)
        
        return file_path

    def describe_images_in_pdf(self, pdf_path: str, output_dir: str = None) -> dict:
        """
        Extrait et décrit toutes les images d'un document PDF.
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            output_dir: Répertoire de sortie pour les résultats et images
            
        Returns:
            Dictionnaire contenant les informations sur les images et leurs descriptions
        """
        # Générer un ID unique basé sur le nom du fichier et l'horodatage
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
            "nb_images_detectees": 0,
            "nb_images_analysees": 0,
            "images": [],
            "meta": {
                "filename": os.path.basename(pdf_path),
                "language": self.language,
                "model": self.model,
                "timestamp": timestamp,
                "result_id": result_id,
                "output_dir": output_dir
            }
        }
        
        try:
            console.print(f"\n[bold green]Analyse du document[/bold green]: {pdf_path}")
            
            # Vérifier si le fichier existe
            if not os.path.exists(pdf_path):
                console.print(f"[bold red]Erreur[/bold red]: Le fichier {pdf_path} n'existe pas.")
                return result
            
            # Ouvrir le document PDF
            doc = fitz.open(pdf_path)
            console.print(f"[bold]Document ouvert avec succès[/bold]: {len(doc)} pages")
            
            # Compteur d'images
            processed_images = 0
            
            # Parcourir chaque page
            for page_num, page in enumerate(doc):
                console.print(f"\n[bold]Analyse de la page[/bold] {page_num+1}/{len(doc)}...")
                
                # Utiliser get_images() qui fonctionne mieux pour détecter les images
                image_list = page.get_images()
                
                if not image_list:
                    console.print(f"  [yellow]Aucune image détectée sur la page {page_num+1}[/yellow]")
                    continue
                
                console.print(f"  [green]{len(image_list)} image(s) détectée(s) sur la page {page_num+1}[/green]")
                result["nb_images_detectees"] += len(image_list)
                
                # Traiter chaque image
                for img_idx, img in enumerate(image_list):
                    
                    # Vérifier si on a atteint le nombre maximum d'images à traiter
                    if processed_images >= self.max_images:
                        console.print(f"[yellow]Nombre maximum d'images atteint ({self.max_images}). Arrêt du traitement.[/yellow]")
                        break
                    
                    console.print(f"  [bold]Traitement de l'image {img_idx+1}/{len(image_list)}[/bold]")
                    
                    try:
                        # Récupérer l'image
                        xref = img[0]  # Référence xref de l'image
                        
                        # Extraire l'image avec la matrice de transformation
                        pix = fitz.Pixmap(doc, xref)
                        
                        # Obtenir les dimensions de l'image
                        width, height = img[2], img[3]
                        
                        # Rechercher la position de l'image sur la page
                        # Note: Ceci est approximatif car get_images() ne fournit pas directement la position
                        # On utilise les informations des blocs pour trouver une correspondance approximative
                        img_bbox = None
                        for item in page.get_text("dict")["blocks"]:
                            if item.get("type") == 1 and item.get("width") == width and item.get("height") == height:
                                img_bbox = item["bbox"]
                                break
                        
                        # Si on n'a pas trouvé de position exacte, utiliser les dimensions de la page
                        if not img_bbox:
                            img_bbox = [0, 0, page.rect.width, page.rect.height]
                        
                        # Extraire le texte environnant
                        surrounding_text = self._get_surrounding_text(page, img_bbox)
                        console.print(f"  [dim]Extraction du texte environnant: {len(surrounding_text)} caractères[/dim]")
                        
                        # Convertir l'image en PNG
                        img_bytes = pix.tobytes("png")
                        
                        # Sauvegarder l'image en tant que fichier PNG si demandé
                        image_file_path = None
                        if self.save_images:
                            image_filename = f"{result_id}_image_p{page_num+1}_i{img_idx+1}.png"
                            image_file_path = self.save_image_to_file(img_bytes, output_dir, image_filename)
                            console.print(f"  [green]Image sauvegardée: {image_filename}[/green]")
                        
                        # Encoder l'image en base64
                        img_b64 = self._encode_image(img_bytes)
                        console.print(f"  [dim]Image encodée en base64: {len(img_b64)} caractères[/dim]")
                        
                        # Obtenir la description de l'image
                        console.print(f"  [bold]Envoi de l'image à l'API d'analyse d'image...[/bold]")
                        description = self._get_image_description(img_b64, surrounding_text)
                        
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
                            "width": width,
                            "height": height,
                            "position": img_bbox,
                            "xref": xref,
                            "description_ai": description,
                            "surrounding_text": surrounding_text,
                            "file_path": image_file_path,
                            "image_b64": None  # On ne stocke pas les images en base64 dans le JSON final
                        }
                        
                        result["images"].append(image_info)
                        processed_images += 1
                        
                    except Exception as e:
                        console.print(f"  [red]Erreur lors du traitement de l'image {img_idx+1}: {str(e)}[/red]")
                        continue
            
            # Fermer le document
            doc.close()
            
            # Sauvegarder le résultat
            result_json_path = os.path.join(output_dir, f"{result_id}_images_described.json")
            with open(result_json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # Créer un rapport lisible
            report_path = os.path.join(output_dir, f"{result_id}_report.md")
            self._create_human_readable_report(result, report_path)
            
            console.print(f"\nAnalyse terminée: {result['nb_images_analysees']}/{result['nb_images_detectees']} images analysées")
            console.print(f"Résultats sauvegardés dans: \n{result_json_path}")
            console.print(f"Rapport lisible créé dans: \n{report_path}")
            
            return result
            
        except Exception as e:
            console.print(f"[bold red]Erreur lors de l'analyse du document: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
            return result
            
    def _create_human_readable_report(self, result: dict, output_path: str):
        """
        Crée un rapport lisible pour les humains.
        
        Args:
            result: Résultat de l'analyse
            output_path: Chemin du fichier de sortie
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Rapport d'analyse des images du PDF\n\n")
                f.write(f"Fichier: {result['meta']['filename']}\n")
                f.write(f"Date d'analyse: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['meta']['timestamp']/1000))}\n")
                f.write(f"Langue: {result['meta']['language']}\n")
                f.write(f"Modèle utilisé: {result['meta']['model']}\n\n")
                f.write(f"Images détectées: {result['nb_images_detectees']}\n")
                f.write(f"Images analysées: {result['nb_images_analysees']}\n\n")
                
                for i, img in enumerate(result['images']):
                    f.write(f"## Image {i+1} - Page {img['page']} (index {img['index']})\n\n")
                    f.write(f"Dimensions: {img['width']}x{img['height']}\n")
                    f.write(f"Position: {img['position']}\n")
                    
                    if img.get('file_path'):
                        rel_path = os.path.relpath(img['file_path'], os.path.dirname(output_path))
                        f.write(f"Fichier: {rel_path}\n\n")
                    
                    f.write(f"### Texte environnant\n\n")
                    f.write(f"{img['surrounding_text']}\n\n")
                    
                    f.write(f"### Description par IA\n\n")
                    f.write(f"{img['description_ai']}\n\n")
                    
                    f.write("---\n\n")
                
                f.write(f"Fin du rapport\n")
                
            return output_path
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du rapport: {e}")
            return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extraire et décrire les images d'un document PDF")
    parser.add_argument("pdf_path", help="Chemin vers le fichier PDF")
    parser.add_argument("--max-images", type=int, default=10, help="Nombre maximum d'images à traiter")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout pour l'appel API (secondes)")
    parser.add_argument("--language", choices=["fr", "en"], default="fr", help="Langue de description")
    parser.add_argument("--output", help="Chemin du répertoire de sortie")
    parser.add_argument("--no-save-images", action="store_true", help="Ne pas sauvegarder les images en fichiers PNG")
    args = parser.parse_args()
    
    # Charger les variables d'environnement
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("VISION_LLM_MODEL") or "gpt-4o"
    
    # Si la clé API n'est pas définie, afficher un message et quitter
    if not api_key:
        print("Erreur: Clé API OpenAI non définie. Définissez la variable d'environnement OPENAI_API_KEY.")
        exit(1)
    
    # Créer l'objet PDFImageDescriber
    describer = PDFImageDescriber(
        openai_api_key=api_key,
        max_images=args.max_images,
        timeout=args.timeout,
        language=args.language,
        model=model,
        save_images=not args.no_save_images,
    )
    
    # Décrire les images
    result = describer.describe_images_in_pdf(args.pdf_path, args.output)
    
    # Afficher un résumé
    print("\nRésumé de l'analyse:")
    print(f"  Fichier: {result['meta']['filename']}")
    print(f"  Images détectées: {result['nb_images_detectees']}")
    print(f"  Images analysées: {result['nb_images_analysees']}")
    print(f"  Résultats sauvegardés dans: {result['meta']['output_dir']}") 