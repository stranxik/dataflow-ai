# CLI for JSON Data Processing and Analysis

This CLI provides a powerful interface to process, analyze, and transform JSON files from various sources (JIRA, Confluence, GitHub, etc.), preparing them for indexing in a RAG system with Llamendex.

## 🎯 Main Features

- **Full interactive mode**: Guided assistant for all operations (processing, chunking, matching, unified flow)
- **Automatic file type detection** (JIRA, Confluence, GitHub)
- **Flexible transformation** via customizable mappings
- **Chunking and processing of large files** (`chunks`)
- **Structured metadata extraction**
- **Matching between different sources**
- **LLM enrichment** (OpenAI) for semantic analysis
- **Interactive interface** for easy file navigation and usage
- **Organized results** with unique timestamps for each run
- **Detailed file trees** for every processed file
- **Robust handling** of malformed or incomplete JSON files
- **Environment variable support** for configuration

## 🚀 Installation

1. Clone this repository and go to the folder
2. Create a `.env` file by copying `.env.example`
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

Configure the tool via the `.env` file:

```
# General settings
MAPPINGS_DIR=extract/mapping_examples
OUTPUT_DIR=output

# LLM settings
OPENAI_API_KEY=your_openai_api_key
DEFAULT_LLM_MODEL=gpt-4.1
LLM_MODELS=gpt-4.1,gpt-3.5-turbo,o3,gpt-4
```

## 📖 Usage Guide

### Interactive Mode (Recommended)

Launch the full assistant that guides you step by step:

```bash
python -m cli.cli interactive
```

You can:
- Choose the operation type (process, chunk, match, full flow)
- Browse your folders to select files
- Create or choose a mapping
- Set advanced options (LLM, limits, etc.)
- View a summary before each action
- Get clear notifications at the end of each step
- Know exactly where result files are generated

### `chunks` Command – Chunking and Processing Large Files

Split a large JSON file into smaller chunks, then process each chunk automatically:

```bash
python -m cli.cli chunks my_large_file.json --output-dir chunks_folder --items-per-file 500 --process --mapping extract/mapping_examples/jira_mapping.json --llm
```

- Chunks are created in the folder `results/chunks_folder_YYYY-MM-DD-HH-MM-SS/`
- Processed files are placed in a `processed/` subfolder
- Each file generates its own detailed tree structure
- End notification and summary are displayed

### `process` Command – Processing Individual JSON Files

```bash
python -m cli.cli process my_file.json --output result.json
```

Main options:

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Output file (default: `results/{input}_processed_YYYY-MM-DD-HH-MM-SS.json`) |
| `--mapping`, `-m` | Mapping file to use |
| `--detect/--no-detect` | Enable/disable automatic file type detection |
| `--llm/--no-llm` | Enable/disable LLM enrichment |
| `--model` | LLM model to use |
| `--interactive`, `-i` | Interactive mode for choices |
| `--max` | Maximum number of items to process |

### `match` Command – JIRA ↔ Confluence Matching

```bash
python -m cli.cli match jira_processed.json confluence_processed.json --output-dir match_results
```

Main options:

| Option | Description |
|--------|-------------|
| `--output-dir`, `-o` | Output directory (generates `results/match_results_YYYY-MM-DD-HH-MM-SS/`) |
| `--min-score`, `-s` | Minimum score for matches |
| `--llm-assist` | Use an LLM to improve matches |

### `unified` Command – Full Flow (JIRA + Confluence + Matching)

```bash
python -m cli.cli unified jira1.json jira2.json --confluence conf1.json conf2.json --output-dir full_results
```

Main options:

| Option | Description |
|--------|-------------|
| `--confluence`, `-c` | Confluence files to process |
| `--output-dir`, `-o` | Output directory (generates `results/full_results_YYYY-MM-DD-HH-MM-SS/`) |
| `--min-score`, `-s` | Minimum score for matches |
| `--max` | Maximum number of items to process per file |
| `--llm` | Enable LLM enrichment |
| `--skip-matching` | Disable matching between JIRA and Confluence |

## 🔍 Interactive Navigation & User Experience

- Select files/folders via an interactive browser (no need to type paths)
- Create custom mappings via integrated editor
- Summary before each action
- End-of-process notifications and output folder display

## 📊 Results Organization

All results are organized in the `results/` folder with a clear structure:

```
results/
├── jira_confluence_2023-08-30-14-22-55/     # Unified run folder
│   ├── jira/                               # Subfolder for JIRA files
│   ├── confluence/                         # Subfolder for Confluence files
│   ├── matches/                            # Subfolder for matches
│   ├── split_jira_files/                   # Split JIRA files
│   ├── split_confluence_files/             # Split Confluence files
│   ├── llm_ready/                          # Files ready for LLM
│   ├── global_arborescence.txt             # Global tree
│   ├── jira1_arborescence_20230830_142255.txt  # Detailed tree for jira1.json
│   └── confluence1_arborescence_20230830_142255.txt  # Detailed tree for confluence1.json
├── chunks_file1_2023-08-31-09-15-20/       # Chunks run folder
│   ├── part1.json                          # First chunk
│   ├── file1_arborescence.txt              # Tree for the source file
│   └── ...
└── file2_processed_2023-08-31-10-45-30.json  # Result of a process run
```

## 📝 File Tree Structure

For each processed file, a detailed tree is generated, showing:

- File information (name, size, processing date)
- Structure type (object or array)
- Main keys for objects
- Preview of the first element for arrays
- Full content structure with example values
- Robust handling of partially corrupted or malformed files

These trees let you quickly understand the content and structure of JSON files, making mapping creation and debugging easier.

## 🧩 Extension

To add new file types:
1. Create a mapping file in `mapping_examples/`
2. Adapt detection in `detect_file_type()`
3. Use the `process` command or interactive mode with your new mapping

## ⚠️ Dependencies

- Python 3.8+
- typer, rich, inquirer, python-dotenv, ijson, openai

## 📜 License

This project is distributed under the Polyform Small Business License 1.0.0.

[![License: Polyform-SBL](https://img.shields.io/badge/license-Polyform_SBL-blue.svg)](../LICENSE)

For full license details, see the [LICENSE](../LICENSE) file. 