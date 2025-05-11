import { Bot } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useLanguage } from "@/components/LanguageProvider";

interface HelpTooltipProps {
  explanationKey: string;
  className?: string;
}

export function HelpTooltip({ explanationKey, className }: HelpTooltipProps) {
  const { t } = useLanguage();
  
  return (
    <div className={`fixed bottom-4 right-4 z-50 ${className}`}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              className="bg-primary hover:bg-primary/90 text-primary-foreground p-3 rounded-none shadow-lg"
              aria-label={t('help_tooltip')}
            >
              <Bot className="h-8 w-8" />
            </button>
          </TooltipTrigger>
          <TooltipContent
            side="left"
            align="end"
            className="max-w-[350px] p-4 text-sm whitespace-pre-wrap"
          >
            <div className="font-semibold mb-2">{t('help_tooltip')}</div>
            <div className="text-muted-foreground">{t(explanationKey)}</div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
} 