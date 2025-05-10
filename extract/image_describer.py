import fitz  # PyMuPDF
import base64
import io
import time
import requests
import os
from typing import List, Dict, Any, Optional

class PDFImageDescriber:
    def __init__(
        self,
        openai_api_key: str,
        max_images: int = 10,
        timeout: int = 30,
        language: str = "fr",
        model: str = None,
        api_url: str = "https://api.openai.com/v1/chat/completions",
    ):
        self.api_key = openai_api_key
        self.max_images = max_images
        self.timeout = timeout
        self.language = language
        # Utiliser la variable d'environnement si model n'est pas fourni
        self.model = model or os.environ.get("VISION_LLM_MODEL", "gpt-4-vision-preview")
        self.api_url = api_url

    def describe_images_in_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Parcourt le PDF, extrait les images, récupère le contexte textuel, appelle GPT-4 Vision,
        et retourne une liste de dicts avec description_ai, image_b64, context_text, page, position, etc.
        """
        doc = fitz.open(pdf_path)
        results = []
        image_count = 0
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            # Indexer les blocs texte pour le contexte
            text_blocks = [b for b in blocks if b["type"] == 0]
            image_blocks = [b for b in blocks if b["type"] == 1]
            for img_block in image_blocks:
                if image_count >= self.max_images:
                    break
                # Extraire l'image
                bbox = img_block["bbox"]
                img = self._extract_image_from_block(page, img_block)
                if img is None:
                    continue
                image_b64 = self._image_to_base64(img)
                # Trouver le texte le plus proche (avant/après ou spatialement)
                context_text = self._find_context_text(img_block, text_blocks)
                # Appel API OpenAI Vision
                description_ai = self._call_openai_vision(image_b64, context_text)
                results.append({
                    "page": page_num + 1,
                    "bbox": bbox,
                    "image_b64": image_b64,
                    "context_text": context_text,
                    "description_ai": description_ai,
                })
                image_count += 1
        return results

    def _extract_image_from_block(self, page, img_block) -> Optional[bytes]:
        # PyMuPDF: extraire l'image à partir du bloc
        try:
            xref = img_block.get("image")
            if xref is None:
                # fallback: chercher l'image la plus proche dans la page
                return None
            pix = fitz.Pixmap(page.parent, xref)
            if pix.n > 4:  # CMYK
                pix = fitz.Pixmap(fitz.csRGB, pix)
            img_bytes = pix.tobytes("png")
            return img_bytes
        except Exception as e:
            return None

    def _image_to_base64(self, img_bytes: bytes) -> str:
        return base64.b64encode(img_bytes).decode("utf-8")

    def _find_context_text(self, img_block, text_blocks) -> str:
        # Cherche les blocs texte spatialement proches (marge configurable)
        img_bbox = img_block["bbox"]
        margin = 50  # pixels
        context = []
        for tb in text_blocks:
            tb_bbox = tb["bbox"]
            # Si le bloc texte est proche de l'image (verticalement ou horizontalement)
            if (
                abs(tb_bbox[1] - img_bbox[1]) < margin or
                abs(tb_bbox[3] - img_bbox[3]) < margin or
                abs(tb_bbox[0] - img_bbox[0]) < margin or
                abs(tb_bbox[2] - img_bbox[2]) < margin
            ):
                context.append(tb.get("text", ""))
        return "\n".join(context).strip()

    def _call_openai_vision(self, image_b64: str, context_text: str) -> str:
        # Appelle l'API OpenAI Vision avec le prompt structuré
        prompt = self._build_prompt(context_text, image_b64)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": prompt,
            "max_tokens": 512,
        }
        try:
            resp = requests.post(self.api_url, json=data, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _build_prompt(self, context_text: str, image_b64: str) -> List[Dict[str, Any]]:
        # Prompt multilingue selon self.language
        if self.language == "fr":
            system_prompt = "Tu es un assistant intelligent spécialisé dans l'analyse documentaire et visuelle. Ton objectif est de décrire de manière précise, synthétique et utile toute image contenue dans un document PDF."
            user_text = f"Contexte : voici le texte situé autour de l'image dans le document :\n\"{context_text}\"\n\nAnalyse l'image suivante et réponds aux points suivants :\n1. Quel est le type d'image ? (graphique, diagramme, scan de texte, photo, tableau, illustration, etc.)\n2. Que contient-elle précisément ?\n3. Quelle est son utilité potentielle dans un document ?"
        else:
            system_prompt = "You are an intelligent assistant specialized in document and visual analysis. Your goal is to describe precisely, concisely, and usefully any image found in a PDF document."
            user_text = f"Context: here is the text located around the image in the document:\n\"{context_text}\"\n\nAnalyze the following image and answer the following points:\n1. What type of image is it? (chart, diagram, text scan, photo, table, illustration, etc.)\n2. What does it contain precisely?\n3. What is its potential usefulness in a document?"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]}
        ]

# Exemple d'utilisation
# describer = PDFImageDescriber(openai_api_key="sk-...", max_images=5, timeout=30, language="fr")
# results = describer.describe_images_in_pdf("mon_fichier.pdf")
# for img in results:
#     print(img["description_ai"]) 