"""
PDF processing routes for DataFlow AI API.
These endpoints handle PDF file uploads and processing using the existing CLI.
"""
import os
import uuid
import shutil
import zipfile
import logging
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Form, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from api.services.subprocess_service import run_cli_command
from api.services.temp_file_service import create_temp_file, cleanup_files

# Configure logging
logger = logging.getLogger("pdf_routes")

router = APIRouter()

# Ce endpoint ne nécessite PAS d'API key - c'est un endpoint de test public
@router.get("/test-no-auth", summary="Test endpoint (no auth)", include_in_schema=True, tags=["Testing"])
async def test_endpoint_public():
    """
    Simple test endpoint to verify API is working correctly.
    This endpoint does not require authentication.
    """
    logger.info("Test endpoint called")
    
    # Print environment information for debugging
    cwd = os.getcwd()
    python_path = sys.executable
    dirs = {
        "cwd": cwd,
        "files": os.path.join(cwd, "files"),
        "results": os.path.join(cwd, "results"),
        "cli": os.path.join(cwd, "cli")
    }
    
    # Check existence of critical directories
    exists = {dir_name: os.path.exists(path) for dir_name, path in dirs.items()}
    
    # Check for OpenAI API key
    api_key_exists = "OPENAI_API_KEY" in os.environ
    
    # Check for commands
    cmd_check = {
        "python": shutil.which("python"),
        "zip": shutil.which("zip"),
        "unzip": shutil.which("unzip")
    }
    
    return {
        "status": "API is working",
        "environment": {
            "python_executable": python_path,
            "directories": dirs,
            "directories_exist": exists,
            "api_key_exists": api_key_exists,
            "commands": cmd_check
        }
    }

@router.get("/test", summary="Test endpoint")
async def test_endpoint():
    """
    Simple test endpoint to verify API is working correctly.
    """
    logger.info("Test endpoint called")
    
    # Print environment information for debugging
    cwd = os.getcwd()
    python_path = sys.executable
    dirs = {
        "cwd": cwd,
        "files": os.path.join(cwd, "files"),
        "results": os.path.join(cwd, "results"),
        "cli": os.path.join(cwd, "cli")
    }
    
    # Check existence of critical directories
    exists = {dir_name: os.path.exists(path) for dir_name, path in dirs.items()}
    
    # Check for OpenAI API key
    api_key_exists = "OPENAI_API_KEY" in os.environ
    
    # Check for commands
    cmd_check = {
        "python": shutil.which("python"),
        "zip": shutil.which("zip"),
        "unzip": shutil.which("unzip")
    }
    
    return {
        "status": "API is working",
        "environment": {
            "python_executable": python_path,
            "directories": dirs,
            "directories_exist": exists,
            "api_key_exists": api_key_exists,
            "commands": cmd_check
        }
    }

