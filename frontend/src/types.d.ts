/**
 * Types definitions for the DataFlow AI frontend
 */

// Basic React JSX types
declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

// Declare module for React
declare module 'react' {
  export import createElement = React.createElement;
  export import Fragment = React.Fragment;
  export import useState = React.useState;
  export const useEffect: typeof React.useEffect;
}

// Declare module for React JSX Runtime
declare module 'react/jsx-runtime' {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: React.ComponentType;
}

// Declare module for React Router DOM
declare module 'react-router-dom' {
  export const BrowserRouter: React.ComponentType<any>;
  export const Routes: React.ComponentType<any>;
  export const Route: React.ComponentType<any>;
  export const Link: React.ComponentType<any>;
  export const Navigate: React.ComponentType<any>;
  export const Outlet: React.ComponentType<any>;
  export const useNavigate: () => any;
  export const useLocation: () => any;
  export const useParams: () => any;
}

// Declare module for react-dropzone
declare module 'react-dropzone' {
  export function useDropzone(options: any): any;
}

// Declare module for lucide-react
declare module 'lucide-react' {
  export const FileText: React.FC<{ className?: string }>;
  export const Database: React.FC<{ className?: string }>;
  export const Cpu: React.FC<{ className?: string }>;
  export const Menu: React.FC<{ className?: string }>;
  export const X: React.FC<{ className?: string }>;
  export const Upload: React.FC<{ className?: string }>;
  export const Check: React.FC<{ className?: string }>;
  export const Loader2: React.FC<{ className?: string }>;
}

// Declare global types
declare global {
  interface Window {
    // Add any window properties if needed
  }
}

export {}; 