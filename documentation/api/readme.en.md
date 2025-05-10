# DataFlow AI API

## Overview

The DataFlow AI API is a RESTful programming interface built with FastAPI. It provides a set of endpoints for processing data, analyzing documents, and integrating artificial intelligence into data processing workflows.

## Technologies Used

- **FastAPI** - Modern and fast web framework for building APIs
- **Python 3.10+** - Main programming language
- **Uvicorn** - High-performance ASGI server for running the application
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
│   ├── unified.py       # Routes for unified processing (JIRA/Confluence)
│   └── auth.py          # API key authentication middleware
└── services/            # Business logic and underlying services
    ├── __init__.py      # Services package initialization
    ├── pdf_service.py   # PDF processing service
    ├── json_service.py  # JSON processing service
    └── unified_service.py # Unified processing service
```

## API Authentication

All API endpoints (except the health endpoint `/api/health` and root `/`) require API key authentication.

### API Key Configuration

1. Define your API key in the `.env` file at the project root:
   ```
   API_KEY=your_secure_api_key
   ```

2. For production, use a strong, random key:
   ```bash
   openssl rand -hex 32
   ```

### Using the API Key

For each API request, include the API key in the HTTP header:

```
X-API-Key: your_secure_api_key
```

Example with curl:
```bash
curl -X POST http://localhost:8000/api/json/process \
  -H "X-API-Key: your_secure_api_key" \
  -F "file=@my_file.json"
```

Example with JavaScript/Fetch:
```javascript
const response = await fetch('http://localhost:8000/api/json/process', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your_secure_api_key'
  },
  body: formData
});
```

## Main Endpoints

The API exposes the following endpoints:

### PDF Processing
- `POST /api/pdf/process` - Process a PDF file and extract text and images with AI analysis

### JSON Processing
- `POST /api/json/process` - Process a JSON file with structure detection
- `POST /api/json/clean` - Clean sensitive data from a JSON file
- `POST /api/json/compress` - Compress a JSON file to reduce its size
- `POST /api/json/split` - Split a JSON file into multiple chunks

### Unified Processing
- `POST /api/unified/process` - Process and associate JIRA and Confluence files

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

4. Create a `.env` file with your configurations:

```
API_PORT=8000
API_HOST=localhost
DEBUG=True
MAX_UPLOAD_SIZE=52428800  # 50MB
API_KEY=your_secure_api_key
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000
```

5. Start the server:

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
API_KEY=your_secure_api_key
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Frontend Integration

The API is designed to work with the DataFlow AI frontend. The frontend automatically uses the API key defined in its `.env` file for all communications with the API. To configure the frontend:

1. Make sure the same API key is configured in `frontend/.env`:
   ```
   VITE_API_KEY=your_secure_api_key
   ```

2. The `FRONTEND_ORIGINS` variable in the backend's `.env` file must include the frontend's origin to allow CORS requests.

## Security

- **API Key Authentication** - All routes are protected by an API key
- **CORS Validation** - Only authorized origins can access the API
- **Temporary Files** - All processed files are temporary and not permanently stored
- **Input Validation** - Pydantic is used to validate inputs
- **Size Limits** - File size limits to prevent abuse
- **Secure Headers** - HTTP headers configured for security

For more details about security and authentication, see the dedicated document in `documentation/security/API_AUTHENTICATION.md`.

## Performance

- Asynchronous processing for better scalability
- Optimizations for large file processing
- Configurable caching for frequent operations

## Development and Extension

To extend the API with new features:

1. Create a new routes file in the `routes/` folder
2. Implement the necessary services in `services/`
3. Define data models in `models/` if needed
4. Register the new routes in `main.py` with the authentication dependency
   ```python
   app.include_router(my_new_route.router, prefix="/api/new", tags=["New Feature"], dependencies=[require_api_key])
   ``` 