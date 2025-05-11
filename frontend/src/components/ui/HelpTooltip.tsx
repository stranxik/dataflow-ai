import { Bot } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useLanguage } from "@/components/LanguageProvider";

interface HelpTooltipProps {
  explanationKey?: string;
  className?: string;
}

export function HelpTooltip({ explanationKey, className }: HelpTooltipProps) {
  const { t } = useLanguage();
  
  // Si une clé d'explication spécifique est fournie, l'utiliser
  // Sinon, utiliser l'explication générale de la page courante basée sur l'URL
  const getExplanationContent = () => {
    if (explanationKey) {
      return t(explanationKey);
    }
    
    // Déterminer la page courante
    const path = window.location.pathname;
    
    if (path.includes('json-processing')) {
      return t('json_processing_page_info');
    } else if (path.includes('llm-enrichment')) {
      return t('llm_enrichment_page_info');
    } else {
      // Page d'accueil - Extraction PDF
      return t('pdf_extraction_page_info');
    }
  };
  
  return (
    <div className={`fixed bottom-4 right-4 z-50 ${className}`}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              className="bg-primary hover:bg-primary/90 text-primary-foreground p-2 rounded-md shadow-lg"
              aria-label={t('help_tooltip')}
            >
              <Bot className="h-6 w-6" />
            </button>
          </TooltipTrigger>
          <TooltipContent
            side="left"
            align="end"
            className="max-w-[350px] p-4 text-sm whitespace-pre-wrap"
          >
            <div className="font-semibold mb-2">{t('help_tooltip')}</div>
            <div className="text-muted-foreground">{getExplanationContent()}</div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
} 