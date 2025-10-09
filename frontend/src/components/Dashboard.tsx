/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Brain, GraduationCap, LogOut, BarChart3 } from 'lucide-react';
import { KnowledgeBaseManager } from './KnowledgeBaseManager';
import { AITutor } from './AITutor';
import TrainingAnalytics from './TrainingAnalytics';
import TrainingHistory from './TrainingHistory';

type TabType = 'courses' | 'knowledge-base' | 'tutor' | 'analytics';

export const Dashboard = () => {
  const [activeTab, setActiveTab] = useState<TabType>('knowledge-base');
  const [user, setUser] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');

    if (!token || !userData) {
      navigate('/');
      return;
    }

    setUser(JSON.parse(userData));
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  const tabs = [
    { id: 'knowledge-base' as TabType, label: 'Knowledge Base', icon: Brain },
    { id: 'tutor' as TabType, label: 'AI Tutor', icon: GraduationCap },
    { id: 'analytics' as TabType, label: 'Training Analytics', icon: BarChart3 },
    { id: 'courses' as TabType, label: 'URL Processing', icon: BookOpen, disabled: true },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-lg border-b border-white/10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-3xl font-bold text-white">myTutor</h1>
              {user && (
                <span className="text-blue-300">Welcome, {user.username}!</span>
              )}
            </div>

            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded-lg transition-colors"
            >
              <LogOut size={18} />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="container mx-auto px-6 py-6">
        <div className="flex space-x-2 bg-black/30 backdrop-blur-lg p-2 rounded-xl border border-white/10">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isDisabled = (tab as any).disabled;
            return (
              <motion.button
                key={tab.id}
                onClick={() => !isDisabled && setActiveTab(tab.id)}
                className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
                  isDisabled
                    ? 'text-gray-500 cursor-not-allowed opacity-50'
                    : activeTab === tab.id
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
                whileHover={{ scale: !isDisabled ? 1.02 : 1 }}
                whileTap={{ scale: !isDisabled ? 0.98 : 1 }}
              >
                <Icon size={20} />
                {tab.label}
                {isDisabled && <span className="text-xs ml-1">(Coming Soon)</span>}
              </motion.button>
            );
          })}
        </div>

        {/* Tab Content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="mt-6"
        >
          {activeTab === 'knowledge-base' && <KnowledgeBaseManager />}
          {activeTab === 'tutor' && <AITutor />}
          {activeTab === 'analytics' && (
            <div className="space-y-6">
              <TrainingAnalytics className="mb-6" />
              <TrainingHistory />
            </div>
          )}
          {activeTab === 'courses' && (
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 text-center">
              <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4 opacity-50" />
              <h3 className="text-2xl font-bold text-white mb-4">URL Processing Coming Soon</h3>
              <p className="text-white/70 mb-6">
                Direct URL processing for online courses will be available in a future update.
                For now, please use the Knowledge Base tab to upload your course files.
              </p>
              <button
                onClick={() => setActiveTab('knowledge-base')}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all"
              >
                Go to Knowledge Base
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};
