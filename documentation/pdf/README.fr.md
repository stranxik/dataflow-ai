# Extracteur PDF Complet - Documentation Française

## 📑 Sommaire

- [Introduction](#-introduction)
- [Fonctionnalités](#-fonctionnalités)
- [Extraction ciblée](#-extraction-ciblée)
- [Utilisation](#-utilisation)
- [Exemples](#-exemples)
- [Structure de sortie](#-structure-de-sortie)
- [Options avancées](#-options-avancées)
- [Guide de dépannage](#-guide-de-dépannage)

## 🔍 Introduction

L'Extracteur PDF Complet est un module spécialisé conçu pour extraire et analyser intelligemment le contenu des documents PDF. Contrairement aux extracteurs PDF traditionnels, ce module:

1. **Extrait nativement** le texte brut du PDF, préservant sa structure originale
2. **Détecte et extrait** uniquement les images intégrées dans le document
3. **Analyse avec IA** exclusivement les images pour une compréhension enrichie 
4. **Génère un JSON unifié** combinant le texte extrait et les analyses d'images

Cette approche ciblée évite de transformer toutes les pages en images, ce qui préserve la qualité du texte natif tout en permettant une compréhension améliorée par IA des éléments visuels.

## 🎯 Fonctionnalités

- **Extraction native du texte** avec PyMuPDF (fitz)
- **Détection et extraction ciblée des images** intégrées
- **Analyse des images via modèles multimodaux** (OpenAI GPT-4.1)
- **Récupération du texte environnant** les images pour contextualisation
- **JSON unifié** combinant texte et analyses d'images
- **Reconstruction structurée** de chaque page avec ses éléments
- **Conservation des images extraites** en PNG pour référence
- **Interface CLI** intégrée pour une utilisation facile

## 🔍 Extraction ciblée

L'approche d'extraction se déroule en plusieurs étapes précises:

### 1. Traitement du texte natif
- Utilisation de `page.get_text()` pour extraire le texte brut fidèle au PDF
- Conservation de la structure avec `page.get_text("dict")` qui fournit des informations sur les blocs et la mise en page

### 2. Détection et extraction des images intégrées
- Extraction exclusive des images intégrées avec `page.get_images(full=True)`
- Récupération des données binaires de l'image avec `fitz.Pixmap(doc, xref)`
- Identification des coordonnées de l'image sur la page

### 3. Analyse IA des images uniquement
- Analyse sémantique des images via l'API OpenAI (GPT-4.1)
- Contextualisation avec le texte environnant extrait autour de chaque image
- Description détaillée incluant le type d'image, son contenu et sa signification

### 4. Génération d'un JSON unifié
- Assemblage structuré contenant à la fois le texte et les images
- Organisation par page avec éléments de type texte et image
- Conservation des liens vers les images extraites
- Inclusion des analyses IA pour chaque image

## 🛠 Utilisation

### Via CLI interactif

```bash
# Mode interactif général
python -m cli.cli interactive
# Puis sélectionner "Extraction complète d'un PDF (texte + images analysées)"

# OU commande directe
python -m cli.cli extract-images complete chemin/vers/fichier.pdf
```

### Options principales
```bash
python -m cli.cli extract-images complete fichier.pdf [OPTIONS]

Options:
  --max-images INTEGER        Nombre maximum d'images à traiter (défaut: 10)
  --timeout INTEGER           Timeout pour l'appel API (défaut: 30 secondes)
  --language [fr|en]          Langue des descriptions (défaut: fr)
  --output PATH               Répertoire de sortie personnalisé
  --no-save-images            Ne pas sauvegarder les images extraites
  --help                      Afficher l'aide
```

### Utilisation programmatique
```python
from extract.pdf_complete_extractor import PDFCompleteExtractor

# Initialiser l'extracteur
extractor = PDFCompleteExtractor(
    openai_api_key="votre_clé_api",  # Facultatif si définie dans .env
    max_images=5,                    # Limiter le nombre d'images à traiter
    language="fr",                   # Langue des descriptions
    save_images=True                 # Sauvegarder les images extraites
)

# Traiter un PDF
result = extractor.process_pdf("chemin/vers/fichier.pdf", "dossier_sortie")

# Accéder aux données
print(f"Pages extraites: {len(result['pages'])}")
print(f"Images détectées: {result['nb_images_detectees']}")
print(f"Images analysées: {result['nb_images_analysees']}")
```

## 📋 Exemples

### Exemple de commande complète
```bash
python -m cli.cli extract-images complete rapport_technique.pdf --max-images 20 --language fr --output resultats_rapport
```

### Extraction avec compression des résultats
```bash
# Extraction avec compression des résultats
python -m cli.cli extract-images complete document.pdf --compress --compress-level 19 --keep-originals
```

## 📊 Structure de sortie

Pour chaque PDF traité, vous obtiendrez:

### Fichiers générés
```
results/nom_pdf_timestamp/
├── nom_pdf_timestamp_complete.json     # Résultats détaillés complets
├── nom_pdf_timestamp_unified.json      # JSON unifié texte + images
├── nom_pdf_timestamp_image_p1_i1.png   # Image 1 de la page 1 extraite
├── nom_pdf_timestamp_image_p2_i1.png   # Image 1 de la page 2 extraite
└── ...
```

### Structure du JSON unifié
```json
{
  "meta": {
    "filename": "document.pdf",
    "timestamp": 1234567890123,
    "language": "fr",
    "model": "gpt-4.1"
  },
  "pages": [
    {
      "page_number": 1,
      "text": "Texte complet de la page...",
      "elements": [
        {
          "type": "text",
          "position": [x1, y1, x2, y2],
          "content": "Contenu du bloc de texte"
        },
        {
          "type": "image",
          "position": [x1, y1, x2, y2],
          "width": 800,
          "height": 600,
          "file_path": "nom_image.png",
          "description_ai": "Description détaillée générée par l'IA...",
          "surrounding_text": "Texte environnant l'image..."
        }
      ]
    },
    // Autres pages...
  ],
  "stats": {
    "pages_count": 10,
    "images_detected": 15,
    "images_analyzed": 10
  }
}
```

## ⚙️ Options avancées

### Configuration du modèle Vision

Par défaut, le système utilise le modèle défini dans la variable d'environnement `VISION_LLM_MODEL` (ou `gpt-4.1` si non défini). Vous pouvez spécifier un modèle différent:

```bash
# Dans .env
VISION_LLM_MODEL=gpt-4.1

# Ou via CLI
python -m cli.cli extract-images complete fichier.pdf --model gpt-4.1
```

### Prompts personnalisés

Les prompts envoyés à l'API pour l'analyse des images sont adaptés en fonction de la langue:

- **Français**: Optimisé pour extraire les informations pertinentes en français
- **Anglais**: Adapté pour une description détaillée en anglais

Ces prompts peuvent être modifiés dans le code source (`image_describer.py`) pour des besoins spécifiques.

### Extraction du texte environnant

L'algorithme d'extraction du texte environnant utilise une méthode de calcul de distance pour trouver les blocs de texte les plus proches de chaque image:

1. Identification des coordonnées de l'image sur la page
2. Calcul de la distance entre le centre de l'image et chaque bloc de texte
3. Tri des blocs par proximité et assemblage jusqu'à atteindre la limite de caractères (500 par défaut)

Ceci permet de fournir au modèle d'IA un contexte pertinent pour chaque image.

## 🔧 Guide de dépannage

### Le module ne détecte pas d'images
- Vérifiez que le PDF contient bien des images intégrées (et non des rendus vectoriels)
- Les images vectorielles pures peuvent ne pas être détectées comme images

### Erreurs d'API OpenAI
- Vérifiez votre clé API dans le fichier `.env` (variable `OPENAI_API_KEY`)
- Assurez-vous d'avoir un solde suffisant pour les appels API
- Augmentez le timeout si nécessaire avec `--timeout 60`

### Problèmes de mémoire
- Limitez le nombre d'images traitées avec `--max-images`
- Traitez des PDF de taille raisonnable (moins de 100 Mo)

### Améliorations possibles
- Pour les documents très volumineux, envisagez de traiter le PDF page par page
- Pour une plus grande précision, vous pouvez ajuster le prompt d'analyse d'image dans le code 