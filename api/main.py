"""
Main FastAPI application entry point for DataFlow AI SaaS.
"""
import os
from pathlib import Path
import shutil
import uuid
from datetime import datetime, timedelta
from typing import Dict, List
import sys

from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes import pdf_routes, json_routes, llm_routes, settings_routes
from api.services.temp_file_service import setup_temp_cleanup

# Create temp directory if it doesn't exist
TEMP_DIR = Path("/tmp/dataflow_temp")
TEMP_DIR.mkdir(exist_ok=True)

# Create FastAPI application
app = FastAPI(
    title="DataFlow AI API",
    description="API for DataFlow AI - Pipeline intelligent, CLI avancée & outils pour la préparation, "
                "la transformation, la sécurisation et l'enrichissement des données JSON & PDF pour l'IA et le RAG",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pdf_routes.router, prefix="/api/pdf", tags=["PDF Processing"])
app.include_router(json_routes.router, prefix="/api/json", tags=["JSON Processing"])
app.include_router(llm_routes.router, prefix="/api/llm", tags=["LLM Enrichment"])
app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])

# Task storage - in production this should be replaced with a proper task queue
tasks: Dict[str, Dict] = {}

# Setup a background task to clean up temporary files
setup_temp_cleanup(app)

# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="DataFlow AI API",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5.9.1/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5.9.1/swagger-ui.css",
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(
        title="DataFlow AI API",
        version="1.0.0",
        description="API for DataFlow AI",
        routes=app.routes,
    )

# Health check endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": str(type(exc).__name__),
            "path": str(request.url.path),
        },
    )

@app.get("/")
async def root():
    """
    Endpoint racine pour vérifier que l'API est en cours d'exécution.
    """
    return {
        "status": "success",
        "message": "DataFlow AI API est opérationnelle",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 