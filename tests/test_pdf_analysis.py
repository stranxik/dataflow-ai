#!/usr/bin/env python3
"""
Script de diagnostic pour l'extraction d'images dans un PDF
"""

import fitz
import os
import base64
from pprint import pprint

def analyze_pdf(pdf_path):
    print(f"{'='*20} ANALYSE PDF {'='*20}")
    print(f"Fichier: {os.path.abspath(pdf_path)}")
    
    # Vérification du fichier
    if not os.path.exists(pdf_path):
        print(f"ERREUR: Fichier {pdf_path} introuvable")
        return
    
    # Ouvrir le document
    try:
        doc = fitz.open(pdf_path)
        print(f"Document ouvert avec succès: {len(doc)} pages")
    except Exception as e:
        print(f"ERREUR lors de l'ouverture du document: {e}")
        return
    
    # Analyser les pages et blocs
    print("\n----- STRUCTURE DÉTAILLÉE -----")
    total_images_found = 0
    
    for page_num, page in enumerate(doc):
        print(f"\nPAGE {page_num+1}:")
        print(f"  Dimensions: {page.rect.width}x{page.rect.height}")
        
        # 1. Méthode dict
        print("\n  1. Analyse avec get_text('dict'):")
        try:
            blocks = page.get_text("dict")["blocks"]
            print(f"    Nombre total de blocs: {len(blocks)}")
            
            # Analyse par type de bloc
            block_types = {}
            for i, block in enumerate(blocks):
                block_type = block.get("type", "inconnu")
                if block_type not in block_types:
                    block_types[block_type] = []
                block_types[block_type].append(i)
            
            # Afficher le résumé des types
            for btype, indices in block_types.items():
                type_name = "IMAGE" if btype == 1 else "TEXTE" if btype == 0 else f"TYPE-{btype}"
                print(f"    - {type_name}: {len(indices)} bloc(s)")
            
            # Détail des blocs d'images
            if 1 in block_types:
                print("\n    Détail des blocs images:")
                for i, block_idx in enumerate(block_types[1]):
                    block = blocks[block_idx]
                    print(f"    - Image {i+1}:")
                    print(f"      Position: {block.get('bbox')}")
                    print(f"      xref: {block.get('image', 'non spécifié')}")
                    print(f"      Taille: {block.get('width', '?')}x{block.get('height', '?')}")
                    
                    # Essayer d'extraire cette image
                    try:
                        xref = block.get('image')
                        if xref:
                            pix = fitz.Pixmap(doc, xref)
                            img_bytes = pix.tobytes("png")
                            print(f"      ✅ Image extraite avec succès: {len(img_bytes)} octets")
                            total_images_found += 1
                        else:
                            print("      ❌ Pas de référence xref pour l'image")
                    except Exception as e:
                        print(f"      ❌ Erreur extraction: {e}")
        except Exception as e:
            print(f"    ERREUR: {e}")
        
        # 2. Méthode get_images()
        print("\n  2. Analyse avec get_images():")
        try:
            image_list = page.get_images()
            print(f"    Nombre d'images trouvées: {len(image_list)}")
            
            for i, img in enumerate(image_list):
                print(f"    - Image {i+1}:")
                print(f"      xref: {img[0]}")
                print(f"      Dimensions: {img[2]}x{img[3]}")
                
                # Essayer d'extraire cette image
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    img_bytes = pix.tobytes("png")
                    print(f"      ✅ Image extraite avec succès: {len(img_bytes)} octets")
                    total_images_found += 1
                except Exception as e:
                    print(f"      ❌ Erreur extraction: {e}")
        except Exception as e:
            print(f"    ERREUR: {e}")
        
        # 3. Méthode getImageList (obsolète mais parfois utile)
        print("\n  3. Analyse avec getImageList():")
        try:
            # Cette méthode est obsolète mais peut fonctionner dans certains cas
            image_list = page.getImageList()
            print(f"    Nombre d'images trouvées: {len(image_list)}")
        except Exception as e:
            print(f"    ERREUR (probablement méthode obsolète): {e}")
    
    # Résumé final
    print(f"\n{'='*20} RÉSULTAT {'='*20}")
    print(f"Total images trouvées et extractibles: {total_images_found}")
    
    if total_images_found == 0:
        print("\nDIAGNOSTIC POSSIBLE:")
        print("1. Le PDF ne contient pas d'images réelles (peut contenir des graphiques vectoriels)")
        print("2. Les images sont incorporées d'une manière non standard")
        print("3. Les images sont protégées ou chiffrées")
        print("4. Le PDF utilise un format complexe que PyMuPDF ne peut pas extraire")
        print("\nSOLUTIONS POTENTIELLES:")
        print("1. Utiliser une approche de rasterisation de page complète au lieu de l'extraction d'images")
        print("2. Essayer d'autres bibliothèques comme pdf2image ou Poppler")

# Exécuter le script
if __name__ == "__main__":
    # Chemin vers le PDF à analyser
    pdf_path = "files/1744005520250-10-11.pdf"
    analyze_pdf(pdf_path) 