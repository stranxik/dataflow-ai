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
  console.log(`Processing JSON: ${file.name}, llmEnrichment: ${llmEnrichment}, preserveSource: ${preserveSource}`);
  
  try {
    const response = await processFile(file, "/json/process", {
      llm_enrichment: llmEnrichment,
      preserve_source: preserveSource,
    });
    
    const blob = await response.blob();
    
    // Vérifier le blob
    console.log(`Response blob type: ${blob.type}, size: ${blob.size} bytes`);
    
    // Si le contenu est HTML et de petite taille, il s'agit probablement d'une erreur
    if (blob.type.includes('html') && blob.size < 1000) {
      const text = await blob.text();
      console.error('HTML response instead of JSON:', text.substring(0, 200));
      throw new Error('Received HTML instead of JSON file. API error or redirect occurred.');
    }
    
    // Si le type MIME n'est pas JSON, corriger
    if (!blob.type.includes('json')) {
      console.warn(`Warning: Expected JSON but got ${blob.type}`);
      return new Blob([blob], { type: 'application/json' });
    }
    
    return blob;
  } catch (error) {
    console.error('Error in processJson:', error);
    throw error;
  }
}

/**
 * Clean sensitive data from a JSON file
 */
export async function cleanJson(
  file: File,
  recursive: boolean = false
): Promise<Blob> {
  console.log(`Cleaning JSON: ${file.name}, recursive: ${recursive}`);
  
  try {
    const response = await processFile(file, "/json/clean", {
      recursive,
    });
    
    const blob = await response.blob();
    
    // Vérifier le blob
    console.log(`Response blob type: ${blob.type}, size: ${blob.size} bytes`);
    
    // Si le contenu est HTML et de petite taille, il s'agit probablement d'une erreur
    if (blob.type.includes('html') && blob.size < 1000) {
      const text = await blob.text();
      console.error('HTML response instead of JSON:', text.substring(0, 200));
      throw new Error('Received HTML instead of JSON file. API error or redirect occurred.');
    }
    
    // Si le type MIME n'est pas JSON, corriger
    if (!blob.type.includes('json')) {
      console.warn(`Warning: Expected JSON but got ${blob.type}`);
      return new Blob([blob], { type: 'application/json' });
    }
    
    return blob;
  } catch (error) {
    console.error('Error in cleanJson:', error);
    throw error;
  }
}

/**
 * Compress a JSON file or decompress a ZST file
 */
export async function compressJson(
  file: File,
  compressionLevel: number = 19, // Niveau par défaut (équilibré)
  keepOriginal: boolean = false
): Promise<Blob> {
  // Déterminer si c'est une compression ou une décompression basé sur l'extension du fichier
  const isCompression = file.name.toLowerCase().endsWith('.json');
  const isDecompression = file.name.toLowerCase().endsWith('.zst');
  
  console.log(`${isCompression ? 'Compressing' : 'Decompressing'} JSON: ${file.name}, compressionLevel: ${compressionLevel}, keepOriginal: ${keepOriginal}`);
  
  try {
    const response = await processFile(file, "/json/compress", {
      compression_level: compressionLevel,
      keep_original: keepOriginal,
    });
    
    const blob = await response.blob();
    
    // Vérifier le blob
    console.log(`Response blob type: ${blob.type}, size: ${blob.size} bytes`);
    
    // Vérifier que le blob est valide
    if (blob.size === 0) {
      throw new Error("Empty response received from server");
    }
    
    // Si c'est une compression, le résultat devrait être un fichier ZST
    if (isCompression) {
      // S'assurer que le type MIME est correct pour ZST
      if (!blob.type.includes('zstd') && !blob.type.includes('octet-stream')) {
        console.warn(`Warning: Expected ZST but got ${blob.type}`);
        return new Blob([blob], { type: 'application/zstd' });
      }
    } 
    // Si c'est une décompression, le résultat devrait être un fichier JSON
    else if (isDecompression) {
      // S'assurer que le type MIME est correct pour JSON
      if (!blob.type.includes('json')) {
        console.warn(`Warning: Expected JSON but got ${blob.type}`);
        
        // Si le contenu est HTML et de petite taille, il s'agit probablement d'une erreur
        if (blob.type.includes('html') && blob.size < 1000) {
          const text = await blob.text();
          console.error('HTML response instead of JSON:', text.substring(0, 200));
          throw new Error('Received HTML instead of JSON file. API error or redirect occurred.');
        }
        
        return new Blob([blob], { type: 'application/json' });
      }
    }
    
    return blob;
  } catch (error) {
    console.error('Error in compressJson:', error);
    throw error;
  }
}

/**
 * Find matches between JIRA and Confluence files
 */
