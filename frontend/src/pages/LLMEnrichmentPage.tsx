import React, { useState } from 'react';
import { Loader2, Link as LinkIcon, FileJson, Bot } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { unifiedProcess } from '@/api/apiService';
import { useToast } from '@/components/ui/use-toast';
import { useDropzone } from 'react-dropzone';
import { formatFileSize, isValidFileType, createDownloadLink } from '@/lib/utils';
import { useLanguage } from '@/components/LanguageProvider';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export default function LLMEnrichmentPage() {
  const { t } = useLanguage();
  const [jiraFiles, setJiraFiles] = useState<File[]>([]);
  const [confluenceFiles, setConfluenceFiles] = useState<File[]>([]);
  const [mappingFiles, setMappingFiles] = useState<File[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [compressOutput, setCompressOutput] = useState(true);
  const [minMatchScore, setMinMatchScore] = useState('0.5');
  const [useCustomMapping, setUseCustomMapping] = useState(false);
  const { toast } = useToast();

  const onDropJira = (acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter(file => isValidFileType(file, ['json']));
    if (validFiles.length > 0) {
      setJiraFiles(prev => [...prev, ...validFiles]);
      toast({
        title: t('file_selected'),
        description: `Added ${validFiles.length} JIRA file(s)`,
      });
    }
  };

  const onDropConfluence = (acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter(file => isValidFileType(file, ['json']));
    if (validFiles.length > 0) {
      setConfluenceFiles(prev => [...prev, ...validFiles]);
      toast({
        title: t('file_selected'),
        description: `Added ${validFiles.length} Confluence file(s)`,
      });
    }
  };

  const onDropMapping = (acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter(file => isValidFileType(file, ['json']));
    if (validFiles.length > 0) {
      setMappingFiles(prev => [...prev, ...validFiles]);
      toast({
        title: t('file_selected'),
        description: `Added ${validFiles.length} mapping file(s)`,
      });
    }
  };

  const { getRootProps: getJiraRootProps, getInputProps: getJiraInputProps } = useDropzone({
    onDrop: onDropJira,
    accept: {
      'application/json': ['.json'],
    },
  });

  const { getRootProps: getConfluenceRootProps, getInputProps: getConfluenceInputProps } = useDropzone({
    onDrop: onDropConfluence,
    accept: {
      'application/json': ['.json'],
    },
  });

  const { getRootProps: getMappingRootProps, getInputProps: getMappingInputProps } = useDropzone({
    onDrop: onDropMapping,
    accept: {
      'application/json': ['.json'],
    },
  });

  const handleUnifiedProcessing = async () => {
    if (jiraFiles.length === 0) {
      toast({
        title: t('no_file_selected'),
        description: t('select_file_first'),
        variant: 'destructive',
      });
      return;
    }

    setIsProcessing(true);
    try {
      const result = await unifiedProcess(jiraFiles, confluenceFiles, compressOutput);
      
      createDownloadLink(
        result, 
        `enriched_results.zip`
      );
      
      toast({
        title: t('processing_complete'),
        description: t('unified_processing_complete'),
      });
    } catch (error) {
      console.error('Error in unified processing:', error);
      toast({
        title: t('processing_failed'),
        description: error instanceof Error ? error.message : 'An unknown error occurred',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const removeJiraFile = (index: number) => {
    setJiraFiles(prev => prev.filter((_, i) => i !== index));
  };

  const removeConfluenceFile = (index: number) => {
    setConfluenceFiles(prev => prev.filter((_, i) => i !== index));
  };

  const removeMappingFile = (index: number) => {
    setMappingFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="container mx-auto max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">{t('unified_processing_title')}</h1>
      
      <div className="grid grid-cols-1 gap-8">
        {/* Unified Processing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <LinkIcon className="mr-2 h-5 w-5" />
              {t('jira_confluence')}
            </CardTitle>
            <CardDescription>
              {t('jira_confluence_description')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* JIRA Files */}
              <div>
                <h3 className="text-sm font-medium mb-2">{t('jira_files')} ({t('required')})</h3>
                <div
                  {...getJiraRootProps()}
                  className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-primary/5"
                >
                  <input {...getJiraInputProps()} />
                  <p className="text-sm">{t('drop_files')}</p>
                </div>
                
                {jiraFiles.length > 0 && (
                  <div className="mt-2">
                    <h4 className="text-xs font-medium mb-1">{t('selected_files')}</h4>
                    <ul className="text-xs space-y-1">
                      {jiraFiles.map((file, index) => (
                        <li key={index} className="flex justify-between">
                          <span>{file.name} ({formatFileSize(file.size)})</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 px-2"
                            onClick={() => removeJiraFile(index)}
                          >
                            {t('remove')}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
              
              {/* Confluence Files */}
              <div>
                <h3 className="text-sm font-medium mb-2">{t('confluence_files')} ({t('optional')})</h3>
                <div
                  {...getConfluenceRootProps()}
                  className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-primary/5"
                >
                  <input {...getConfluenceInputProps()} />
                  <p className="text-sm">{t('drop_files')}</p>
                </div>
                
                {confluenceFiles.length > 0 && (
                  <div className="mt-2">
                    <h4 className="text-xs font-medium mb-1">{t('selected_files')}</h4>
                    <ul className="text-xs space-y-1">
                      {confluenceFiles.map((file, index) => (
                        <li key={index} className="flex justify-between">
                          <span>{file.name} ({formatFileSize(file.size)})</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 px-2"
                            onClick={() => removeConfluenceFile(index)}
                          >
                            {t('remove')}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
              
              {/* Custom Mapping Option */}
              <div className="p-4 border border-dashed rounded-md">
                <div className="flex items-center space-x-2 mb-3">
                  <input
                    type="checkbox"
                    id="use-custom-mapping"
                    checked={useCustomMapping}
                    onChange={() => setUseCustomMapping(!useCustomMapping)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <label htmlFor="use-custom-mapping" className="text-sm font-medium">
                    {t('custom_mapping')}
                  </label>
                </div>
                
                {useCustomMapping && (
                  <div>
                    <div
                      {...getMappingRootProps()}
                      className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-primary/5"
                    >
                      <input {...getMappingInputProps()} />
                      <FileJson className="h-5 w-5 mx-auto mb-2 text-muted-foreground" />
                      <p className="text-sm">{t('drop_files')}</p>
                    </div>
                    
                    {mappingFiles.length > 0 && (
                      <div className="mt-2">
                        <h4 className="text-xs font-medium mb-1">{t('select_mapping_files')}</h4>
                        <ul className="text-xs space-y-1">
                          {mappingFiles.map((file, index) => (
                            <li key={index} className="flex justify-between">
                              <span>{file.name} ({formatFileSize(file.size)})</span>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 px-2"
                                onClick={() => removeMappingFile(index)}
                              >
                                {t('remove')}
                              </Button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* Processing Options */}
              <div>
                <h3 className="text-sm font-medium mb-3">{t('processing_options')}</h3>
                
                <div className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="compress-output"
                      checked={compressOutput}
                      onChange={() => setCompressOutput(!compressOutput)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <label htmlFor="compress-output" className="text-sm">
                      {t('compress_output')}
                    </label>
                  </div>
                  
                  <div>
                    <label htmlFor="min-match-score" className="block text-sm mb-1">
                      {t('min_match_score')}
                    </label>
                    <input
                      type="number"
                      id="min-match-score"
                      value={minMatchScore}
                      onChange={(e) => setMinMatchScore(e.target.value)}
                      min="0"
                      max="1"
                      step="0.1"
                      className="w-24 p-1 border rounded-md bg-background"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {t('higher_values')}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="p-3 bg-primary/5 rounded-md">
                <p className="text-sm text-muted-foreground">
                  <strong>Note:</strong> {t('complete_workflow')}
                </p>
                <ul className="text-xs text-muted-foreground list-disc list-inside mt-1">
                  <li>{t('process_files')}</li>
                  <li>{t('enrich_content')}</li>
                  <li>{t('establish_matches')}</li>
                  <li>{t('generate_reports')}</li>
                </ul>
              </div>
              
              <Button
                onClick={handleUnifiedProcessing}
                disabled={isProcessing || jiraFiles.length === 0}
                className="w-full"
              >
                {isProcessing ? (
                  <React.Fragment>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('processing')}
                  </React.Fragment>
                ) : (
                  t('run_unified')
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <div className="mt-8 p-4 bg-primary-foreground rounded-lg">
        <h2 className="text-lg font-semibold mb-2">{t('expected_output')}</h2>
        <p className="text-sm text-muted-foreground mb-2">
          {t('zip_file')}
        </p>
        <ul className="text-sm text-muted-foreground list-disc list-inside">
          <li>{t('processed_jira_confluence')}</li>
          <li>{t('matching_results')}</li>
          <li>{t('llm_enriched_files')}</li>
          <li>{t('full_directory_structure')}</li>
          <li>{t('similar_to_demo')}</li>
        </ul>
      </div>
      
      {/* Help button in the bottom right corner */}
      <div className="fixed bottom-6 right-6 z-50">
        <TooltipProvider delayDuration={300}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="default" size="icon" className="h-14 w-14 shadow-lg bg-primary hover:bg-primary/90 transition-all">
                <Bot className="h-6 w-6" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left" align="end" className="max-w-md p-4 bg-card border shadow-lg">
              <div className="space-y-2">
                <h4 className="font-semibold text-base">{t('help_tooltip')}</h4>
                <p className="text-sm whitespace-pre-line">
                  {t('language') === 'en' 
                    ? "• Upload JSON files from Jira and/or Confluence\n• Links documents across platforms by matching content\n• Enriches data with AI analysis and categorization\n• Creates LLM-ready output for knowledge bases"
                    : "• Importez des fichiers JSON de Jira et/ou Confluence\n• Établit des liens entre documents en comparant le contenu\n• Enrichit les données avec analyse et catégorisation IA\n• Crée une sortie compatible LLM pour bases de connaissances"}
                </p>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
} 