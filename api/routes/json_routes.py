"""
JSON processing routes for DataFlow AI API.
These endpoints handle JSON file uploads and processing using the existing CLI.
"""
import os
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
import sys
import json
import logging
import aiofiles
import asyncio
import io

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Form, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from api.services.subprocess_service import run_cli_command
from api.services.temp_file_service import create_temp_file, cleanup_files

# Configure logger
logger = logging.getLogger("json_routes")

# Function to clean up temporary files
async def cleanup_temp_files(directory: Path):
    """
    Clean up temporary files and directories after processing
    
    Args:
        directory: Directory to clean up
    """
    if directory.exists():
        try:
            # Use shutil to remove the directory and all its contents
            import shutil
            shutil.rmtree(directory)
            logger.info(f"Cleaned up temporary directory: {directory}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory {directory}: {e}")

router = APIRouter()

@router.post("/process", summary="Process a JSON file")
async def process_json(
    file: UploadFile = File(...),
    llm_enrichment: bool = Form(True, description="Enable LLM enrichment"),
    preserve_source: bool = Form(True, description="Preserve source structure"),
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
    
    logger.info(f"Démarrage du traitement JSON: {file.filename}")
    logger.info(f"Paramètres: llm_enrichment={llm_enrichment}, preserve_source={preserve_source}")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file to temp directory
    input_path = temp_dir / file.filename
    output_path = temp_dir / f"{Path(file.filename).stem}_processed.json"
    
    async with aiofiles.open(input_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    try:
        # Call CLI script through subprocess (better isolation)
        # Note: Pour json-process, input_path est un argument positionnel, pas une option
        cmd = [
            "python", "-m", "cli.cli",
            "json-process",
            str(input_path),       # Input comme argument positionnel
            "--output", str(output_path)
        ]
        
        # Add parameters with explicit values
        if llm_enrichment:
            cmd.append("--llm-enrichment")
            logger.info("Enrichissement LLM activé pour le traitement")
        else:
            cmd.append("--no-llm-enrichment")
            logger.info("Enrichissement LLM désactivé pour le traitement")
        
        if preserve_source:
            cmd.append("--preserve-source")
            logger.info("Préservation de la structure source activée")
        else:
            cmd.append("--no-preserve-source")
            logger.info("Préservation de la structure source désactivée")
        
        logger.info(f"Exécution de la commande: {' '.join(cmd)}")
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Erreur lors du traitement JSON: {stderr.decode()}")
            raise HTTPException(status_code=500, detail=f"Error processing JSON: {stderr.decode()}")
        
        logger.info(f"Traitement JSON terminé avec succès: {stdout.decode()}")
        
        # Check if output file exists
        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Output file was not generated")
        
        # Read the output file
        async with aiofiles.open(output_path, 'rb') as f:
            result = await f.read()
        
        # Schedule cleanup of temp files
        background_tasks.add_task(cleanup_temp_files, temp_dir)
        
        logger.info(f"Fichier JSON traité disponible: {output_path} (taille: {len(result)} octets)")
        
        return StreamingResponse(
            io.BytesIO(result),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={Path(file.filename).stem}_processed.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Exception during JSON processing: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Schedule cleanup of temp files even on error
        background_tasks.add_task(cleanup_temp_files, temp_dir)
        
        # For debugging, check if stderr was populated
        error_msg = str(e)
        if hasattr(e, 'stderr') and e.stderr:
            error_msg += f"\nDetails: {e.stderr.decode()}"
            
        raise HTTPException(status_code=500, detail=f"Error processing JSON: {error_msg}")

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
    output_file_path = temp_dir / f"cleaned_sensitive.json"
    
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    try:
        import logging
        logger = logging.getLogger("json_routes")
        logger.info(f"Processing JSON file: {file.filename}, job_id: {job_id}")
        logger.info(f"Recursive mode: {recursive}")
        
        # Appeler directement le script clean_sensitive_data.py au lieu de passer par cli.py
        script_path = os.path.join(os.getcwd(), "tools", "clean_sensitive_data.py")
        
        if not os.path.exists(script_path):
            logger.error(f"Script not found at {script_path}")
            raise HTTPException(status_code=500, detail=f"Cleaning script not found")
        
        # Préparation de la commande pour appeler directement le script
        cmd = [sys.executable, script_path, str(input_file_path), 
              "--output", str(output_file_path)]
        
        if recursive:
            cmd.append("--recursive")
        
        # Exécution de la commande
        result = await run_cli_command(cmd)
        
        if result["return_code"] != 0:
            logger.error(f"JSON cleaning failed: {result['stderr']}")
            raise HTTPException(status_code=500, detail=f"JSON cleaning failed: {result['stderr']}")
        
        # Verify output file exists
        if not output_file_path.exists():
            logger.error("Cleaning completed but no output file was generated")
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
        logger.error(f"Error cleaning JSON: {str(e)}")
        # Clean up in case of error
        cleanup_files([temp_dir])
        raise HTTPException(status_code=500, detail=f"Error cleaning JSON: {str(e)}")

@router.post("/compress", summary="Compress JSON file or decompress ZST file")
async def compress_json(
    file: UploadFile = File(...),
    compression_level: int = Form(19, description="Compression level (1-22)"),
    keep_original: bool = Form(True, description="Keep original file alongside compressed version"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Compress a JSON file using zstandard or decompress a ZST file.
    
    - **file**: JSON file to compress or ZST file to decompress
    - **compression_level**: Compression level (1-22) - only used for compression
    - **keep_original**: Keep original file alongside compressed version (default: True)
    """
    # Check if this is a compression or decompression operation
    is_compression = file.filename.lower().endswith('.json')
    is_decompression = file.filename.lower().endswith('.zst')
    
    if not (is_compression or is_decompression):
        raise HTTPException(status_code=400, detail="File must be a JSON document or a ZST compressed file")
    
    # Create a unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Create temp directory for this job
    temp_dir = Path(f"/tmp/dataflow_temp/{job_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    input_file_path = temp_dir / f"input{'.json' if is_compression else '.zst'}"
    with open(input_file_path, "wb") as f:
        f.write(await file.read())
    
    try:
        if is_compression:
            # Utiliser le module zstandard directement pour avoir le format correct
            try:
                import zstandard as zstd
                import json
                import logging
                
                logger = logging.getLogger("json_routes")
                logger.info(f"Compressing JSON file with compression level {compression_level}")
                
                # Lire le fichier JSON
                with open(input_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Créer le fichier de sortie compressé avec la bonne extension
                compressed_file_path = temp_dir / f"{file.filename}.zst"
                
                # Sérialiser en JSON et compresser directement
                json_str = json.dumps(data)
                compressor = zstd.ZstdCompressor(level=compression_level)
                
                with open(compressed_file_path, 'wb') as f:
                    compressed_data = compressor.compress(json_str.encode('utf-8'))
                    f.write(compressed_data)
                
                # Retourner le fichier compressé
                return FileResponse(
                    path=compressed_file_path,
                    filename=f"{file.filename}.zst",
                    media_type="application/zstd",
                    background=BackgroundTask(lambda: cleanup_files([temp_dir]))
                )
                
            except Exception as e:
                logger = logging.getLogger("json_routes")
                logger.error(f"Error compressing file: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Error compressing file: {str(e)}")
        
        else:  # Decompression
            # Préparer le fichier de sortie
            original_filename = file.filename.replace('.zst', '')
            output_json_path = temp_dir / original_filename

            # Décompresser le fichier
            try:
                import zstandard as zstd
                import zipfile
                import logging
                import json  # Importer json pour vérifier la validité du fichier décompressé
                
                logger = logging.getLogger("json_routes")
                logger.info(f"Decompressing file: {file.filename}")
                
                # Vérifier si c'est un fichier ZIP ou ZST en examinant la signature
                with open(input_file_path, 'rb') as test_file:
                    header = test_file.read(4)
                    # Rewind to beginning of file
                    test_file.seek(0)
                
                # Si c'est un fichier ZIP (signature PK\x03\x04 = 504b0304 en hex)
                if header.startswith(b'PK\x03\x04'):
                    logger.info("Detected ZIP file with .zst extension. Decompressing as ZIP file.")
                    
                    # Traiter comme un fichier ZIP
                    try:
                        with zipfile.ZipFile(input_file_path, 'r') as zip_ref:
                            # Lister les fichiers dans le ZIP
                            json_files = [f for f in zip_ref.namelist() if f.lower().endswith('.json')]
                            
                            if not json_files:
                                raise ValueError("Le fichier ZIP ne contient pas de fichiers JSON.")
                            
                            # Extraire le premier fichier JSON trouvé
                            zip_ref.extract(json_files[0], path=temp_dir)
                            extracted_path = temp_dir / json_files[0]
                            
                            # Renommer le fichier extrait si nécessaire
                            if str(extracted_path) != str(output_json_path):
                                import shutil
                                shutil.move(extracted_path, output_json_path)
                    
                    except zipfile.BadZipFile:
                        raise ValueError("Le fichier n'est ni un ZIP valide ni un fichier ZST.")
                
                # Sinon, essayer de le décompresser comme un fichier ZST (signature 0x28 0xB5 0x2F 0xFD)
                else:
                    logger.info("Processing as Zstandard file.")
                    try:
                        # Signature magique de Zstandard: 0x28 0xB5 0x2F 0xFD
                        if header.startswith(b'\x28\xB5\x2F\xFD'):
                            logger.info("Detected valid Zstandard signature.")
                        
                        with open(input_file_path, 'rb') as compressed_file:
                            with open(output_json_path, 'wb') as decompressed_file:
                                dctx = zstd.ZstdDecompressor()
                                dctx.copy_stream(compressed_file, decompressed_file)
                    except Exception as ze:
                        raise ValueError(f"Erreur lors de la décompression du fichier ZST: {str(ze)}")
                        
                # Vérifier que le fichier JSON est valide
                try:
                    with open(output_json_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                        logger.info(f"Successfully validated JSON in {output_json_path}")
                except json.JSONDecodeError as je:
                    logger.error(f"Invalid JSON after decompression: {str(je)}")
                    raise ValueError(f"Le fichier décompressé n'est pas un fichier JSON valide: {str(je)}")
                        
            except Exception as e:
                # Capturer et logger l'erreur
                import logging
                logger = logging.getLogger("json_routes")
                logger.error(f"Error decompressing file: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Error decompressing file: {str(e)}")
            
            # Vérifier que le fichier décompressé existe
            if not output_json_path.exists():
                raise HTTPException(status_code=500, detail="Decompression failed, no output file was generated")
            
            # Log file size and stats
            logger.info(f"Decompressed file size: {os.path.getsize(output_json_path)} bytes")
            logger.info(f"Returning file: {output_json_path} as {original_filename}")
                
            # Retourner le fichier JSON décompressé avec le bon type MIME
            return FileResponse(
                path=output_json_path,
                filename=original_filename,
                media_type="application/json",
                # Clean up after sending
                background=BackgroundTask(lambda: cleanup_files([temp_dir]))
            )
            
    except Exception as e:
        # Clean up in case of error
        cleanup_files([temp_dir])
        import logging
        logger = logging.getLogger("json_routes")
        logger.error(f"Error in compress_json endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error {'compressing' if is_compression else 'decompressing'} file: {str(e)}")

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