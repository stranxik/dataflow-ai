# JSON Processor – Generic Solution for Analysis and Transformation

## 🎯 Main Objective

This solution is designed to structure and unify diverse data sources (JIRA, Confluence, Google Drive, Git) for an advanced RAG system with **Llamendex**. Each source follows a common pipeline, but with specific adaptation logic to maximize semantic and structural indexing quality.

**The concrete goal:**
- Extract structured metadata from various JSON formats
- Create a well-typed hierarchical tree for each source
- Establish matches (matching) between different sources (JIRA ↔ Confluence ↔ Drive ↔ Git)
- Prepare data in `NodeWithScore` format for Llamendex, including the relationship graph

## 📂 Contents of the `extract` Folder

Here are the main files and their function:

### Main Generic Script
- `generic_json_processor.py`: Universal solution to process any JSON

### Specialized Scripts
- **JIRA:**
  - `extract_jira_structure.py`: Structure extraction and analysis
  - `transform_for_llm.py`: JIRA-specific data transformation
  - `analyze_jira_export.py`: JIRA export analysis

- **Confluence:**
  - `extract_confluence_structure.py`: Extraction and transformation of Confluence pages

### Utilities
- `process_by_chunks.py`: Handling large JSON files
- `match_jira_confluence.py`: JIRA-Confluence matching
- `run_analysis.py`: Workflow orchestration for JIRA only
- `run_unified_analysis.py`: Full workflow orchestration for JIRA + Confluence

## 🔍 Generic Approach

The approach here allows processing any JSON structure, thanks to:

1. **Automatic structure detection**: Analysis and detection of important fields
2. **Customizable mappers**: Adaptation to any input format
3. **Chunk processing**: Efficient handling of large files
4. **Flexible transformation**: Output structure adaptable to needs

## 📖 Practical Usage Guide

How to use this solution for your JIRA and Confluence files.

### 1. Basic Processing

```bash
python generic_json_processor.py --input my_file.json --output result.json
```

### 2. With a Custom Mapping

Create a JSON mapping file (e.g., `mapping.json`):
```json
{
  "id": "key",
  "title": ["title", "name", "subject"],
  "content": {
    "field": "description",
    "transform": "clean_text"
  },
  "keywords": {
    "field": "description",
    "transform": "extract_keywords"
  }
}
```

Then use it:
```bash
python generic_json_processor.py --input my_file.json --output result.json --mapping-file mapping.json
```

### 3. For Large Files

```bash
python process_by_chunks.py split --input large_file.json --output-dir chunks_folder --items-per-file 500
```

Then process each chunk:
```bash
for file in chunks_folder/*.json; do
  python generic_json_processor.py --input "$file" --output "$(basename "$file" .json)_processed.json"
done
```

### 4. Processing Multiple Files from the Same Source

You can process multiple JIRA or Confluence files sequentially:

```bash
# Multiple JIRA files
for file in jira_*.json; do
  output="${file%.json}_processed.json"
  python generic_json_processor.py --input "$file" --output "$output" --mapping-file mapping_examples/jira_mapping.json
done

# Multiple Confluence files
for file in confluence_*.json; do
  output="${file%.json}_processed.json"
  python generic_json_processor.py --input "$file" --output "$output" --mapping-file mapping_examples/confluence_mapping.json
done
```

### 5. Full JIRA + Confluence Workflow

To process multiple JIRA and Confluence files at once and establish matches:

```bash
python run_unified_analysis.py --jira-files jira1.json jira2.json --confluence-files confluence1.json confluence2.json --output-dir results
```

This command:
- Processes all specified JIRA files
- Processes all specified Confluence files
- Establishes matches between them
- Saves all results in the `results` folder

### 6. Matching After Individual Processing

If you have already processed your files separately:

```bash
python match_jira_confluence.py --jira jira_processed.json --confluence confluence_processed.json --output matches.json --updated-jira jira_with_matches.json --updated-confluence confluence_with_matches.json
```

### 7. Common Usage Scenarios

#### Scenario 1: Extraction and Analysis of a JIRA Export

```bash
# Step 1: Structure extraction
python extract_jira_structure.py my_jira_export.json

# Step 2: Transformation for LLM
python transform_for_llm.py --files my_jira_export.json --output jira_llm_ready.json

# Step 3 (optional): Analysis with OpenAI
python analyze_jira_export.py --api-key YOUR_API_KEY
```

#### Scenario 2: Integrate a New Data Type

```bash
# Step 1: Create a mapping file for the new source
echo '{
  "id": "issueId", 
  "title": "summary",
  "content": {"field": "description", "transform": "clean_text"},
  "metadata": {
    "created_by": "authorName",
    "created_at": "creationDate"
  }
}' > new_system_mapping.json

# Step 2: Process the file with this mapping
python generic_json_processor.py --input new_system.json --output new_processed.json --mapping-file new_system_mapping.json
```

## 📊 Structure of Generated Results

After processing, your results folder will contain:

- **Detected structure files:**
  - `jira_structure.json`: Detected structure of JIRA files
  - `confluence_structure.json`: Detected structure of Confluence files

- **Data transformed for Llamendex:**
  - `llm_ready_jira.json`: Transformed JIRA data
  - `llm_ready_confluence.json`: Transformed Confluence data

- **Matches and relationships:**
  - `jira_confluence_matches.json`: Detected matches
  - `jira_with_matches.json`: JIRA data enriched with links
  - `confluence_with_matches.json`: Confluence data enriched with links

## 🧩 System Extension

### Create Your Own Mappers

To adapt the solution to new sources:

```python
from generic_json_processor import GenericJsonProcessor

def my_custom_mapper(item):
    # Transform the item as needed
    result = {
        "id": item.get("identifiant", ""),
        "content": {
            "title": item.get("nom", ""),
            "body": item.get("contenu", "")
        },
        "metadata": {
            "created_at": item.get("date_creation", ""),
            "type": item.get("type", "")
        }
    }
    return result

# Create the processor with your mapper
processor = GenericJsonProcessor(custom_mapper=my_custom_mapper)
processor.process_file("my_file.json", "result.json")
```

## 🔄 Integration with Temporal

To integrate this solution into your Temporal workflows:

```javascript
// Simplified Temporal activity example in JavaScript
export async function syncJiraAndIndex(ctx) {
  // 1. Run JIRA processing
  const processOutput = await executeCommand(
    'python', 
    ['run_analysis.py', '--files', 'export_jira.json', '--output-dir', 'jira_processed']
  );
  
  // 2. Read the transformed results
  const processedData = await fs.readFile('jira_processed/llm_ready_jira.json', 'utf8');
  
  // 3. Update the Llamendex index with the transformed data
  await llamendexClient.updateIndex('JiraIndex', JSON.parse(processedData));
  
  return { status: 'completed', ticketsProcessed: processedData.items.length };
}
```

## 📝 Format for Llamendex

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
        "keywords": ["WORD1", "WORD2"],
        "entities": {
          "ids": ["ID1", "ID2"],
          "urls": ["URL1", "URL2"]
        }
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
    "structure": { ... }
  }
}
```

## ⚠️ Dependencies

- Python 3.8+
- dotenv, ijson, openai
- Standard modules (json, os, datetime, etc.) 