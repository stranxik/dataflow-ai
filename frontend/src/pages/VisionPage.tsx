import React, { useEffect, useState } from 'react';
import { useLanguage } from '@/components/LanguageProvider';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Helmet } from 'react-helmet-async';

// Import markdown files
import visionEn from './Vision.en.md?raw';
import visionFr from './Vision.fr.md?raw';

const VisionPage: React.FC = () => {
  const { language, t } = useLanguage();
  const [markdownContent, setMarkdownContent] = useState<string>('');

  useEffect(() => {
    // Sélectionner le contenu en fonction de la langue
    const content = language === 'fr' ? visionFr : visionEn;
    setMarkdownContent(content);
  }, [language]);

  return (
    <React.Fragment>
      <Helmet>
        <title>{t('our_vision')} - DataFlow AI</title>
        <meta name="description" content={t('DataFlow AI vision and mission')} />
      </Helmet>
      
      <div className="container mx-auto px-4 py-8">
        <div className="bg-card shadow-md rounded-none">
          <div className="p-6 space-y-6">
            <div className="prose dark:prose-invert max-w-none 
              prose-headings:border-b prose-headings:pb-2 
              prose-headings:border-border
              prose-h1:text-4xl prose-h1:font-black prose-h1:text-primary prose-h1:mb-6
              prose-h2:text-2xl prose-h2:font-bold prose-h2:text-foreground prose-h2:mt-10 prose-h2:mb-4
              prose-h3:text-xl prose-h3:font-semibold prose-h3:mt-8 prose-h3:mb-3
              prose-a:text-primary prose-a:no-underline hover:prose-a:underline
              prose-blockquote:border-l-4 prose-blockquote:border-primary
              prose-code:bg-muted prose-code:p-1
              prose-hr:border-border prose-hr:my-10
              prose-p:leading-relaxed prose-p:text-muted-foreground
              prose-ul:mt-2 prose-ol:mt-2 prose-li:mb-1 prose-li:text-muted-foreground
              prose-strong:text-foreground">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  hr: ({node, ...props}) => (
                    <hr 
                      {...props} 
                      className="border-t border-border my-10 w-full" 
                    />
                  ),
                  h2: ({node, children, ...props}) => (
                    <h2 {...props} className="mt-10 mb-4">{children}</h2>
                  ),
                  h3: ({node, children, ...props}) => (
                    <h3 {...props} className="mt-8 mb-3">{children}</h3>
                  ),
                  p: ({node, children, ...props}) => {
                    return <p {...props} className="mb-6">{children}</p>;
                  }
                }}
              >
                {markdownContent}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
};

export default VisionPage; 