@router.post("/extract-images", summary="Extract and analyze images from PDF")
async def extract_images_from_pdf(
    file: UploadFile = File(...),
    max_images: Optional[int] = Form(int(os.environ.get("DEFAULT_IMAGES_ANALYSIS", 10)), description="Maximum number of images to extract and analyze"),
    format: Optional[str] = Form("json", description="Output format: 'json' for single JSON file or 'zip' for complete folder"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Extract text and analyze images from a PDF file using OpenAI Vision.
    
    - **file**: PDF file to process
    - **max_images**: Maximum number of images to extract and analyze
    - **format**: Output format: 'json' or 'zip'
    """
    logger.info(f"Receiving PDF extraction request - File: {file.filename}, Size: {file.size}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Requested format: {format}")
    
    # Generate a unique ID for this job
    job_id = str(uuid.uuid4())
    logger.info(f"Generated job ID: {job_id}")
    
    # Determine the base path for files
    base_path = os.environ.get("BASE_PATH", os.getcwd())
    logger.info(f"Base path: {base_path}")
    
    # Create temp directory for input file
    temp_dir = os.path.join(base_path, "files", f"temp_{job_id}")
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"Created temp directory: {temp_dir}")
    
    # Create output directory for results
    output_dir = os.path.join(base_path, "results", f"pdf_extraction_{job_id}")
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    
    # Save the uploaded PDF file
    input_file_path = os.path.join(temp_dir, "input.pdf")
    content = await file.read()
    with open(input_file_path, "wb") as f:
        f.write(content)
    
    logger.info(f"File saved to {input_file_path}, size: {os.path.getsize(input_file_path)} bytes")
    
    # Process the PDF
    try:
        logger.info(f"Processing PDF: {file.filename}, job_id: {job_id}, format: {format}")
        logger.info(f"Using max_images: {max_images}")
        
        # Check if OpenAI API key is available
        if "OPENAI_API_KEY" in os.environ:
            logger.info("OPENAI_API_KEY found in environment variables")
        else:
            logger.warning("OPENAI_API_KEY not found in environment variables")
        
        # Check if output directory has proper permissions
        logger.info(f"Checking permissions for {output_dir}")
        
        # Get python executable
        python_executable = sys.executable
        logger.info(f"Using Python executable: {python_executable}")
        
        # Use extract/pdf_complete_extractor.py directly instead of cli module
        extract_script = os.path.join(base_path, "extract", "pdf_complete_extractor.py")
        
        if not os.path.exists(extract_script):
            logger.error(f"Extract script not found at {extract_script}")
            raise HTTPException(status_code=500, detail=f"Extract script not found at {extract_script}")
            
        cmd = [
            python_executable,
            extract_script,
            input_file_path,
            "--output", output_dir,
            "--max-images", str(max_images)
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Execute the command
        result = await run_cli_command(cmd, timeout=300)
        
        if result["return_code"] != 0:
            logger.error(f"Command failed: {result}")
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {result['stderr']}")
        
        logger.info(f"Command completed successfully")
        
        # Check that output files were generated
        output_files = list(Path(output_dir).glob("**/*"))
        logger.info(f"Generated files: {[str(f) for f in output_files]}")
        
        if not output_files:
            logger.error("No output files were generated")
            raise HTTPException(status_code=500, detail="No output files were generated")
        
        # Handle the requested output format
        if format and format.lower() == "zip":
            # Create a ZIP filename based on the original PDF name
            zip_filename = f"{file.filename.rsplit('.', 1)[0]}_extraction.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            logger.info(f"Creating ZIP file at: {zip_path}")
            
            # Use shutil.make_archive for reliability
            base_name = zip_path.rsplit('.', 1)[0]  # remove .zip extension for make_archive
            logger.info(f"Zipping directory: {output_dir} to {base_name}")
            
            archive_path = shutil.make_archive(base_name, 'zip', output_dir)
            logger.info(f"Created ZIP archive at: {archive_path}")
            
            # Verify the ZIP file was created
            if not os.path.exists(archive_path):
                logger.error(f"Failed to create ZIP file at: {archive_path}")
                raise HTTPException(status_code=500, detail="Failed to create ZIP file")
            
            # Verify the ZIP file is not empty
            zip_size = os.path.getsize(archive_path)
            logger.info(f"ZIP file size: {zip_size} bytes")
            
            if zip_size == 0:
                logger.error("Created ZIP file is empty")
                raise HTTPException(status_code=500, detail="Created ZIP file is empty")
            
            # Return the ZIP file with proper headers
            headers = {
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Type, Content-Length",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate" 
            }
            
            logger.info(f"Returning ZIP file response with headers: {headers}")
            
            # Directement retourner le fichier avec FileResponse plutôt que StreamingResponse
            return FileResponse(
                path=archive_path,
                filename=zip_filename,
                media_type="application/zip",
                headers=headers
            )
            
        else:  # format.lower() == "json" ou format par défaut
            # Find the JSON result file
            result_files = list(Path(output_dir).glob("*_complete.json"))
            
            if not result_files:
                # Chercher n'importe quel fichier JSON si pas de fichier complet
                result_files = list(Path(output_dir).glob("*.json"))
                
            if not result_files:
                logger.error("No JSON result files found")
                raise HTTPException(status_code=500, detail="No JSON result files found")
            
            result_file = result_files[0]  # Take the first JSON file
            logger.info(f"Returning JSON file: {result_file}")
            
            # Return the JSON file with proper headers
            headers = {
                "Content-Disposition": f"attachment; filename={file.filename.rsplit('.', 1)[0]}_extraction.json",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Type, Content-Length",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate" 
            }
            
            # Directement retourner le fichier avec FileResponse plutôt que StreamingResponse
            return FileResponse(
                path=result_file,
                filename=f"{file.filename.rsplit('.', 1)[0]}_extraction.json",
                media_type="application/json",
                headers=headers
            )
            
    except Exception as e:
        logger.exception(f"Error processing PDF for job_id {job_id}: {str(e)}")
        cleanup_files(temp_dir)
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

@router.post("/extract-text", summary="Extract only text from PDF")
async def extract_text_from_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Extract only text from a PDF file without image analysis.
    
    - **file**: PDF file to process
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input.pdf"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    try:
        # Use extract/pdf_text_extractor.py directly
        extract_script = os.path.join(os.getcwd(), "extract", "pdf_text_extractor.py")
        
        if not os.path.exists(extract_script):
            raise HTTPException(status_code=500, detail=f"Extract script not found at {extract_script}")
            
        result = await run_cli_command(
            [sys.executable, extract_script, str(input_file_path), "--output", str(output_dir)]
        )
        
        # Find the output JSON file
        result_files = list(output_dir.glob("*.json"))
        if not result_files:
            raise HTTPException(status_code=500, detail="Processing completed but no output file was generated")
        
        result_file = result_files[0]
        
        # Return the file to the client
        return FileResponse(
            path=result_file,
            filename=f"text_extraction_{file.filename}.json",
            media_type="application/json",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")

@router.post("/extract-structured", summary="Extract structured data from PDF")
async def extract_structured_from_pdf(
    file: UploadFile = File(...),
    schema: Optional[str] = Form(None, description="JSON schema for structured extraction"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Extract structured data from a PDF file using a specified schema (using Outlines).
    
    - **file**: PDF file to process
    - **schema**: Optional JSON schema for structured extraction
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input.pdf"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    # Save schema if provided
    schema_path = None
    if schema:
        schema_path = temp_dir / "schema.json"
        with open(schema_path, "w") as f:
            f.write(schema)
    
    try:
        # Use extract/pdf_structured_extractor.py directly
        extract_script = os.path.join(os.getcwd(), "extract", "pdf_structured_extractor.py")
        
        if not os.path.exists(extract_script):
            raise HTTPException(status_code=500, detail=f"Extract script not found at {extract_script}")
            
        cmd = [sys.executable, extract_script, str(input_file_path), "--output", str(output_dir)]
        
        if schema_path:
            cmd.extend(["--schema", str(schema_path)])
        
        # Run the command
        result = await run_cli_command(cmd)
        
        # Find the output JSON file
        result_files = list(output_dir.glob("*.json"))
        if not result_files:
            raise HTTPException(status_code=500, detail="Processing completed but no output file was generated")
        
        result_file = result_files[0]
        
        # Return the file to the client
        return FileResponse(
            path=result_file,
            filename=f"structured_extraction_{file.filename}.json",
            media_type="application/json",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error extracting structured data: {str(e)}") 