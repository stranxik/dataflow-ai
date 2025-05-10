# LLM Enrichment with Outlines for Llamendex

## Overview

This module integrates LLM enrichment capabilities via two main mechanisms:

1. **Outlines Framework**: Using the Outlines framework for structured extraction and controlled generation
2. **Custom Implementation**: Our own LLM enrichment implementation

These enrichments transform raw JIRA and Confluence data into richer data for Llamendex.

## Enrichments Performed

For each document (JIRA ticket or Confluence page), we perform the following enrichments:

1. **Automatic summary** (`llm_summary`): Generation of a concise and informative summary
2. **Keyword extraction** (`llm_keywords`): Identification of key terms and concepts
3. **Entity recognition** (`llm_entities`):
   - People
   - Organizations
   - Locations
   - Technical terms
4. **Sentiment analysis** (`llm_sentiment`): Classification as "positive", "neutral", or "negative"

## Technical Architecture

### Outlines Integration

The `outlines_integration.py` module provides:

- Automatic detection of Outlines with fallback installation
- Integration with the Outlines `OpenAI` model
- Custom grammars for structured extraction
- Robust fallbacks in case of failure

### Generic JSON Processor

The `GenericJsonProcessor` uses the LLM to:

- Repair malformed JSON (`use_llm_fallback`)
- Enrich data with additional analyses
- Extract keywords and meta-information

### Usage in Llamendex

LLM enrichments prepare data for Llamendex by:

1. **Improving search**: Summaries and keywords enable better semantic matches
2. **Facilitating filtering**: Entities and sentiment allow advanced filtering
3. **Optimizing results**: LLM-generated summaries provide a concise overview without full reading

## Models Used

- **OpenAI GPT-4**: Main model for enrichment
- **OpenAI GPT-3.5-Turbo**: Fallback for less complex tasks (optional)

## Configuration

LLM model configuration is done via:

1. The `.env` file, which defines:
   - `OPENAI_API_KEY`: OpenAI API key
   - `DEFAULT_LLM_MODEL`: Default model (gpt-4.1)
   - `LLM_MODELS`: List of available models

2. CLI options (enabled by default):
   - `--with-openai`: Enables LLM enrichment (default: ON)
   - `--no-openai`: Disables LLM enrichment
   - `--model`: Specifies a particular model

## Generated Artifacts

Several files are generated when using the LLM:

1. **Enriched files**:
   - `enriched_jira.json`
   - `enriched_confluence.json`

2. **Enrichment summaries**:
   - `llm_enrichment_summary.md`: Summary of enrichments and statistics

## Usage Examples

### CLI Command with LLM Enrichment

LLM enrichment is enabled by default in the unified command:

```bash
python -m cli.cli unified --jira-files CARTAN_jira.json --confluence-files hollard_confluence.json
```

To explicitly disable it:

```bash
python -m cli.cli unified --jira-files CARTAN_jira.json --confluence-files hollard_confluence.json --no-llm
```

### LLM Enrichment JSON Format

```json
{
  "id": "TICKET-123",
  "title": "Issue with the payment API",
  "content": "...",
  "analysis": {
    "llm_summary": "Integration issue with the Stripe payment API causing transaction failures for some customers.",
    "llm_keywords": ["API", "payment", "Stripe", "failure", "transaction", "integration"],
    "llm_entities": {
      "people": ["John Smith"],
      "organizations": ["Stripe"],
      "technical_terms": ["API", "webhook", "authentication"]
    },
    "llm_sentiment": "negative"
  }
}
``` 