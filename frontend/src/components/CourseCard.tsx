import { motion } from 'framer-motion';
import { BookOpen, Video, Headphones, FileText, Calendar } from 'lucide-react';

interface CourseCardProps {
  course: {
    id: string;
    course_id: string;
    title: string;
    total_modules: number;
    total_videos: number;
    total_audios: number;
    total_files: number;
    created_at: string;
    overview?: string;
  };
  onClick: () => void;
}

export const CourseCard: React.FC<CourseCardProps> = ({ course, onClick }) => {
  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Unknown date';
    }
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -5 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20 cursor-pointer transition-all hover:border-blue-400/50 hover:shadow-lg hover:shadow-blue-500/20"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-2 line-clamp-2">
            {course.title}
          </h3>
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Calendar className="w-4 h-4" />
            <span>{formatDate(course.created_at)}</span>
          </div>
        </div>
        <div className="bg-blue-500/20 rounded-lg p-3">
          <BookOpen className="w-6 h-6 text-blue-400" />
        </div>
      </div>

      {/* Overview Preview */}
      {course.overview && (
        <p className="text-gray-300 text-sm mb-4 line-clamp-2">
          {course.overview}
        </p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-black/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <BookOpen className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-gray-400">Modules</span>
          </div>
          <div className="text-xl font-bold text-white">
            {course.total_modules}
          </div>
        </div>

        <div className="bg-black/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Video className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-gray-400">Videos</span>
          </div>
          <div className="text-xl font-bold text-white">
            {course.total_videos}
          </div>
        </div>

        {course.total_audios > 0 && (
          <div className="bg-black/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Headphones className="w-4 h-4 text-pink-400" />
              <span className="text-xs text-gray-400">Audio</span>
            </div>
            <div className="text-xl font-bold text-white">
              {course.total_audios}
            </div>
          </div>
        )}

        {course.total_files > 0 && (
          <div className="bg-black/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-yellow-400" />
              <span className="text-xs text-gray-400">Files</span>
            </div>
            <div className="text-xl font-bold text-white">
              {course.total_files}
            </div>
          </div>
        )}
      </div>

      {/* Click hint */}
      <div className="mt-4 pt-4 border-t border-white/10">
        <p className="text-blue-400 text-sm text-center">
          Click to view details →
        </p>
      </div>
    </motion.div>
  );
};
