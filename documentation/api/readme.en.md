# DataFlow AI API

## Overview

The DataFlow AI API is a RESTful programming interface built with FastAPI. It provides a set of endpoints for processing data, analyzing documents, and integrating artificial intelligence into data processing workflows.

## Technologies Used

- **FastAPI** - Modern and fast web framework for building APIs
- **Python 3.10+** - Main programming language
- **Uvicorn** - High-performance ASGI server to run the application
- **PyMuPDF (Fitz)** - Library for PDF document analysis
- **Outlines** - LLM integration framework with structured generation
- **GPT-4o** - For advanced image and text analysis
- **Docker** - Containerization (optional)

## Project Structure

```
api/
├── main.py              # Main API entry point
├── __init__.py          # Package initialization
├── models/              # Data models and Pydantic schemas
├── routes/              # Endpoint definitions by functionality
│   ├── __init__.py      # Routes package initialization
│   ├── pdf.py           # Routes for PDF processing
│   ├── json.py          # Routes for JSON processing
│   └── unified.py       # Routes for unified processing (JIRA/Confluence)
└── services/            # Business logic and underlying services
    ├── __init__.py      # Services package initialization
    ├── pdf_service.py   # PDF processing service
    ├── json_service.py  # JSON processing service
    └── unified_service.py # Unified processing service
```

## Main Endpoints

The API exposes the following endpoints:

### PDF Processing
- `POST /api/pdf/process` - Processes a PDF file and extracts text and images with AI analysis

### JSON Processing
- `POST /api/json/process` - Processes a JSON file with structure detection
- `POST /api/json/clean` - Cleans sensitive data from a JSON file
- `POST /api/json/compress` - Compresses a JSON file to reduce its size
- `POST /api/json/split` - Divides a JSON file into multiple chunks

### Unified Processing
- `POST /api/unified/process` - Processes and associates JIRA and Confluence files

## Installation and Startup

1. Make sure you have Python 3.10+ installed
2. Create and activate a virtual environment:

```bash
python -m venv venv_outlines
source venv_outlines/bin/activate  # On Windows: venv_outlines\\Scripts\\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the server:

```bash
python run_api.py
```

The API will be accessible at `http://localhost:8000`. Interactive documentation is available at `http://localhost:8000/docs`.

## Environment Variables

Environment variables can be configured in a `.env` file at the project root:

```
API_PORT=8000
API_HOST=localhost
DEBUG=True
MAX_UPLOAD_SIZE=52428800  # 50MB
```

## Frontend Integration

The API is designed to work with the DataFlow AI frontend but can also be used independently as a backend service. Responses are formatted in JSON and follow consistent structures.

## Security

- All processed files are temporary and not permanently stored
- Input validation via Pydantic
- File size limits to prevent abuse
- CORS support for secure cross-origin requests

## Performance

- Asynchronous processing for better scalability
- Optimizations for processing large files
- Configurable caching for frequent operations

## Development and Extension

To extend the API with new features:

1. Create a new route file in the `routes/` folder
2. Implement necessary services in `services/`
3. Define data models in `models/` if needed
4. Register the new routes in `main.py` 