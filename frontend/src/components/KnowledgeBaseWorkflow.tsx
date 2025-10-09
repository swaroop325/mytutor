/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Brain, BookOpen, Target } from 'lucide-react';
import { KnowledgeBaseCreator } from './KnowledgeBaseCreator';
import { KnowledgeBaseStatus } from './KnowledgeBaseStatus';
import { TrainingInterface } from './TrainingInterface';

type WorkflowStep = 'create' | 'processing' | 'training';

interface KnowledgeBaseWorkflowProps {
  onComplete?: () => void;
}

export const KnowledgeBaseWorkflow: React.FC<KnowledgeBaseWorkflowProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('create');
  const [knowledgeBase, setKnowledgeBase] = useState<any>(null);

  const handleKnowledgeBaseCreated = (kb: any) => {
    setKnowledgeBase(kb);
    setCurrentStep('processing');
  };

  const handleTrainingReady = () => {
    setCurrentStep('training');
  };

  const handleEndTraining = () => {
    // Call onComplete callback if provided, otherwise reset
    if (onComplete) {
      onComplete();
    } else {
      setCurrentStep('create');
      setKnowledgeBase(null);
    }
  };

  const goBack = () => {
    if (currentStep === 'processing') {
      setCurrentStep('create');
      setKnowledgeBase(null);
    } else if (currentStep === 'training') {
      setCurrentStep('processing');
    }
  };

  const getStepInfo = () => {
    switch (currentStep) {
      case 'create':
        return {
          title: 'Create Knowledge Base',
          description: 'Upload your course materials to get started',
          icon: Brain,
          color: 'text-purple-400'
        };
      case 'processing':
        return {
          title: 'Processing Files',
          description: 'Multi-agent system is analyzing your content',
          icon: BookOpen,
          color: 'text-blue-400'
        };
      case 'training':
        return {
          title: 'Training Session',
          description: 'Interactive learning with AI-generated questions',
          icon: Target,
          color: 'text-green-400'
        };
    }
  };

  const stepInfo = getStepInfo();
  const IconComponent = stepInfo.icon;

  return (
    <div className="w-full">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            {currentStep !== 'create' && (
              <button
                onClick={goBack}
                className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-6 h-6" />
              </button>
            )}
            
            <div className="flex items-center gap-3">
              <IconComponent className={`w-8 h-8 ${stepInfo.color}`} />
              <div>
                <h1 className="text-3xl font-bold text-white">{stepInfo.title}</h1>
                <p className="text-white/70">{stepInfo.description}</p>
              </div>
            </div>
          </div>

          {/* Progress Steps */}
          <div className="flex items-center gap-4">
            {['create', 'processing', 'training'].map((step, index) => {
              const isActive = currentStep === step;
              const isCompleted = ['create', 'processing', 'training'].indexOf(currentStep) > index;
              
              return (
                <div key={step} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    isActive 
                      ? 'bg-blue-500 text-white' 
                      : isCompleted 
                        ? 'bg-green-500 text-white' 
                        : 'bg-white/20 text-white/60'
                  }`}>
                    {index + 1}
                  </div>
                  
                  <span className={`ml-2 text-sm ${
                    isActive ? 'text-white' : isCompleted ? 'text-green-200' : 'text-white/60'
                  }`}>
                    {step.charAt(0).toUpperCase() + step.slice(1)}
                  </span>
                  
                  {index < 2 && (
                    <div className={`w-8 h-0.5 mx-4 ${
                      isCompleted ? 'bg-green-500' : 'bg-white/20'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Main Content */}
        <AnimatePresence mode="wait">
          {currentStep === 'create' && (
            <motion.div
              key="create"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <KnowledgeBaseCreator onKnowledgeBaseCreated={handleKnowledgeBaseCreated} />
            </motion.div>
          )}

          {currentStep === 'processing' && knowledgeBase && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <KnowledgeBaseStatus 
                knowledgeBaseId={knowledgeBase.id}
                onTrainingReady={handleTrainingReady}
              />
            </motion.div>
          )}

          {currentStep === 'training' && knowledgeBase && (
            <motion.div
              key="training"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <TrainingInterface 
                knowledgeBaseId={knowledgeBase.id}
                onEndTraining={handleEndTraining}
              />
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
};