export async function matchFiles(
  jiraFile: File,
  confluenceFile: File
): Promise<Blob> {
  console.log(`Matching files: ${jiraFile.name} with ${confluenceFile.name}`);
  
  try {
    const formData = new FormData();
    formData.append("jira_file", jiraFile);
    formData.append("confluence_file", confluenceFile);
    
    // Log request details
    console.log(`Making API request to ${API_BASE_URL}/json/match`);
    console.log('Headers:', { 'X-API-Key': API_KEY ? '***' : 'Not set' });
    console.log('FormData contains:', ['jira_file: [File]', 'confluence_file: [File]']);
    
    const response = await fetch(`${API_BASE_URL}/json/match`, {
      method: "POST",
      headers: {
        'X-API-Key': API_KEY || ''
      },
      body: formData,
    });
    
    // Log response details
    console.log(`Response status: ${response.status} ${response.statusText}`);
    console.log(`Response headers:`, Object.fromEntries([...response.headers.entries()]));
    
    if (!response.ok) {
      // Try to get error details
      let errorMessage;
      const contentType = response.headers.get('content-type') || '';
      
      if (contentType.includes('application/json')) {
        const errorData = await response.json() as ApiError;
        errorMessage = errorData.error || `Error: ${response.status} ${response.statusText}`;
      } else {
        // Try to read error message from text response
        errorMessage = await response.text();
        if (errorMessage.length > 200) {
          errorMessage = errorMessage.substring(0, 200) + '...';
        }
        errorMessage = `Error: ${response.status} ${response.statusText} - ${errorMessage}`;
      }
      
      console.error('API error:', errorMessage);
      throw new Error(errorMessage);
    }
    
    const blob = await response.blob();
    
    // Vérifier le blob
    console.log(`Response blob type: ${blob.type}, size: ${blob.size} bytes`);
    
    // Si le contenu est HTML et de petite taille, il s'agit probablement d'une erreur
    if (blob.type.includes('html') && blob.size < 1000) {
      const text = await blob.text();
      console.error('HTML response instead of JSON:', text.substring(0, 200));
      throw new Error('Received HTML instead of JSON file. API error or redirect occurred.');
    }
    
    return blob;
  } catch (error) {
    console.error('Error in matchFiles:', error);
    throw error;
  }
}

/**
 * Unified process for JIRA and Confluence files
 */
export async function unifiedProcess(
  jiraFiles: File[],
  confluenceFiles: File[] = [],
  compress: boolean = true
): Promise<Blob> {
  console.log(`Unified processing: ${jiraFiles.length} JIRA files, ${confluenceFiles.length} Confluence files, compress: ${compress}`);
  
  try {
    const formData = new FormData();
    
    // Add JIRA files
    jiraFiles.forEach((file) => {
      formData.append("jira_files", file);
    });
    
    // Add Confluence files
    confluenceFiles.forEach((file) => {
      formData.append("confluence_files", file);
    });
    
    // Add options - Toujours compresser, quelle que soit la valeur de l'option
    formData.append("compress", "true");
    
    // Log request details
    console.log(`Making API request to ${API_BASE_URL}/llm/unified`);
    console.log('Headers:', { 'X-API-Key': API_KEY ? '***' : 'Not set' });
    console.log('FormData contains JIRA files:', jiraFiles.map(f => f.name));
    console.log('FormData contains Confluence files:', confluenceFiles.map(f => f.name));
    console.log('FormData options: compress=true');
    
    const response = await fetch(`${API_BASE_URL}/llm/unified`, {
      method: "POST",
      headers: {
        'X-API-Key': API_KEY || '',
        'Accept': 'application/zip, application/octet-stream'
      },
      body: formData,
    });
    
    // Log response details
    console.log(`Response status: ${response.status} ${response.statusText}`);
    console.log(`Response headers:`, Object.fromEntries([...response.headers.entries()]));
    
    if (!response.ok) {
      // Try to get error details
      let errorMessage;
      const contentType = response.headers.get('content-type') || '';
      
      if (contentType.includes('application/json')) {
        const errorData = await response.json() as ApiError;
        errorMessage = errorData.error || `Error: ${response.status} ${response.statusText}`;
      } else {
        // Try to read error message from text response
        errorMessage = await response.text();
        if (errorMessage.length > 200) {
          errorMessage = errorMessage.substring(0, 200) + '...';
        }
        errorMessage = `Error: ${response.status} ${response.statusText} - ${errorMessage}`;
      }
      
      console.error('API error:', errorMessage);
      throw new Error(errorMessage);
    }
    
    const blob = await response.blob();
    
    // Vérifier le blob
    console.log(`Response blob type: ${blob.type}, size: ${blob.size} bytes`);
    
    // Le résultat devrait être un ZIP
    if (!blob.type.includes('zip') && !blob.type.includes('octet-stream')) {
      console.warn(`Warning: Expected ZIP but got ${blob.type}`);
      
      // Si le contenu est HTML et de petite taille, il s'agit probablement d'une erreur
      if (blob.type.includes('html') && blob.size < 1000) {
        const text = await blob.text();
        console.error('HTML response instead of ZIP:', text.substring(0, 200));
        throw new Error('Received HTML instead of ZIP file. API error or redirect occurred.');
      }
      
      // Tenter de corriger le type MIME
      return new Blob([blob], { type: 'application/zip' });
    }
    
    return blob;
  } catch (error) {
    console.error('Error in unifiedProcess:', error);
    throw error;
  }
}

/**
 * Enrichie un texte avec LLM
 */
export async function enrichText(content: string): Promise<any> {
  console.log(`Enriching text (length: ${content.length})`);
  
  try {
    const formData = new FormData();
    formData.append("content", content);
    
    // Log request details
    console.log(`Making API request to ${API_BASE_URL}/llm/enrich-text`);
    console.log('Headers:', { 'X-API-Key': API_KEY ? '***' : 'Not set' });
    
    const response = await fetch(`${API_BASE_URL}/llm/enrich-text`, {
      method: "POST",
      headers: {
        'X-API-Key': API_KEY || ''
      },
      body: formData,
    });
    
    // Log response details
    console.log(`Response status: ${response.status} ${response.statusText}`);
    
    if (!response.ok) {
      const errorData = await response.json() as ApiError;
      throw new Error(errorData.error || `Error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('Response data:', data);
    return data;
  } catch (error) {
    console.error('Error in enrichText:', error);
    throw error;
  }
}

/**
 * Set language for API
 */
export const setLanguage = async (language: string): Promise<void> => {
  try {
    const response = await fetch(`${API_BASE_URL}/settings/language`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        'X-API-Key': API_KEY || ''
      },
      body: JSON.stringify({ language }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `Error: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    console.error("Error setting language:", error);
    throw error;
  }
}; 