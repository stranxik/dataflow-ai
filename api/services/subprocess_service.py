"""
Subprocess management service for DataFlow AI API.
Handles executing CLI commands asynchronously and securely.
"""
import asyncio
import logging
import os
import sys
import subprocess
import importlib.util
from typing import List, Dict, Optional, Any, Union, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("subprocess_service")

# Maximum execution time for a command in seconds
MAX_EXECUTION_TIME = 1800  # 30 minutes

async def run_cli_command(
    cmd: List[str], 
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = 120
) -> Dict[str, Any]:
    """
    Run a command asynchronously and return stdout, stderr, and return code.
    
    Args:
        cmd: Command to run (list of arguments)
        env: Environment variables to pass to the command
        cwd: Working directory for the command
        timeout: Timeout in seconds
    """
    logger.info(f"Running command: {' '.join(cmd)}")
    logger.info(f"Working directory: {cwd or os.getcwd()}")
    
    # Préparer l'environnement pour le sous-processus
    if env is None:
        env = {}
    
    # Combiner avec les variables d'environnement actuelles
    merged_env = os.environ.copy()
    merged_env.update(env)
    
    # Ajouter PYTHONPATH pour s'assurer que tous les modules sont trouvables
    project_root = os.environ.get("BASE_PATH", os.getcwd())
    
    if "PYTHONPATH" in merged_env:
        merged_env["PYTHONPATH"] = f"{project_root}:{merged_env['PYTHONPATH']}"
    else:
        merged_env["PYTHONPATH"] = project_root
    
    logger.info(f"Timeout: {timeout} seconds")
    logger.info(f"Project root: {project_root}")
    logger.info(f"PYTHONPATH: {merged_env.get('PYTHONPATH')}")
    
    # Vérifier si les modules sont accessibles
    if cmd[0] == "python" and len(cmd) > 2 and cmd[1] == "-m" and cmd[2].startswith("cli."):
        # Vérifier si le module cli.py existe
        cli_path = os.path.join(project_root, "cli", "cli.py")
        if not os.path.exists(cli_path):
            logger.error(f"CLI module not found at {cli_path}")
        else:
            logger.info(f"CLI module found at {cli_path}")
    
    # Vérifier si l'extrait existe
    extract_dir = os.path.join(project_root, "extract")
    if os.path.exists(extract_dir):
        logger.info(f"Extract directory found at {extract_dir}")
    
    # Log environment variables (excluding sensitive ones)
    safe_env = {k: v if not _is_sensitive_key(k) else '***' for k, v in merged_env.items()}
    logger.info(f"Environment variables: {str(safe_env)[:200]}...")
    
    try:
        logger.info(f"Starting subprocess with command: {' '.join(cmd)}")
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
            cwd=cwd
        )
        
        logger.info(f"Subprocess started with PID: {process.pid}")
        logger.info(f"Waiting for process to complete (timeout: {timeout}s)...")
        
        # Wait for process with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            # Decode stdout and stderr
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            logger.info(f"Command completed with return code: {process.returncode}")
            if stdout:
                logger.info(f"Command stdout (first 200 chars): {stdout[:200]}")
            if stderr:
                logger.error(f"Command stderr: {stderr}")
            
            if process.returncode != 0:
                logger.error(f"Command failed with return code {process.returncode}")
                logger.error(f"Command: {' '.join(cmd)}")
                logger.error(f"Working directory: {cwd or os.getcwd()}")
                logger.error(f"Command stderr: {stderr}")
                logger.error(f"Error executing command: Command failed with return code {process.returncode}: {stderr}")
                
                # Détails techniques pour faciliter le débogage
                traceback_info = f"""
                Traceback (most recent call last):
                  File "{__file__}", line {sys._getframe().f_lineno}, in run_cli_command
                    raise Exception(f"Command failed with return code {process.returncode}: {stderr}")
                Exception: Command failed with return code {process.returncode}: {stderr}
                """
                logger.error(traceback_info)
                
                raise Exception(f"Command failed with return code {process.returncode}: {stderr}")
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")
            process.kill()
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "return_code": -1
            }
            
    except Exception as e:
        logger.exception(f"Error running command: {e}")
        return {
            "stdout": "",
            "stderr": f"Error running command: {str(e)}",
            "return_code": -1
        }

def _is_sensitive_key(key: str) -> bool:
    """Check if an environment variable key is sensitive."""
    sensitive_keys = [
        "key", "token", "secret", "password", "pass", "auth"
    ]
    
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in sensitive_keys)

def sanitize_command(command: List[str]) -> List[str]:
    """
    Sanitize a command to prevent command injection attacks.
    This is a security measure to limit which commands can be executed.
    
    Args:
        command: List of command arguments
        
    Returns:
        Sanitized command list
        
    Raises:
        ValueError: If command is not allowed
    """
    # Only allow Python as the main command
    if not command or command[0] != "python":
        raise ValueError("Only Python commands are allowed")
    
    # Check that the module is within our project
    if len(command) < 3 or command[1] != "-m" or not command[2].startswith(("cli.", "tools.", "extract.")):
        raise ValueError("Only modules within cli., tools., and extract. are allowed")
    
    # Return the sanitized command
    return command 