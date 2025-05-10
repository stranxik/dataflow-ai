# Complete PDF Extractor - English Documentation

## 📑 Table of Contents

- [Introduction](#-introduction)
- [Features](#-features)
- [Targeted Extraction](#-targeted-extraction)
- [Usage](#-usage)
- [Examples](#-examples)
- [Output Structure](#-output-structure)
- [Advanced Options](#-advanced-options)
- [Troubleshooting](#-troubleshooting)

## 🔍 Introduction

The Complete PDF Extractor is a specialized module designed to intelligently extract and analyze PDF document content. Unlike traditional PDF extractors, this module:

1. **Natively extracts** raw text from PDF, preserving its original structure
2. **Detects and extracts** only the embedded images in the document
3. **Analyzes with AI** exclusively the images for enriched understanding
4. **Generates a unified JSON** combining the extracted text and image analyses

This targeted approach avoids transforming all pages into images, preserving the quality of native text while enabling enhanced AI understanding of visual elements.

## 🎯 Features

- **Native text extraction** with PyMuPDF (fitz)
- **Targeted detection and extraction of embedded images**
- **Image analysis via multimodal models** (OpenAI GPT-4o)
- **Retrieval of surrounding text** for image contextualization
- **Unified JSON** combining text and image analyses
- **Structured reconstruction** of each page with its elements
- **Preservation of extracted images** in PNG for reference
- **Integrated CLI interface** for easy use

## 🔍 Targeted Extraction

The extraction approach takes place in several precise steps:

### 1. Native Text Processing
- Use of `page.get_text()` to extract raw text faithful to the PDF
- Structure preservation with `page.get_text("dict")` which provides information about blocks and layout

### 2. Detection and Extraction of Embedded Images
- Exclusive extraction of embedded images with `page.get_images(full=True)`
- Retrieval of image binary data with `fitz.Pixmap(doc, xref)`
- Identification of image coordinates on the page

### 3. AI Analysis of Images Only
- Semantic analysis of images via OpenAI API (GPT-4o or other multimodal model)
- Contextualization with surrounding text extracted around each image
- Detailed description including image type, content, and significance

### 4. Generation of a Unified JSON
- Structured assembly containing both text and images
- Organization by page with text and image type elements
- Preservation of links to extracted images
- Inclusion of AI analyses for each image

## 🛠 Usage

### Via Interactive CLI

```bash
# General interactive mode
python -m cli.cli interactive
# Then select "Complete PDF extraction (text + analyzed images)"

# OR direct command
python -m cli.cli extract-images complete path/to/file.pdf
```

### Main Options
```bash
python -m cli.cli extract-images complete file.pdf [OPTIONS]

Options:
  --max-images INTEGER        Maximum number of images to process (default: 10)
  --timeout INTEGER           Timeout for API call (default: 30 seconds)
  --language [fr|en]          Language for descriptions (default: en)
  --output PATH               Custom output directory
  --no-save-images            Don't save extracted images
  --help                      Show help
```

### Programmatic Usage
```python
from extract.pdf_complete_extractor import PDFCompleteExtractor

# Initialize the extractor
extractor = PDFCompleteExtractor(
    openai_api_key="your_api_key",  # Optional if defined in .env
    max_images=5,                   # Limit number of images to process
    language="en",                  # Language for descriptions
    save_images=True                # Save extracted images
)

# Process a PDF
result = extractor.process_pdf("path/to/file.pdf", "output_directory")

# Access data
print(f"Extracted pages: {len(result['pages'])}")
print(f"Detected images: {result['nb_images_detectees']}")
print(f"Analyzed images: {result['nb_images_analysees']}")
```

## 📋 Examples

### Complete Command Example
```bash
python -m cli.cli extract-images complete technical_report.pdf --max-images 20 --language en --output report_results
```

### Extraction with Result Compression
```bash
# Extraction with result compression
python -m cli.cli extract-images complete document.pdf --compress --compress-level 19 --keep-originals
```

## 📊 Output Structure

For each processed PDF, you will get:

### Generated Files
```
results/pdf_name_timestamp/
├── pdf_name_timestamp_complete.json     # Complete detailed results
├── pdf_name_timestamp_unified.json      # Unified JSON text + images
├── pdf_name_timestamp_image_p1_i1.png   # Extracted image 1 from page 1
├── pdf_name_timestamp_image_p2_i1.png   # Extracted image 1 from page 2
└── ...
```

### Unified JSON Structure
```json
{
  "meta": {
    "filename": "document.pdf",
    "timestamp": 1234567890123,
    "language": "en",
    "model": "gpt-4o"
  },
  "pages": [
    {
      "page_number": 1,
      "text": "Complete text of the page...",
      "elements": [
        {
          "type": "text",
          "position": [x1, y1, x2, y2],
          "content": "Text block content"
        },
        {
          "type": "image",
          "position": [x1, y1, x2, y2],
          "width": 800,
          "height": 600,
          "file_path": "image_name.png",
          "description_ai": "Detailed description generated by AI...",
          "surrounding_text": "Text surrounding the image..."
        }
      ]
    },
    // Other pages...
  ],
  "stats": {
    "pages_count": 10,
    "images_detected": 15,
    "images_analyzed": 10
  }
}
```

## ⚙️ Advanced Options

### Vision Model Configuration

By default, the system uses the model defined in the `VISION_LLM_MODEL` environment variable (or `gpt-4o` if not defined). You can specify a different model:

```bash
# In .env
VISION_LLM_MODEL=gpt-4-vision-preview

# Or via CLI
python -m cli.cli extract-images complete file.pdf --model gpt-4-vision-preview
```

### Custom Prompts

The prompts sent to the API for image analysis are adapted according to language:

- **English**: Adapted for detailed description in English
- **French**: Optimized to extract relevant information in French

These prompts can be modified in the source code (`image_describer.py`) for specific needs.

### Surrounding Text Extraction

The surrounding text extraction algorithm uses a distance calculation method to find the text blocks closest to each image:

1. Identification of image coordinates on the page
2. Calculation of distance between the center of the image and each text block
3. Sorting blocks by proximity and assembly until reaching the character limit (500 by default)

This provides the AI model with relevant context for each image.

## 🔧 Troubleshooting

### The Module Doesn't Detect Images
- Check that the PDF actually contains embedded images (not vector renderings)
- Pure vector images may not be detected as images

### OpenAI API Errors
- Check your API key in the `.env` file (`OPENAI_API_KEY` variable)
- Ensure you have sufficient balance for API calls
- Increase timeout if needed with `--timeout 60`

### Memory Issues
- Limit the number of processed images with `--max-images`
- Process reasonably sized PDFs (less than 100 MB)

### Possible Improvements
- For very large documents, consider processing the PDF page by page
- For greater accuracy, you can adjust the image analysis prompt in the code 