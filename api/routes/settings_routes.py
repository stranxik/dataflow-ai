from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import subprocess
import sys

router = APIRouter(prefix="/settings", tags=["settings"])

class LanguageRequest(BaseModel):
    language: str

@router.post("/language")
async def set_language(request: LanguageRequest):
    """
    Définit la langue pour la CLI et le système.
    Accepte 'fr' ou 'en'.
    """
    language = request.language
    
    if language not in ['fr', 'en']:
        raise HTTPException(status_code=400, detail=f"Langue non supportée: {language}. Utilisez 'fr' ou 'en'.")
    
    try:
        # Chemin du fichier CLI
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(current_dir)
        cli_path = os.path.join(parent_dir, "cli", "cli.py")
        
        # Exécuter la commande CLI pour changer la langue
        subprocess.run([sys.executable, cli_path, "--lang", language], 
                       capture_output=True, text=True, check=True)
        
        # Sauvegarder la préférence de langue dans un fichier de configuration
        config_file = os.path.join(parent_dir, ".language")
        with open(config_file, "w") as f:
            f.write(language)
        
        return JSONResponse({"status": "success", "language": language})
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, 
                            detail=f"Erreur lors du changement de langue: {str(e.stderr)}")
    except Exception as e:
        raise HTTPException(status_code=500, 
                            detail=f"Erreur inattendue: {str(e)}") 