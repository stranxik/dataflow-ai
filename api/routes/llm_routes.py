"""
LLM enrichment routes for DataFlow AI API.
These endpoints handle LLM enrichment operations using the existing CLI.
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

@router.post("/unified", summary="Run unified processing with LLM enrichment")
async def unified_process(
    jira_files: List[UploadFile] = File(..., description="JIRA JSON files to process"),
    confluence_files: Optional[List[UploadFile]] = File(None, description="Confluence JSON files to process (optional)"),
    compress: bool = Form(True, description="Compress output files (default: True)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Run a unified processing pipeline that includes JIRA and Confluence file processing, 
    matching, and LLM enrichment.
    
    - **jira_files**: One or more JIRA JSON files
    - **confluence_files**: Optional Confluence JSON files
    - **compress**: Whether to compress output files (default: True)
    """
    # Validate file types
    for file in jira_files + (confluence_files or []):
        if not file.filename.lower().endswith('.json'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be a JSON document")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    jira_dir = temp_dir / "jira"
    confluence_dir = temp_dir / "confluence"
    output_dir = temp_dir / "output"
    
    jira_dir.mkdir()
    confluence_dir.mkdir()
    output_dir.mkdir()
    
    # Save uploaded files
    jira_paths = []
    for i, file in enumerate(jira_files):
        file_path = jira_dir / f"jira_{i}.json"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        jira_paths.append(str(file_path))
    
    confluence_paths = []
    if confluence_files:
        for i, file in enumerate(confluence_files):
            file_path = confluence_dir / f"confluence_{i}.json"
            with open(file_path, "wb") as f:
                f.write(await file.read())
            confluence_paths.append(str(file_path))
    
    try:
        # Construct command
        cmd = ["python", "-m", "cli.cli", "unified"] + jira_paths
        
        if confluence_paths:
            cmd.extend(["--confluence"] + confluence_paths)
        
        cmd.extend(["--output-dir", str(output_dir)])
        
        # Toujours activer la compression, quelles que soient les options du frontend
        cmd.append("--compress")
        
        # Run the CLI command
        result = await run_cli_command(cmd)
        
        # Check for llm_ready directory which contains the enriched files
        llm_ready_dir = output_dir / "llm_ready"
        
        if not llm_ready_dir.exists() or not any(llm_ready_dir.iterdir()):
            raise HTTPException(status_code=500, detail="Processing completed but no enriched files were generated")
        
        # Create a zip file with all results
        import zipfile
        zip_path = temp_dir / "enriched_results.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add all files from the output directory recursively
            for folder_path, _, filenames in os.walk(output_dir):
                folder = Path(folder_path)
                for filename in filenames:
                    file_path = folder / filename
                    zipf.write(
                        file_path, 
                        arcname=str(file_path.relative_to(output_dir))
                    )
        
        # Return the zip file
        return FileResponse(
            path=zip_path,
            filename="enriched_results.zip",
            media_type="application/zip",
            # Clean up after sending
            background=BackgroundTask(lambda: cleanup_files([temp_dir]))
        )
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error in unified processing: {str(e)}")

@router.post("/enrich-text", summary="Enrich text content with LLM")
async def enrich_text(
    content: str = Form(..., description="Text content to enrich"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Enrich raw text content with LLM analysis (summary, keywords, entities, sentiment).
    
    - **content**: Text content to analyze
    """
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Save content to a text file
    input_file_path = temp_dir / "input.txt"
    with open(input_file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    # Create a small JSON wrapper for the content
    json_wrapper_path = temp_dir / "wrapped_content.json"
    with open(json_wrapper_path, "w", encoding="utf-8") as f:
        f.write(f'{{"items": [{{"id": "text1", "content": {{"text": {content!r}}}}}]}}')
    
    # Output path
    output_file_path = temp_dir / "enriched.json"
    
    try:
        # Run the CLI command for processing with LLM enrichment
        result = await run_cli_command(
            ["python", "-m", "cli.cli", "process", 
             str(json_wrapper_path), "--llm", 
             "--output", str(output_file_path)]
        )
        
        # Verify the output file exists
        if not output_file_path.exists():
            raise HTTPException(status_code=500, detail="Enrichment completed but no output file was generated")
        
        # Read the enriched result
        import json
        with open(output_file_path, "r", encoding="utf-8") as f:
            enriched_data = json.load(f)
        
        # Extract just the analysis part
        if "items" in enriched_data and len(enriched_data["items"]) > 0:
            analysis = enriched_data["items"][0].get("analysis", {})
            return JSONResponse(content=analysis)
        else:
            raise HTTPException(status_code=500, detail="Enrichment completed but no analysis was generated")
        
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error in LLM enrichment: {str(e)}")
    finally:
        # Clean up
        background_tasks.add_task(cleanup_files, [temp_dir]) 