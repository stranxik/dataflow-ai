import React, { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { FileText, Upload, Check, Loader2, Shield, Wrench, Database, Bot } from 'lucide-react';
import { processPdf } from '@/api/apiService';
import { formatFileSize, isValidFileType, createDownloadLink } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';
import { useLanguage } from '@/components/LanguageProvider';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export default function HomePage() {
  const { t } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [maxImages, setMaxImages] = useState(10);
  const { toast } = useToast();

  // Add the Blaike easter egg in the console
  useEffect(() => {
    const blaikeLogo = `
%c████████╗ ██████╗ ██████╗     ███████╗███████╗ ██████╗██████╗ ███████╗████████╗
%c╚══██╔══╝██╔═══██╗██╔══██╗    ██╔════╝██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝
%c   ██║   ██║   ██║██████╔╝    ███████╗█████╗  ██║     ██████╔╝█████╗     ██║   
%c   ██║   ██║   ██║██╔═══╝     ╚════██║██╔══╝  ██║     ██╔══██╗██╔══╝     ██║   
%c   ██║   ╚██████╔╝██║         ███████║███████╗╚██████╗██║  ██║███████╗   ██║   
%c   ╚═╝    ╚═════╝ ╚═╝         ╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   
                                                                             
%cBBBBB   L       AAAAA   III  K   K  EEEEE
%cB    B  L      A     A  I   K  K   E
%cBBBBB   L      AAAAAAA  I   KKK    EEEE
%cB    B  L      A     A  I   K  K   E
%cBBBBB   LLLLL  A     A III  K   K  EEEEE
    `;

    // Console styling
    console.log(
      blaikeLogo,
      'color: #6d28d9; font-weight: bold;',
      'color: #7c3aed; font-weight: bold;',
      'color: #8b5cf6; font-weight: bold;',
      'color: #9d7aea; font-weight: bold;',
      'color: #a78bfa; font-weight: bold;',
      'color: #c4b5fd; font-weight: bold;',
      'color: #7c3aed; font-weight: bold;',
      'color: #8b5cf6; font-weight: bold;',
      'color: #9d7aea; font-weight: bold;',
      'color: #a78bfa; font-weight: bold;',
      'color: #c4b5fd; font-weight: bold;',
    );

    const welcomeMessage = `
%c📢 So, you found us! Welcome to Blaike's hidden world.

%cWho are we?
%cBlaike is a specialized entity in AI. We combine technical and educational expertise to support professionals and companies in their digital transformation, with a particular focus on data sovereignty and operational efficiency.

%cOur Services:
%c• AI Agents - Conversational assistants tailored to your business needs
• RAG Systems - Connect your document bases for intelligent retrieval
• Smart Automation - Integrate with your existing tools
• Rapid AI Prototyping - From concept to MVP in days

%cOur Products:
%c• Passerelle.cc - SaaS for training management and data integration
• Flowz.cc - Workflow automation and data orchestration platform
• DataFlow AI - This tool you're using for intelligent PDF extraction and JSON processing!

%cWant to learn more or work with us?
%cVisit us at https://blaike.cc
Contact us at https://blaike.cc/contact
Explore our ecosystem at https://blaike.cc/ecosystem
    `;

    setTimeout(() => {
      console.log(
        welcomeMessage,
        'font-size: 14px; font-weight: bold; color: #6d28d9;',
        'font-size: 16px; font-weight: bold; color: #4f46e5;',
        'font-size: 14px; color: #4b5563;',
        'font-size: 16px; font-weight: bold; color: #4f46e5;',
        'font-size: 14px; color: #4b5563;',
        'font-size: 16px; font-weight: bold; color: #4f46e5;',
        'font-size: 14px; color: #4b5563;',
        'font-size: 16px; font-weight: bold; color: #4f46e5;',
        'font-size: 14px; color: #6d28d9;'
      );
    }, 500);
  }, []);

  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      if (isValidFileType(file, ['pdf'])) {
        setSelectedFile(file);
        toast({
          title: t('file_selected'),
          description: `${file.name} (${formatFileSize(file.size)})`,
        });
      } else {
        toast({
          title: t('invalid_file_type'),
          description: t('select_pdf_file'),
          variant: 'destructive',
        });
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
  });

  const handleProcessPDF = async () => {
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
      // Using 'complete' mode for the homepage
      const result = await processPdf(selectedFile, 'complete', maxImages);
      
      // Create a download link for the processed file
      createDownloadLink(
        result, 
        `${selectedFile.name.replace('.pdf', '')}_processed.json`
      );
      
      toast({
        title: t('processing_complete'),
        description: t('your_pdf_has_been_processed_successfully'),
      });
    } catch (error) {
      console.error('Error processing PDF:', error);
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
    <div className="py-10 px-4">
      <div className="text-center mb-12">
        <h1 className="text-5xl font-black tracking-tight mb-6 flex items-center justify-center flex-wrap">
          {t('pdf_analysis')}
          <div className="relative inline-block ml-2 translate-y-[-24px]">
            <span className="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-white text-primary dark:bg-background border border-primary rounded-full hover:animate-[wiggle_0.5s_ease-in-out_infinite] cursor-pointer transition-all hover:shadow-md duration-300">
              GPT-4o
            </span>
          </div>
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          {t('extract_text')}
        </p>
      </div>

      <div className="max-w-3xl mx-auto bg-card shadow-lg rounded-none p-8 mb-16">
        <div className="space-y-8">
          <div className="flex items-center justify-center space-x-4 mx-auto max-w-sm">
            <label className="text-sm font-medium whitespace-nowrap">
              {t('max_images')}
            </label>
            <input
              type="number"
              min="1"
              max="100"
              value={maxImages}
              onChange={(e) => setMaxImages(Number(e.target.value))}
              className="w-24 p-2 border rounded-none bg-background text-center"
            />
          </div>
          
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-none p-10 text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-primary bg-primary/5' : 'border-border'
            } ${selectedFile ? 'bg-primary/5' : ''}`}
          >
            <input {...getInputProps()} />
            
            {selectedFile ? (
              <div className="space-y-3">
                <Check className="h-12 w-12 text-green-500 mx-auto" />
                <p className="font-medium text-lg">{selectedFile.name}</p>
                <p className="text-muted-foreground">
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
              <div className="space-y-4">
                <div className="flex justify-center">
                  {isDragActive ? (
                    <Upload className="h-16 w-16 text-primary" />
                  ) : (
                    <FileText className="h-16 w-16 text-primary" />
                  )}
                </div>
                <p className="font-medium text-xl">
                  {isDragActive
                    ? t('drop_pdf_file')
                    : t('drag_drop_pdf')}
                </p>
                <p className="text-muted-foreground">
                  {t('or')} <span className="text-primary">{t('click_to_browse')}</span> {t('your_device')}
                </p>
                <p className="text-sm text-muted-foreground">
                  {t('pdf_files_only')} ({t('max_50mb')})
                </p>
              </div>
            )}
          </div>
          
          <div className="flex justify-center">
            <Button
              onClick={handleProcessPDF}
              disabled={!selectedFile || isProcessing}
              size="lg"
              className="px-12 py-6 text-lg"
            >
              {isProcessing ? (
                <React.Fragment>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  {t('processing')}
                </React.Fragment>
              ) : (
                t('process_pdf')
              )}
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-24 py-20 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10 rounded-none">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-16">{t('why_choose')}</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-x-12 gap-y-16">
            <div className="flex flex-col items-center text-center">
              <div className="bg-background rounded-none p-5 shadow-md mb-6 w-20 h-20 flex items-center justify-center">
                <Shield className="h-10 w-10 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-3">{t('100_private')}</h3>
              <p className="text-muted-foreground">
                {t('data_never_persists')}
              </p>
            </div>
            
            <div className="flex flex-col items-center text-center">
              <div className="bg-background rounded-none p-5 shadow-md mb-6 w-20 h-20 flex items-center justify-center">
                <Wrench className="h-10 w-10 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-3">{t('powerful_tools')}</h3>
              <p className="text-muted-foreground">
                {t('battle_tested')}
              </p>
            </div>
            
            <div className="flex flex-col items-center text-center">
              <div className="bg-background rounded-none p-5 shadow-md mb-6 w-20 h-20 flex items-center justify-center">
                <Database className="h-10 w-10 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-3">{t('rag_ready')}</h3>
              <p className="text-muted-foreground">
                {t('optimized_for_rag')}
              </p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Bouton d'aide positionné en bas à droite */}
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
                <p className="text-sm whitespace-pre-line">{t('pdf_extraction_explanation')}</p>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
} 