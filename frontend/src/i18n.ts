import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import visionEn from './pages/Vision.en.md?raw';
import visionFr from './pages/Vision.fr.md?raw';

// Define resources
const resources = {
  en: {
    translation: {
      'Vision - DataFlow AI': 'Vision - DataFlow AI',
      'DataFlow AI vision and mission': 'Transforming data for AI innovation',
      visionContent: visionEn
    }
  },
  fr: {
    translation: {
      'Vision - DataFlow AI': 'Vision - DataFlow AI',
      'DataFlow AI vision and mission': 'Transformer les données pour l\'innovation IA',
      visionContent: visionFr
    }
  }
};

// Initialize i18next
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: ['en', 'fr'],
    debug: true,
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ['querystring', 'cookie', 'localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage', 'cookie']
    }
  });

export default i18n; 