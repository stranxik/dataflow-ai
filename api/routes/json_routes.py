"""
JSON processing routes for DataFlow AI API.
These endpoints handle JSON file uploads and processing using the existing CLI.
"""
import os
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Form, Query
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from api.services.subprocess_service import run_cli_command
from api.services.temp_file_service import create_temp_file, cleanup_files

router = APIRouter()

@router.post("/process", summary="Process a JSON file")
async def process_json(
    file: UploadFile = File(...),
    llm_enrichment: bool = Form(False, description="Enable LLM enrichment"),
    preserve_source: bool = Form(False, description="Preserve source structure"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Process a JSON file using the existing CLI functionality.
    
    - **file**: JSON file to process
    - **llm_enrichment**: Enable LLM enrichment for better semantic search
    - **preserve_source**: Preserve the source structure of the JSON
    """
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON document")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input.json"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    # Output file path
    output_file_path = output_dir / f"processed_{file.filename}"
    
    try:
        # Prepare command
        cmd = ["python", "-m", "cli.cli", "process", str(input_file_path), 
               "--output", str(output_file_path)]
        
        # Add options based on form parameters
        if llm_enrichment:
            cmd.append("--llm")
        
        if preserve_source:
            cmd.append("--preserve-source")
        
        # Run the CLI command
        result = await run_cli_command(cmd)
        
        # Verify output file exists
        if not output_file_path.exists():
            raise HTTPException(status_code=500, detail="Processing completed but no output file was generated")
        
        # Return the file to the client
        return FileResponse(
            path=output_file_path,
            filename=f"processed_{file.filename}",
            media_type="application/json",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error processing JSON: {str(e)}")

@router.post("/chunks", summary="Split a large JSON file into chunks")
async def split_json_chunks(
    file: UploadFile = File(...),
    items_per_file: int = Form(500, description="Number of items per chunk"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Split a large JSON file into smaller chunks.
    
    - **file**: Large JSON file to split
    - **items_per_file**: Number of items per output file
    """
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON document")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input.json"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    try:
        # Run the CLI command
        result = await run_cli_command(
            ["python", "-m", "cli.cli", "chunks", str(input_file_path), 
             "--output-dir", str(output_dir),
             "--items-per-file", str(items_per_file)]
        )
        
        # Check if output files were created
        output_files = list(output_dir.glob("*.json"))
        if not output_files:
            raise HTTPException(status_code=500, detail="Processing completed but no output files were generated")
        
        # Create a zip file with all chunks
        import zipfile
        zip_path = temp_dir / f"chunks_{file.filename.replace('.json', '')}.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for f in output_files:
                zipf.write(f, arcname=f.name)
        
        # Return the zip file
        return FileResponse(
            path=zip_path,
            filename=f"chunks_{file.filename.replace('.json', '')}.zip",
            media_type="application/zip",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error chunking JSON: {str(e)}")

@router.post("/clean", summary="Clean sensitive data from JSON file")
async def clean_json(
    file: UploadFile = File(...),
    recursive: bool = Form(False, description="Clean recursively through nested objects"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Clean sensitive data from a JSON file.
    
    - **file**: JSON file to clean
    - **recursive**: Clean recursively through nested objects
    """
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON document")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input.json"
    output_file_path = temp_dir / f"cleaned_{file.filename}"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    try:
        # Prepare command
        cmd = ["python", "-m", "cli.cli", "clean", str(input_file_path), 
               "--output", str(output_file_path)]
        
        if recursive:
            cmd.append("--recursive")
        
        # Run the CLI command
        result = await run_cli_command(cmd)
        
        # Verify output file exists
        if not output_file_path.exists():
            raise HTTPException(status_code=500, detail="Cleaning completed but no output file was generated")
        
        # Return the file to the client
        return FileResponse(
            path=output_file_path,
            filename=f"cleaned_{file.filename}",
            media_type="application/json",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error cleaning JSON: {str(e)}")

@router.post("/compress", summary="Compress JSON file")
async def compress_json(
    file: UploadFile = File(...),
    compression_level: int = Form(19, description="Compression level (1-22)"),
    keep_original: bool = Form(True, description="Keep original file alongside compressed version"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Compress a JSON file using zstandard.
    
    - **file**: JSON file to compress
    - **compression_level**: Compression level (1-22)
    - **keep_original**: Keep original file alongside compressed version (default: True)
    """
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON document")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input.json"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    try:
        # Prepare command - Force keep_originals to always be True
        cmd = ["python", "-m", "cli.cli", "compress", str(temp_dir), 
               "--level", str(compression_level),
               "--keep-originals"]  # Always keep originals regardless of frontend setting
        
        # Run the CLI command
        result = await run_cli_command(cmd)
        
        # Find the compressed file
        compressed_file = next(temp_dir.glob("*.zst"), None)
        if not compressed_file:
            raise HTTPException(status_code=500, detail="Compression completed but no compressed file was generated")
        
        # Create a zip file containing both the original JSON and compressed file
        import zipfile
        zip_path = temp_dir / f"{file.filename.replace('.json', '')}_compressed.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add compressed file to zip
            zipf.write(compressed_file, arcname=f"{file.filename}.zst")
            
            # Add original JSON file (should always exist now that we force --keep-originals)
            original_json = next(temp_dir.glob("*.json"), None)
            if original_json:
                zipf.write(original_json, arcname=file.filename)
            
            # Add compression report if it exists
            report_files = list(temp_dir.glob("compression_report_*.txt"))
            for report_file in report_files:
                zipf.write(report_file, arcname=report_file.name)
            
            # Add human-readable text version if it exists
            text_files = list(temp_dir.glob("*.txt"))
            for text_file in text_files:
                if not text_file.name.startswith("compression_report_"):
                    zipf.write(text_file, arcname=text_file.name)
        
        # Return the zip file
        return FileResponse(
            path=zip_path,
            filename=f"{file.filename.replace('.json', '')}_compressed.zip",
            media_type="application/zip",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error compressing JSON: {str(e)}")

@router.post("/match", summary="Find matches between JIRA and Confluence files")
async def match_json_files(
    jira_file: UploadFile = File(...),
    confluence_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Find matches between JIRA and Confluence JSON files.
    
    - **jira_file**: JIRA JSON file
    - **confluence_file**: Confluence JSON file
    """
    if not jira_file.filename.lower().endswith('.json') or not confluence_file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="Both files must be JSON documents")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded files
    jira_path = temp_dir / "jira.json"
    confluence_path = temp_dir / "confluence.json"
    
    with open(jira_path, "wb") as f:
        f.write(await jira_file.read())
    
    with open(confluence_path, "wb") as f:
        f.write(await confluence_file.read())
    
    try:
        # Run the CLI command
        result = await run_cli_command(
            ["python", "-m", "cli.cli", "match", 
             str(jira_path), str(confluence_path),
             "--output-dir", str(output_dir)]
        )
        
        # Find the matches file
        match_files = list(output_dir.glob("*matches*.json"))
        if not match_files:
            raise HTTPException(status_code=500, detail="Matching completed but no matches file was generated")
        
        match_file = match_files[0]
        
        # Return the file to the client
        return FileResponse(
            path=match_file,
            filename="jira_confluence_matches.json",
            media_type="application/json",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error matching files: {str(e)}") 