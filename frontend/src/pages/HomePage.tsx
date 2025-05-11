import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { FileText, Upload, Loader2, Shield, Wrench, Database, Bot, DollarSign } from 'lucide-react';
import { processPdf } from '@/api/apiService';
import { formatFileSize, isValidFileType, createDownloadLink } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';
import { useLanguage } from '@/components/LanguageProvider';
import { HelpTooltip } from '@/components/ui/HelpTooltip';
import { MAX_PDF_SIZE_MB, MAX_PDF_SIZE_BYTES, MAX_IMAGES_ANALYSIS, DEFAULT_IMAGES_ANALYSIS, validatePdfSize } from '@/lib/config';

export default function HomePage() {
  const { t } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [maxImages, setMaxImages] = useState(DEFAULT_IMAGES_ANALYSIS);
  const { toast } = useToast();

  // Easter egg pour la console
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

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      if (isValidFileType(file, ['pdf'])) {
        // Vérifier la taille du fichier
        if (!validatePdfSize(file)) {
          toast({
            title: t('file_too_large'),
            description: t('file_size_limit').replace('{size}', `${MAX_PDF_SIZE_MB}`),
            variant: 'destructive',
          });
          return;
        }
        
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
  }, [t, toast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    maxSize: MAX_PDF_SIZE_BYTES,
  });

  // Traitement du PDF avec téléchargement automatique
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
      console.log(`Starting PDF processing: ${selectedFile.name}`);
      
      const result = await processPdf(
        selectedFile,
        'complete',
        maxImages,
        undefined,
        'zip'
      );
      
      console.log(`PDF processing completed, blob received: ${result.size} bytes, type: ${result.type}`);
      
      // Vérifier la validité du blob retourné
      if (result.size === 0) {
        throw new Error('Empty response received from server');
      }
      
      if (result.size < 1000 && result.type.includes('html')) {
        const text = await result.text();
        if (text.includes('error') || text.includes('Error')) {
          throw new Error('Server returned an error page');
        }
      }
      
      // Déclencher le téléchargement directement
      const zipBlob = (!result.type.includes('zip') && !result.type.includes('octet-stream'))
        ? new Blob([result], { type: 'application/zip' })
        : result;
      
      // Déclencher le téléchargement immédiatement
      createDownloadLink(
        zipBlob,
        `${selectedFile.name.replace('.pdf', '')}_analysis.zip`
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
          <div className="relative inline-block ml-2 translate-y-[-22px]">
            <span className="inline-flex items-center px-3 py-1 text-xs font-medium bg-white text-primary dark:bg-background border border-primary rounded-full hover:animate-[wiggle_0.5s_ease-in-out_infinite] cursor-pointer transition-all hover:shadow-lg shadow-md transform rotate-2 duration-300">
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
              min="0"
              max={MAX_IMAGES_ANALYSIS}
              value={maxImages}
              onChange={(e) => setMaxImages(Number(e.target.value))}
              className="w-24 p-2 border rounded-none bg-background text-center"
            />
          </div>
          
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
                  <FileText className="h-6 w-6 text-primary" />
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
                  }}
                >
                  {t('remove_file')}
                </Button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <div className="h-12 w-12 rounded-full bg-[#ff220c]/10 flex items-center justify-center">
                  <Upload className="h-6 w-6 text-primary" />
                </div>
                <div className="font-medium">
                  {isDragActive ? t('drop_file_here') : t('upload_pdf')}
                </div>
                <div className="text-sm text-muted-foreground">
                  PDF (max {MAX_PDF_SIZE_MB}MB)
                </div>
              </div>
            )}
          </div>
          
          <div className="flex justify-center">
            <Button 
              size="lg" 
              onClick={handleProcessPDF}
              disabled={!selectedFile || isProcessing}
              className="gap-2 min-w-[200px]"
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              {isProcessing ? t('processing') : t('process_pdf')}
            </Button>
          </div>
        </div>
      </div>

      <div className="py-16 bg-gray-50 dark:bg-gray-900/10 w-full my-20 -mx-4">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-2xl font-bold mb-10 text-center">{t('how_it_works')}</h2>
          
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div className="bg-card p-6 shadow-md rounded-none">
              <div className="flex flex-col items-center text-center space-y-4">
                <div className="h-10 w-10 rounded-none bg-[#ff220c]/10 flex items-center justify-center">
                  <Shield className="h-5 w-5 text-primary" />
                </div>
                <h3 className="text-lg font-semibold">{t('secure_processing')}</h3>
                <p className="text-sm text-muted-foreground">{t('secure_processing_description')}</p>
              </div>
            </div>
            
            <div className="bg-card p-6 shadow-md rounded-none">
              <div className="flex flex-col items-center text-center space-y-4">
                <div className="h-10 w-10 rounded-none bg-[#ff220c]/10 flex items-center justify-center">
                  <Wrench className="h-5 w-5 text-primary" />
                </div>
                <h3 className="text-lg font-semibold">{t('powerful_extraction')}</h3>
                <p className="text-sm text-muted-foreground">{t('powerful_extraction_description')}</p>
              </div>
            </div>
            
            <div className="bg-card p-6 shadow-md rounded-none">
              <div className="flex flex-col items-center text-center space-y-4">
                <div className="h-10 w-10 rounded-none bg-[#ff220c]/10 flex items-center justify-center">
                  <Database className="h-5 w-5 text-primary" />
                </div>
                <h3 className="text-lg font-semibold">{t('organized_data')}</h3>
                <p className="text-sm text-muted-foreground">{t('organized_data_description')}</p>
              </div>
            </div>
            
            <div className="bg-card p-6 shadow-md rounded-none">
              <div className="flex flex-col items-center text-center space-y-4">
                <div className="h-10 w-10 rounded-none bg-[#ff220c]/10 flex items-center justify-center">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
                <h3 className="text-lg font-semibold">{t('ai_analysis')}</h3>
                <p className="text-sm text-muted-foreground">{t('ai_analysis_description')}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <HelpTooltip explanationKey="pdf_extraction_page_info" />
      
      <div className="mt-24 max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold mb-10 text-center">
          {t('why_our_image_extraction_is_different')}
        </h2>
        <p className="text-sm text-muted-foreground max-w-2xl mx-auto text-center mb-10">
          {t('beyond_traditional_ocr_description')}
        </p>

        <div className="space-y-6">
          {[
            {
              icon: Wrench,
              title: t('beyond_traditional_ocr_title'),
              description: t('beyond_traditional_ocr_description'),
            },
            {
              icon: Database,
              title: t('structured_data_extraction_title'),
              description: t('structured_data_extraction_description'),
            },
            {
              icon: Bot,
              title: t('transform_your_technical_documents'),
              description: t('technical_documentation_description'),
            }
          ].map(({ icon: Icon, title, description }, index) => (
            <div key={index} className="bg-gradient-to-r from-[#ff220c]/5 to-transparent p-6 rounded-none border-l-4 border-[#ff220c]/30">
              <div className="flex items-center">
                <div className="mr-4 h-10 w-10 rounded-none bg-[#ff220c]/10 flex items-center justify-center">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{title}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-24 mb-12">
          <h2 className="text-2xl font-bold mb-10 text-center">{t('perfect_for_professionals')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: t('engineering_title'),
                description: t('engineering_description'),
                icon: Wrench,
              },
              {
                title: t('medical_research_title'),
                description: t('medical_research_description'),
                icon: DollarSign,
              },
              {
                title: t('technical_documentation_title'),
                description: t('technical_documentation_description'),
                icon: Upload,
              }
            ].map(({ title, description, icon: Icon }, index) => (
              <div key={index} className="bg-gradient-to-r from-[#ff220c]/10 to-[#ff220c]/5 p-6 rounded-none shadow-sm hover:shadow-md transition-all duration-300 border border-border">
                <div className="flex flex-col items-center text-center space-y-4">
                  <div className="h-10 w-10 rounded-none bg-[#ff220c]/10 flex items-center justify-center">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <h4 className="text-lg font-semibold">{title}</h4>
                  <p className="text-sm text-muted-foreground">{description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
} 