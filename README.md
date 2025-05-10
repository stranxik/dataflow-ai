# DataFlow AI – Intelligent Pipeline, Advanced CLI & Tools for Preparation, Transformation, Security, and Enrichment of JSON & PDF Data for AI and RAG

![Version](https://img.shields.io/badge/version-1.0-blue) ![Python](https://img.shields.io/badge/Python-3.8%2B-green) ![License](https://img.shields.io/badge/license-MIT-orange)

> 🌐 [Version française disponible ici](README.fr.md)
> 📚 **All documentation (EN/FR) is now centralized in the [`/documentation`](documentation/) folder.**
> You will find English and French guides for CLI, Extract, LLM, Outlines, and Security in their respective subfolders.

## 📑 Table of Contents

- [Introduction](#-introduction)
- [Overview](#-overview)
- [Quick Reference Guide](#-quick-reference-guide)
- [Main Features](#-main-features)
- [Installation](#️-installation)
- [Quick Start Guide](#-quick-start-guide)
- [Results Organization](#-results-organization)
- [Automatic LLM Summaries](#-automatic-llm-summaries)
- [Flexible and Generic Approach](#-flexible-and-generic-approach)
- [Robust Fallback System](#-robust-fallback-system)
- [Utilities](#️-utilities)
- [Extending the System](#-extending-the-system)
- [Integration with Temporal and Llamendex](#-integration-with-temporal-and-llamendex)
- [Llamendex Format](#-llamendex-format)
- [PDF Document Analysis](#-pdf-document-analysis)
- [Security](#-security)
- [Dependencies](#️-dependencies)
- [License](#-license)

## 🔍 Introduction

This project is a complete solution for processing, analyzing, and transforming JSON files from different sources (JIRA, Confluence, GitHub, etc.) in preparation for indexing in Llamendex or any other modern RAG system.

The uniqueness of this solution lies in its ability to **automatically adapt to any JSON structure** and ensure robust file processing, even in the presence of errors or inconsistencies. Unlike generic JSON processing tools, our solution combines:

- **Intelligent detection** of data structure
- **Preservation of source files** (never directly modified)
- **Semantic enrichment via LLM** with Outlines
- **Detailed reports** automatically generated
- **Automatic correction** of JSON syntax errors
- **Interactive and accessible CLI interface**

> 💡 **NEW!** Complete integration of security tools and sensitive data cleaning directly in the CLI interface and JSON processors.

### Why this solution?

In the development of RAG (Retrieval Augmented Generation) systems like Llamendex, quality data ingestion is crucial. Yet, we face several concrete challenges:

1. **Heterogeneity of sources**: Each system (JIRA, Confluence, GitHub) exports different JSON structures
2. **Malformed files**: Exports often contain syntactic or structural errors
3. **Large volumes**: Exports can reach several gigabytes, exceeding standard processing capabilities
4. **Loss of context**: Manual data enrichment is time-consuming and inconsistent
5. **Absence of correspondences**: Links between JIRA tickets and Confluence pages are often lost

Our solution addresses these challenges by proposing a complete and robust pipeline that:
- Automatically detects and repairs structural problems
- Standardizes data in an optimal format for RAG systems
- Enriches content using LLMs to improve semantic search
- Establishes correspondences between different data sources
- Automatically generates summaries and analyses to facilitate ingestion

Moreover, unlike generic ETL tools or tabular processing solutions like pandas, our solution is specifically designed to prepare rich textual data for RAG systems, with particular attention to context preservation and semantic enrichment.

## 🎯 Overview

The project consists of three main modules:
- **CLI**: Interactive and powerful command-line interface for all operations
- **Extract**: Flexible processing engine for data analysis and transformation
- **Tools**: Utilities to solve specific problems (cleaning, validation)

<!-- START QUICK REFERENCE SECTION -->
<div align="center">

## 📋 Quick Reference Guide

</div>

| Command | Description | Example |
|---------|-------------|---------|
| `interactive` | **Interactive mode** with guided assistant | `python -m cli.cli interactive` |
| `process` | **Process** a JSON file | `python -m cli.cli process file.json --llm` |
| `chunks` | **Split** a large file | `python -m cli.cli chunks large_file.json --items-per-file 500` |
| `match` | **Match** JIRA-Confluence | `python -m cli.cli match jira.json confluence.json` |
| `unified` | **Complete flow** processing | `python -m cli.cli unified jira1.json jira2.json --confluence conf1.json` |
| `clean` | **Clean** sensitive data | `python -m cli.cli clean file.json --recursive` |
| `compress` | **Compress & optimize** JSON files | `python -m cli.cli compress directory --level 19` |

<div align="center">

### 🛠️ Independent Tools

</div>

| Tool | Description | Example |
|-------|-------------|---------|
| `check_json.py` | **Check** JSON file validity | `python -m tools.check_json file.json` |
| `clean_sensitive_data.py` | **Clean** sensitive data | `python -m tools.clean_sensitive_data file.json` |
| `fix_paths.py` | **Repair** paths and files | `python -m tools.fix_paths --all --source-dir=files` |

<!-- END QUICK REFERENCE SECTION -->

## 🎯 Main Features

- **Automatic detection** of file type (JIRA, Confluence, GitHub)
- **Flexible transformation** via customizable mappings
- **Complete interactive mode** with guided assistant for all operations
- **Splitting and processing** of large files
- **Structured metadata extraction**
- **Establishing correspondences** between different sources
- **Structured extraction with Outlines** for schema-constrained generation
- **LLM enrichment** (OpenAI) for semantic analysis
- **Detailed trees** of the content of each processed file
- **Automatic organization** of results with unique timestamps
- **Automatically generated LLM summaries** for each processing
- **Robust error handling** with different fallback levels

## ⚙️ Installation

1. Clone this repository and access the folder
2. Create a `.env` file by copying `.env.example`
3. Install dependencies:

```bash
pip install -r requirements.txt
```

### ⚠️ Python Requirements for Outlines

**IMPORTANT**: Outlines 0.2.3 specifically requires **Python 3.12**. It is strongly recommended to create a dedicated virtual environment:

```bash
# Create a virtual environment with Python 3.12
python3.12 -m venv venv_outlines

# Activate the environment
source venv_outlines/bin/activate  # Linux/Mac
venv_outlines\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

More recent versions of Python (3.13+) are not compatible with Outlines 0.2.3, and LLM functionalities will not work correctly without this specific environment.

### Outlines Configuration (optional)

The system uses the [Outlines](https://github.com/dottxt/outlines) library (v0.2.3) for structured data extraction. Two modes of operation are available:

1. **Full mode**: With the Outlines library installed and an OpenAI API key
2. **Stub mode**: Degraded operation without Outlines or without an API key

The system automatically detects the available configuration and adapts accordingly. To verify your installation:

```bash
python -m tests.test_outlines_integration
```

## 📖 Quick Start Guide

<div class="command-box">

### 🔍 Interactive Mode (recommended)

Launch the complete assistant that guides you step by step:

```bash
python -m cli.cli interactive
```

</div>

<div class="command-box">

### 📄 Processing JSON Files

```bash
python -m cli.cli process my_file.json --output result.json
```

#### With LLM enrichment and source preservation

```bash
python -m cli.cli process my_file.json --llm --preserve-source
```

</div>

<div class="command-box">

### 🔪 Splitting Large Files

```bash
python -m cli.cli chunks my_large_file.json --output-dir chunks_folder --items-per-file 500
```

</div>

<div class="command-box">

### 🔗 Matching JIRA and Confluence

```bash
python -m cli.cli match jira_processed.json confluence_processed.json --output-dir match_results
```

</div>

<div class="command-box">

### 🚀 Complete Processing Flow

```bash
python -m cli.cli unified jira1.json jira2.json --confluence conf1.json conf2.json --output-dir complete_results
```

</div>

<div class="command-box">

### 🧹 Cleaning Sensitive Data

```bash
python -m cli.cli clean file.json --output clean_file.json
```

</div>

<div class="command-box">

### 📦 Compressing and Optimizing JSON Files

```bash
# Compress a specific directory of JSON files
python -m cli.cli compress results/my_data --level 19 --keep-originals

# Compression with unified processing
python -m cli.cli unified jira1.json --output-dir results_dir --compress
```

The compression system uses orjson and zstd to achieve significant space savings (up to 90%) while preserving data integrity.

</div>

## 📊 Results Organization

All results are organized in the `results/` folder with a clear structure:

```
results/
├── demo_test/                             # Example folder from our latest run
│   ├── jira/                               # Subfolder for JIRA files
│   │   ├── demo_NEXUS_jira_processed.json  # Processed JIRA file
│   ├── confluence/                         # Subfolder for Confluence files
│   ├── matches/                            # Subfolder for matches
│   ├── split_jira_files/                   # Split JIRA files
│   ├── split_confluence_files/             # Split Confluence files
│   ├── llm_ready/                          # Files ready for LLM
│   │   ├── enriched_jira.json              # JIRA enriched with LLM
│   │   ├── enriched_jira.json.zst          # Compressed version (if enabled)
│   │   ├── enriched_confluence.json        # Confluence enriched with LLM
│   │   ├── enriched_confluence.json.zst    # Compressed version (if enabled)
│   │   ├── jira_llm_enrichment_summary.md  # LLM summary for JIRA
│   │   └── confluence_llm_enrichment_summary.md # LLM summary for Confluence
│   ├── compression_report_en.txt           # Compression statistics (if enabled)
│   ├── global_arborescence.txt             # Global tree structure
│   └── ...
```

## 🧠 Automatic LLM Summaries

> 📝 **Advanced feature**: For each processing using an LLM, a summary report is automatically generated in Markdown format.

> 💡 **NEW!** Our `outlines_enricher.py` module now enriches each JSON element (JIRA tickets/Confluence pages) with advanced LLM analyses. For each element, it extracts textual content (title, description, comments), sends it to the OpenAI API (GPT-4-0125-preview), and retrieves a structured analysis containing: a concise summary (150 words max), 5-10 important keywords, identified entities (people, organizations, technical terms) and general sentiment. This data is added under the `analysis` key with the sub-fields `llm_summary`, `llm_keywords`, `llm_entities` and `llm_sentiment`. The module automatically adapts different JSON structures to ensure a correct `items` list before processing.

Example of a generated summary:

<details>
<summary>👉 See an example of an LLM summary (click to expand)</summary>

```markdown
# LLM Enrichment Summary

## General Information
- Analysis date: 2023-05-08 23:34:37
- Total number of elements analyzed: 42
- LLM model used: gpt-4

## Analysis
### Main extracted keywords
project, development, API, backend, user, interface, database

### Sentiment distribution
{'positive': 12, 'neutral': 25, 'negative': 5}

### Enrichment example
**Ticket**: NEXUS-123 - OAuth2 Authentication Implementation
**LLM Summary**: This ticket concerns the integration of the OAuth2 protocol to secure the API. The implementation includes client registration, token management, and scope handling. The team noted challenges with refresh token persistence but resolved these through a dedicated database table. Testing shows successful integration with the frontend application. Ready for review by the security team before final deployment to production.
**Keywords**: OAuth2, authentication, API security, tokens, client registration
**Entities**: John Smith (developer), Security Team, OAuth2 protocol, JWT
**Sentiment**: Positive
```

</details>

These summaries allow:
1. A quick overview of the processed content
2. Extraction of main themes and sentiments
3. Concrete examples of LLM enrichment
4. Optimal preparation for ingestion into Llamendex

## 🔍 Flexible and Generic Approach

The adopted approach allows processing any JSON structure, thanks to:

1. **Automatic structure detection**: Analysis of important fields
2. **Customizable mappers**: Adaptation to any format
3. **Chunk processing**: Efficient handling of large files
4. **Flexible transformation**: Adaptable output structure
5. **Source preservation**: Working only on copies

## 💡 Robust Fallback System

Our solution is designed to work in different environments, thanks to a multi-level fallback system:

| Level | Configuration | Features |
|--------|--------------|-----------------|
| **1** | Outlines + OpenAI | Complete structured extraction, automatic repair |
| **2** | Without OpenAI | Degraded Outlines mode, certain features disabled |
| **3** | Without Outlines | Use of internal stubs mimicking the Outlines API |
| **4** | Standard fallback | Standard JSON parser as a last resort |

This architecture ensures that the system remains operational even without internet connection or API key.

## 🔄 Robust JSON Processing

The system includes advanced JSON processing capabilities to handle malformed or invalid JSON files:

- **Robust parsing**: Multiple fallback mechanisms to handle malformed JSON files
- **Smart repair**: Ability to recover from common JSON format errors
- **LLM-assisted repair**: Optional use of LLM to fix complex structural issues
- **Progressive parsing**: Can process extremely large files by reading them in chunks
- **Fault tolerance**: The system continues processing even if some files have errors

In our latest tests, the system successfully processed the demo files with NEXUS project data that contained several formatting inconsistencies, without any manual intervention required.

## 🛠️ Utilities

The project includes practical tools in the `tools/` folder:

1. **check_json.py**: Check the validity of JSON files
   ```bash
   python -m tools.check_json path/to/file.json
   ```

2. **fix_paths.py**: Fix path problems and repair JSON files
   ```bash
   python -m tools.fix_paths --all --source-dir=files --target-dir=results/fixed
   ```

3. **clean_sensitive_data.py**: Clean sensitive data (API keys, emails, etc.)
   ```bash
   python -m tools.clean_sensitive_data file.json --output clean_file.json
   ```

4. **compress_utils.py**: Compress and optimize JSON files with zstd and orjson
   ```bash
   python -m extract.compress_utils --directory results/my_data --level 19
   ```

### Using Tools in the CLI

The tools are integrated into the main CLI and can be used interactively:

```bash
# Launch sensitive data cleaning via CLI
python -m cli.cli clean file.json --output clean_file.json

# Compress JSON files via CLI
python -m cli.cli compress results/my_data --level 19

# Use interactive mode
python -m cli.cli interactive
# Then select "Clean sensitive data (clean)" or "Compress and optimize JSON files"
```

### Programmatic Integration

The tools can also be imported and used directly in your code:

```python
# Check the validity of a JSON file
from tools import validate_file
is_valid, error_msg = validate_file("my_file.json")
if not is_valid:
    print(f"Error in file: {error_msg}")

# Clean sensitive data
from tools import clean_json_file
clean_json_file("file_with_api_keys.json", "secure_file.json")

# Fix duplicate paths
from tools import fix_duplicate_paths
fix_duplicate_paths("results_folder")
```

The main processing via `GenericJsonProcessor` automatically integrates these tools to check the validity of JSON files and clean sensitive data before saving.

## 🧩 Extending the System

### Create Your Own Mappers

To adapt the solution to new sources:

```python
from extract.generic_json_processor import GenericJsonProcessor

def my_custom_mapper(item):
    # Transform the item according to your needs
    result = {
        "id": item.get("identifier", ""),
        "content": {
            "title": item.get("name", ""),
            "body": item.get("content", "")
        },
        "metadata": {
            "created_at": item.get("creation_date", ""),
            "type": item.get("type", "")
        }
    }
    return result

# Create the processor with your mapper
processor = GenericJsonProcessor(custom_mapper=my_custom_mapper)
processor.process_file("my_file.json", "result.json")
```

### Use Outlines for Structured Extraction

```python
from extract.outlines_enhanced_parser import outlines_robust_json_parser
from extract.outlines_extractor import extract_structured_data

# Parse a JSON file with Outlines
data = outlines_robust_json_parser("my_file.json", llm_fallback=True)

# Extract structured data according to a schema
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "categories": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}
result = extract_structured_data(text_content, schema)
```

## 🔄 Integration with Temporal and Llamendex

Our solution integrates perfectly with Temporal workflows and Llamendex:

| **Temporal Workflow** | **Associated Index** | **Our Solution** |
|------------------------|-------------------|---------------------|
| `SyncJiraAndIndex` | `JiraIndex` | Uses our processor with JIRA mapping |
| `SyncConfluenceAndIndex` | `ConfluenceIndex` | Uses our processor with Confluence mapping |
| `HandleUserQueryToAgent` | (all) | Queries data transformed by our solution |

## 📝 Llamendex Format

The output structure is optimized for Llamendex, allowing direct conversion to `NodeWithScore`:

```json
{
  "items": [
    {
      "id": "IDENTIFIER",
      "title": "TITLE",
      "content": {
        "field1": "CONTENT1",
        "field2": "CONTENT2"
      },
      "metadata": {
        "created_at": "DATE",
        "author": "AUTHOR"
      },
      "analysis": {
        "llm_summary": "Concise summary generated by LLM",
        "llm_keywords": ["WORD1", "WORD2"],
        "llm_entities": {
          "people": ["PERSON1", "PERSON2"],
          "organizations": ["ORG1", "ORG2"]
        },
        "llm_sentiment": "positive"
      },
      "relationships": {
        "confluence_links": [],
        "jira_tickets": []
      }
    }
  ],
  "metadata": {
    "source_file": "source_file.json",
    "processed_at": "PROCESSING_DATE",
    "llm_enrichment": {
      "model": "gpt-4",
      "enrichment_date": "ENRICHMENT_DATE"
    }
  }
}
```

## 📄 PDF Document Analysis

> 🔍 **NEW!** The system now includes an intelligent PDF extractor that combines native text extraction and AI image analysis.

### PDF Extractor Features

The Complete PDF Extractor is a specialized module designed to intelligently extract and analyze PDF document content. Unlike traditional PDF extractors, this module:

1. **Natively extracts** raw text from the PDF, preserving its original structure
2. **Detects and extracts** only the embedded images in the document
3. **Analyzes with AI** exclusively the images for enriched understanding
4. **Generates a unified JSON** combining the extracted text and image analyses

This targeted approach avoids transforming all pages into images, preserving the quality of native text while enabling enhanced AI understanding of visual elements.

### Usage via CLI

```bash
# Interactive mode
python -m cli.cli interactive
# Then select "Complete PDF extraction (text + analyzed images)"

# OR direct command
python -m cli.cli extract-images complete path/to/file.pdf --max-images 10
```

### Unified JSON Structure

For each processed PDF, you will get a structured JSON containing:

- Document metadata (name, timestamp, language)
- Raw text of each page
- Structured elements by page (text and images)
- AI descriptions for each image with context
- General statistics (pages, detected images, analyzed images)

### Application Examples

- **Technical document analysis**: Extraction of textual content with AI enrichment of diagrams and figures
- **Legal documentation**: Preservation of exact text structure with analysis of signatures and stamps
- **Financial reports**: Extraction of textual data with AI understanding of charts and tables
- **Scientific publications**: Conservation of structured text with analysis of formulas and illustrations

### Complete Documentation

Detailed documentation is available in the [`/documentation/pdf/`](documentation/pdf/) folder with:

- Complete user guide in English and French
- Advanced command examples
- Detailed description of output structure
- Troubleshooting guide

## 🔒 Security

### Security Best Practices

This project includes protection measures to prevent sensitive data leaks:

#### 🚫 Never commit sensitive data
- **API keys** (AWS, OpenAI, etc.)
- **Personal information** (emails, names, etc.)
- **Real test data**
- **Authentication tokens**
- **Login credentials**

#### ✅ Handling sensitive data
1. **Environment variables**: Always store API keys in the `.env` file (never in the code)
2. **Test data**: Use only synthetic or anonymized data
3. **Git protection**: A pre-commit hook automatically detects potential leaks

#### 🧹 Cleaning sensitive data
The project includes a tool to clean test files:

```bash
# Clean a specific file
python -m tools.clean_sensitive_data path/to/file.json

# Clean a folder
python -m tools.clean_sensitive_data path/to/directory --output path/to/output
```

#### 🚨 In case of a leak
1. **Remove** the sensitive data from Git history
   ```bash
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch path/to/file" --prune-empty --tag-name-filter cat -- --all
   git push origin --force
   ```
2. **Invalidate** compromised keys or tokens
3. **Inform** affected people

For more details, see the [SECURITY.md](SECURITY.md) file.

## ⚠️ Dependencies

- Python 3.8+
- typer, rich, inquirer, python-dotenv, ijson
- openai (optional, for LLM functionalities)
- outlines==0.2.3 (optional, for structured extraction)
- zstandard, orjson (optional, for JSON compression and optimization)

## 📜 License

This project is distributed under the MIT license.
