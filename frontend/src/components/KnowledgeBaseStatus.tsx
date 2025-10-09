/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  FileText,
  Video,
  Music,
  Image,
  File,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
  Play,
  BookOpen,
  Target
} from 'lucide-react';

interface AgentStatus {
  type: string;
  status: string;
  progress: number;
  files_processed: number;
  total_files: number;
  error?: string;
}

interface KnowledgeBaseStatusProps {
  knowledgeBaseId: string;
  onTrainingReady: () => void;
}

export const KnowledgeBaseStatus: React.FC<KnowledgeBaseStatusProps> = ({
  knowledgeBaseId,
  onTrainingReady
}) => {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/knowledge-base/${knowledgeBaseId}/status`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch status');
        }

        const data = await response.json();
        setStatus(data);
        setLoading(false);

        // If training is ready AND training content is generated, notify parent
        if (data.training_ready && data.status === 'completed' && data.training_content_generated) {
          onTrainingReady();
        }

      } catch (err: any) {
        setError(err.message);
        setLoading(false);
      }
    };

    // Initial fetch
    fetchStatus();

    // Poll for updates every 3 seconds
    const interval = setInterval(fetchStatus, 3000);

    return () => clearInterval(interval);
  }, [knowledgeBaseId, onTrainingReady]);

  const getAgentIcon = (agentType: string) => {
    switch (agentType.toLowerCase()) {
      case 'pdf':
        return FileText;
      case 'video':
        return Video;
      case 'audio':
        return Music;
      case 'image':
        return Image;
      case 'text':
        return File;
      default:
        return File;
    }
  };

  const getAgentColor = (agentType: string) => {
    switch (agentType.toLowerCase()) {
      case 'pdf':
        return 'text-red-400';
      case 'video':
        return 'text-purple-400';
      case 'audio':
        return 'text-green-400';
      case 'image':
        return 'text-pink-400';
      case 'text':
        return 'text-blue-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusIcon = (agentStatus: string) => {
    switch (agentStatus) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getOverallStatusMessage = () => {
    if (!status) return 'Loading...';
    
    switch (status.status) {
      case 'processing':
        const completedAgents = status.agents.filter((agent: AgentStatus) => agent.status === 'completed').length;
        const totalAgents = status.agents.length;
        return `Multi-agent processing: ${completedAgents}/${totalAgents} agents completed`;
      case 'training':
        return 'Generating AI training content and questions...';
      case 'completed':
        return status.training_ready ? 'Knowledge base ready for training!' : 'Processing completed';
      case 'error':
        return 'Processing failed';
      default:
        return 'Initializing processing pipeline...';
    }
  };

  if (loading) {
    return (
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mr-3" />
          <span className="text-white">Loading status...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
        <div className="flex items-center justify-center py-8 text-red-400">
          <AlertCircle className="w-6 h-6 mr-2" />
          <span>Error: {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      <div className="flex items-center gap-3 mb-6">
        <Brain className="w-8 h-8 text-purple-400" />
        <div>
          <h2 className="text-2xl font-bold text-white">{status.name}</h2>
          <p className="text-white/70">{getOverallStatusMessage()}</p>
        </div>
      </div>

      {/* Overall Progress */}
      <div className="mb-8">
        <div className="flex justify-between text-sm text-white/70 mb-2">
          <span>Overall Progress</span>
          <span>{status.progress.percentage}%</span>
        </div>
        <div className="w-full bg-white/20 rounded-full h-3 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${status.progress.percentage}%` }}
            transition={{ duration: 0.5 }}
            className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
          />
        </div>
        <div className="flex justify-between text-xs text-white/50 mt-1">
          <span>{status.progress.processed_files} of {status.progress.total_files} files processed</span>
          <span>Updated: {new Date(status.updated_at).toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Agent Status */}
      <div className="space-y-4 mb-8">
        <h3 className="text-lg font-semibold text-white mb-4">Agent Processing Status</h3>
        
        {status.agents.map((agent: AgentStatus, index: number) => {
          const IconComponent = getAgentIcon(agent.type);
          const colorClass = getAgentColor(agent.type);
          
          return (
            <motion.div
              key={agent.type}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-white/5 rounded-lg p-4 border border-white/10"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <IconComponent className={`w-6 h-6 ${colorClass}`} />
                  <div>
                    <h4 className="text-white font-medium capitalize">{agent.type} Agent</h4>
                    <p className="text-white/60 text-sm">
                      {agent.files_processed} of {agent.total_files} files
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusIcon(agent.status)}
                  <span className="text-sm text-white/70 capitalize">{agent.status}</span>
                </div>
              </div>

              {/* Agent Progress Bar */}
              <div className="mb-2">
                <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${agent.progress}%` }}
                    transition={{ duration: 0.3 }}
                    className={`h-full rounded-full ${
                      agent.status === 'completed' ? 'bg-green-500' :
                      agent.status === 'error' ? 'bg-red-500' :
                      'bg-blue-500'
                    }`}
                  />
                </div>
              </div>

              {/* Error Message */}
              {agent.error && (
                <div className="mt-2 text-sm text-red-400 bg-red-500/10 rounded p-2">
                  Error: {agent.error}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Waiting for Training Content Generation */}
      <AnimatePresence>
        {status.training_ready && status.status === 'completed' && !status.training_content_generated && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-500/30 rounded-lg p-6"
          >
            <div className="flex items-center gap-3 mb-2">
              <Clock className="w-8 h-8 text-yellow-400" />
              <div>
                <h3 className="text-xl font-semibold text-white">Processing Complete</h3>
                <p className="text-yellow-200">Training content needs to be generated before starting a training session.</p>
              </div>
            </div>
            <p className="text-white/70 text-sm mt-3">
              Go to the Knowledge Base details page and click "Generate Training Content" to create MCQs and learning materials.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Training Ready Section */}
      <AnimatePresence>
        {status.training_ready && status.status === 'completed' && status.training_content_generated && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-r from-green-500/20 to-blue-500/20 border border-green-500/30 rounded-lg p-6"
          >
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle className="w-8 h-8 text-green-400" />
              <div>
                <h3 className="text-xl font-semibold text-white">Knowledge Base Ready!</h3>
                <p className="text-green-200">All agents have completed processing and training content is generated. Training is now available.</p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4 mb-6">
              <div className="bg-white/10 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-5 h-5 text-blue-400" />
                  <span className="font-medium text-white">Training Features</span>
                </div>
                <ul className="text-sm text-white/80 space-y-1">
                  <li>• Adaptive MCQ questions</li>
                  <li>• Personalized difficulty</li>
                  <li>• Detailed explanations</li>
                  <li>• Progress tracking</li>
                </ul>
              </div>

              <div className="bg-white/10 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <BookOpen className="w-5 h-5 text-purple-400" />
                  <span className="font-medium text-white">Content Processed</span>
                </div>
                <ul className="text-sm text-white/80 space-y-1">
                  <li>• {status.progress.total_files} files analyzed</li>
                  <li>• Multi-modal content extracted</li>
                  <li>• Knowledge graph created</li>
                  <li>• Assessment ready</li>
                </ul>
              </div>
            </div>

            <motion.button
              onClick={onTrainingReady}
              className="w-full px-6 py-4 bg-gradient-to-r from-green-500 to-blue-600 text-white font-bold rounded-lg hover:from-green-600 hover:to-blue-700 transition-all flex items-center justify-center gap-3"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Play className="w-5 h-5" />
              Start Training Session
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Status Legend */}
      <div className="mt-6 bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <h4 className="text-blue-200 font-medium mb-3">Processing Stages:</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-blue-100">
          <div className="flex items-center gap-2">
            <Clock className="w-3 h-3" />
            <span>Pending</span>
          </div>
          <div className="flex items-center gap-2">
            <Loader2 className="w-3 h-3" />
            <span>Processing</span>
          </div>
          <div className="flex items-center gap-2">
            <Brain className="w-3 h-3" />
            <span>Training</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-3 h-3" />
            <span>Completed</span>
          </div>
        </div>
      </div>
    </div>
  );
};