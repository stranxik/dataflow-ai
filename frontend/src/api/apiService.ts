/**
 * API service for DataFlow AI
 * Handles all communication with the backend API
 */

const API_BASE_URL = "/api";

// Récupérer l'API key depuis les variables d'environnement
// D'abord essayer window.env (pour Docker), puis import.meta.env (pour dev)
const API_KEY = (window as any).env?.VITE_API_KEY || import.meta.env?.VITE_API_KEY || '';

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

  // Log the request details for debugging
  console.log(`Making API request to ${API_BASE_URL}${endpoint}`);
  console.log('Headers:', { 'X-API-Key': API_KEY ? '***' : 'Not set' });
  console.log('FormData contains:', Array.from(formData.entries()).map(([k, v]) => 
    typeof v === 'string' ? `${k}: ${v}` : `${k}: [File]`
  ));
  
  try {
    // Déterminer le bon en-tête Accept selon le format demandé
    let acceptHeader = 'application/json';
    if (options.format === 'zip') {
      acceptHeader = 'application/zip, application/octet-stream';
    }
    
    console.log(`Using Accept header: ${acceptHeader}`);
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: {
        'X-API-Key': API_KEY || '',
        'Accept': acceptHeader
      },
      body: formData,
    });
    
    // Log response details
    console.log(`Response status: ${response.status} ${response.statusText}`);
    console.log(`Response headers:`, Object.fromEntries([...response.headers.entries()]));
    
    if (!response.ok) {
      // For better debugging, try to get error details
      let errorMessage;
      const contentType = response.headers.get('content-type') || '';
      
      if (contentType.includes('application/json')) {
        const errorData = await response.json() as ApiError;
        errorMessage = errorData.error || `Error: ${response.status} ${response.statusText}`;
      } else {
        // Try to read error message from text response
        errorMessage = await response.text();
        // Limit length for readability
        if (errorMessage.length > 200) {
          errorMessage = errorMessage.substring(0, 200) + '...';
        }
        errorMessage = `Error: ${response.status} ${response.statusText} - ${errorMessage}`;
      }
      
      console.error('API error:', errorMessage);
      throw new Error(errorMessage);
    }
    
    return response;
  } catch (error) {
    console.error('Network or processing error:', error);
    throw error;
  }
}

/**
 * Process a PDF file for extraction
 */
export async function processPdf(
  file: File,
  mode: "complete" | "text-only" | "structured" = "complete",
  maxImages: number = 10,
  schema?: string,
  format: "json" | "zip" = "json"
): Promise<Blob> {
  console.log(`Processing PDF: ${file.name}, mode: ${mode}, maxImages: ${maxImages}, format: ${format}`);
  
  // Toujours utiliser extract-images pour le mode complet
  let endpoint = "/pdf/extract-images";
  if (mode === "text-only") {
    endpoint = "/pdf/extract-text";
  } else if (mode === "structured") {
    endpoint = "/pdf/extract-structured";
  }
  
  const options: Record<string, any> = { 
    max_images: maxImages,
    format: format
  };
  
  if (schema) {
    options.schema = schema;
  }
  
  console.log(`Calling endpoint: ${endpoint} with options:`, options);
  
  try {
    const response = await processFile(file, endpoint, options);
    const blob = await response.blob();
    
    // Vérifier que le blob est valide et a un type de contenu approprié
    console.log(`Response blob type: ${blob.type}, size: ${blob.size} bytes`);
    
    // Corriger le type MIME pour les fichiers ZIP si nécessaire
    if (format === 'zip') {
      // Si on a demandé un ZIP, on devrait recevoir un ZIP
      if (!blob.type.includes('zip') && !blob.type.includes('octet-stream')) {
        console.warn(`Warning: Expected zip format but got ${blob.type}`);
        
        // Si le contenu est HTML et de petite taille, il s'agit probablement d'une erreur
        if (blob.type.includes('html') && blob.size < 1000) {
          const text = await blob.text();
          console.error('HTML response instead of ZIP:', text.substring(0, 200));
          throw new Error('Received HTML instead of ZIP file. API error or redirect occurred.');
        }
        
        // Si c'est du JSON et qu'on attendait un ZIP, il y a eu une erreur
        if (blob.type.includes('json')) {
          // Essayons de voir si c'est un message d'erreur
          try {
            const jsonText = await blob.text();
            const jsonContent = JSON.parse(jsonText);
            if (jsonContent.detail) {
              throw new Error(`API error: ${jsonContent.detail}`);
            }
          } catch (err) {
            // En cas d'erreur de parsing, on continue avec notre correction
            console.warn('Failed to parse potential error response as JSON');
          }
        }
        
        // Tenter de corriger le type MIME
        return new Blob([blob], { type: 'application/zip' });
      }
      return blob;
    } else {
      // Pour le format JSON, vérifier si on a bien reçu du JSON
      if (!blob.type.includes('json')) {
        console.warn(`Warning: Expected JSON but got ${blob.type}`);
        // Tenter de corriger le type MIME
        return new Blob([blob], { type: 'application/json' });
      }
      return blob;
    }
  } catch (error) {
    console.error('Error in processPdf:', error);
    throw error;
  }
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
    headers: {
      'X-API-Key': API_KEY || ''
    },
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
    headers: {
      'X-API-Key': API_KEY || ''
    },
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
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY || ''
    },
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
        'X-API-Key': API_KEY || ''
      },
      body: JSON.stringify({ language }),
    });
  } catch (error) {
    console.error('Error setting language:', error);
    throw error;
  }
}; 