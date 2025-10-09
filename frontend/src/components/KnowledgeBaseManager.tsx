/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  Plus, 
  BookOpen, 
  Calendar, 
  FileText, 
  Video, 
  Music, 
  Image,
  Trash2,
  Eye,
  Clock,
  CheckCircle,
  AlertCircle,
  Zap,
  Loader2
} from 'lucide-react';
import { CreateKnowledgeBase } from './CreateKnowledgeBase';
import TrainingHistory from './TrainingHistory';
import { API_URL } from '../services/api';

interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  status: string;
  total_files: number;
  processed_files: number;
  training_ready: boolean;
  created_at: string;
  updated_at: string;
  agent_statuses: Array<{
    agent_type: string;
    status: string;
    progress: number;
    files_processed: number;
    total_files: number;
  }>;
}

export const KnowledgeBaseManager = () => {
  const [view, setView] = useState<'list' | 'create' | 'details'>('list');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<KnowledgeBase | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (view === 'list') {
      fetchKnowledgeBases();
    }
  }, [view]);

  const fetchKnowledgeBases = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/knowledge-base/list`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch knowledge bases');
      }

      const data = await response.json();
      setKnowledgeBases(data.knowledge_bases || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNew = () => {
    setView('create');
  };

  const handleKnowledgeBaseCreated = () => {
    // Refresh the list and go back to list view
    setView('list');
    fetchKnowledgeBases();
  };

  const handleViewDetails = (kb: KnowledgeBase) => {
    setSelectedKB(kb);
    setView('details');
  };

  const handleDeleteKnowledgeBase = (kb: KnowledgeBase) => {
    setDeleteConfirm(kb);
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;

    setDeleting(true);
    try {
      const response = await fetch(`${API_URL}/knowledge-base/${deleteConfirm.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to delete knowledge base');
      }

      // Refresh the list
      await fetchKnowledgeBases();
      setDeleteConfirm(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDeleting(false);
    }
  };

  const cancelDelete = () => {
    setDeleteConfirm(null);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-400 bg-green-500/20';
      case 'processing':
        return 'text-blue-400 bg-blue-500/20';
      case 'training':
        return 'text-purple-400 bg-purple-500/20';
      case 'error':
        return 'text-red-400 bg-red-500/20';
      default:
        return 'text-gray-400 bg-gray-500/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4" />;
      case 'processing':
      case 'training':
        return <Clock className="w-4 h-4" />;
      case 'error':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFileTypeStats = (kb: KnowledgeBase) => {
    const stats = {
      pdf: 0,
      video: 0,
      audio: 0,
      image: 0,
      text: 0
    };

    kb.agent_statuses.forEach(agent => {
      const type = agent.agent_type.toLowerCase();
      if (type in stats) {
        stats[type as keyof typeof stats] = agent.total_files;
      }
    });

    return stats;
  };

  if (view === 'create') {
    return (
      <CreateKnowledgeBase
        onBack={() => setView('list')}
        onComplete={handleKnowledgeBaseCreated}
      />
    );
  }

  if (view === 'details' && selectedKB) {
    return (
      <div>
        <div className="mb-6">
          <button
            onClick={() => setView('list')}
            className="flex items-center gap-2 text-white/70 hover:text-white transition-colors mb-4"
          >
            ← Back to Knowledge Bases
          </button>
        </div>
        {/* Knowledge Base Details View */}
        <div className="space-y-6">
          {/* Basic Info */}
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
            <h2 className="text-2xl font-bold text-white mb-4">{selectedKB.name}</h2>
            <p className="text-white/70 mb-6">{selectedKB.description || 'No description provided'}</p>
            
            {/* Status and Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-black/20 p-4 rounded-lg">
                <div className="text-2xl font-bold text-white">{selectedKB.total_files}</div>
                <div className="text-sm text-white/70">Total Files</div>
              </div>
              <div className="bg-black/20 p-4 rounded-lg">
                <div className="text-2xl font-bold text-green-400">{selectedKB.processed_files}</div>
                <div className="text-sm text-white/70">Processed</div>
              </div>
              <div className="bg-black/20 p-4 rounded-lg">
                <div className={`text-2xl font-bold ${selectedKB.training_ready ? 'text-green-400' : 'text-yellow-400'}`}>
                  {selectedKB.training_ready ? 'Ready' : 'Processing'}
                </div>
                <div className="text-sm text-white/70">Training Status</div>
              </div>
              <div className="bg-black/20 p-4 rounded-lg">
                <div className="text-2xl font-bold text-blue-400">{selectedKB.agent_statuses.length}</div>
                <div className="text-sm text-white/70">Agent Types</div>
              </div>
            </div>

            {/* Agent Status */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-white mb-3">Processing Status</h3>
              <div className="space-y-2">
                {selectedKB.agent_statuses.map((agent, index) => (
                  <div key={index} className="flex items-center justify-between bg-black/20 p-3 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="capitalize text-white font-medium">{agent.agent_type}</div>
                      <div className={`px-2 py-1 rounded text-xs ${
                        agent.status === 'completed' ? 'bg-green-500/20 text-green-300' :
                        agent.status === 'processing' ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-gray-500/20 text-gray-300'
                      }`}>
                        {agent.status}
                      </div>
                    </div>
                    <div className="text-white/70 text-sm">
                      {agent.files_processed}/{agent.total_files} files ({agent.progress}%)
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Training Content Generation */}
            {selectedKB.training_ready && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white mb-3">Training Content</h3>
                <div className="bg-black/20 p-4 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-medium mb-1">Generate Training Materials</div>
                      <div className="text-white/70 text-sm">Create MCQs, learning objectives, and assessment materials</div>
                    </div>
                    <GenerateTrainingButton knowledgeBaseId={selectedKB.id} />
                  </div>
                </div>
              </div>
            )}

            {/* Timestamps */}
            <div className="text-sm text-white/50">
              <div>Created: {new Date(selectedKB.created_at).toLocaleString()}</div>
              <div>Updated: {new Date(selectedKB.updated_at).toLocaleString()}</div>
            </div>
          </div>

          {/* Training History for this Knowledge Base */}
          <TrainingHistory 
            knowledgeBaseId={selectedKB.id}
            className="bg-white/10 backdrop-blur-lg border-white/20"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Brain className="w-8 h-8 text-purple-400" />
          <div>
            <h2 className="text-2xl font-bold text-white">Knowledge Bases</h2>
            <p className="text-white/70">Manage your processed course materials</p>
          </div>
        </div>

        <motion.button
          onClick={handleCreateNew}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-600 text-white font-bold rounded-lg hover:from-purple-600 hover:to-pink-700 transition-all"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Plus className="w-5 h-5" />
          Create New
        </motion.button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-white/70">Loading knowledge bases...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-200 mb-6">
          Error: {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && knowledgeBases.length === 0 && (
        <div className="text-center py-12">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <Brain className="w-20 h-20 text-purple-400/50 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Knowledge Bases Yet</h3>
            <p className="text-white/70 mb-6">
              Create your first knowledge base by uploading course materials
            </p>
            <motion.button
              onClick={handleCreateNew}
              className="px-8 py-4 bg-gradient-to-r from-purple-500 to-pink-600 text-white font-bold rounded-lg hover:from-purple-600 hover:to-pink-700 transition-all"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Create Your First Knowledge Base
            </motion.button>
          </motion.div>
        </div>
      )}

      {/* Knowledge Bases Grid */}
      {!loading && knowledgeBases.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {knowledgeBases.map((kb) => {
            const fileStats = getFileTypeStats(kb);
            const progressPercentage = kb.total_files > 0 ? Math.round((kb.processed_files / kb.total_files) * 100) : 0;

            return (
              <motion.div
                key={kb.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white/5 rounded-xl p-6 border border-white/10 hover:border-white/20 transition-all group"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white mb-1 group-hover:text-purple-200 transition-colors">
                      {kb.name}
                    </h3>
                    {kb.description && (
                      <p className="text-white/60 text-sm line-clamp-2">{kb.description}</p>
                    )}
                  </div>
                  
                  <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(kb.status)}`}>
                    {getStatusIcon(kb.status)}
                    <span className="capitalize">
                      {kb.status === 'completed' && kb.training_ready ? 'Ready for Training' : kb.status}
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                {kb.status === 'processing' && (
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-white/70 mb-1">
                      <span>Processing</span>
                      <span>{progressPercentage}%</span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${progressPercentage}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* File Stats */}
                <div className="grid grid-cols-5 gap-2 mb-4">
                  {fileStats.pdf > 0 && (
                    <div className="text-center">
                      <FileText className="w-4 h-4 text-red-400 mx-auto mb-1" />
                      <span className="text-xs text-white/70">{fileStats.pdf}</span>
                    </div>
                  )}
                  {fileStats.video > 0 && (
                    <div className="text-center">
                      <Video className="w-4 h-4 text-purple-400 mx-auto mb-1" />
                      <span className="text-xs text-white/70">{fileStats.video}</span>
                    </div>
                  )}
                  {fileStats.audio > 0 && (
                    <div className="text-center">
                      <Music className="w-4 h-4 text-green-400 mx-auto mb-1" />
                      <span className="text-xs text-white/70">{fileStats.audio}</span>
                    </div>
                  )}
                  {fileStats.image > 0 && (
                    <div className="text-center">
                      <Image className="w-4 h-4 text-pink-400 mx-auto mb-1" />
                      <span className="text-xs text-white/70">{fileStats.image}</span>
                    </div>
                  )}
                  {fileStats.text > 0 && (
                    <div className="text-center">
                      <BookOpen className="w-4 h-4 text-blue-400 mx-auto mb-1" />
                      <span className="text-xs text-white/70">{fileStats.text}</span>
                    </div>
                  )}
                </div>

                {/* Metadata */}
                <div className="flex items-center gap-4 text-xs text-white/50 mb-4">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    <span>{formatDate(kb.created_at)}</span>
                  </div>
                  <div>
                    {kb.total_files} files
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => handleViewDetails(kb)}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-white/10 hover:bg-white/20 text-white/80 hover:text-white rounded-lg transition-colors text-sm"
                  >
                    <Eye className="w-4 h-4" />
                    View
                  </button>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteKnowledgeBase(kb);
                    }}
                    className="flex items-center justify-center gap-1 px-3 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300 rounded-lg transition-colors text-sm"
                    title="Delete Knowledge Base"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl shadow-2xl w-full max-w-md border border-white/10 p-6"
            >
              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Trash2 className="w-8 h-8 text-red-400" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Delete Knowledge Base</h3>
                <p className="text-gray-300 mb-4">
                  Are you sure you want to delete "{deleteConfirm.name}"?
                </p>
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
                  <p className="text-red-200 text-sm">
                    This action cannot be undone. All processed content, training materials, and associated data will be permanently deleted.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={cancelDelete}
                  disabled={deleting}
                  className="flex-1 px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  disabled={deleting}
                  className="flex-1 px-4 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {deleting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Generate Training Button Component
interface GenerateTrainingButtonProps {
  knowledgeBaseId: string;
}

const GenerateTrainingButton: React.FC<GenerateTrainingButtonProps> = ({ knowledgeBaseId }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [alreadyGenerated, setAlreadyGenerated] = useState(false);

  // Check if training content is already generated
  useEffect(() => {
    const checkTrainingContent = async () => {
      try {
        const response = await fetch(`${API_URL}/knowledge-base/${knowledgeBaseId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });

        if (response.ok) {
          const kb = await response.json();
          if (kb.training_content && kb.training_content.status === 'completed') {
            setAlreadyGenerated(true);
            setStatus('success');
            setMessage('Training content already generated');
          }
        }
      } catch (error) {
        console.error('Error checking training content:', error);
      }
    };

    checkTrainingContent();
  }, [knowledgeBaseId]);

  const handleGenerateTraining = async () => {
    setIsGenerating(true);
    setStatus('idle');
    setMessage('');

    try {
      const response = await fetch(`${API_URL}/knowledge-base/${knowledgeBaseId}/generate-training`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to generate training content');
      }

      const result = await response.json();

      if (result.training_content && result.training_content.status === 'completed') {
        setStatus('success');
        setMessage('Training content generated successfully!');
        setAlreadyGenerated(true);
      } else if (result.training_content && result.training_content.status === 'error') {
        setStatus('error');
        setMessage(result.training_content.message || 'Failed to generate training content');
      } else {
        setStatus('success');
        setMessage('Training content generation initiated successfully!');
        setAlreadyGenerated(true);
      }
    } catch (error: any) {
      setStatus('error');
      setMessage(error.message || 'Failed to generate training content');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-2">
      <motion.button
        onClick={handleGenerateTraining}
        disabled={isGenerating || alreadyGenerated}
        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-600 text-white font-semibold rounded-lg hover:from-purple-600 hover:to-pink-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        whileHover={{ scale: (isGenerating || alreadyGenerated) ? 1 : 1.05 }}
        whileTap={{ scale: (isGenerating || alreadyGenerated) ? 1 : 0.95 }}
      >
        {isGenerating ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Generating...
          </>
        ) : alreadyGenerated ? (
          <>
            <CheckCircle className="w-4 h-4" />
            Training Content Generated
          </>
        ) : (
          <>
            <Zap className="w-4 h-4" />
            Generate Training Content
          </>
        )}
      </motion.button>

      {/* Status Message */}
      <AnimatePresence>
        {message && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`text-sm p-2 rounded ${
              status === 'success' 
                ? 'bg-green-500/20 text-green-300 border border-green-500/30' 
                : status === 'error'
                ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
            }`}
          >
            {message}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};