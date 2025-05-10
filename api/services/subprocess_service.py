"""
Subprocess management service for DataFlow AI API.
Handles executing CLI commands asynchronously and securely.
"""
import asyncio
import logging
import os
import subprocess
from typing import List, Dict, Optional, Any, Union, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("subprocess_service")

# Maximum execution time for a command in seconds
MAX_EXECUTION_TIME = 1800  # 30 minutes

async def run_cli_command(
    command: List[str], 
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = MAX_EXECUTION_TIME
) -> Dict[str, Any]:
    """
    Run a CLI command asynchronously using asyncio.subprocess.
    
    Args:
        command: List of command arguments
        env: Optional environment variables to set
        cwd: Optional working directory
        timeout: Optional timeout in seconds
        
    Returns:
        Dictionary with stdout, stderr, and return_code
        
    Raises:
        Exception: If command execution fails or times out
    """
    # Prepare environment
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    
    logger.info(f"Running command: {' '.join(command)}")
    
    try:
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=process_env,
            cwd=cwd
        )
        
        # Wait for the process to complete with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            logger.info(f"Command completed with return code: {process.returncode}")
            
            # Check for errors
            if process.returncode != 0:
                logger.error(f"Command failed with return code {process.returncode}")
                logger.error(f"Command stderr: {stderr}")
                raise Exception(f"Command failed with return code {process.returncode}: {stderr}")
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode
            }
            
        except asyncio.TimeoutError:
            # Kill the process if it times out
            logger.error(f"Command timed out after {timeout} seconds")
            
            try:
                process.kill()
            except Exception as e:
                logger.error(f"Error killing process: {str(e)}")
                
            raise Exception(f"Command timed out after {timeout} seconds")
            
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        raise

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
    if len(command) < 3 or command[1] != "-m" or not command[2].startswith(("cli.", "tools.")):
        raise ValueError("Only modules within cli. and tools. are allowed")
    
    # Return the sanitized command
    return command 