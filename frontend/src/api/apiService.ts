/**
 * API service for DataFlow AI
 * Handles all communication with the backend API
 */

const API_BASE_URL = "/api";

interface ApiError {
  error: string;
  type?: string;
  path?: string;
}

/**
 * Process a PDF file
 */
export async function processFile(
  file: File,
  endpoint: string,
  options: Record<string, any> = {}
): Promise<Response> {
  const formData = new FormData();
  formData.append("file", file);
  
  // Add all options to the form data
  Object.entries(options).forEach(([key, value]) => {
    if (typeof value === "boolean") {
      formData.append(key, value ? "true" : "false");
    } else if (value !== null && value !== undefined) {
      formData.append(key, value.toString());
    }
  });
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    body: formData,
  });
  
  if (!response.ok) {
    const errorData = await response.json() as ApiError;
    throw new Error(errorData.error || `Error: ${response.status} ${response.statusText}`);
  }
  
  return response;
}

/**
 * Process a PDF file for extraction
 */
export async function processPdf(
  file: File,
  mode: "complete" | "text-only" | "structured" = "complete",
  maxImages: number = 10,
  schema?: string
): Promise<Blob> {
  let endpoint = "/pdf/extract-images";
  if (mode === "text-only") {
    endpoint = "/pdf/extract-text";
  } else if (mode === "structured") {
    endpoint = "/pdf/extract-structured";
  }
  
  const options: Record<string, any> = { max_images: maxImages };
  if (schema) {
    options.schema = schema;
  }
  
  const response = await processFile(file, endpoint, options);
  return await response.blob();
}

/**
 * Process a JSON file
 */
export async function processJson(
  file: File,
  llmEnrichment: boolean = false,
  preserveSource: boolean = false
): Promise<Blob> {
  const response = await processFile(file, "/json/process", {
    llm_enrichment: llmEnrichment,
    preserve_source: preserveSource,
  });
  
  return await response.blob();
}

/**
 * Clean sensitive data from a JSON file
 */
export async function cleanJson(
  file: File,
  recursive: boolean = false
): Promise<Blob> {
  const response = await processFile(file, "/json/clean", {
    recursive,
  });
  
  return await response.blob();
}

/**
 * Compress a JSON file
 */
export async function compressJson(
  file: File,
  compressionLevel: number = 19,
  keepOriginal: boolean = false
): Promise<Blob> {
  const response = await processFile(file, "/json/compress", {
    compression_level: compressionLevel,
    keep_original: keepOriginal,
  });
  
  return await response.blob();
}

/**
 * Find matches between JIRA and Confluence files
 */
export async function matchFiles(
  jiraFile: File,
  confluenceFile: File
): Promise<Blob> {
  const formData = new FormData();
  formData.append("jira_file", jiraFile);
  formData.append("confluence_file", confluenceFile);
  
  const response = await fetch(`${API_BASE_URL}/json/match`, {
    method: "POST",
    body: formData,
  });
  
  if (!response.ok) {
    const errorData = await response.json() as ApiError;
    throw new Error(errorData.error || `Error: ${response.status} ${response.statusText}`);
  }
  
  return await response.blob();
}

/**
 * Run unified processing with LLM enrichment
 */
export async function unifiedProcess(
  jiraFiles: File[],
  confluenceFiles: File[] = [],
  compress: boolean = false
): Promise<Blob> {
  const formData = new FormData();
  
  // Add all JIRA files
  jiraFiles.forEach((file) => {
    formData.append("jira_files", file);
  });
  
  // Add all Confluence files
  confluenceFiles.forEach((file) => {
    formData.append("confluence_files", file);
  });
  
  // Add options
  formData.append("compress", compress ? "true" : "false");
  
  const response = await fetch(`${API_BASE_URL}/llm/unified`, {
    method: "POST",
    body: formData,
  });
  
  if (!response.ok) {
    const errorData = await response.json() as ApiError;
    throw new Error(errorData.error || `Error: ${response.status} ${response.statusText}`);
  }
  
  return await response.blob();
}

/**
 * Enrich text content with LLM
 */
export async function enrichText(content: string): Promise<any> {
  const formData = new FormData();
  formData.append("content", content);
  
  const response = await fetch(`${API_BASE_URL}/llm/enrich-text`, {
    method: "POST",
    body: formData,
  });
  
  if (!response.ok) {
    const errorData = await response.json() as ApiError;
    throw new Error(errorData.error || `Error: ${response.status} ${response.statusText}`);
  }
  
  return await response.json();
}

/**
 * Change the language setting in the backend
 * @param language The language code ('fr' or 'en')
 */
export const setLanguage = async (language: string): Promise<void> => {
  try {
    await fetch(`${API_BASE_URL}/settings/language`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ language }),
    });
  } catch (error) {
    console.error('Error setting language:', error);
    throw error;
  }
}; 