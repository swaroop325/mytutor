import { motion, AnimatePresence } from 'framer-motion';
import { X, BookOpen, Video, Headphones, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { useState, useEffect } from 'react';
import axios from 'axios';

interface CourseDetailsProps {
  courseId: string;
  onClose: () => void;
}

interface Module {
  title: string;
  url: string;
  order: number;
  text_preview: string;
  video_count: number;
  audio_count: number;
  file_count: number;
}

interface CourseData {
  course_id: string;
  title: string;
  total_modules: number;
  total_videos: number;
  total_audios: number;
  total_files: number;
  overview?: string;
  key_topics?: string[];
  learning_outcomes?: string[];
  modules: Module[];
}

export const CourseDetails: React.FC<CourseDetailsProps> = ({ courseId, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [courseData, setCourseData] = useState<CourseData | null>(null);
  const [expandedModules, setExpandedModules] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetchCourseDetails();
  }, [courseId]);

  const fetchCourseDetails = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        'http://localhost:8000/api/v1/agent/courses/details',
        { course_id: courseId },
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (response.data.status === 'success') {
        setCourseData(response.data.course);
      } else {
        setError(response.data.message || 'Failed to load course details');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load course details');
    } finally {
      setLoading(false);
    }
  };

  const toggleModule = (order: number) => {
    const newExpanded = new Set(expandedModules);
    if (newExpanded.has(order)) {
      newExpanded.delete(order);
    } else {
      newExpanded.add(order);
    }
    setExpandedModules(newExpanded);
  };

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col border border-white/10"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 flex items-start justify-between flex-shrink-0">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-white mb-2">
              {loading ? 'Loading...' : courseData?.title || 'Course Details'}
            </h2>
            {courseData && (
              <div className="flex gap-4 text-blue-100 text-sm">
                <span>{courseData.total_modules} modules</span>
                <span>•</span>
                <span>{courseData.total_videos} videos</span>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white/10 rounded-lg p-2 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-200">
              {error}
            </div>
          )}

          {courseData && !loading && (
            <div className="space-y-6">
              {/* Overview */}
              {courseData.overview && (
                <div className="bg-white/5 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Overview</h3>
                  <p className="text-gray-300 leading-relaxed">{courseData.overview}</p>
                </div>
              )}

              {/* Key Topics */}
              {courseData.key_topics && courseData.key_topics.length > 0 && (
                <div className="bg-white/5 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Key Topics</h3>
                  <div className="flex flex-wrap gap-2">
                    {courseData.key_topics.map((topic, idx) => (
                      <span
                        key={idx}
                        className="bg-blue-500/20 text-blue-300 px-3 py-1 rounded-full text-sm"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Learning Outcomes */}
              {courseData.learning_outcomes && courseData.learning_outcomes.length > 0 && (
                <div className="bg-white/5 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Learning Outcomes</h3>
                  <ul className="space-y-2">
                    {courseData.learning_outcomes.map((outcome, idx) => (
                      <li key={idx} className="text-gray-300 flex items-start gap-2">
                        <span className="text-green-400 mt-1">✓</span>
                        <span>{outcome}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Modules */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">
                  Course Modules ({courseData.modules.length})
                </h3>
                <div className="space-y-3">
                  {courseData.modules.map((module) => (
                    <div
                      key={module.order}
                      className="bg-white/5 rounded-lg overflow-hidden border border-white/10"
                    >
                      <button
                        onClick={() => toggleModule(module.order)}
                        className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="bg-blue-500/20 rounded-lg p-2">
                            <BookOpen className="w-5 h-5 text-blue-400" />
                          </div>
                          <div className="text-left">
                            <div className="text-white font-medium">{module.title}</div>
                            <div className="flex gap-3 text-sm text-gray-400 mt-1">
                              {module.video_count > 0 && (
                                <span className="flex items-center gap-1">
                                  <Video className="w-3 h-3" /> {module.video_count}
                                </span>
                              )}
                              {module.audio_count > 0 && (
                                <span className="flex items-center gap-1">
                                  <Headphones className="w-3 h-3" /> {module.audio_count}
                                </span>
                              )}
                              {module.file_count > 0 && (
                                <span className="flex items-center gap-1">
                                  <FileText className="w-3 h-3" /> {module.file_count}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        {expandedModules.has(module.order) ? (
                          <ChevronUp className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        )}
                      </button>

                      <AnimatePresence>
                        {expandedModules.has(module.order) && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="p-4 bg-black/30 border-t border-white/10">
                              <p className="text-gray-300 text-sm leading-relaxed">
                                {module.text_preview || 'No preview available'}
                              </p>
                              {module.url && (
                                <a
                                  href={module.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="mt-3 inline-block text-blue-400 hover:text-blue-300 text-sm"
                                >
                                  View module →
                                </a>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};
