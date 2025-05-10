"""
Module d'authentification pour sécuriser l'API
"""
import os
from typing import Optional

from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

# Charger l'API key depuis les variables d'environnement
API_KEY = os.getenv("API_KEY", "your_secure_api_key_here")

# Définir le header pour l'API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
) -> str:
    """
    Vérifie que l'API key fournie est valide.
    Lève une exception si l'API key est invalide ou manquante.
    """
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Accès non autorisé. API key invalide ou manquante."
    )

# Dépendance à utiliser dans les endpoints qui nécessitent une authentification
require_api_key = Depends(get_api_key) 