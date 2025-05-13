import { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Database, Check, Loader2, Scissors } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { processJson, cleanJson, compressJson } from '@/api/apiService';
import { formatFileSize,createDownloadLink } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';
import { useLanguage } from '@/components/LanguageProvider';
import { Bot } from 'lucide-react';
import { HelpTooltip } from '@/components/ui/HelpTooltip';

export default function JSONProcessingPage() {
  const { t } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingMode, setProcessingMode] = useState<'process' | 'clean' | 'compress' | 'chunks'>('process');
  const [compressionLevel, setCompressionLevel] = useState(19);
  const [recursive, setRecursive] = useState(false);
  const [itemsPerFile, setItemsPerFile] = useState(500);
  const { toast } = useToast();

  // Add new state to track if file is JSON or ZST
  const [isZstFile, setIsZstFile] = useState(false);

  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      // Check if file is a JSON or ZST file
      if (file.name.toLowerCase().endsWith('.json')) {
        setIsZstFile(false);
        setSelectedFile(file);
        toast({
          title: t('file_selected'),
          description: `${file.name} (${formatFileSize(file.size)})`,
        });
      } else if (file.name.toLowerCase().endsWith('.zst')) {
        setIsZstFile(true);
        setSelectedFile(file);
        toast({
          title: t('file_selected'),
          description: `${file.name} (${formatFileSize(file.size)})`,
        });
      } else {
        toast({
          title: t('invalid_file_type'),
          description: t('select_json_or_zst_file'),
          variant: 'destructive',
        });
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
      'application/zstd': ['.zst'],
      'application/octet-stream': ['.zst'],
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
          try {
            result = await compressJson(selectedFile, compressionLevel, false);
            // Change filename depending on if we're compressing or decompressing
            if (isZstFile) {
              // For decompression, return the original JSON filename
              filename = selectedFile.name.replace('.zst', '');
            } else {
              // For compression, use the original filename logic
              filename = `${selectedFile.name.replace('.json', '')}_compressed.zst`;
            }
          } catch (error) {
            console.error('Error compressing/decompressing file:', error);
            let errorMessage = 'Unknown error occurred';
            
            // Try to extract the error message from the API response
            if (error instanceof Error) {
              // Check if it's a network error or an API error
              if (error.message.includes('500')) {
                try {
                  // If we have more detailed error info, extract it
                  const match = error.message.match(/detail":"([^"]+)"/);
                  if (match && match[1]) {
                    errorMessage = match[1];
                  } else {
                    errorMessage = isZstFile ? 
                      t('error_decompressing') : 
                      t('error_compressing');
                  }
                } catch (e) {
                  errorMessage = isZstFile ? 
                    t('error_decompressing') : 
                    t('error_compressing');
                }
              } else {
                errorMessage = error.message;
              }
            }
            
            toast({
              title: isZstFile ? t('decompression_failed') : t('compression_failed'),
              description: errorMessage,
              variant: 'destructive',
            });
            setIsProcessing(false);
            return;
          }
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
        description: isZstFile ? 
          t('your_json_file_has_been_decompressed_successfully') :
          (processingMode === 'compress' ? 
            t('your_json_file_has_been_compressed_successfully') : 
            t('your_json_file_has_been_processed_successfully')),
      });
    } catch (error) {
      console.error(`Error processing JSON (${processingMode}):`, error);
      let errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      
      // Try to extract API error message if present
      if (typeof errorMessage === 'string' && errorMessage.includes('detail')) {
        try {
          const detail = JSON.parse(errorMessage.substring(errorMessage.indexOf('{')));
          if (detail.detail) {
            errorMessage = detail.detail;
          }
        } catch (e) {
          // If parsing fails, keep the original message
        }
      }
      
      toast({
        title: t('processing_failed'),
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Function to reset file on tab change
  const handleTabChange = (value: string) => {
    setProcessingMode(value as any);
    // Reset the file selection if switching to/from compress tab
    if (value === 'compress' || processingMode === 'compress') {
      setSelectedFile(null);
      setIsZstFile(false);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">{t('json_processing_title')}</h1>
      
      <Tabs defaultValue="process" onValueChange={handleTabChange}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="process">{t('process_json')}</TabsTrigger>
          <TabsTrigger value="clean">{t('clean_data')}</TabsTrigger>
          <TabsTrigger value="compress">{t('compress_decompress')}</TabsTrigger>
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
              <CardTitle>{isZstFile ? t('decompress_zst') : t('compress_json')}</CardTitle>
              <CardDescription>
                {isZstFile ? t('restore_json_files') : t('optimize_json_files')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-muted-foreground">
                {isZstFile ? t('decompress_zst_description') : t('compress_json_description')}
              </p>
              
              {!isZstFile && (
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
              )}
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
      
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-none p-10 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-primary bg-[#ff220c]/5' : 'border-border'
        } ${selectedFile ? 'bg-[#ff220c]/5' : ''}`}
      >
        <input {...getInputProps()} />
        
        {selectedFile ? (
          <div className="flex flex-col items-center gap-2">
            <div className="h-12 w-12 rounded-full bg-[#ff220c]/10 flex items-center justify-center">
              <Database className="h-6 w-6 text-primary" />
            </div>
            <div className="font-medium">{selectedFile.name}</div>
            <div className="text-sm text-muted-foreground">
              {formatFileSize(selectedFile.size)}
            </div>
            <Button 
              variant="outline" 
              size="sm"
              className="mt-2"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
                setIsZstFile(false);
              }}
            >
              {t('remove_file')}
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="h-12 w-12 rounded-full bg-[#ff220c]/10 flex items-center justify-center">
              <Database className="h-6 w-6 text-primary" />
            </div>
            <div className="font-medium">
              {isDragActive ? t('drop_the_file_here') : processingMode === 'compress' ? t('drag_drop_json_or_zst') : t('drag_drop_json')}
            </div>
            <div className="text-sm text-muted-foreground">
              {processingMode === 'compress' ? t('json_zst_files_only') : t('json_files_only')}
            </div>
          </div>
        )}
      </div>
      
      <div className="mt-6 flex justify-center">
        <Button
          size="lg"
          onClick={handleProcessJSON}
          disabled={!selectedFile || isProcessing}
          className="gap-2 min-w-[200px]"
        >
          {isProcessing ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            processingMode === 'process' ? <Bot className="h-4 w-4" /> :
            processingMode === 'clean' ? <Check className="h-4 w-4" /> :
            processingMode === 'compress' ? <Database className="h-4 w-4" /> :
            <Scissors className="h-4 w-4" />
          )}
          {isProcessing ? t('processing') : (
            processingMode === 'process' ? t('process_file') :
            processingMode === 'clean' ? t('clean_file') :
            processingMode === 'compress' ? (isZstFile ? t('decompress_file') : t('compress_file')) :
            t('split_file')
          )}
        </Button>
      </div>
      
      <HelpTooltip explanationKey="json_processing_page_info" />
    </div>
  );
} 