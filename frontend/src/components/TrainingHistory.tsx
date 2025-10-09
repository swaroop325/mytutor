import React, { useState, useEffect } from 'react';
import { knowledgeBaseService } from '../services/api';
import type { TrainingSession, TrainingHistoryStats } from '../types';

interface TrainingHistoryProps {
  knowledgeBaseId?: string; // If provided, show history for specific KB
  className?: string;
}

const TrainingHistory: React.FC<TrainingHistoryProps> = ({ 
  knowledgeBaseId, 
  className = '' 
}) => {
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [stats, setStats] = useState<TrainingHistoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTrainingHistory();
  }, [knowledgeBaseId]);

  const loadTrainingHistory = async () => {
    try {
      setLoading(true);
      setError(null);

      let sessionsData: TrainingSession[];
      
      if (knowledgeBaseId) {
        // Get history for specific knowledge base
        sessionsData = await knowledgeBaseService.getKnowledgeBaseTrainingHistory(knowledgeBaseId);
      } else {
        // Get all user training history
        sessionsData = await knowledgeBaseService.getUserTrainingHistory();
      }

      setSessions(sessionsData);
      
      // Calculate stats
      if (sessionsData.length > 0) {
        const totalQuestions = sessionsData.reduce((sum, s) => sum + s.questions_answered, 0);
        const totalCorrect = sessionsData.reduce((sum, s) => sum + s.correct_answers, 0);
        const scores = sessionsData.map(s => s.score).filter(s => s > 0);
        
        const calculatedStats: TrainingHistoryStats = {
          total_sessions: sessionsData.length,
          total_questions_answered: totalQuestions,
          total_correct_answers: totalCorrect,
          average_score: scores.length > 0 ? scores.reduce((sum, s) => sum + s, 0) / scores.length : 0,
          best_score: scores.length > 0 ? Math.max(...scores) : 0,
          recent_sessions: sessionsData.slice(0, 5) // Last 5 sessions
        };
        
        setStats(calculatedStats);
      }
    } catch (err) {
      console.error('Failed to load training history:', err);
      setError('Failed to load training history');
    } finally {
      setLoading(false);
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

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-300';
    if (score >= 60) return 'text-yellow-300';
    return 'text-red-300';
  };

  const getAccuracy = (session: TrainingSession) => {
    if (session.questions_answered === 0) return 0;
    return Math.round((session.correct_answers / session.questions_answered) * 100);
  };

  if (loading) {
    return (
      <div className={`bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-white/20 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-white/10 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 ${className}`}>
        <div className="text-center">
          <p className="text-red-300 mb-4">{error}</p>
          <button
            onClick={loadTrainingHistory}
            className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className={`bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 ${className}`}>
        <h3 className="text-xl font-bold text-white mb-4">
          {knowledgeBaseId ? 'Knowledge Base Training History' : 'Training History'}
        </h3>
        <div className="text-center text-white/70 py-8">
          <p className="text-lg">No training sessions found.</p>
          <p className="text-sm mt-2">Start a training session to see your progress here!</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 ${className}`}>
      <div className="p-6">
        <h3 className="text-2xl font-bold text-white mb-6">
          {knowledgeBaseId ? 'Knowledge Base Training History' : 'Training History'}
        </h3>

        {/* Stats Overview */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-500/20 backdrop-blur-sm p-4 rounded-lg border border-blue-400/30">
              <div className="text-2xl font-bold text-blue-300">{stats.total_sessions}</div>
              <div className="text-sm text-blue-200">Total Sessions</div>
            </div>
            <div className="bg-green-500/20 backdrop-blur-sm p-4 rounded-lg border border-green-400/30">
              <div className="text-2xl font-bold text-green-300">{stats.total_questions_answered}</div>
              <div className="text-sm text-green-200">Questions Answered</div>
            </div>
            <div className="bg-purple-500/20 backdrop-blur-sm p-4 rounded-lg border border-purple-400/30">
              <div className="text-2xl font-bold text-purple-300">{Math.round(stats.average_score)}%</div>
              <div className="text-sm text-purple-200">Average Score</div>
            </div>
            <div className="bg-yellow-500/20 backdrop-blur-sm p-4 rounded-lg border border-yellow-400/30">
              <div className="text-2xl font-bold text-yellow-300">{Math.round(stats.best_score)}%</div>
              <div className="text-sm text-yellow-200">Best Score</div>
            </div>
          </div>
        )}

        {/* Sessions List */}
        <div className="space-y-3">
          <h4 className="text-lg font-semibold text-white mb-3">Recent Sessions</h4>
          {sessions.map((session) => (
            <div key={session.id} className="bg-white/5 border border-white/10 rounded-lg p-4 hover:bg-white/10 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-4">
                    <div className="flex-1">
                      <div className="text-sm text-white/60">
                        {formatDate(session.created_at)}
                      </div>
                      <div className="flex items-center space-x-4 mt-1">
                        <span className="text-sm text-white/70">
                          <span className="font-medium text-white">{session.questions_answered}</span> questions
                        </span>
                        <span className="text-sm text-white/70">
                          <span className="font-medium text-white">{session.correct_answers}</span> correct
                        </span>
                        <span className="text-sm text-white/70">
                          <span className={`font-medium ${getScoreColor(getAccuracy(session))}`}>
                            {getAccuracy(session)}% accuracy
                          </span>
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-lg font-bold ${getScoreColor(session.score)}`}>
                        {Math.round(session.score)}%
                      </div>
                      <div className={`text-xs px-2 py-1 rounded-full ${
                        session.status === 'completed'
                          ? 'bg-green-500/20 text-green-300 border border-green-400/30'
                          : 'bg-yellow-500/20 text-yellow-300 border border-yellow-400/30'
                      }`}>
                        {session.status}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Load More Button */}
        {sessions.length >= 5 && (
          <div className="mt-4 text-center">
            <button
              onClick={loadTrainingHistory}
              className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all"
            >
              Load More Sessions
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrainingHistory;