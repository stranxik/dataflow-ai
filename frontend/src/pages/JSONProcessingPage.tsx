import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Database, Check, Loader2, Scissors } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { processJson, cleanJson, compressJson } from '@/api/apiService';
import { formatFileSize, isValidFileType, createDownloadLink } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';
import { useLanguage } from '@/components/LanguageProvider';
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
      let filename: string;
      
      // Process the file based on the selected mode
      switch (processingMode) {
        case 'process':
          result = await processJson(selectedFile, true, true);
          filename = `${selectedFile.name.replace('.json', '')}_processed.json`;
          break;
        case 'clean':
          result = await cleanJson(selectedFile, recursive);
          filename = `${selectedFile.name.replace('.json', '')}_cleaned.json`;
          break;
        case 'compress':
          result = await compressJson(selectedFile, compressionLevel, false);
          filename = `${selectedFile.name.replace('.json', '')}_compressed.zst`;
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
          filename = `${selectedFile.name.replace('.json', '')}_chunks.zip`;
          break;
        default:
          throw new Error('Invalid processing mode');
      }
      
      // Create a download link and trigger download immediately
      createDownloadLink(result, filename);
      
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
                  {t('items_per_file')}
                </label>
                <input
                  type="number"
                  value={itemsPerFile}
                  onChange={(e) => setItemsPerFile(Number(e.target.value))}
                  min={1}
                  step={100}
                  className="w-full p-2 border rounded-md bg-background"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {t('recommended_value_500')}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      <div className={`mt-6 p-6 border-2 border-dashed rounded-lg ${isDragActive ? 'border-primary' : 'border-muted-foreground/25'}`} {...getRootProps()}>
        <input {...getInputProps()} />
        <div className="text-center">
          <Database className="mx-auto h-10 w-10 text-muted-foreground mb-4" />
          <p className="text-sm text-muted-foreground mb-2">
            {isDragActive ? t('drop_the_file_here') : t('drag_drop_json')}
          </p>
          <p className="text-xs text-muted-foreground">
            {t('or_click_to_select')}
          </p>
        </div>
      </div>
      
      {selectedFile && (
        <div className="mt-4 p-4 border rounded-md">
          <p className="text-sm font-medium">
            {t('selected_file')}: <span className="text-primary">{selectedFile.name}</span> ({formatFileSize(selectedFile.size)})
          </p>
        </div>
      )}
      
      <div className="mt-6 flex justify-center">
        <Button
          onClick={handleProcessJSON}
          disabled={!selectedFile || isProcessing}
          className="min-w-[200px]"
        >
          {isProcessing ? (
            <React.Fragment>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('processing')}...
            </React.Fragment>
          ) : (
            <React.Fragment>
              {processingMode === 'process' && (
                <React.Fragment>
                  <Bot className="mr-2 h-4 w-4" />
                  {t('process_file')}
                </React.Fragment>
              )}
              {processingMode === 'clean' && (
                <React.Fragment>
                  <Check className="mr-2 h-4 w-4" />
                  {t('clean_file')}
                </React.Fragment>
              )}
              {processingMode === 'compress' && (
                <React.Fragment>
                  <Database className="mr-2 h-4 w-4" />
                  {t('compress_file')}
                </React.Fragment>
              )}
              {processingMode === 'chunks' && (
                <React.Fragment>
                  <Scissors className="mr-2 h-4 w-4" />
                  {t('split_file')}
                </React.Fragment>
              )}
            </React.Fragment>
          )}
        </Button>
      </div>
    </div>
  );
} 