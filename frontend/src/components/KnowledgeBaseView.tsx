/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Brain, BookOpen, Search, X, Loader2 } from 'lucide-react';
import axios from 'axios';
import { CourseCard } from './CourseCard';
import { CourseDetails } from './CourseDetails';

interface Course {
  id: string;
  course_id: string;
  title: string;
  total_modules: number;
  total_videos: number;
  total_audios: number;
  total_files: number;
  created_at: string;
  overview?: string;
  key_topics?: string[];
  learning_outcomes?: string[];
}

export const KnowledgeBaseView = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null);

  useEffect(() => {
    fetchCourses();
  }, []);

  // Debounced search
  useEffect(() => {
    if (searchQuery.length > 0) {
      const timer = setTimeout(() => {
        performSearch(searchQuery);
      }, 500);
      return () => clearTimeout(timer);
    } else {
      fetchCourses();
    }
  }, [searchQuery]);

  const fetchCourses = async () => {
    try {
      setLoading(true);
      setError('');
      const token = localStorage.getItem('token');
      const response = await axios.get(
        'http://localhost:8000/api/v1/agent/courses',
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (response.data.status === 'success') {
        setCourses(response.data.courses || []);
      } else {
        setError(response.data.message || 'Failed to load courses');
      }
    } catch (err: any) {
      console.error('Failed to fetch courses:', err);
      setError(err.response?.data?.detail || 'Failed to load courses');
    } finally {
      setLoading(false);
    }
  };

  const performSearch = async (query: string) => {
    try {
      setIsSearching(true);
      setError('');
      const token = localStorage.getItem('token');
      const response = await axios.post(
        'http://localhost:8000/api/v1/agent/courses/search',
        { query },
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (response.data.status === 'success') {
        setCourses(response.data.courses || []);
      } else {
        setError(response.data.message || 'Search failed');
      }
    } catch (err: any) {
      console.error('Search failed:', err);
      setError(err.response?.data?.detail || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    fetchCourses();
  };

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
          <Brain className="text-blue-400" />
          Knowledge Base
        </h2>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search courses (semantic search enabled)..."
            className="w-full pl-12 pr-12 py-3 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          )}
          {isSearching && (
            <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
              <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
            </div>
          )}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
            <p className="text-gray-300">Loading your courses...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-200 mb-6">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && courses.length === 0 && (
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

          <p className="text-gray-300 text-lg mb-4">
            {searchQuery ? 'No courses found matching your search' : 'Your knowledge base is empty'}
          </p>
          <p className="text-gray-400">
            {searchQuery ? 'Try a different search query' : 'Process courses from the "Course Processing" tab to build your knowledge base'}
          </p>
        </div>
      )}

      {/* Courses Grid */}
      {!loading && courses.length > 0 && (
        <div>
          <p className="text-gray-300 mb-4">
            {searchQuery ? `Found ${courses.length} course${courses.length !== 1 ? 's' : ''}` : `${courses.length} course${courses.length !== 1 ? 's' : ''} in your knowledge base`}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                onClick={() => setSelectedCourseId(course.course_id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Course Details Modal */}
      {selectedCourseId && (
        <CourseDetails
          courseId={selectedCourseId}
          onClose={() => setSelectedCourseId(null)}
        />
      )}
    </div>
  );
};
