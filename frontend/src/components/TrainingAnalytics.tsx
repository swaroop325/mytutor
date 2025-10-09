import React, { useState, useEffect } from 'react';
import { knowledgeBaseService } from '../services/api';
import type { TrainingSession } from '../types';

interface TrainingAnalyticsProps {
  className?: string;
}

interface AnalyticsData {
  totalSessions: number;
  totalQuestions: number;
  totalCorrect: number;
  averageScore: number;
  bestScore: number;
  worstScore: number;
  recentTrend: 'improving' | 'declining' | 'stable';
  sessionsThisWeek: number;
  sessionsThisMonth: number;
  knowledgeBaseStats: Array<{
    id: string;
    name: string;
    sessions: number;
    averageScore: number;
    lastSession: string;
  }>;
}

const TrainingAnalytics: React.FC<TrainingAnalyticsProps> = ({ className = '' }) => {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get all user training sessions
      const sessions: TrainingSession[] = await knowledgeBaseService.getUserTrainingHistory();
      
      if (sessions.length === 0) {
        setAnalytics(null);
        return;
      }

      // Calculate analytics
      const now = new Date();
      const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      const oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

      const totalQuestions = sessions.reduce((sum, s) => sum + s.questions_answered, 0);
      const totalCorrect = sessions.reduce((sum, s) => sum + s.correct_answers, 0);
      const scores = sessions.map(s => s.score).filter(s => s > 0);
      
      const sessionsThisWeek = sessions.filter(s => 
        new Date(s.created_at) >= oneWeekAgo
      ).length;
      
      const sessionsThisMonth = sessions.filter(s => 
        new Date(s.created_at) >= oneMonthAgo
      ).length;

      // Calculate trend (last 5 sessions vs previous 5)
      const recentSessions = sessions.slice(0, 5);
      const previousSessions = sessions.slice(5, 10);
      
      let recentTrend: 'improving' | 'declining' | 'stable' = 'stable';
      if (recentSessions.length >= 3 && previousSessions.length >= 3) {
        const recentAvg = recentSessions.reduce((sum, s) => sum + s.score, 0) / recentSessions.length;
        const previousAvg = previousSessions.reduce((sum, s) => sum + s.score, 0) / previousSessions.length;
        
        if (recentAvg > previousAvg + 5) recentTrend = 'improving';
        else if (recentAvg < previousAvg - 5) recentTrend = 'declining';
      }

      // Group by knowledge base
      const kbGroups = sessions.reduce((acc, session) => {
        const kbId = session.knowledge_base_id;
        if (!acc[kbId]) {
          acc[kbId] = [];
        }
        acc[kbId].push(session);
        return acc;
      }, {} as Record<string, TrainingSession[]>);

      const knowledgeBaseStats = Object.entries(kbGroups).map(([kbId, kbSessions]) => {
        const kbScores = kbSessions.map(s => s.score).filter(s => s > 0);
        const averageScore = kbScores.length > 0 ? kbScores.reduce((sum, s) => sum + s, 0) / kbScores.length : 0;
        const lastSession = kbSessions[0]?.created_at || '';
        
        return {
          id: kbId,
          name: `Knowledge Base ${kbId.slice(0, 8)}...`, // Would be replaced with actual KB name
          sessions: kbSessions.length,
          averageScore,
          lastSession
        };
      }).sort((a, b) => b.sessions - a.sessions);

      const analyticsData: AnalyticsData = {
        totalSessions: sessions.length,
        totalQuestions,
        totalCorrect,
        averageScore: scores.length > 0 ? scores.reduce((sum, s) => sum + s, 0) / scores.length : 0,
        bestScore: scores.length > 0 ? Math.max(...scores) : 0,
        worstScore: scores.length > 0 ? Math.min(...scores) : 0,
        recentTrend,
        sessionsThisWeek,
        sessionsThisMonth,
        knowledgeBaseStats
      };

      setAnalytics(analyticsData);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError('Failed to load training analytics');
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving':
        return <span className="text-green-300">↗️</span>;
      case 'declining':
        return <span className="text-red-300">↘️</span>;
      default:
        return <span className="text-white/50">→</span>;
    }
  };

  const getTrendText = (trend: string) => {
    switch (trend) {
      case 'improving':
        return 'Improving';
      case 'declining':
        return 'Needs Focus';
      default:
        return 'Stable';
    }
  };

  if (loading) {
    return (
      <div className={`bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-white/20 rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-20 bg-white/10 rounded"></div>
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
            onClick={loadAnalytics}
            className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className={`bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 ${className}`}>
        <h3 className="text-xl font-bold text-white mb-4">Training Analytics</h3>
        <div className="text-center text-white/70 py-8">
          <p className="text-lg">No training data available yet.</p>
          <p className="text-sm mt-2">Complete some training sessions to see your analytics!</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 ${className}`}>
      <div className="p-6">
        <h3 className="text-2xl font-bold text-white mb-6">Training Analytics</h3>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-blue-500/20 backdrop-blur-sm p-4 rounded-lg border border-blue-400/30">
            <div className="text-2xl font-bold text-blue-300">{analytics.totalSessions}</div>
            <div className="text-sm text-blue-200">Total Sessions</div>
            <div className="text-xs text-blue-300 mt-1">
              {analytics.sessionsThisWeek} this week
            </div>
          </div>

          <div className="bg-green-500/20 backdrop-blur-sm p-4 rounded-lg border border-green-400/30">
            <div className="text-2xl font-bold text-green-300">
              {Math.round(analytics.averageScore)}%
            </div>
            <div className="text-sm text-green-200">Average Score</div>
            <div className="text-xs text-green-300 mt-1 flex items-center">
              {getTrendIcon(analytics.recentTrend)} {getTrendText(analytics.recentTrend)}
            </div>
          </div>

          <div className="bg-purple-500/20 backdrop-blur-sm p-4 rounded-lg border border-purple-400/30">
            <div className="text-2xl font-bold text-purple-300">{analytics.totalQuestions}</div>
            <div className="text-sm text-purple-200">Questions Answered</div>
            <div className="text-xs text-purple-300 mt-1">
              {Math.round((analytics.totalCorrect / analytics.totalQuestions) * 100)}% accuracy
            </div>
          </div>

          <div className="bg-yellow-500/20 backdrop-blur-sm p-4 rounded-lg border border-yellow-400/30">
            <div className="text-2xl font-bold text-yellow-300">
              {Math.round(analytics.bestScore)}%
            </div>
            <div className="text-sm text-yellow-200">Best Score</div>
            <div className="text-xs text-yellow-300 mt-1">
              Worst: {Math.round(analytics.worstScore)}%
            </div>
          </div>
        </div>

        {/* Knowledge Base Performance */}
        <div className="mb-6">
          <h4 className="text-lg font-semibold text-white mb-4">Knowledge Base Performance</h4>
          <div className="space-y-3">
            {analytics.knowledgeBaseStats.slice(0, 5).map((kb) => (
              <div key={kb.id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition-colors">
                <div className="flex-1">
                  <div className="font-medium text-white">{kb.name}</div>
                  <div className="text-sm text-white/60">
                    {kb.sessions} sessions • Last: {new Date(kb.lastSession).toLocaleDateString()}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-lg text-white">
                    {Math.round(kb.averageScore)}%
                  </div>
                  <div className="text-xs text-white/50">avg score</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Activity Summary */}
        <div className="bg-white/5 backdrop-blur-sm p-4 rounded-lg border border-white/10">
          <h4 className="text-lg font-semibold text-white mb-3">Activity Summary</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-white/60">This Week:</span>
              <span className="ml-2 font-medium text-white">{analytics.sessionsThisWeek} sessions</span>
            </div>
            <div>
              <span className="text-white/60">This Month:</span>
              <span className="ml-2 font-medium text-white">{analytics.sessionsThisMonth} sessions</span>
            </div>
            <div>
              <span className="text-white/60">Total Correct:</span>
              <span className="ml-2 font-medium text-white">{analytics.totalCorrect} answers</span>
            </div>
            <div>
              <span className="text-white/60">Knowledge Bases:</span>
              <span className="ml-2 font-medium text-white">{analytics.knowledgeBaseStats.length} active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TrainingAnalytics;