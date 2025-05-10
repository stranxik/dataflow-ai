import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Database, Upload, Check, Loader2, Scissors } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { processJson, cleanJson, compressJson } from '@/api/apiService';
import { formatFileSize, isValidFileType, createDownloadLink } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';
import { useLanguage } from '@/components/LanguageProvider';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Bot } from 'lucide-react';

export default function JSONProcessingPage() {
  const { t } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingMode, setProcessingMode] = useState<'process' | 'clean' | 'compress' | 'chunks'>('process');
  const [compressionLevel, setCompressionLevel] = useState(19);
  const [recursive, setRecursive] = useState(false);
  const [itemsPerFile, setItemsPerFile] = useState(500);
  const { toast } = useToast();

  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      if (isValidFileType(file, ['json'])) {
        setSelectedFile(file);
        toast({
          title: t('file_selected'),
          description: `${file.name} (${formatFileSize(file.size)})`,
        });
      } else {
        toast({
          title: t('invalid_file_type'),
          description: t('select_json_file'),
          variant: 'destructive',
        });
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
    },
    maxFiles: 1,
  });

  const handleProcessJSON = async () => {
    if (!selectedFile) {
      toast({
        title: t('no_file_selected'),
        description: t('select_file_first'),
        variant: 'destructive',
      });
      return;
    }

    setIsProcessing(true);

    try {
      let result: Blob;
      
      switch (processingMode) {
        case 'process':
          result = await processJson(selectedFile, true, true);
          break;
        case 'clean':
          result = await cleanJson(selectedFile, recursive);
          break;
        case 'compress':
          result = await compressJson(selectedFile, compressionLevel, false);
          break;
        case 'chunks':
          // Call API to split JSON file
          const formData = new FormData();
          formData.append('file', selectedFile);
          formData.append('items_per_file', String(itemsPerFile));

          const response = await fetch('/api/json/chunks', {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error: ${response.status} ${response.statusText}`);
          }

          result = await response.blob();
          
          // Create a download link for the processed file
          createDownloadLink(
            result, 
            `${selectedFile.name.replace('.json', '')}_chunks.zip`
          );
          
          toast({
            title: t('processing_complete'),
            description: t('your_json_file_has_been_split_into_chunks_successfully'),
          });
          setIsProcessing(false);
          return;
        default:
          throw new Error('Invalid processing mode');
      }
      
      // Create a download link for the processed file (for non-chunks modes)
      createDownloadLink(
        result, 
        `${selectedFile.name.replace('.json', '')}_processed.json`
      );
      
      toast({
        title: t('processing_complete'),
        description: t('your_json_file_has_been_processed_successfully'),
      });
    } catch (error) {
      console.error('Error processing JSON:', error);
      toast({
        title: t('processing_failed'),
        description: error instanceof Error ? error.message : 'An unknown error occurred',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">{t('json_processing_title')}</h1>
      
      <Tabs defaultValue="process" onValueChange={(value) => setProcessingMode(value as any)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="process">{t('process_json')}</TabsTrigger>
          <TabsTrigger value="clean">{t('clean_data')}</TabsTrigger>
          <TabsTrigger value="compress">{t('compress')}</TabsTrigger>
          <TabsTrigger value="chunks">{t('split_chunks')}</TabsTrigger>
        </TabsList>
        
        <TabsContent value="process">
          <Card>
            <CardHeader>
              <CardTitle>{t('json_processing_title')}</CardTitle>
              <CardDescription>
                {t('automatic_structure')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-muted-foreground">
                {t('json_processing_description')}
              </p>
              
              <div className="p-3 bg-primary/5 rounded-md">
                <p className="text-sm text-muted-foreground">
                  <strong>Note:</strong> {t('note_llm_enrichment')}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="clean">
          <Card>
            <CardHeader>
              <CardTitle>{t('clean_sensitive_data')}</CardTitle>
              <CardDescription>
                {t('remove_sensitive_data')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-muted-foreground">
                {t('clean_sensitive_data_description')}
              </p>
              
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="recursive"
                  checked={recursive}
                  onChange={() => setRecursive(!recursive)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <label htmlFor="recursive" className="text-sm font-medium">
                  {t('clean_recursively')}
                </label>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="compress">
          <Card>
            <CardHeader>
              <CardTitle>{t('compress_json')}</CardTitle>
              <CardDescription>
                {t('optimize_json_files')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-muted-foreground">
                {t('compress_json_description')}
              </p>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">
                  {t('compression_level')}
                </label>
                <select
                  value={compressionLevel}
                  onChange={(e) => setCompressionLevel(Number(e.target.value))}
                  className="w-full p-2 border rounded-md bg-background"
                >
                  <option value="15">15 - {t('fast')}</option>
                  <option value="19">19 - {t('balanced')}</option>
                  <option value="22">22 - {t('maximum')}</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  {t('higher_compression_slower')}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="chunks">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Scissors className="mr-2 h-5 w-5" />
                {t('split_json_files')}
              </CardTitle>
              <CardDescription>
                {t('smaller_chunks')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-muted-foreground">
                {t('json_split_description')}
              </p>
              
              <div className="mb-6">
                <label className="block text-sm font-medium mb-1">
                  {t('items_per_chunk')}
                </label>
                <input
                  type="number"
                  min="100"
                  max="10000"
                  value={itemsPerFile}
                  onChange={(e) => setItemsPerFile(Number(e.target.value))}
                  className="w-full p-2 border rounded-md bg-background"
                />
              </div>
              
              <div className="mt-4 p-4 bg-muted rounded-lg">
                <h2 className="text-lg font-semibold mb-2">{t('when_use_chunking')}</h2>
                <ul className="space-y-2 text-sm text-muted-foreground ml-5 list-disc">
                  <li>{t('large_files')}</li>
                  <li>{t('parallel_processing')}</li>
                  <li>{t('timeout_errors')}</li>
                  <li>{t('memory_management')}</li>
                </ul>
                <p className="mt-4 text-sm text-muted-foreground">
                  {t('chunked_files_output')}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      <div className="mt-8">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive ? 'border-primary bg-primary/5' : 'border-border'
          } ${selectedFile ? 'bg-primary/5' : ''}`}
        >
          <input {...getInputProps()} />
          
          {selectedFile ? (
            <div className="space-y-2">
              <Check className="h-10 w-10 text-green-500 mx-auto" />
              <p className="font-medium">{selectedFile.name}</p>
              <p className="text-sm text-muted-foreground">
                {formatFileSize(selectedFile.size)}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                }}
              >
                {t('change_file')}
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex justify-center">
                {isDragActive ? (
                  <Upload className="h-10 w-10 text-primary" />
                ) : (
                  <Database className="h-10 w-10 text-primary" />
                )}
              </div>
              <p className="font-medium">
                {isDragActive
                  ? t('drop_files')
                  : t('drop_files')}
              </p>
              <p className="text-sm text-muted-foreground">
                {t('json_files_only')}
              </p>
            </div>
          )}
        </div>
      </div>
      
      <div className="mt-6 flex justify-end">
        <Button
          onClick={handleProcessJSON}
          disabled={!selectedFile || isProcessing}
          className="min-w-32"
        >
          {isProcessing ? (
            <React.Fragment>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {processingMode === 'chunks' ? t('splitting') : t('processing')}
            </React.Fragment>
          ) : (
            processingMode === 'chunks' ? t('split_chunks') : t('process_json')
          )}
        </Button>
      </div>

      <div className="mt-8 p-4 bg-primary-foreground rounded-lg">
        <h2 className="text-lg font-semibold mb-2">{t('processing_info')}</h2>
        <p className="text-sm text-muted-foreground">
          {t('secure_server')}. {t('automatic_pipeline')}.
        </p>
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
                    ? "• Process: Extract data structure and detect fields automatically\n• Clean: Remove sensitive data like API keys and credentials\n• Compress: Reduce file size for storage or transfer\n• Split: Break large JSON into manageable chunks"
                    : "• Traiter: Extrait la structure et détecte les champs automatiquement\n• Nettoyer: Supprime les données sensibles (clés API, identifiants)\n• Compresser: Réduit la taille des fichiers pour stockage ou transfert\n• Diviser: Découpe les gros fichiers JSON en morceaux gérables"}
                </p>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
} 