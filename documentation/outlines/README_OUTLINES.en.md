# Using Outlines 0.2.3 in this Project

This document explains how the project uses the [Outlines](https://github.com/dottxt-ai/outlines) library version 0.2.3 for robust JSON data processing and extraction.

## Outlines Overview

Outlines is a Python library for generating structured text from language models (LLMs). It offers advanced features such as:

- JSON generation following a precise schema
- Text generation following a regular expression
- Structured data extraction
- Support for multiple models (OpenAI, Transformers, etc.)

## Installing Outlines 0.2.3

⚠️ **IMPORTANT**: Outlines 0.2.3 strictly requires **Python 3.12** (Python 3.13 is not supported).

```bash
# Install in a virtual environment with Python 3.12
python3.12 -m venv venv_outlines
source venv_outlines/bin/activate  # Linux/Mac
# OR
venv_outlines\Scripts\activate     # Windows

# Install Outlines
pip install outlines==0.2.3

# Install project dependencies
pip install -r requirements.txt
```

## Data Sources

The source JSON files to process are located in the `files` folder at the project root:
- `CASM_jira.json`: JIRA tickets for the CASM project
- `CARTAN_jira.json`: JIRA tickets for the CARTAN project
- `hollard_confluence.json`: Hollard Confluence pages

To process these files, make sure to activate the Python 3.12 virtual environment before running commands.

## Integration Structure in Our Project

Our Outlines implementation consists of two main modules:

1. `extract/outlines_enhanced_parser.py` - Robust JSON parser using Outlines
2. `extract/outlines_extractor.py` - Structured data extractor

### System Architecture

```
┌───────────────────┐
│  CLI/Application  │
└─────────┬─────────┘
          │
┌─────────▼─────────┐
│ outlines_extractor │◄─────┐
└─────────┬─────────┘      │
          │                │
┌─────────▼─────────┐      │
│outlines_parser    │      │
└─────────┬─────────┘      │
          │                │
┌─────────▼─────────┐      │
│robust_json_parser │──────┘
└───────────────────┘   (fallback)
```

### Hybrid Operating Mode

Our system uses a hybrid approach:
1. First tries to parse with Outlines
2. If Outlines is not available, uses internal stubs
3. As a last resort, falls back to the standard robust JSON parser

## API and Usage

### Model Initialization

```python
from outlines import models

# Create an OpenAI model - Note: in 0.2.3 the signature changed
# and the temperature parameter is no longer supported with OpenAI
model = models.openai("gpt-4.1", api_key="your-api-key")
```

### Parsing JSON with Outlines

```python
from extract import outlines_robust_json_parser

# Parse a JSON file with LLM fallback if needed
data = outlines_robust_json_parser(
    file_path="data.json", 
    llm_fallback=True,
    model="gpt-4.1"  # OpenAI model to use
)
```

### Structured Extraction with a Schema

```python
from extract.outlines_enhanced_parser import extract_structured_data

# Define a schema for the data to extract
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "author": {"type": "string"},
        "tags": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

# Extract data according to this schema
structured_data = extract_structured_data(
    content=json_content,
    schema=schema,
    model="gpt-4.1"
)
```

### Named Entity Extraction

```python
from extract.outlines_enhanced_parser import extract_entities

# Extract entities such as IDs, emails, URLs, people, and organizations
entities = extract_entities(
    text="Contact john.doe@example.com about ticket PROJ-123.",
    model="gpt-4.1"
)
# Result: {"ids": ["PROJ-123"], "emails": ["john.doe@example.com"], ...}
```

## Using Generation Guides (0.2.3)

In Outlines 0.2.3, the API changed significantly compared to previous versions:

### 1. Regex Guide

```python
# Import generate module and models
from outlines import models
import outlines.generate as generate

# Create a model
model = models.openai("gpt-4.1", api_key="your-api-key")

# Create a generator with regex constraint
regex_pattern = r'\{(?:[^{}]|(?R))*\}|\[(?:[^\[\]]|(?R))*\]'
generator = generate.regex(model, regex_pattern)

# Generate text following this constraint
result = generator("Generate a valid JSON object")
```

### 2. JSON Schema Guide

```python
# Import generate module
import outlines.generate as generate

# Define a schema
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"}
    },
    "required": ["name", "age"]
}

# Create a generator with schema constraint
generator = generate.json(model, schema)

# Generate JSON following this schema
result = generator("Generate an object with name and age")
```

### 3. Prompts with Template

```python
# Import Template
from outlines import Template

# Create a template with Jinja2
template = Template.from_string("Here is a variable: {{ variable }}")

# Render the template with variables
prompt = template(variable="value")
```

## Limitations and Compatibility

### Important Notes on OpenAI

- With Outlines 0.2.3, some features are limited with OpenAI models:
  - `generate.format(model, int)` does not work with OpenAI models
  - Some advanced guides may not be compatible with the OpenAI API
  - It is best to use `generate.text()` and `generate.json()` with OpenAI

### General Compatibility

- Outlines 0.2.3 is not compatible with Python 3.13
- Different Outlines versions may have slightly different APIs
- If Outlines is not available, our system will continue to work with reduced features

## Error Handling and Fallbacks

Our implementation ensures maximum robustness by:

1. Automatically detecting if Outlines is available
2. Providing stubs for testing and development
3. Falling back to the standard JSON parser if needed
4. Offering JSON repair mechanisms via LLM

---

For more information on Outlines, see the [official documentation](https://dottxt-ai.github.io/outlines/latest/welcome/). 