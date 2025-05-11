import { Button } from './button';
import { Download, Check, FileText, Archive } from 'lucide-react';
import Modal from './modal';
import { useLanguage } from '@/components/LanguageProvider';
import { formatDate } from '@/lib/utils';

interface PdfResultsModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileName: string;
  processedDate: Date;
  downloadZip: () => void;
  hasResults: boolean;
}

export function PdfResultsModal({
  isOpen,
  onClose,
  fileName,
  processedDate,
  downloadZip,
  hasResults = true,
}: PdfResultsModalProps) {
  const { t } = useLanguage();
  
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('processing_complete')}
      size="md"
    >
      <div className="space-y-6">
        <div className="bg-primary/5 p-4 border rounded-none">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
              <Check className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h3 className="font-medium">{t('file_processed_successfully')}</h3>
              <p className="text-sm text-muted-foreground">{formatDate(processedDate)}</p>
            </div>
          </div>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <FileText className="h-5 w-5 text-muted-foreground" />
            <span className="font-medium">{fileName}</span>
          </div>
          
          {hasResults ? (
            <div className="space-y-4">
              <p className="text-sm">{t('your_extraction_is_ready')}</p>
              
              <div className="flex justify-between items-center p-3 border rounded-none bg-secondary/10">
                <div className="flex items-center space-x-3">
                  <Archive className="h-5 w-5 text-primary" />
                  <div>
                    <div className="font-medium">{t('complete_results')}</div>
                    <div className="text-xs text-muted-foreground">{t('zip_file_with_all_extracted_data')}</div>
                  </div>
                </div>
                <Button 
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={downloadZip}
                >
                  <Download className="h-4 w-4" />
                  {t('download')}
                </Button>
              </div>
              
              <div className="text-xs text-muted-foreground mt-2">
                {t('results_include_extracted_text_images_analyses')}
              </div>
            </div>
          ) : (
            <div className="text-amber-600 text-sm bg-amber-50 dark:bg-amber-950/30 p-3 rounded-none">
              {t('no_results_found')}
            </div>
          )}
        </div>
        
        <div className="flex justify-end pt-4 border-t space-x-2">
          <Button variant="outline" onClick={onClose}>
            {t('close')}
          </Button>
          <Button onClick={downloadZip} className="gap-1.5">
            <Download className="h-4 w-4" />
            {t('download_results')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default PdfResultsModal; 