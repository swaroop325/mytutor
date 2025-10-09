/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, ArrowLeft } from 'lucide-react';
import { KnowledgeBaseCreator } from './KnowledgeBaseCreator';
import { KnowledgeBaseStatus } from './KnowledgeBaseStatus';

interface CreateKnowledgeBaseProps {
  onBack: () => void;
  onComplete: () => void;
}

export const CreateKnowledgeBase: React.FC<CreateKnowledgeBaseProps> = ({ onBack, onComplete }) => {
  const [step, setStep] = useState<'create' | 'processing'>('create');
  const [knowledgeBase, setKnowledgeBase] = useState<any>(null);

  const handleKnowledgeBaseCreated = (kb: any) => {
    setKnowledgeBase(kb);
    setStep('processing');
  };

  const handleTrainingReady = () => {
    onComplete();
  };

  return (
    <div>
      {/* Back Button */}
      <div className="mb-6">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-white/70 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Knowledge Bases
        </button>
      </div>

      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Brain className="w-8 h-8 text-purple-400" />
        <div>
          <h2 className="text-2xl font-bold text-white">
            {step === 'create' ? 'Create Knowledge Base' : 'Processing Files'}
          </h2>
          <p className="text-white/70">
            {step === 'create' 
              ? 'Upload your course materials to get started'
              : 'Multi-agent system is analyzing your content'
            }
          </p>
        </div>
      </div>

      {/* Content */}
      {step === 'create' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <KnowledgeBaseCreator onKnowledgeBaseCreated={handleKnowledgeBaseCreated} />
        </motion.div>
      )}

      {step === 'processing' && knowledgeBase && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <KnowledgeBaseStatus 
            knowledgeBaseId={knowledgeBase.id}
            onTrainingReady={handleTrainingReady}
          />
        </motion.div>
      )}
    </div>
  );
};