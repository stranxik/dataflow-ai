"""
Temporary file management service for DataFlow AI API.
Handles creating, tracking, and cleaning up temporary files.
"""
import os
import shutil
import tempfile
import time
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from fastapi import FastAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("temp_file_service")

# Base directory for all temporary files
TEMP_BASE_DIR = Path("/tmp/dataflow_temp")
TEMP_BASE_DIR.mkdir(exist_ok=True)

# Max age of temporary files in minutes
MAX_FILE_AGE_MINUTES = 60  # 1 hour

async def create_temp_file(content: bytes = None, prefix: str = "", suffix: str = "") -> Path:
    """
    Create a temporary file and optionally write content to it.
    
    Args:
        content: Optional content to write to the file
        prefix: Optional prefix for the filename
        suffix: Optional suffix for the filename
        
    Returns:
        Path to the created temporary file
    """
    # Create a unique temp filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = TEMP_BASE_DIR / timestamp
    temp_dir.mkdir(exist_ok=True, parents=True)
    
    fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=temp_dir)
    os.close(fd)
    
    file_path = Path(temp_path)
    
    # Write content if provided
    if content:
        with open(file_path, "wb") as f:
            f.write(content)
    
    logger.info(f"Created temp file: {file_path}")
    return file_path

def cleanup_files(paths: List[Union[str, Path]]) -> None:
    """
    Clean up a list of files or directories.
    
    Args:
        paths: List of file or directory paths to clean up
    """
    for path in paths:
        path = Path(path)
        try:
            if path.is_file():
                path.unlink()
                logger.info(f"Removed temp file: {path}")
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                logger.info(f"Removed temp directory: {path}")
        except Exception as e:
            logger.error(f"Error cleaning up {path}: {str(e)}")

async def cleanup_old_temp_files() -> None:
    """
    Clean up temporary files older than MAX_FILE_AGE_MINUTES.
    """
    logger.info("Running scheduled temp file cleanup")
    now = datetime.now()
    
    # Skip if temp directory doesn't exist
    if not TEMP_BASE_DIR.exists():
        return
    
    # Check all subdirectories in the temp directory
    for item in TEMP_BASE_DIR.iterdir():
        try:
            if not item.is_dir():
                continue
                
            # Get the creation time
            created_time = datetime.fromtimestamp(item.stat().st_ctime)
            age = now - created_time
            
            # If older than max age, remove it
            if age > timedelta(minutes=MAX_FILE_AGE_MINUTES):
                logger.info(f"Removing old temp directory: {item} (age: {age})")
                shutil.rmtree(item, ignore_errors=True)
        except Exception as e:
            logger.error(f"Error during cleanup of {item}: {str(e)}")

def setup_temp_cleanup(app: FastAPI) -> None:
    """
    Setup a background task to periodically clean up old temporary files.
    
    Args:
        app: FastAPI application instance
    """
    @app.on_event("startup")
    async def start_temp_cleanup_task():
        asyncio.create_task(periodic_cleanup())
    
    async def periodic_cleanup():
        while True:
            await cleanup_old_temp_files()
            # Run cleanup every 15 minutes
            await asyncio.sleep(15 * 60)
    
    # Also clean up on shutdown
    @app.on_event("shutdown")
    async def cleanup_on_shutdown():
        await cleanup_old_temp_files() 