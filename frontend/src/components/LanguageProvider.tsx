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
    'unified_processing_nav': 'Traitement unifié',
    'switch_to_light': 'Passer en mode clair',
    'switch_to_dark': 'Passer en mode sombre',
    
    // JSON Processing
    'process_json': 'Traiter JSON',
    'clean_data': 'Nettoyer les données',
    'compress': 'Compresser',
    'compress_decompress': 'Compresser/Décompresser',
    'compress_file': 'Compresser le fichier',
    'decompress_file': 'Décompresser le fichier',
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
    'automatic_structure': 'Analyse et traitement automatique de la structure JSON',
    'clean_sensitive_data': 'Nettoyage des données sensibles',
    'remove_sensitive_data': 'Supprimez les données sensibles de vos fichiers JSON',
    'compress_json': 'Compresser JSON',
    'optimize_json_files': 'Optimisez vos fichiers JSON avec une compression efficace',
    'compression_level': 'Niveau de compression',
    'split_json_files': 'Découpage de fichiers JSON',
    'smaller_chunks': 'Divisez un grand fichier JSON en morceaux plus petits',
    'items_per_file': 'Éléments par fichier',
    'when_use_chunking': 'Quand utiliser le découpage ?',
    'large_files': 'Pour les fichiers JSON volumineux (100MB+)',
    'parallel_processing': 'Pour traiter les données en parallèle',
    'timeout_errors': 'En cas d\'erreurs de timeout avec de gros fichiers',
    'memory_management': 'Pour une meilleure gestion de la mémoire',
    'processing_info': 'Informations sur le traitement',
    'secure_server': 'Tous les traitements sont effectués de manière sécurisée sur le serveur',
    'automatic_pipeline': 'Les fichiers sont traités avec notre pipeline avancé',
    'your_json_file_has_been_processed_successfully': 'Votre fichier JSON a été traité avec succès',
    'your_json_file_has_been_split_into_chunks_successfully': 'Votre fichier JSON a été divisé en morceaux avec succès',
    'json_processing_description': 'Traite vos fichiers JSON avec une analyse intelligente de la structure. L\'organisation originale est préservée durant le traitement.',
    'note_llm_enrichment': 'L\'enrichissement IA et la préservation de structure sont activés par défaut pour des résultats optimaux.',
    'clean_sensitive_data_description': 'Supprime les données sensibles de vos fichiers JSON, y compris les emails, clés API et informations personnelles.',
    'clean_recursively': 'Nettoyer récursivement (parcourir les objets imbriqués)',
    'compress_json_description': 'Réduit la taille des fichiers JSON tout en préservant l\'intégrité des données.',
    'higher_compression_slower': 'Une compression plus élevée peut réduire la taille jusqu\'à 90%',
    'json_split_description': 'Divise les grands fichiers JSON en parties plus petites et plus faciles à gérer. Idéal pour les fichiers trop volumineux pour être traités en une seule fois.',
    'change_file': 'Changer de fichier',
    'chunked_files_output': 'Le résultat sera un fichier zip contenant tous les fichiers JSON découpés.',
    'fast': 'rapide',
    'balanced': 'équilibré',
    'maximum': 'maximum',
    'always_enabled': 'toujours activé',
    
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
    'drag_drop_json': 'Glissez-déposez un fichier JSON ici',
    'click_to_browse': 'cliquez pour parcourir',
    'your_device': 'votre appareil',
    'max_50mb': 'max 50MB',
    'your_pdf_has_been_processed_successfully': 'Votre PDF a été traité avec succès',
    'or': 'ou',
    'or_click_to_select': 'ou cliquez pour sélectionner',
    'drop_the_file_here': 'Déposez le fichier ici',
    'process_file': 'Traiter le fichier',
    'clean_file': 'Nettoyer le fichier',
    'split_file': 'Découper le fichier',
    'recommended_value_500': 'Valeur recommandée: 500 éléments par fichier',
    'help_and_tips': 'Aide et astuces',
    'json_tip_1': 'Assurez-vous que votre fichier JSON est correctement formaté',
    'json_tip_2': 'Les grands fichiers seront automatiquement traités en streaming',
    'json_tip_3': 'La détection automatique identifie les structures JIRA et Confluence',
    
    // Unified Processing
    'unified_processing_title': 'Traitement unifié',
    'jira_confluence': 'JIRA & Confluence',
    'jira_confluence_description': 'Fusionnez et enrichissez vos fichiers JIRA et Confluence automatiquement',
    'required': 'requis',
    'optional': 'optionnel',
    'drop_files': 'Déposez les fichiers ici, ou cliquez pour sélectionner',
    'custom_mapping': 'Utiliser des correspondances personnalisées',
    'processing_options': 'Options de traitement',
    'compress_output': 'Compresser les fichiers résultants (recommandé pour les gros ensembles)',
    'compress_output_files': 'Compresser les fichiers résultants (recommandé pour les gros ensembles)',
    'min_match_score': 'Précision minimale (0.0-1.0)',
    'higher_values': 'Des valeurs plus élevées donnent des correspondances plus précises mais moins nombreuses',
    'jira_confluence_matching': 'La correspondance JIRA-Confluence est activée par défaut',
    'more_matches_lower_quality': 'plus de correspondances mais qualité réduite',
    'default': 'défaut',
    'higher_quality_fewer_matches': 'meilleure qualité mais moins de correspondances',
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
    'start_unified_processing': 'Lancer le traitement unifié',
    'about_llm_enrichment': 'À propos de l\'enrichissement IA',
    'llm_enrichment_explanation': 'L\'enrichissement par IA analyse le contenu de vos fichiers pour en extraire des informations pertinentes et ajouter du contexte.',
    'benefits': 'Avantages',
    'llm_benefit_1': 'Extraction automatique de mots-clés et d\'entités nommées',
    'llm_benefit_2': 'Résumés automatiques pour chaque élément',
    'llm_benefit_3': 'Analyse de sentiment et pertinence contextuelle',
    'limitations': 'Limitations',
    'llm_limitation_1': 'Dépend de la qualité des données sources',
    'llm_limitation_2': 'Peut varier en précision selon le contexte',
    'llm_limitation_3': 'Peut entraîner des coûts d\'API supplémentaires',
    'processed_jira_confluence': 'Fichiers JIRA et Confluence traités (dans des répertoires séparés)',
    'matching_results': 'Correspondances établies (relations entre les éléments)',
    'llm_enriched_files': 'Fichiers enrichis par IA avec résumés, mots-clés et entités',
    'full_directory_structure': 'Structure complète avec rapports et fichiers de correspondance',
    'similar_to_demo': 'Résultat similaire à /results/demo_jira_confluence_test',
    
    // Help tooltip
    'help_tooltip': 'Comment ça marche ?',
    'pdf_extraction_explanation': 'Notre traitement PDF avancé :\n\n• Extrait le texte natif du PDF\n• Détecte et analyse les images intégrées avec GPT-4.1\n• Génère un fichier JSON structuré\n• Inclut des descriptions détaillées des images\n• Préserve le contexte textuel autour des images',
    
    // Page-specific help texts
    'json_processing_page_info': 'Ce module traite intelligemment vos fichiers JSON en:\n\n• Détectant automatiquement la structure des données\n• Préservant l\'organisation originale pendant le traitement\n• Utilisant l\'enrichissement IA pour améliorer le contexte\n• Permettant le nettoyage des données sensibles\n• Optimisant les fichiers avec compression avancée\n• Divisant les gros fichiers en parties plus gérables',
    'llm_enrichment_page_info': 'Ce module unifie et enrichit vos données JIRA et Confluence en:\n\n• Établissant des correspondances entre tickets et pages\n• Enrichissant le contenu avec analyse IA\n• Extrayant automatiquement mots-clés et entités\n• Générant des résumés concis de chaque élément\n• Créant une structure unifiée pour RAG\n• Produisant un rapport détaillé des correspondances',
    'pdf_extraction_page_info': 'Notre extracteur PDF avancé combine:\n\n• Extraction native du texte brut du PDF\n• Détection et extraction des images intégrées\n• Analyse IA des images avec GPT-4.1\n• Conservation de la structure originale du texte\n• Génération d\'un JSON unifié texte + analyses d\'images\n• Préservation du contexte textuel autour des images',
    
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
    'secure_processing': 'Protection des données',
    'secure_processing_description': 'Confidentialité garantie : vos données sont traitées localement et ne sont jamais conservées sur nos serveurs.',
    'powerful_extraction': 'Extraction puissante',
    'powerful_extraction_description': 'Notre technologie avancée extrait le texte et les images avec une précision exceptionnelle',
    'organized_data': 'Données organisées',
    'organized_data_description': 'Les résultats sont structurés pour faciliter l\'analyse et l\'intégration dans d\'autres systèmes',
    'ai_analysis': 'Analyse IA',
    'ai_analysis_description': 'Les images sont analysées par GPT-4.1 pour en extraire le contexte et les informations pertinentes',
    
    // File upload errors
    'file_too_large': 'Fichier trop volumineux',
    'file_size_limit': 'La taille maximale de fichier autorisée est de {size} MB',
    'our_vision': 'Notre vision',
    
    // Nouvelles traductions pour l'extraction d'images
    'why_our_image_extraction_is_different': 'Une analyse technique avancée',
    'beyond_traditional_ocr_title': 'Au-delà de l\'OCR',
    'beyond_traditional_ocr_description': 'Notre technologie transforme les documents techniques en données structurées, dépassant les limites de la simple reconnaissance de caractères.',
    'structured_data_extraction_title': 'Données structurées',
    'structured_data_extraction_description': 'Chaque image est analysée avec précision, générant des données JSON exploitables immédiatement.',
    'perfect_for_professionals': 'Des applications dans tous les secteurs',
    'engineering_title': 'Ingénierie',
    'engineering_description': 'Analyse précise des schémas techniques et diagrammes industriels.',
    'medical_research_title': 'Finance et Assurance',
    'medical_research_description': 'Extraction automatisée des données depuis les rapports financiers et documents contractuels.',
    'technical_documentation_title': 'Documentation Technique',
    'technical_documentation_description': 'Transformation efficace de documents complexes en données exploitables.',
    'transform_your_technical_documents': 'Valorisation des documents',
    // Nouvelles clés pour la compression/décompression
    'decompress_zst': 'Décompresser ZST',
    'restore_json_files': 'Restaurer les fichiers JSON compressés',
    'decompress_zst_description': 'Restaure un fichier JSON à partir de sa version compressée au format ZST.',
    'select_json_or_zst_file': 'Veuillez sélectionner un fichier JSON ou ZST',
    'json_zst_files_only': 'Fichiers JSON ou ZST uniquement',
    'drag_drop_json_or_zst': 'Glissez-déposez un fichier JSON ou ZST ici',
    'compression_failed': 'Échec de la compression',
    'decompression_failed': 'Échec de la décompression',
    'error_compressing': 'Erreur lors de la compression du fichier',
    'error_decompressing': 'Erreur lors de la décompression du fichier',
    'your_json_file_has_been_compressed_successfully': 'Votre fichier JSON a été compressé avec succès',
    'your_json_file_has_been_decompressed_successfully': 'Votre fichier ZST a été décompressé avec succès',
    
    // Traductions pour l'orchestrateur de tâches
    'active_tasks': 'Tâches actives',
    'retry': 'Réessayer',
    'started': 'Démarré',
    'last_updated': 'Dernière mise à jour',
    'retries': 'Tentatives',
    'error': 'Erreur',
    'processing_started': 'Traitement démarré',
    'processing_status_available': 'Vous pouvez suivre le statut du traitement ci-dessous',
    'empty_result': 'Résultat vide',
    'task_status_message': 'Le traitement des PDF est géré par un orchestrateur de tâches qui assure la fiabilité du traitement. Vous pouvez suivre la progression des tâches ci-dessus.',
    'no_active_tasks': 'Aucune tâche active',
    'upload_and_process': 'Téléchargez et traitez un fichier pour voir apparaître des tâches ici',
    'processing_in_progress': 'Traitement en cours',
    'finalizing_extraction': 'Finalisation de l\'extraction...',
    'finalizing_message': 'Nous finalisons votre extraction. Cette dernière étape peut prendre quelques instants.',
    'paused': 'En pause',
    'pending': 'En attente',
    'raster_mode_auto': 'Automatique (détecte et rasterise uniquement les pages contenant des plans ou schémas)',
    'raster_mode_manual': 'Manuel (rasterise toutes les pages ou celles sélectionnées)',
    'raster_mode_explanation': "Le mode 'Automatique' détecte et analyse automatiquement les pages contenant des images vectorielles (plans, schémas, etc.) en plus des images classiques. Le mode 'Manuel' vous permet de spécifier vous-même les pages à analyser pour les images vectorielles (dans les deux cas, toutes les images classiques sont extraites).",
    'pdf_extraction_config_title': "Configuration de l'extraction",
    'raster_mode_label': 'Mode :',
    'raster_pages_label': 'Pages à analyser',
    'raster_pages_placeholder': 'Ex: 1,3,5-7'
  },
  en: {
    // Navigation
    'home': 'Home',
    'json_processing': 'JSON Processing',
    'unified_processing_nav': 'Unified processing',
    'switch_to_light': 'Switch to Light Mode',
    'switch_to_dark': 'Switch to Dark Mode',
    
    // JSON Processing
    'process_json': 'Process JSON',
    'clean_data': 'Clean Data',
    'compress': 'Compress',
    'compress_decompress': 'Compress/Decompress',
    'compress_file': 'Compress file',
    'decompress_file': 'Decompress file',
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
    'automatic_structure': 'Automatic JSON structure analysis and processing',
    'clean_sensitive_data': 'Clean Sensitive Data',
    'remove_sensitive_data': 'Remove sensitive data from your JSON files',
    'compress_json': 'Compress JSON',
    'optimize_json_files': 'Optimize your JSON files with efficient compression',
    'compression_level': 'Compression level',
    'split_json_files': 'Split JSON Files',
    'smaller_chunks': 'Split a large JSON file into smaller pieces',
    'items_per_file': 'Items per file',
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
    'json_processing_description': 'Process your JSON files with intelligent structure analysis. Original organization is preserved during processing.',
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
    'always_enabled': 'always enabled',
    
    // Home
    'pdf_analysis': 'Analyze PDFs with AI',
    'extract_text': 'Intelligent extraction of text and images, more than just OCR for your AI agents',
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
    'drag_drop_json': 'Drag & drop a JSON file here',
    'click_to_browse': 'click to browse',
    'your_device': 'your device',
    'max_50mb': 'max 50MB',
    'your_pdf_has_been_processed_successfully': 'Your PDF has been processed successfully',
    'or': 'or',
    'or_click_to_select': 'or click to select',
    'drop_the_file_here': 'Drop the file here',
    'process_file': 'Process file',
    'clean_file': 'Clean file',
    'split_file': 'Split file',
    'recommended_value_500': 'Recommended value: 500 items per file',
    'help_and_tips': 'Help and tips',
    'json_tip_1': 'Make sure your JSON file is properly formatted',
    'json_tip_2': 'Large files will be automatically processed in streaming mode',
    'json_tip_3': 'Automatic detection identifies JIRA and Confluence structures',
    
    // Unified Processing
    'unified_processing_title': 'Unified processing',
    'jira_confluence': 'JIRA & Confluence',
    'jira_confluence_description': 'Merge and enrich your JIRA and Confluence files automatically',
    'required': 'required',
    'optional': 'optional',
    'drop_files': 'Drop files here, or click to select',
    'custom_mapping': 'Use custom mappings',
    'processing_options': 'Processing Options',
    'compress_output': 'Compress output files (recommended for large datasets)',
    'compress_output_files': 'Compress output files (recommended for large datasets)',
    'min_match_score': 'Minimum accuracy (0.0-1.0)',
    'higher_values': 'Higher values produce more precise but fewer matches',
    'jira_confluence_matching': 'JIRA-Confluence matching is enabled by default',
    'more_matches_lower_quality': 'more matches but lower quality',
    'default': 'default',
    'higher_quality_fewer_matches': 'higher quality but fewer matches',
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
    'start_unified_processing': 'Start unified processing',
    'about_llm_enrichment': 'About AI enrichment',
    'llm_enrichment_explanation': 'AI enrichment analyzes your files content to extract relevant information and add context.',
    'benefits': 'Benefits',
    'llm_benefit_1': 'Automatic extraction of keywords and named entities',
    'llm_benefit_2': 'Automatic summaries for each item',
    'llm_benefit_3': 'Sentiment analysis and contextual relevance',
    'limitations': 'Limitations',
    'llm_limitation_1': 'Depends on the quality of source data',
    'llm_limitation_2': 'Accuracy may vary depending on context',
    'llm_limitation_3': 'May incur additional API costs',
    'processed_jira_confluence': 'Processed JIRA and Confluence files (in separate directories)',
    'matching_results': 'Established matches (relationships between items)',
    'llm_enriched_files': 'AI-enriched files with summaries, keywords, and entities',
    'full_directory_structure': 'Complete structure with reports and mapping files',
    'similar_to_demo': 'Result similar to /results/demo_jira_confluence_test',
    
    // Help tooltip
    'help_tooltip': 'How does it work?',
    'pdf_extraction_explanation': 'Our advanced PDF processing:\n\n• Extracts native PDF text\n• Detects and analyzes embedded images with GPT-4.1\n• Generates a structured JSON file\n• Includes detailed image descriptions\n• Preserves textual context around images',
    
    // Page-specific help texts
    'json_processing_page_info': 'This module intelligently processes your JSON files by:\n\n• Automatically detecting data structure\n• Preserving original organization during processing\n• Using AI enrichment to improve context\n• Enabling sensitive data cleaning\n• Optimizing files with advanced compression\n• Splitting large files into manageable parts',
    'llm_enrichment_page_info': 'This module unifies and enriches your JIRA and Confluence data by:\n\n• Establishing matches between tickets and pages\n• Enriching content with AI analysis\n• Automatically extracting keywords and entities\n• Generating concise summaries of each item\n• Creating a unified structure for RAG\n• Producing a detailed matching report',
    'pdf_extraction_page_info': 'Our advanced PDF extractor combines:\n\n• Native extraction of raw PDF text\n• Detection and extraction of embedded images\n• AI analysis of images with GPT-4.1\n• Preservation of original text structure\n• Generation of unified JSON with text + image analyses\n• Preservation of textual context around images',
    
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
    'secure_processing': 'Data Protection',
    'secure_processing_description': 'Privacy guaranteed: your data is processed locally and never stored on our servers.',
    'powerful_extraction': 'Powerful Extraction',
    'powerful_extraction_description': 'Our advanced technology extracts text and images with exceptional accuracy',
    'organized_data': 'Organized Data',
    'organized_data_description': 'Results are structured for easy analysis and integration with other systems',
    'ai_analysis': 'AI Analysis',
    'ai_analysis_description': 'Images are analyzed by GPT-4.1 to extract context and relevant information',
    
    // File upload errors
    'file_too_large': 'File too large',
    'file_size_limit': 'Maximum allowed file size is {size} MB',
    'our_vision': 'Our vision',
    
    // Nouvelles traductions pour l'extraction d'images
    'why_our_image_extraction_is_different': 'Advanced Technical Analysis',
    'beyond_traditional_ocr_title': 'Beyond OCR',
    'beyond_traditional_ocr_description': 'Our technology transforms technical documents into structured data, exceeding the limits of simple character recognition.',
    'structured_data_extraction_title': 'Structured Data',
    'structured_data_extraction_description': 'Each image is analyzed with precision, generating immediately usable JSON data.',
    'perfect_for_professionals': 'Applications Across Industries',
    'engineering_title': 'Engineering',
    'engineering_description': 'Accurate analysis of technical diagrams and industrial schematics.',
    'medical_research_title': 'Finance and Insurance',
    'medical_research_description': 'Automated extraction of data from financial reports and contractual documents.',
    'technical_documentation_title': 'Technical Documentation',
    'technical_documentation_description': 'Efficient transformation of complex documents into actionable data.',
    'transform_your_technical_documents': 'Document Enhancement',
    // Nouvelles clés pour la compression/décompression
    'decompress_zst': 'Decompress ZST',
    'restore_json_files': 'Restore compressed JSON files',
    'decompress_zst_description': 'Restores a JSON file from its compressed ZST version.',
    'select_json_or_zst_file': 'Please select a JSON or ZST file',
    'json_zst_files_only': 'JSON or ZST files only',
    'drag_drop_json_or_zst': 'Drag & drop a JSON or ZST file here',
    'compression_failed': 'Compression failed',
    'decompression_failed': 'Decompression failed',
    'error_compressing': 'Error compressing file',
    'error_decompressing': 'Error decompressing file',
    'your_json_file_has_been_compressed_successfully': 'Your JSON file has been compressed successfully',
    'your_json_file_has_been_decompressed_successfully': 'Your ZST file has been decompressed successfully',
    
    // Traductions pour l'orchestrateur de tâches
    'active_tasks': 'Active tasks',
    'retry': 'Retry',
    'started': 'Started',
    'last_updated': 'Last updated',
    'retries': 'Retries',
    'error': 'Error',
    'processing_started': 'Processing started',
    'processing_status_available': 'You can follow the processing status below',
    'empty_result': 'Empty result',
    'task_status_message': 'Processing is managed by a task orchestrator which ensures the reliability of the processing. You can follow the progress of the tasks above.',
    'no_active_tasks': 'No active tasks',
    'upload_and_process': 'Upload and process a file to see tasks here',
    'processing_in_progress': 'Processing in progress',
    'finalizing_extraction': 'Finalizing extraction...',
    'finalizing_message': 'We are finalizing your extraction. This last step may take a moment.',
    'paused': 'Paused',
    'pending': 'Pending',
    'raster_mode_auto': 'Automatic (detects and rasterizes only pages containing plans or diagrams)',
    'raster_mode_manual': 'Manual (rasterizes all pages or selected ones)',
    'raster_mode_explanation': "‘Automatic’ mode detects and analyzes pages with vector images (such as plans, diagrams, etc.) in addition to standard images. 'Manual' mode lets you specify which pages to analyze for vector images (in both modes, all standard images are extracted).",
    'pdf_extraction_config_title': 'Extraction settings',
    'raster_mode_label': 'Mode:',
    'raster_pages_label': 'Pages to analyze',
    'raster_pages_placeholder': 'e.g. 1,3,5-7'
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