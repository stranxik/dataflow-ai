/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_KEY: string;
  readonly VITE_API_URL?: string;
  // ajouter d'autres variables d'environnement au besoin
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
} 