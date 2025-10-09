/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, Upload, Link, Play, Loader2 } from 'lucide-react';
import { FileUpload } from './FileUpload';
import { DirectLinkInput } from './DirectLinkInput';

type InputMethod = 'url' | 'files' | 'links' | 'mixed';
type ProcessingStage = 'idle' | 'processing' | 'completed' | 'error';

interface EnhancedCourseInputProps {
  onStartProcessing: (data: {
    courseUrl?: string;
    files?: File[];
    directLinks?: string[];
    method: InputMethod;
  }) => void;
  disabled?: boolean;
}

export const EnhancedCourseInput: React.FC<EnhancedCourseInputProps> = ({
  onStartProcessing,
  disabled = false
}) => {
  const [activeTab, setActiveTab] = useState<'url' | 'files' | 'links'>('url');
  const [courseUrl, setCourseUrl] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [directLinks, setDirectLinks] = useState<string[]>([]);
  const [stage, setStage] = useState<ProcessingStage>('idle');

  const tabs = [
    { id: 'url', label: 'Course URL', icon: Globe, description: 'Process online courses' },
    { id: 'files', label: 'File Upload', icon: Upload, description: 'Upload course materials' },
    { id: 'links', label: 'Direct Links', icon: Link, description: 'Add resource links' }
  ] as const;

  const handleFilesSelected = (files: File[]) => {
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const handleFileRemove = (fileId: string) => {
    // Note: This is a simplified implementation
    // In a real app, you'd need to track file IDs properly
    console.log('Remove file:', fileId);
  };

  const handleLinksChange = (links: string[]) => {
    setDirectLinks(links);
  };

  const canStartProcessing = () => {
    switch (activeTab) {
      case 'url':
        return courseUrl.trim().length > 0;
      case 'files':
        return selectedFiles.length > 0;
      case 'links':
        return directLinks.length > 0;
      default:
        return false;
    }
  };

  const getInputMethod = (): InputMethod => {
    const hasUrl = courseUrl.trim().length > 0;
    const hasFiles = selectedFiles.length > 0;
    const hasLinks = directLinks.length > 0;
    
    const activeCount = [hasUrl, hasFiles, hasLinks].filter(Boolean).length;
    
    if (activeCount > 1) return 'mixed';
    if (hasUrl) return 'url';
    if (hasFiles) return 'files';
    if (hasLinks) return 'links';
    
    return activeTab as InputMethod;
  };

  const handleStartProcessing = () => {
    if (!canStartProcessing() || disabled) return;

    const method = getInputMethod();
    const data = {
      courseUrl: courseUrl.trim() || undefined,
      files: selectedFiles.length > 0 ? selectedFiles : undefined,
      directLinks: directLinks.length > 0 ? directLinks : undefined,
      method
    };

    setStage('processing');
    onStartProcessing(data);
  };

  const getProcessingMessage = () => {
    const method = getInputMethod();
    switch (method) {
      case 'url':
        return 'Processing course from URL...';
      case 'files':
        return 'Processing uploaded files...';
      case 'links':
        return 'Processing direct links...';
      case 'mixed':
        return 'Processing mixed content sources...';
      default:
        return 'Processing...';
    }
  };

  const getSummary = () => {
    const items = [];
    if (courseUrl.trim()) items.push(`Course URL: ${courseUrl}`);
    if (selectedFiles.length > 0) items.push(`${selectedFiles.length} uploaded files`);
    if (directLinks.length > 0) items.push(`${directLinks.length} direct links`);
    return items;
  };

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      <h2 className="text-2xl font-bold text-white mb-6">Enhanced Course Processing</h2>

      {stage === 'idle' && (
        <>
          {/* Tab Navigation */}
          <div className="flex space-x-1 mb-6 bg-white/10 rounded-lg p-1">
            {tabs.map((tab) => {
              const IconComponent = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
                    activeTab === tab.id
                      ? 'bg-white/20 text-white shadow-lg'
                      : 'text-white/70 hover:text-white hover:bg-white/10'
                  }`}
                >
                  <IconComponent className="w-4 h-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="mb-6"
            >
              {activeTab === 'url' && (
                <div>
                  <div className="mb-4">
                    <label htmlFor="courseUrl" className="block text-white mb-2 font-medium">
                      Course URL
                    </label>
                    <input
                      type="url"
                      id="courseUrl"
                      value={courseUrl}
                      onChange={(e) => setCourseUrl(e.target.value)}
                      placeholder="https://www.coursera.org/learn/course-name"
                      className="w-full px-4 py-3 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-400"
                      disabled={disabled}
                    />
                  </div>
                  <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                    <p className="text-blue-200 text-sm">
                      Enter the URL of an online course from platforms like Coursera, Udemy, edX, or any educational website.
                      The system will automatically discover and process all course modules.
                    </p>
                  </div>
                </div>
              )}

              {activeTab === 'files' && (
                <FileUpload
                  onFilesSelected={handleFilesSelected}
                  onFileRemove={handleFileRemove}
                  disabled={disabled}
                />
              )}

              {activeTab === 'links' && (
                <DirectLinkInput
                  onLinksChange={handleLinksChange}
                  disabled={disabled}
                />
              )}
            </motion.div>
          </AnimatePresence>

          {/* Summary Section */}
          {getSummary().length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 mb-6"
            >
              <h4 className="text-green-200 font-medium mb-2">Ready to Process:</h4>
              <ul className="text-green-100 text-sm space-y-1">
                {getSummary().map((item, index) => (
                  <li key={index}>• {item}</li>
                ))}
              </ul>
            </motion.div>
          )}

          {/* Start Processing Button */}
          <motion.button
            onClick={handleStartProcessing}
            disabled={!canStartProcessing() || disabled}
            className="w-full px-6 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            whileHover={{ scale: canStartProcessing() && !disabled ? 1.02 : 1 }}
            whileTap={{ scale: canStartProcessing() && !disabled ? 0.98 : 1 }}
          >
            <Play className="w-5 h-5" />
            Start Processing
          </motion.button>
        </>
      )}

      {stage === 'processing' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-8"
        >
          <div className="w-16 h-16 mx-auto mb-4 bg-blue-500/20 rounded-full flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">
            {getProcessingMessage()}
          </h3>
          <p className="text-white/70">
            This may take a few minutes depending on the content size...
          </p>
        </motion.div>
      )}

      {/* Instructions */}
      {stage === 'idle' && (
        <div className="mt-8 bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-200 mb-3">Multiple Input Methods:</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm text-blue-100">
            <div>
              <h4 className="font-medium mb-2">🌐 Course URLs</h4>
              <p>Automatically scrape and process online courses from educational platforms.</p>
            </div>
            <div>
              <h4 className="font-medium mb-2">📁 File Uploads</h4>
              <p>Upload PDFs, videos, audio files, and documents directly for processing.</p>
            </div>
            <div>
              <h4 className="font-medium mb-2">🔗 Direct Links</h4>
              <p>Add direct links to resources like YouTube videos, PDFs, and other materials.</p>
            </div>
          </div>
          <div className="mt-4 text-xs text-blue-200">
            💡 You can combine multiple methods - add a course URL, upload supplementary files, and include additional resource links!
          </div>
        </div>
      )}
    </div>
  );
};