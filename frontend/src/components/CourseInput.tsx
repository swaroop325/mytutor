import { useState } from 'react';
import { motion } from 'framer-motion';
import { courseService } from '../services/api';
import { BrowserViewer } from './BrowserViewer';

type ProcessingStage =
  | 'idle'
  | 'creating-session'
  | 'navigating'
  | 'awaiting-login'
  | 'scraping'
  | 'analyzing'
  | 'building-kb'
  | 'completed';

export const CourseInput = () => {
  const [courseUrl, setCourseUrl] = useState('');
  const [stage, setStage] = useState<ProcessingStage>('idle');
  const [sessionInfo, setSessionInfo] = useState<any>(null);
  const [error, setError] = useState('');
  const [results, setResults] = useState<any>(null);
  const [showBrowser, setShowBrowser] = useState(false);

  const handleStartProcessing = async () => {
    if (!courseUrl) return;

    setError('');
    setStage('creating-session');

    try {
      // Step 1: Start the full processing pipeline
      const processResult = await courseService.processCourseFull(courseUrl);
      setSessionInfo(processResult);
      setStage('awaiting-login');

      // Show browser viewer
      setShowBrowser(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start processing');
      setStage('idle');
    }
  };

  const handleContinueAfterLogin = async () => {
    setStage('scraping');
    setShowBrowser(false);  // Close browser viewer

    try {
      // Continue processing after manual login
      const result = await courseService.continueAfterLogin(courseUrl);
      setResults(result);
      setStage('completed');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process course');
      setStage('idle');
    }
  };

  const getStageMessage = () => {
    const messages = {
      'idle': 'Enter a course URL to begin',
      'creating-session': 'Creating browser session...',
      'navigating': 'Navigating to course...',
      'awaiting-login': 'Please log in to the course platform in the browser window',
      'scraping': 'Extracting course content...',
      'analyzing': 'Analyzing with AI...',
      'building-kb': 'Building knowledge base...',
      'completed': 'Processing complete!',
    };
    return messages[stage];
  };

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      <h2 className="text-2xl font-bold text-white mb-6">Process Course Content</h2>

      {/* Course URL Input */}
      <div className="mb-6">
        <label htmlFor="courseUrl" className="block text-white mb-2 font-medium">
          Course URL
        </label>
        <div className="flex gap-3">
          <input
            type="url"
            id="courseUrl"
            value={courseUrl}
            onChange={(e) => setCourseUrl(e.target.value)}
            placeholder="https://example.com/course"
            className="flex-1 px-4 py-3 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-400"
            disabled={stage !== 'idle'}
          />
          <motion.button
            onClick={handleStartProcessing}
            disabled={!courseUrl || stage !== 'idle'}
            className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={{ scale: stage === 'idle' ? 1.05 : 1 }}
            whileTap={{ scale: stage === 'idle' ? 0.95 : 1 }}
          >
            Start Processing
          </motion.button>
        </div>
      </div>

      {/* Processing Status */}
      {stage !== 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-blue-500/20 border border-blue-500/50 rounded-lg p-6 mb-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-white">Processing Status</h3>
            {stage !== 'completed' && stage !== 'awaiting-login' && (
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-white border-t-transparent" />
            )}
          </div>

          <p className="text-blue-200 mb-4">{getStageMessage()}</p>

          {/* Progress Steps */}
          <div className="space-y-2">
            {['creating-session', 'navigating', 'awaiting-login', 'scraping', 'analyzing', 'building-kb', 'completed'].map((s, idx) => (
              <div key={s} className="flex items-center space-x-3">
                <div className={`w-4 h-4 rounded-full ${
                  stage === s ? 'bg-blue-400 animate-pulse' :
                  ['creating-session', 'navigating', 'awaiting-login', 'scraping', 'analyzing', 'building-kb', 'completed'].indexOf(stage) > idx ? 'bg-green-400' : 'bg-gray-600'
                }`} />
                <span className={`${
                  ['creating-session', 'navigating', 'awaiting-login', 'scraping', 'analyzing', 'building-kb', 'completed'].indexOf(stage) >= idx ? 'text-white' : 'text-gray-400'
                }`}>
                  {s.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </span>
              </div>
            ))}
          </div>

          {/* DCV Session Info */}
          {stage === 'awaiting-login' && sessionInfo && (
            <div className="mt-6 p-4 bg-yellow-500/20 border border-yellow-500/50 rounded-lg">
              <p className="text-yellow-200 mb-3">
                <strong>Amazon DCV Session Active</strong>
              </p>
              <p className="text-yellow-100 text-sm mb-4">
                A browser session has been opened. Please log in to your course platform.
              </p>
              <motion.button
                onClick={handleContinueAfterLogin}
                className="px-6 py-2 bg-green-500 hover:bg-green-600 text-white font-bold rounded-lg transition-colors"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                I've Logged In - Continue Processing
              </motion.button>
            </div>
          )}
        </motion.div>
      )}

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 mb-6 text-red-200"
        >
          {error}
        </motion.div>
      )}

      {/* Results Display */}
      {results && stage === 'completed' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-green-500/20 border border-green-500/50 rounded-lg p-6"
        >
          <h3 className="text-xl font-semibold text-white mb-4">✅ Processing Complete!</h3>

          {results.course_analysis && (
            <div className="mb-4">
              <h4 className="text-lg font-medium text-green-200 mb-2">Course Analysis:</h4>
              <div className="bg-black/30 rounded-lg p-4">
                <p className="text-white"><strong>Title:</strong> {results.course_analysis.title}</p>
                <p className="text-white mt-2"><strong>Summary:</strong> {results.course_analysis.summary}</p>
                {results.course_analysis.topics && results.course_analysis.topics.length > 0 && (
                  <div className="mt-2">
                    <strong className="text-white">Topics:</strong>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {results.course_analysis.topics.map((topic: string, idx: number) => (
                        <span key={idx} className="px-2 py-1 bg-blue-500/30 rounded text-blue-200 text-sm">
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {results.knowledge_base && (
            <div className="bg-black/30 rounded-lg p-4">
              <p className="text-green-200">
                <strong>Knowledge Base ID:</strong> {results.knowledge_base.id}
              </p>
              <p className="text-green-200 mt-1">
                <strong>Total Courses:</strong> {results.knowledge_base.total_courses || 1}
              </p>
            </div>
          )}

          <motion.button
            onClick={() => {
              setStage('idle');
              setCourseUrl('');
              setResults(null);
              setSessionInfo(null);
            }}
            className="mt-4 px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg transition-colors"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Process Another Course
          </motion.button>
        </motion.div>
      )}

      {/* Instructions */}
      <div className="mt-8 bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-200 mb-3">How it works:</h3>
        <ol className="space-y-2 text-blue-100">
          <li>1. Enter the URL of your course platform</li>
          <li>2. System opens a browser session using AgentCore MCP</li>
          <li>3. Browser viewer opens so you can see the session</li>
          <li>4. You manually log in to your course platform</li>
          <li>5. After login, click continue to scrape content intelligently</li>
          <li>6. Amazon Bedrock (Claude) analyzes the content using multimodal AI</li>
          <li>7. Knowledge base is built automatically with all course materials</li>
        </ol>
      </div>

      {/* Browser Viewer Modal */}
      {showBrowser && sessionInfo && (
        <BrowserViewer
          sessionId={sessionInfo.session_id || 'default'}
          courseUrl={courseUrl}
          onClose={() => setShowBrowser(false)}
        />
      )}
    </div>
  );
};
