import React from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  className?: string;
  showCloseButton?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  className,
  showCloseButton = true,
  size = 'md',
}: ModalProps) {
  // Empêcher le scroll du body quand le modal est ouvert
  React.useEffect(() => {
    if (isOpen) {
      document.body.classList.add('overflow-hidden');
    } else {
      document.body.classList.remove('overflow-hidden');
    }
    
    return () => {
      document.body.classList.remove('overflow-hidden');
    };
  }, [isOpen]);

  // Ne pas rendre le composant si le modal n'est pas ouvert
  if (!isOpen) return null;

  // Classes pour les différentes tailles
  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  // Fermer avec Escape
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm transition-opacity animate-fade">
      <div className="fixed inset-0" onClick={onClose} />
      <div 
        className={cn(
          "relative z-10 bg-card border shadow-lg rounded-none p-6",
          sizeClasses[size],
          "w-full animate-scale-in transform transition-all duration-300 ease-out",
          className
        )}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">{title}</h2>
          {showCloseButton && (
            <button 
              onClick={onClose} 
              className="text-muted-foreground hover:text-foreground transition rounded-full p-1"
              aria-label="Close"
            >
              <X className="h-[18px] w-[18px]" />
            </button>
          )}
        </div>
        <div className="modal-content">{children}</div>
      </div>
    </div>
  );
}

export default Modal; 