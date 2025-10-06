/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Brain, GraduationCap, LogOut } from 'lucide-react';
import { CourseProcessor } from './CourseProcessor';
import { KnowledgeBaseView } from './KnowledgeBaseView';
import { TutorView } from './TutorView';

type TabType = 'courses' | 'knowledge-base' | 'tutor';

export const Dashboard = () => {
  const [activeTab, setActiveTab] = useState<TabType>('courses');
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
    { id: 'courses' as TabType, label: 'Course Processing', icon: BookOpen },
    { id: 'knowledge-base' as TabType, label: 'Knowledge Base', icon: Brain },
    { id: 'tutor' as TabType, label: 'AI Tutor', icon: GraduationCap },
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
            return (
              <motion.button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
                  activeTab === tab.id
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Icon size={20} />
                {tab.label}
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
          {activeTab === 'courses' && <CourseProcessor />}
          {activeTab === 'knowledge-base' && <KnowledgeBaseView />}
          {activeTab === 'tutor' && <TutorView />}
        </motion.div>
      </div>
    </div>
  );
};
