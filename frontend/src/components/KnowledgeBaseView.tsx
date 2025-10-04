import { motion } from 'framer-motion';
import { Brain, BookOpen } from 'lucide-react';

export const KnowledgeBaseView = () => {
  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
        <Brain className="text-blue-400" />
        Knowledge Base
      </h2>

      <div className="text-center py-12">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="flex justify-center mb-6"
        >
          <div className="relative">
            <Brain size={80} className="text-blue-400/50" />
            <motion.div
              className="absolute inset-0"
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            >
              <BookOpen size={40} className="text-purple-400/50 absolute top-0 right-0" />
            </motion.div>
          </div>
        </motion.div>

        <p className="text-gray-300 text-lg mb-4">Your knowledge base is empty</p>
        <p className="text-gray-400">
          Process courses from the "Course Processing" tab to build your knowledge base
        </p>
      </div>

      {/* Placeholder for future knowledge base display */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* This would be populated with actual knowledge base items */}
      </div>
    </div>
  );
};
