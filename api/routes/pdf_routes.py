"""
PDF processing routes for DataFlow AI API.
These endpoints handle PDF file uploads and processing using the existing CLI.
"""
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Form, Query
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from api.services.subprocess_service import run_cli_command
from api.services.temp_file_service import create_temp_file, cleanup_files

router = APIRouter()

@router.post("/extract-images", summary="Extract and analyze images from PDF")
async def extract_images_from_pdf(
    file: UploadFile = File(...),
    max_images: Optional[int] = Query(10, description="Maximum number of images to extract and analyze"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Extract text and analyze images from a PDF file using OpenAI Vision.
    
    - **file**: PDF file to process
    - **max_images**: Maximum number of images to analyze
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
        # Run the CLI command
        result = await run_cli_command(
            ["python", "-m", "cli.cli", "extract-images", "complete", 
             str(input_file_path), "--output-dir", str(output_dir), 
             "--max-images", str(max_images)]
        )
        
        # Find the output JSON file
        result_files = list(output_dir.glob("*.json"))
        if not result_files:
            raise HTTPException(status_code=500, detail="Processing completed but no output file was generated")
        
        result_file = result_files[0]
        
        # Return the file to the client
        return FileResponse(
            path=result_file,
            filename=f"pdf_analysis_{file.filename}.json",
            media_type="application/json",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

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
        # Run the CLI command - using 'text-only' mode
        result = await run_cli_command(
            ["python", "-m", "cli.cli", "extract-images", "text-only", 
             str(input_file_path), "--output-dir", str(output_dir)]
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
        # Prepare CLI command
        cmd = ["python", "-m", "cli.cli", "extract-images", "structured", 
               str(input_file_path), "--output-dir", str(output_dir)]
        
        if schema_path:
            cmd.extend(["--schema", str(schema_path)])
        
        # Run the CLI command
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