import { useState, useEffect } from 'react';
import { useTaskOrchestrator, TaskState } from '@/lib/taskOrchestrator';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/Progress';
import { Loader2, AlertCircle, CheckCircle, PauseCircle, RefreshCw } from 'lucide-react';
import { useLanguage } from '@/components/LanguageProvider';

interface TaskManagerProps {
  onTaskComplete?: (taskId: string, result: any) => void;
  hideCompleted?: boolean;
  autoCleanup?: boolean;
  cleanupInterval?: number; // en millisecondes
}

const TaskStatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case 'running':
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case 'paused':
      return <PauseCircle className="h-4 w-4 text-yellow-500" />;
    default:
      return <Loader2 className="h-4 w-4 text-muted-foreground" />;
  }
};

const TaskStatusBadge = ({ status }: { status: string }) => {
  const { t } = useLanguage();
  let variant: 'default' | 'secondary' | 'destructive' | 'outline' = 'default';
  
  switch (status) {
    case 'running':
      variant = 'default';
      break;
    case 'completed':
      variant = 'secondary';
      break;
    case 'failed':
      variant = 'destructive';
      break;
    case 'paused':
    case 'pending':
      variant = 'outline';
      break;
  }

  // Traduire les statuts
  const getTranslatedStatus = () => {
    switch (status) {
      case 'running':
        return t('processing_in_progress');
      case 'completed':
        return t('processing_complete');
      case 'failed':
        return t('processing_failed');
      case 'paused':
        return t('paused') || 'Paused';
      case 'pending':
        return t('pending') || 'Pending';
      default:
        return status;
    }
  };
  
  return (
    <Badge variant={variant} className="ml-2">
      <TaskStatusIcon status={status} />
      <span className="ml-1">{getTranslatedStatus()}</span>
    </Badge>
  );
};

export function TaskManager({ 
  onTaskComplete, 
  hideCompleted = false,
  autoCleanup = true,
  cleanupInterval = 3600000 // 1 heure par défaut
}: TaskManagerProps) {
  const { t } = useLanguage();
  const { orchestrator, getAllTasks, retryTask } = useTaskOrchestrator();
  const [tasks, setTasks] = useState<TaskState[]>([]);
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>({});

  // Récupérer les tâches toutes les 2 secondes
  useEffect(() => {
    const interval = setInterval(() => {
      const allTasks = getAllTasks();
      setTasks(allTasks);
    }, 2000);
    
    return () => clearInterval(interval);
  }, [getAllTasks]);

  // Auto-nettoyage des tâches terminées
  useEffect(() => {
    if (!autoCleanup) return;
    
    const interval = setInterval(() => {
      orchestrator.cleanupCompletedTasks(cleanupInterval);
    }, Math.min(cleanupInterval, 3600000)); // Au maximum toutes les heures
    
    return () => clearInterval(interval);
  }, [orchestrator, autoCleanup, cleanupInterval]);

  // Gérer les tâches terminées
  useEffect(() => {
    if (onTaskComplete) {
      const currentOptions = orchestrator.getOptions();
      
      // Sauvegarder l'ancien handler
      const oldOnComplete = currentOptions.onComplete;
      
      // Configurer notre handler
      orchestrator.setOptions({
        onComplete: (taskId, result) => {
          // Appeler le callback fourni par le parent
          onTaskComplete(taskId, result);
          
          // Conserver le comportement précédent si nécessaire
          if (oldOnComplete && oldOnComplete !== onTaskComplete) {
            oldOnComplete(taskId, result);
          }
        }
      });
      
      // Nettoyage
      return () => {
        orchestrator.setOptions({ onComplete: oldOnComplete });
      };
    }
  }, [orchestrator, onTaskComplete]);

  // Filtrer les tâches si nécessaire
  const filteredTasks = hideCompleted 
    ? tasks.filter(task => task.status !== 'completed')
    : tasks;

  // S'il n'y a pas de tâches à afficher, montrer un placeholder
  if (filteredTasks.length === 0) {
    return (
      <div className="bg-background border border-primary/10 rounded-md shadow-sm p-4 max-w-xl mx-auto mb-6 task-manager-container opacity-75 hover:opacity-100 transition-opacity duration-300">
        <h3 className="text-lg font-semibold mb-4 text-primary">{t('active_tasks') || 'Tâches actives'}</h3>
        <div className="text-center py-6 text-muted-foreground">
          <div className="mb-2">
            <Loader2 className="h-8 w-8 mx-auto text-primary/30 animate-pulse" />
          </div>
          <p className="font-medium">{t('no_active_tasks') || 'Aucune tâche active'}</p>
          <p className="text-xs mt-1">{t('upload_and_process') || 'Téléchargez et traitez un fichier pour voir apparaître des tâches ici'}</p>
        </div>
      </div>
    );
  }

  // Toggle l'expansion d'une tâche
  const toggleTaskExpand = (taskId: string) => {
    setExpandedTasks(prev => ({
      ...prev,
      [taskId]: !prev[taskId]
    }));
  };

  // Réessayer une tâche échouée
  const handleRetry = (taskId: string) => {
    retryTask(taskId);
  };

  return (
    <div className="bg-background border border-primary/20 rounded-md shadow-lg p-4 max-w-xl mx-auto mb-6 task-manager-container">
      <h3 className="text-lg font-semibold mb-4 text-primary">{t('active_tasks') || 'Tâches actives'}</h3>
      
      <div className="space-y-4">
        {filteredTasks.map(task => (
          <div 
            key={task.id}
            data-task-id={task.id}
            data-filename={task.metadata?.fileName || 'unknown'}
            className="border rounded-md p-3 hover:bg-accent/5 transition-colors cursor-pointer"
            onClick={() => toggleTaskExpand(task.id)}
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center">
                <TaskStatusIcon status={task.status} />
                <span className="ml-2 font-medium">{task.name}</span>
                <TaskStatusBadge status={task.status} />
              </div>
              
              <div className="flex items-center gap-2">
                {task.status === 'failed' && (
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRetry(task.id);
                    }}
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    {t('retry') || 'Réessayer'}
                  </Button>
                )}
              </div>
            </div>
            
            {task.status === 'running' && (
              <Progress value={task.progress} className="mt-2" />
            )}
            
            {expandedTasks[task.id] && (
              <div className="mt-3 pt-2 border-t text-sm">
                <div>
                  <span className="font-medium">{t('started') || 'Démarré'}:</span>{' '}
                  {new Date(task.startTime).toLocaleString()}
                </div>
                <div>
                  <span className="font-medium">{t('last_updated') || 'Dernière mise à jour'}:</span>{' '}
                  {new Date(task.lastUpdated).toLocaleString()}
                </div>
                {task.retryCount > 0 && (
                  <div>
                    <span className="font-medium">{t('retries') || 'Tentatives'}:</span>{' '}
                    {task.retryCount}/{task.maxRetries}
                  </div>
                )}
                {task.error && (
                  <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded">
                    <span className="font-medium">{t('error') || 'Erreur'}:</span>{' '}
                    {task.error.message}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
} 