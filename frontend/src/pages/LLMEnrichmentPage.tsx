import { useState } from 'react';
import { Loader2, Link as LinkIcon, FileJson, Bot, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { unifiedProcess } from '@/api/apiService';
import { useToast } from '@/components/ui/use-toast';
import { useDropzone } from 'react-dropzone';
import { formatFileSize, isValidFileType, createDownloadLink } from '@/lib/utils';
import { useLanguage } from '@/components/LanguageProvider';
import { HelpTooltip } from '@/components/ui/HelpTooltip';

export default function LLMEnrichmentPage() {
  const { t } = useLanguage();
  const [jiraFiles, setJiraFiles] = useState<File[]>([]);
  const [confluenceFiles, setConfluenceFiles] = useState<File[]>([]);
  const [mappingFiles, setMappingFiles] = useState<File[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
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
      // Check for API key before making request
      const apiKey = (window as any).env?.VITE_API_KEY || import.meta.env?.VITE_API_KEY || '';
      if (!apiKey) {
        throw new Error('API key is missing. Please check your configuration.');
      }
      
      const result = await unifiedProcess(jiraFiles, confluenceFiles, true);
      
      createDownloadLink(result, 'enriched_results.zip');
      
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
                  className="border-2 border-dashed rounded-none p-6 text-center cursor-pointer transition-colors hover:bg-[#ff220c]/5"
                >
                  <input {...getJiraInputProps()} />
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-12 w-12 rounded-full bg-[#ff220c]/10 flex items-center justify-center">
                      <Upload className="h-6 w-6 text-primary" />
                    </div>
                    <div className="font-medium">
                      {t('drop_files')}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      JSON {t('files_only')}
                    </div>
                  </div>
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
                  className="border-2 border-dashed rounded-none p-6 text-center cursor-pointer transition-colors hover:bg-[#ff220c]/5"
                >
                  <input {...getConfluenceInputProps()} />
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-12 w-12 rounded-full bg-[#ff220c]/10 flex items-center justify-center">
                      <Upload className="h-6 w-6 text-primary" />
                    </div>
                    <div className="font-medium">
                      {t('drop_files')}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      JSON {t('files_only')}
                    </div>
                  </div>
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
                      className="border-2 border-dashed rounded-none p-6 text-center cursor-pointer transition-colors hover:bg-[#ff220c]/5"
                    >
                      <input {...getMappingInputProps()} />
                      <div className="flex flex-col items-center gap-2">
                        <div className="h-12 w-12 rounded-full bg-[#ff220c]/10 flex items-center justify-center">
                          <FileJson className="h-6 w-6 text-primary" />
                        </div>
                        <div className="font-medium">
                          {t('drop_files')}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          JSON {t('files_only')}
                        </div>
                      </div>
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
              <div className="p-4 bg-muted rounded-lg">
                <h3 className="text-sm font-medium mb-3">{t('processing_options')}</h3>
                
                <div className="space-y-3">
                  {/* Match score threshold */}
                  <div>
                    <label htmlFor="min-match-score" className="text-sm block mb-1">
                      {t('min_match_score')}
                    </label>
                    <select
                      id="min-match-score"
                      value={minMatchScore}
                      onChange={(e) => setMinMatchScore(e.target.value)}
                      className="w-full p-2 text-sm rounded-md border border-input bg-background"
                    >
                      <option value="0.1">0.1 - {t('more_matches_lower_quality')}</option>
                      <option value="0.3">0.3 - {t('balanced')}</option>
                      <option value="0.5">0.5 - {t('default')}</option>
                      <option value="0.7">0.7 - {t('higher_quality_fewer_matches')}</option>
                    </select>
                  </div>
                </div>
              </div>
              
              <div className="flex justify-center pt-4">
                <Button
                  size="lg"
                  onClick={handleUnifiedProcessing}
                  disabled={jiraFiles.length === 0 || isProcessing}
                  className="gap-2 min-w-[200px]"
                >
                  {isProcessing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Bot className="h-4 w-4" />
                  )}
                  {isProcessing ? t('processing') : t('start_unified_processing')}
                </Button>
              </div>
              
              {/* Information sur l'enrichissement LLM */}
              <div className="mt-8 p-6 bg-muted/30 rounded-lg" key="llm-info-section">
                <h3 className="text-xl font-semibold mb-4" key="llm-info-title">{t('about_llm_enrichment')}</h3>
                <p className="mb-6 text-muted-foreground" key="llm-info-desc">{t('llm_enrichment_explanation')}</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6" key="llm-info-grid">
                  <div className="bg-background p-4 rounded-lg" key="llm-benefits">
                    <h4 className="font-medium mb-3" key="benefits-title">{t('benefits')}</h4>
                    <ul className="space-y-2 list-disc pl-5" key="benefits-list">
                      <li key="benefit-1">{t('llm_benefit_1')}</li>
                      <li key="benefit-2">{t('llm_benefit_2')}</li>
                      <li key="benefit-3">{t('llm_benefit_3')}</li>
                    </ul>
                  </div>
                  
                  <div className="bg-background p-4 rounded-lg" key="llm-limitations">
                    <h4 className="font-medium mb-3" key="limitations-title">{t('limitations')}</h4>
                    <ul className="space-y-2 list-disc pl-5" key="limitations-list">
                      <li key="limitation-1">{t('llm_limitation_1')}</li>
                      <li key="limitation-2">{t('llm_limitation_2')}</li>
                      <li key="limitation-3">{t('llm_limitation_3')}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <HelpTooltip explanationKey="llm_enrichment_page_info" />
    </div>
  );
} 