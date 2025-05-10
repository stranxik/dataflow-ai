from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os

router = APIRouter(tags=["Settings"])

class LanguageRequest(BaseModel):
    language: str

@router.post("/language")
async def set_language(request: LanguageRequest):
    """
    Définit la langue pour le système.
    Accepte 'fr' ou 'en'.
    """
    language = request.language
    
    if language not in ['fr', 'en']:
        raise HTTPException(status_code=400, detail=f"Langue non supportée: {language}. Utilisez 'fr' ou 'en'.")
    
    try:
        # Chemin du fichier de configuration
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(current_dir)
        config_file = os.path.join(parent_dir, ".language")
        
        # Sauvegarder la préférence de langue dans un fichier de configuration
        with open(config_file, "w") as f:
            f.write(language)
        
        return JSONResponse({"status": "success", "language": language})
    
    except Exception as e:
        raise HTTPException(status_code=500, 
                            detail=f"Erreur inattendue: {str(e)}") 