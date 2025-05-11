"""
Request models for DataFlow AI API.
Defines Pydantic models for API request validation.
"""
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

class ProcessingOptions(BaseModel):
    """Options for processing JSON files."""
    llm_enrichment: bool = Field(False, description="Enable LLM enrichment")
    preserve_source: bool = Field(False, description="Preserve source structure")
    compress_output: bool = Field(False, description="Compress output files")

class PDFExtractionMode(str, Enum):
    """PDF extraction modes."""
    COMPLETE = "complete"  # Extract text and analyze images
    TEXT_ONLY = "text-only"  # Extract text only
    STRUCTURED = "structured"  # Extract structured data with a schema

class PDFExtractionOptions(BaseModel):
    """Options for PDF extraction."""
    mode: PDFExtractionMode = Field(PDFExtractionMode.COMPLETE, description="Extraction mode")
    max_images: Optional[int] = Field(10, description="Maximum number of images to analyze")
    schema: Optional[str] = Field(None, description="JSON schema for structured extraction")
    
    @validator('max_images')
    def validate_max_images(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("max_images must be between 0 and 100")
        return v

class CompressionOptions(BaseModel):
    """Options for JSON compression."""
    level: int = Field(19, description="Compression level (1-22)")
    keep_originals: bool = Field(False, description="Keep original files alongside compressed versions")
    
    @validator('level')
    def validate_level(cls, v):
        if v < 1 or v > 22:
            raise ValueError("compression level must be between 1 and 22")
        return v

class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status (pending, running, completed, failed)")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    result_url: Optional[str] = Field(None, description="URL to download the result if completed")
    error: Optional[str] = Field(None, description="Error message if failed") 