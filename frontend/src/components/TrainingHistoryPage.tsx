import React from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, Award, Calendar } from 'lucide-react';
import TrainingAnalytics from './TrainingAnalytics';
import TrainingHistory from './TrainingHistory';

const TrainingHistoryPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 p-6">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl">
              <BarChart3 className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Training Analytics</h1>
              <p className="text-white/70">Track your learning progress and performance</p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 }}
              className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20"
            >
              <div className="flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-green-400" />
                <div>
                  <div className="text-sm text-white/70">Performance</div>
                  <div className="text-lg font-bold text-white">Improving</div>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20"
            >
              <div className="flex items-center gap-3">
                <Award className="w-6 h-6 text-yellow-400" />
                <div>
                  <div className="text-sm text-white/70">Best Score</div>
                  <div className="text-lg font-bold text-white">--%</div>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 }}
              className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20"
            >
              <div className="flex items-center gap-3">
                <Calendar className="w-6 h-6 text-blue-400" />
                <div>
                  <div className="text-sm text-white/70">This Week</div>
                  <div className="text-lg font-bold text-white">-- Sessions</div>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.4 }}
              className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20"
            >
              <div className="flex items-center gap-3">
                <BarChart3 className="w-6 h-6 text-purple-400" />
                <div>
                  <div className="text-sm text-white/70">Avg Score</div>
                  <div className="text-lg font-bold text-white">--%</div>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* Main Content */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Analytics - Takes up 2 columns */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="xl:col-span-2"
          >
            <TrainingAnalytics className="bg-white/10 backdrop-blur-lg border-white/20" />
          </motion.div>

          {/* Recent History - Takes up 1 column */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="xl:col-span-1"
          >
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
              <div className="space-y-3">
                <button className="w-full p-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all">
                  Start New Training Session
                </button>
                <button className="w-full p-3 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-all">
                  View All Knowledge Bases
                </button>
                <button className="w-full p-3 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-all">
                  Export Training Data
                </button>
              </div>

              {/* Learning Streak */}
              <div className="mt-6 p-4 bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded-lg border border-green-500/30">
                <div className="flex items-center gap-2 mb-2">
                  <Award className="w-5 h-5 text-green-400" />
                  <span className="text-green-200 font-medium">Learning Streak</span>
                </div>
                <div className="text-2xl font-bold text-white mb-1">-- Days</div>
                <div className="text-sm text-white/70">Keep it up! 🔥</div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Full Training History */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-6"
        >
          <TrainingHistory className="bg-white/10 backdrop-blur-lg border-white/20" />
        </motion.div>
      </div>
    </div>
  );
};

export default TrainingHistoryPage;