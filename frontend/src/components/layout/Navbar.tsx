import { Link } from 'react-router-dom';
import { Database, Cpu, Menu, X, Globe, Github, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/components/ThemeProvider';
import { useLanguage } from '@/components/LanguageProvider';
import { useState } from 'react';

export default function Navbar() {
  const { setTheme, theme } = useTheme();
  const { language, setLanguage, t } = useLanguage();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  const toggleLanguage = () => {
    setLanguage(language === 'fr' ? 'en' : 'fr');
  };

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  return (
    <nav className="bg-card shadow-sm">
      <div className="container mx-auto px-4 py-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Link to="/" className="text-2xl font-black text-primary">
              DataFlow AI
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-4">
            <Link to="/json-processing" className="flex items-center px-3 py-2 hover:bg-accent text-foreground">
              <Database className="mr-2 h-4 w-4" />
              <span>{t('json_processing')}</span>
            </Link>
            <Link to="/llm-enrichment" className="flex items-center px-3 py-2 hover:bg-accent text-foreground">
              <Cpu className="mr-2 h-4 w-4" />
              <span>{t('unified_processing_nav')}</span>
            </Link>
            <Link to="/vision" className="flex items-center px-3 py-2 hover:bg-accent text-foreground">
              <Eye className="mr-2 h-4 w-4" />
              <span>{t('our_vision')}</span>
            </Link>
            <Button 
              variant="outline" 
              className="ml-2" 
              onClick={toggleLanguage}
              aria-label={language === 'fr' ? 'Switch to English' : 'Passer en français'}
            >
              <Globe className="h-4 w-4 mr-1" />
              {language === 'fr' ? 'EN' : 'FR'}
            </Button>
            <Button 
              variant="outline" 
              className="ml-2" 
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? t('switch_to_light') : t('switch_to_dark')}
            >
              {theme === 'dark' ? '🌙' : '☀️'}
            </Button>
            <a 
              href="https://github.com/stranxik/json_parser" 
              target="_blank" 
              rel="noopener noreferrer"
              className="ml-2"
            >
              <Button 
                variant="outline" 
                aria-label="GitHub Repository"
              >
                <Github className="h-4 w-4" />
              </Button>
            </a>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <Button variant="ghost" size="icon" onClick={toggleMenu}>
              {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden pt-4 pb-2 space-y-2">
            <Link 
              to="/json-processing" 
              className="flex items-center px-3 py-2 hover:bg-accent text-foreground w-full"
              onClick={() => setIsMenuOpen(false)}
            >
              <Database className="mr-2 h-4 w-4" />
              <span>{t('json_processing')}</span>
            </Link>
            <Link 
              to="/llm-enrichment" 
              className="flex items-center px-3 py-2 hover:bg-accent text-foreground w-full"
              onClick={() => setIsMenuOpen(false)}
            >
              <Cpu className="mr-2 h-4 w-4" />
              <span>{t('unified_processing_nav')}</span>
            </Link>
            <Link 
              to="/vision" 
              className="flex items-center px-3 py-2 hover:bg-accent text-foreground w-full"
              onClick={() => setIsMenuOpen(false)}
            >
              <Eye className="mr-2 h-4 w-4" />
              <span>{t('our_vision')}</span>
            </Link>
            <Button 
              variant="outline" 
              className="w-full mt-2" 
              onClick={toggleLanguage}
            >
              <Globe className="h-4 w-4 mr-2" />
              {language === 'fr' ? 'Switch to English' : 'Passer en français'}
            </Button>
            <Button 
              variant="outline" 
              className="w-full mt-2" 
              onClick={toggleTheme}
            >
              {theme === 'dark' ? t('switch_to_light') : t('switch_to_dark')}
            </Button>
            <a 
              href="https://github.com/stranxik/json_parser" 
              target="_blank" 
              rel="noopener noreferrer"
              className="block w-full mt-2"
            >
              <Button 
                variant="outline"
                className="w-full flex items-center justify-center"
              >
                <Github className="h-4 w-4 mr-2" />
                {t('language') === 'en' ? 'View on GitHub' : 'Voir sur GitHub'}
              </Button>
            </a>
          </div>
        )}
      </div>
    </nav>
  );
} 