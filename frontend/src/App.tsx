import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { ThemeProvider } from '@/components/ThemeProvider';
import { LanguageProvider } from '@/components/LanguageProvider';

// Layouts
import MainLayout from '@/components/layout/MainLayout';

// Pages
import HomePage from '@/pages/HomePage';
import JSONProcessingPage from '@/pages/JSONProcessingPage';
import LLMEnrichmentPage from '@/pages/LLMEnrichmentPage';
import NotFoundPage from '@/pages/NotFoundPage';

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="dataflow-theme">
      <LanguageProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route element={<MainLayout />}>
            <Route path="/home" element={<HomePage />} />
            <Route path="/json-processing" element={<JSONProcessingPage />} />
            <Route path="/llm-enrichment" element={<LLMEnrichmentPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
        <Toaster />
      </LanguageProvider>
    </ThemeProvider>
  );
}

export default App; 