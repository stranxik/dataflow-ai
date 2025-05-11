import React, { createContext, useContext, useState, useEffect } from 'react';
import { setLanguage as setApiLanguage } from '@/api/apiService';

type Language = 'fr' | 'en';

type LanguageContextType = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string) => string;
};

// Valeurs par défaut du contexte
const LanguageContext = createContext<LanguageContextType>({
  language: 'fr',
  setLanguage: () => {},
  t: (key: string) => key,
});

// Hook pour utiliser le contexte de langue
export const useLanguage = () => useContext(LanguageContext);

// Dictionnaires de traduction
const translations: Record<Language, Record<string, string>> = {
  fr: {
    // Navigation
    'home': 'Accueil',
    'json_processing': 'Traitement JSON',
    'unified_processing_nav': 'Traitement Unifié',
    'switch_to_light': 'Passer en mode clair',
    'switch_to_dark': 'Passer en mode sombre',
    
    // JSON Processing
    'process_json': 'Traiter JSON',
    'clean_data': 'Nettoyer les données',
    'compress': 'Compresser',
    'split_chunks': 'Découper',
    'processing': 'Traitement en cours...',
    'splitting': 'Découpage en cours...',
    'file_selected': 'Fichier sélectionné',
    'no_file_selected': 'Aucun fichier sélectionné',
    'select_file_first': 'Veuillez d\'abord sélectionner un fichier',
    'invalid_file_type': 'Type de fichier invalide',
    'select_json_file': 'Veuillez sélectionner un fichier JSON',
    'processing_complete': 'Traitement terminé',
    'processing_failed': 'Échec du traitement',
    'json_files_only': 'Fichiers JSON uniquement',
    'json_processing_title': 'Traitement JSON',
    'automatic_structure': 'avec détection automatique de structure',
    'clean_sensitive_data': 'Nettoyer les données sensibles',
    'remove_sensitive_data': 'Supprimer les données sensibles des fichiers JSON',
    'compress_json': 'Compresser JSON',
    'optimize_json_files': 'Optimiser les fichiers JSON pour la taille',
    'compression_level': 'Niveau de compression (réduction de 70-90% de la taille)',
    'split_json_files': 'Découper les fichiers JSON',
    'smaller_chunks': 'Diviser en morceaux plus petits pour faciliter le traitement',
    'items_per_chunk': 'Éléments par morceau',
    'when_use_chunking': 'Quand utiliser le découpage ?',
    'large_files': 'Pour les fichiers JSON volumineux (100MB+)',
    'parallel_processing': 'Pour traiter les données en parallèle',
    'timeout_errors': 'En cas d\'erreurs de timeout avec de gros fichiers',
    'memory_management': 'Pour une meilleure gestion de la mémoire',
    'processing_info': 'Informations sur le traitement',
    'secure_server': 'Tous les traitements sont effectués de manière sécurisée sur le serveur',
    'automatic_pipeline': 'Les fichiers sont traités avec notre pipeline avancé',
    'your_json_file_has_been_processed_successfully': 'Votre fichier JSON a été traité avec succès',
    'your_json_file_has_been_split_into_chunks_successfully': 'Votre fichier JSON a été découpé en morceaux avec succès',
    'json_processing_description': 'Traite vos fichiers JSON avec analyse intelligente de structure. L\'organisation originale est préservée pendant le traitement.',
    'note_llm_enrichment': 'L\'enrichissement IA et la préservation de structure sont activés par défaut pour des résultats optimaux.',
    'clean_sensitive_data_description': 'Supprime les données sensibles de vos fichiers JSON, comme les emails, clés API et informations personnelles.',
    'clean_recursively': 'Nettoyer récursivement (à travers les objets imbriqués)',
    'compress_json_description': 'Réduit la taille des fichiers JSON tout en préservant l\'intégrité des données.',
    'higher_compression_slower': 'La compression maximale peut atteindre 90% de réduction de taille',
    'json_split_description': 'Divise les grands fichiers JSON en parties plus petites et faciles à gérer. Idéal pour les fichiers trop volumineux.',
    'change_file': 'Changer de fichier',
    'chunked_files_output': 'Le résultat sera un fichier zip contenant tous les fichiers JSON découpés.',
    'fast': 'rapide',
    'balanced': 'équilibré',
    'maximum': 'maximum',
    
    // Home
    'pdf_analysis': 'Analysez vos PDF avec l\'IA',
    'extract_text': 'Extraction intelligente du texte et des images, plus qu\'un simple OCR pour vos agents IA',
    'max_images': 'Images maximum à analyser:',
    'process_pdf': 'Traiter PDF',
    'why_choose': 'Pourquoi choisir DataFlow AI ?',
    '100_private': '100% Privé',
    'data_never_persists': 'Vos données ne sont jamais conservées sur nos serveurs',
    'powerful_tools': 'Outils Puissants',
    'battle_tested': 'Basé sur notre CLI éprouvée avec extraction PDF avancée',
    'rag_ready': 'Prêt pour votre Agent IA',
    'optimized_for_rag': 'Optimisé pour les workflows d\'Intelligence Artificielle',
    'pdf_files_only': 'Fichiers PDF uniquement',
    'select_pdf_file': 'Veuillez sélectionner un fichier PDF',
    'drop_pdf_file': 'Déposez le fichier PDF ici',
    'drag_drop_pdf': 'Glissez-déposez un fichier PDF ici',
    'click_to_browse': 'cliquez pour parcourir',
    'your_device': 'votre appareil',
    'max_50mb': 'max 50MB',
    'your_pdf_has_been_processed_successfully': 'Votre PDF a été traité avec succès',
    'or': 'ou',
    
    // Unified Processing
    'unified_processing_title': 'Traitement Unifié',
    'jira_confluence': 'JIRA & Confluence',
    'jira_confluence_description': 'Fusionnez et enrichissez vos fichiers JIRA et Confluence automatiquement',
    'required': 'requis',
    'optional': 'optionnel',
    'drop_files': 'Déposez les fichiers ici, ou cliquez pour sélectionner',
    'custom_mapping': 'Utiliser des correspondances personnalisées',
    'processing_options': 'Options de traitement',
    'compress_output': 'Compresser les fichiers résultants (recommandé pour les gros ensembles)',
    'min_match_score': 'Précision minimale (0.0-1.0)',
    'higher_values': 'Des valeurs plus élevées donnent des correspondances plus précises mais moins nombreuses',
    'jira_confluence_matching': 'La correspondance JIRA-Confluence est activée par défaut',
    'complete_workflow': 'Ce traitement automatisé va :',
    'process_files': 'Analyser vos fichiers avec correspondance automatique ou personnalisée',
    'enrich_content': 'Enrichir le contenu avec analyse IA',
    'establish_matches': 'Établir des liens entre éléments JIRA et Confluence',
    'generate_reports': 'Générer des rapports complets et résultats structurés',
    'run_unified': 'Lancer le traitement',
    'expected_output': 'Résultat attendu',
    'unified_processing_complete': 'Le traitement unifié a été effectué avec succès',
    'zip_file': 'Le traitement générera un fichier ZIP contenant :',
    'select_mapping_files': 'Fichiers de correspondance sélectionnés :',
    'selected_files': 'Fichiers sélectionnés :',
    'jira_files': 'Fichiers JIRA',
    'confluence_files': 'Fichiers Confluence',
    'remove': 'Supprimer',
    'processed_jira_confluence': 'Fichiers JIRA et Confluence traités (dans des répertoires séparés)',
    'matching_results': 'Correspondances établies (relations entre les éléments)',
    'llm_enriched_files': 'Fichiers enrichis par IA avec résumés, mots-clés et entités',
    'full_directory_structure': 'Structure complète avec rapports et fichiers de correspondance',
    'similar_to_demo': 'Résultat similaire à /results/demo_jira_confluence_test',
    
    // Help tooltip
    'help_tooltip': 'Comment ça marche ?',
    'pdf_extraction_explanation': 'Notre traitement PDF avancé :\n\n• Extrait le texte natif du PDF\n• Détecte et analyse les images intégrées avec GPT-4o\n• Génère un fichier JSON structuré\n• Inclut des descriptions détaillées des images\n• Préserve le contexte textuel autour des images',
    
    // PDF Results Modal
    'file_processed_successfully': 'Fichier traité avec succès',
    'your_extraction_is_ready': 'Votre extraction est prête à être téléchargée',
    'complete_results': 'Résultats complets',
    'zip_file_with_all_extracted_data': 'Fichier ZIP contenant toutes les données extraites',
    'download': 'Télécharger',
    'results_include_extracted_text_images_analyses': 'Les résultats incluent le texte extrait, les images analysées et les métadonnées',
    'no_results_found': 'Aucun résultat trouvé pour ce document',
    'close': 'Fermer',
    'download_results': 'Télécharger les résultats',
    'remove_file': 'Supprimer le fichier',
    'drop_file_here': 'Déposez le fichier ici',
    'upload_pdf': 'Télécharger un PDF',
    
    // How it works section
    'how_it_works': 'Comment ça marche',
    'secure_processing': 'Traitement sécurisé',
    'secure_processing_description': 'Vos données sont traitées localement et ne sont jamais stockées sur des serveurs tiers',
    'powerful_extraction': 'Extraction puissante',
    'powerful_extraction_description': 'Notre technologie avancée extrait le texte et les images avec une précision exceptionnelle',
    'organized_data': 'Données organisées',
    'organized_data_description': 'Les résultats sont structurés pour faciliter l\'analyse et l\'intégration dans d\'autres systèmes',
    'ai_analysis': 'Analyse IA',
    'ai_analysis_description': 'Les images sont analysées par GPT-4o pour en extraire le contexte et les informations pertinentes',
  },
  en: {
    // Navigation
    'home': 'Home',
    'json_processing': 'JSON Processing',
    'unified_processing_nav': 'Unified Processing',
    'switch_to_light': 'Switch to Light Mode',
    'switch_to_dark': 'Switch to Dark Mode',
    
    // JSON Processing
    'process_json': 'Process JSON',
    'clean_data': 'Clean Data',
    'compress': 'Compress',
    'split_chunks': 'Split Chunks',
    'processing': 'Processing...',
    'splitting': 'Splitting...',
    'file_selected': 'File selected',
    'no_file_selected': 'No file selected',
    'select_file_first': 'Please select a file first',
    'invalid_file_type': 'Invalid file type',
    'select_json_file': 'Please select a JSON file',
    'processing_complete': 'Processing complete',
    'processing_failed': 'Processing failed',
    'json_files_only': 'JSON files only',
    'json_processing_title': 'JSON Processing',
    'automatic_structure': 'with automatic structure detection',
    'clean_sensitive_data': 'Clean Sensitive Data',
    'remove_sensitive_data': 'Remove sensitive data from JSON files',
    'compress_json': 'Compress JSON',
    'optimize_json_files': 'Optimize JSON files for size',
    'compression_level': 'Compression level (reduces file size by 70-90%)',
    'split_json_files': 'Split Large JSON Files',
    'smaller_chunks': 'Divide into smaller chunks for easier processing',
    'items_per_chunk': 'Items per chunk',
    'when_use_chunking': 'When to use JSON chunking?',
    'large_files': 'When dealing with very large JSON files (100MB+)',
    'parallel_processing': 'When you need to process data in parallel',
    'timeout_errors': 'When you\'re getting timeout errors with large files',
    'memory_management': 'For improved memory management with large datasets',
    'processing_info': 'Processing Information',
    'secure_server': 'All processing happens securely on the server',
    'automatic_pipeline': 'Files are processed with our advanced pipeline',
    'your_json_file_has_been_processed_successfully': 'Your JSON file has been processed successfully',
    'your_json_file_has_been_split_into_chunks_successfully': 'Your JSON file has been split into chunks successfully',
    'json_processing_description': 'Processes your JSON files with intelligent structure analysis. The original organization is preserved during processing.',
    'note_llm_enrichment': 'AI enrichment and structure preservation are enabled by default for optimal results.',
    'clean_sensitive_data_description': 'Removes sensitive data from your JSON files, including emails, API keys, and personal information.',
    'clean_recursively': 'Clean recursively (through nested objects)',
    'compress_json_description': 'Reduces JSON file size while preserving data integrity.',
    'higher_compression_slower': 'Maximum compression can achieve up to 90% size reduction',
    'json_split_description': 'Divides large JSON files into smaller, more manageable parts. Ideal for files that are too large to process at once.',
    'change_file': 'Change File',
    'chunked_files_output': 'The output will be a zip file containing all the chunked JSON files.',
    'fast': 'fast',
    'balanced': 'balanced',
    'maximum': 'maximum',
    
    // Home
    'pdf_analysis': 'Analyze PDFs with AI',
    'extract_text': 'Intelligent extraction of text and images, more than just a simple OCR for your AI agents',
    'max_images': 'Maximum images to analyze:',
    'process_pdf': 'Process PDF',
    'why_choose': 'Why Choose DataFlow AI?',
    '100_private': '100% Private',
    'data_never_persists': 'Your data never persists on our servers',
    'powerful_tools': 'Powerful Tools',
    'battle_tested': 'Built on our battle-tested CLI with advanced PDF extraction',
    'rag_ready': 'AI Agent Ready',
    'optimized_for_rag': 'Optimized for Artificial Intelligence workflows',
    'pdf_files_only': 'PDF files only',
    'select_pdf_file': 'Please select a PDF file',
    'drop_pdf_file': 'Drop the PDF file here',
    'drag_drop_pdf': 'Drag & drop a PDF file here',
    'click_to_browse': 'click to browse',
    'your_device': 'your device',
    'max_50mb': 'max 50MB',
    'your_pdf_has_been_processed_successfully': 'Your PDF has been processed successfully',
    'or': 'or',
    
    // Unified Processing
    'unified_processing_title': 'Unified Processing',
    'jira_confluence': 'JIRA & Confluence',
    'jira_confluence_description': 'Merge and enrich your JIRA and Confluence files automatically',
    'required': 'required',
    'optional': 'optional',
    'drop_files': 'Drop files here, or click to select',
    'custom_mapping': 'Use custom mappings',
    'processing_options': 'Processing Options',
    'compress_output': 'Compress output files (recommended for large datasets)',
    'min_match_score': 'Minimum accuracy (0.0-1.0)',
    'higher_values': 'Higher values produce more precise but fewer matches',
    'jira_confluence_matching': 'JIRA-Confluence matching is enabled by default',
    'complete_workflow': 'This automated process will:',
    'process_files': 'Analyze your files with automatic or custom mapping',
    'enrich_content': 'Enrich content with AI analysis',
    'establish_matches': 'Establish links between JIRA and Confluence items',
    'generate_reports': 'Generate comprehensive reports and structured results',
    'run_unified': 'Run Processing',
    'expected_output': 'Expected Output',
    'unified_processing_complete': 'Unified processing completed successfully',
    'zip_file': 'The processing will generate a ZIP file containing:',
    'select_mapping_files': 'Selected mapping files:',
    'selected_files': 'Selected files:',
    'jira_files': 'JIRA Files',
    'confluence_files': 'Confluence Files',
    'remove': 'Remove',
    'processed_jira_confluence': 'Processed JIRA and Confluence files (in separate directories)',
    'matching_results': 'Established matches (relationships between items)',
    'llm_enriched_files': 'AI-enriched files with summaries, keywords, and entities',
    'full_directory_structure': 'Complete structure with reports and mapping files',
    'similar_to_demo': 'Result similar to /results/demo_jira_confluence_test',
    
    // Help tooltip
    'help_tooltip': 'How does it work?',
    'pdf_extraction_explanation': 'Our advanced PDF processing:\n\n• Extracts native PDF text\n• Detects and analyzes embedded images with GPT-4o\n• Generates a structured JSON file\n• Includes detailed image descriptions\n• Preserves textual context around images',
    
    // PDF Results Modal
    'file_processed_successfully': 'File processed successfully',
    'your_extraction_is_ready': 'Your extraction is ready to download',
    'complete_results': 'Complete results',
    'zip_file_with_all_extracted_data': 'ZIP file with all extracted data',
    'download': 'Download',
    'results_include_extracted_text_images_analyses': 'Results include extracted text, analyzed images, and metadata',
    'no_results_found': 'No results found for this document',
    'close': 'Close',
    'download_results': 'Download results',
    'remove_file': 'Remove file',
    'drop_file_here': 'Drop file here',
    'upload_pdf': 'Upload PDF',
    
    // How it works section
    'how_it_works': 'How it works',
    'secure_processing': 'Secure Processing',
    'secure_processing_description': 'Your data is processed locally and never stored on third-party servers',
    'powerful_extraction': 'Powerful Extraction',
    'powerful_extraction_description': 'Our advanced technology extracts text and images with exceptional accuracy',
    'organized_data': 'Organized Data',
    'organized_data_description': 'Results are structured for easy analysis and integration with other systems',
    'ai_analysis': 'AI Analysis',
    'ai_analysis_description': 'Images are analyzed by GPT-4o to extract context and relevant information',
  }
};

interface LanguageProviderProps {
  children: React.ReactNode;
}

export function LanguageProvider({ children }: LanguageProviderProps) {
  // Récupérer la langue initiale depuis localStorage ou utiliser fr par défaut
  const [language, setLanguageState] = useState<Language>(() => {
    const savedLanguage = localStorage.getItem('dataflow-language');
    return (savedLanguage === 'en' ? 'en' : 'fr') as Language;
  });

  // Mettre à jour localStorage quand la langue change
  useEffect(() => {
    localStorage.setItem('dataflow-language', language);
    
    // Notifier l'API du changement de langue
    try {
      setApiLanguage(language).catch(error => {
        console.error('Failed to update language in API:', error);
      });
    } catch (error) {
      console.error('Failed to update language in API:', error);
    }
  }, [language]);

  // Fonction pour définir la langue
  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
  };

  // Fonction de traduction
  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  // Valeur du contexte
  const contextValue = {
    language,
    setLanguage,
    t,
  };

  return (
    <LanguageContext.Provider value={contextValue}>
      {children}
    </LanguageContext.Provider>
  );
} 