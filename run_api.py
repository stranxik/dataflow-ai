"""
Main entry point for running the DataFlow AI API.
"""
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    """
    Main function to run the FastAPI application.
    """
    # Get host and port from environment variables or use defaults
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    print(f"Starting DataFlow AI API on {host}:{port}")
    print("Documentation available at http://localhost:8000/docs")
    
    # Run the FastAPI application
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=os.getenv("API_RELOAD", "False").lower() == "true",
        workers=int(os.getenv("API_WORKERS", "1"))
    )

if __name__ == "__main__":
    main() 