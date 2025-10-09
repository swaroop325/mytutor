/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  GraduationCap, 
  Brain, 
  MessageCircle, 
  Play, 
  BookOpen,
  Target,
  Trophy,
  Clock,
  ArrowRight,
  BarChart3
} from 'lucide-react';
import { EnhancedTrainingInterface } from './EnhancedTrainingInterface';
import { API_URL, knowledgeBaseService } from '../services/api';
import type { TrainingSession } from '../types';

interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  status: string;
  training_ready: boolean;
  training_content_generated?: boolean;
  created_at: string;
  total_files: number;
}

export const AITutor = () => {
  const [view, setView] = useState<'select' | 'training'>('select');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [kbHistories, setKbHistories] = useState<Record<string, TrainingSession[]>>({});

  useEffect(() => {
    fetchKnowledgeBases();
  }, []);

  const loadTrainingHistories = async (kbs: KnowledgeBase[]) => {
    const histories: Record<string, TrainingSession[]> = {};
    
    for (const kb of kbs) {
      try {
        const history = await knowledgeBaseService.getKnowledgeBaseTrainingHistory(kb.id);
        histories[kb.id] = history.slice(0, 3); // Only show last 3 sessions
      } catch (err) {
        console.warn(`Failed to load history for KB ${kb.id}:`, err);
        histories[kb.id] = [];
      }
    }
    
    setKbHistories(histories);
  };

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
      // Filter only training-ready knowledge bases with generated content
      const readyKBs = (data.knowledge_bases || []).filter((kb: KnowledgeBase) =>
        kb.training_ready &&
        kb.status === 'completed' &&
        kb.training_content_generated !== false  // Allow undefined for backward compatibility
      );
      setKnowledgeBases(readyKBs);

      // Load training history for each knowledge base
      await loadTrainingHistories(readyKBs);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartTraining = (kb: KnowledgeBase) => {
    setSelectedKB(kb);
    setView('training');
  };

  const handleEndTraining = () => {
    setView('select');
    setSelectedKB(null);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (view === 'training' && selectedKB) {
    return (
      <div>
        <div className="mb-6">
          <button
            onClick={handleEndTraining}
            className="flex items-center gap-2 text-white/70 hover:text-white transition-colors mb-4"
          >
            ← Back to Knowledge Bases
          </button>
          <div className="flex items-center gap-3">
            <GraduationCap className="w-8 h-8 text-green-400" />
            <div>
              <h2 className="text-2xl font-bold text-white">Training: {selectedKB.name}</h2>
              <p className="text-white/70">Interactive AI-powered learning session</p>
            </div>
          </div>
        </div>
        
        <EnhancedTrainingInterface 
          knowledgeBaseId={selectedKB.id}
          onEndTraining={handleEndTraining}
        />
      </div>
    );
  }

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <GraduationCap className="w-8 h-8 text-green-400" />
        <div>
          <h2 className="text-2xl font-bold text-white">AI Tutor</h2>
          <p className="text-white/70">Start interactive training sessions with your knowledge bases</p>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-green-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-white/70">Loading available training sessions...</p>
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
            <div className="relative mb-6">
              <GraduationCap className="w-20 h-20 text-green-400/50 mx-auto" />
              <Brain className="w-10 h-10 text-purple-400/50 absolute top-0 right-1/2 transform translate-x-8" />
            </div>
            
            <h3 className="text-xl font-semibold text-white mb-2">No Training Sessions Available</h3>
            <p className="text-white/70 mb-6 max-w-md mx-auto">
              Create and process knowledge bases first to unlock AI-powered training sessions with adaptive MCQ questions.
            </p>
            
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6 max-w-lg mx-auto">
              <h4 className="text-blue-200 font-medium mb-3">To start training:</h4>
              <ol className="text-blue-100 text-sm space-y-2 text-left">
                <li className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-blue-500/30 rounded-full flex items-center justify-center text-xs font-bold">1</span>
                  Go to Knowledge Base tab
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-blue-500/30 rounded-full flex items-center justify-center text-xs font-bold">2</span>
                  Create a new knowledge base
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-blue-500/30 rounded-full flex items-center justify-center text-xs font-bold">3</span>
                  Upload your course materials
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-blue-500/30 rounded-full flex items-center justify-center text-xs font-bold">4</span>
                  Wait for processing to complete
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-blue-500/30 rounded-full flex items-center justify-center text-xs font-bold">5</span>
                  Return here to start training
                </li>
              </ol>
            </div>
          </motion.div>
        </div>
      )}

      {/* Knowledge Bases Available for Training */}
      {!loading && knowledgeBases.length > 0 && (
        <div>
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-white mb-2">Available Training Sessions</h3>
            <p className="text-white/60">Select a knowledge base to start an interactive learning session</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {knowledgeBases.map((kb) => (
              <motion.div
                key={kb.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-green-500/10 to-blue-500/10 rounded-xl p-6 border border-green-500/20 hover:border-green-500/40 transition-all group cursor-pointer"
                onClick={() => handleStartTraining(kb)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h4 className="text-lg font-semibold text-white mb-1 group-hover:text-green-200 transition-colors">
                      {kb.name}
                    </h4>
                    {kb.description && (
                      <p className="text-white/60 text-sm line-clamp-2">{kb.description}</p>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-1 px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-xs font-medium">
                    <Trophy className="w-3 h-3" />
                    Ready
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-white/5 rounded-lg p-3 text-center">
                    <BookOpen className="w-6 h-6 text-blue-400 mx-auto mb-1" />
                    <div className="text-lg font-bold text-white">{kb.total_files}</div>
                    <div className="text-xs text-white/60">Files Processed</div>
                  </div>
                  
                  <div className="bg-white/5 rounded-lg p-3 text-center">
                    <Target className="w-6 h-6 text-purple-400 mx-auto mb-1" />
                    <div className="text-lg font-bold text-white">∞</div>
                    <div className="text-xs text-white/60">Questions Available</div>
                  </div>
                </div>

                {/* Training History Preview */}
                {kbHistories[kb.id] && kbHistories[kb.id].length > 0 && (
                  <div className="bg-white/5 rounded-lg p-3 mb-4">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart3 className="w-4 h-4 text-blue-400" />
                      <span className="text-xs text-white/70">Recent Sessions</span>
                    </div>
                    <div className="space-y-1">
                      {kbHistories[kb.id].slice(0, 2).map((session) => (
                        <div key={session.id} className="flex items-center justify-between text-xs">
                          <span className="text-white/60">
                            {new Date(session.created_at).toLocaleDateString()}
                          </span>
                          <span className={`font-medium ${
                            session.score >= 80 ? 'text-green-400' :
                            session.score >= 60 ? 'text-yellow-400' : 'text-red-400'
                          }`}>
                            {Math.round(session.score)}% ({session.questions_answered}Q)
                          </span>
                        </div>
                      ))}
                      {kbHistories[kb.id].length > 2 && (
                        <div className="text-xs text-white/40 text-center pt-1">
                          +{kbHistories[kb.id].length - 2} more sessions
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="flex items-center justify-between text-xs text-white/50 mb-4">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>Created {formatDate(kb.created_at)}</span>
                  </div>
                </div>

                {/* Training Features */}
                <div className="bg-white/5 rounded-lg p-3 mb-4">
                  <div className="text-xs text-white/70 mb-2">Training Features:</div>
                  <div className="flex flex-wrap gap-1">
                    <span className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded text-xs">Adaptive MCQ</span>
                    <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded text-xs">AI Explanations</span>
                    <span className="px-2 py-1 bg-green-500/20 text-green-300 rounded text-xs">Progress Tracking</span>
                  </div>
                </div>

                {/* Start Button */}
                <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 text-white font-medium rounded-lg transition-all group-hover:shadow-lg">
                  <Play className="w-4 h-4" />
                  Start Training Session
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
              </motion.div>
            ))}
          </div>

          {/* Training Tips */}
          <div className="mt-8 bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-3">
              <MessageCircle className="w-5 h-5 text-yellow-400" />
              <span className="text-yellow-200 font-medium">Training Tips</span>
            </div>
            <div className="grid md:grid-cols-2 gap-4 text-yellow-100 text-sm">
              <div>
                <h5 className="font-medium mb-2">🎯 Adaptive Learning</h5>
                <p>Questions automatically adjust difficulty based on your performance</p>
              </div>
              <div>
                <h5 className="font-medium mb-2">💡 Detailed Explanations</h5>
                <p>Get comprehensive explanations for every answer to reinforce learning</p>
              </div>
              <div>
                <h5 className="font-medium mb-2">📊 Progress Tracking</h5>
                <p>Monitor your learning progress with real-time scoring and analytics</p>
              </div>
              <div>
                <h5 className="font-medium mb-2">🧠 AI-Powered</h5>
                <p>Questions generated from your specific course materials using advanced AI</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};