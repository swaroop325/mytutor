/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Loader2,
  CheckCircle,
  Clock,
  Video,
  FileText,
  Headphones,
  Download,
  XCircle,
} from "lucide-react";
import axios from "axios";
import { DCVViewerUI } from "./DCVViewer";

interface ProcessingStatus {
  status: string;
  session_id: string;
  mcp_session_id?: string;
  console_url?: string;
  current_module: number;
  total_modules: number;
  progress: number;
  summary?: any;
}

export const CourseProcessor = () => {
  const [courseUrl, setCourseUrl] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [error, setError] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [showDCVViewer, setShowDCVViewer] = useState(false);
  const statusInterval = useRef<any>(null);

  // Poll status every 2 seconds
  useEffect(() => {
    if (sessionId && isProcessing) {
      statusInterval.current = setInterval(async () => {
        await fetchStatus();
      }, 2000);

      return () => {
        if (statusInterval.current) {
          clearInterval(statusInterval.current);
        }
      };
    }
  }, [sessionId, isProcessing]);

  const fetchStatus = async () => {
    if (!sessionId) return;

    try {
      const response = await axios.post(
        "http://localhost:8000/api/v1/agent/status",
        {
          session_id: sessionId,
        }
      );

      setStatus(response.data);

      // Stop polling if completed or error
      if (
        response.data.status === "completed" ||
        response.data.status === "error"
      ) {
        setIsProcessing(false);
        if (statusInterval.current) {
          clearInterval(statusInterval.current);
        }
      }
    } catch (err) {
      console.error("Failed to fetch status:", err);
    }
  };

  const handleStart = async () => {
    if (!courseUrl) return;

    setError("");
    setIsProcessing(true);

    // Set initial loading state
    setStatus({
      status: "initializing",
      session_id: "",
      current_module: 0,
      total_modules: 0,
      progress: 0,
    });

    try {
      const token = localStorage.getItem("token");

      // Call backend which proxies to agent (avoids CORS)
      const response = await axios.post(
        "http://localhost:8000/api/v1/agent/start-processing",
        { course_url: courseUrl },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // Extract session ID from agent response
      if (response.data.session_id) {
        setSessionId(response.data.session_id);
      }

      setStatus(response.data);

      // Show DCV viewer for login
      if (response.data.status === "awaiting_login") {
        setShowDCVViewer(true);
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "Failed to start processing"
      );
      setIsProcessing(false);
    }
  };

  const handleContinueAfterLogin = async () => {
    if (!sessionId) return;

    setShowDCVViewer(false);

    try {
      const token = localStorage.getItem("token");

      // Tell agent to continue processing via backend
      await axios.post(
        "http://localhost:8000/api/v1/agent/continue-processing",
        { session_id: sessionId },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // Status will be updated via polling
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "Failed to continue processing"
      );
    }
  };

  const handleStop = async () => {
    if (!sessionId) return;

    try {
      const token = localStorage.getItem("token");

      await axios.post(
        "http://localhost:8000/api/v1/agent/stop-processing",
        { session_id: sessionId },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setIsProcessing(false);
      setStatus(null);
      setSessionId(null);

      if (statusInterval.current) {
        clearInterval(statusInterval.current);
      }
    } catch (err) {
      console.error("Failed to stop:", err);
    }
  };

  const getStatusIcon = () => {
    if (!status) return <Clock className="w-5 h-5 text-gray-400" />;

    switch (status.status) {
      case "awaiting_login":
        return <Clock className="w-5 h-5 text-yellow-400 animate-pulse" />;
      case "discovering_modules":
      case "processing_modules":
        return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
      case "analyzing":
        return <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />;
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case "error":
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusMessage = () => {
    if (!status) return "Ready to start";

    switch (status.status) {
      case "initializing":
        return "Initializing browser session...";
      case "awaiting_login":
        return "Waiting for login...";
      case "discovering_modules":
        return "Discovering course modules...";
      case "processing_modules":
        return `Processing module ${status.current_module} of ${status.total_modules}`;
      case "analyzing":
        return "Analyzing complete course...";
      case "completed":
        return "Course processing completed!";
      case "error":
        return "Processing failed";
      default:
        return status.status;
    }
  };

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      <h2 className="text-2xl font-bold text-white mb-6">Course Processor</h2>

      {/* Course URL Input */}
      {!isProcessing && (
        <div className="mb-6">
          <label
            htmlFor="courseUrl"
            className="block text-white mb-2 font-medium"
          >
            Course URL
          </label>
          <div className="flex gap-3">
            <input
              type="url"
              id="courseUrl"
              value={courseUrl}
              onChange={(e) => setCourseUrl(e.target.value)}
              placeholder="Enter course URL (e.g., https://www.coursera.org/learn/...)"
              className="flex-1 px-4 py-3 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <motion.button
              onClick={handleStart}
              disabled={!courseUrl}
              className="px-8 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Play className="w-5 h-5" />
              Start Processing
            </motion.button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 mb-6"
        >
          <p className="text-red-200 mb-3">{error}</p>
          {error.includes("Connection limit") && (
            <button
              onClick={() => {
                setError("");
                handleStart();
              }}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors text-sm"
            >
              Retry
            </button>
          )}
        </motion.div>
      )}

      {/* Processing Status */}
      <AnimatePresence>
        {status && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            {/* Status Header */}
            <div className="bg-blue-500/20 border border-blue-500/50 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  {getStatusIcon()}
                  <h3 className="text-xl font-semibold text-white">
                    {getStatusMessage()}
                  </h3>
                </div>

                {isProcessing && status.status !== "awaiting_login" && (
                  <button
                    onClick={handleStop}
                    className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                  >
                    Stop
                  </button>
                )}
              </div>

              {/* Progress Bar */}
              {status.progress !== undefined && status.progress > 0 && (
                <div className="mb-4">
                  <div className="flex justify-between text-sm text-blue-200 mb-2">
                    <span>Progress</span>
                    <span>{status.progress}%</span>
                  </div>
                  <div className="w-full bg-blue-900/50 rounded-full h-3 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${status.progress}%` }}
                      transition={{ duration: 0.5 }}
                      className="h-full bg-gradient-to-r from-blue-400 to-purple-500 rounded-full"
                    />
                  </div>
                </div>
              )}

              {/* Module Progress */}
              {status.total_modules > 0 && (
                <div className="text-blue-200 text-sm">
                  Module {status.current_module} of {status.total_modules}
                </div>
              )}

              {/* Login Buttons */}
              {status.status === "awaiting_login" && (
                <div className="mt-4 flex gap-3">
                  {!showDCVViewer && (
                    <motion.button
                      onClick={() => setShowDCVViewer(true)}
                      className="flex-1 px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <Video className="w-5 h-5" />
                      Reopen Browser
                    </motion.button>
                  )}
                  <motion.button
                    onClick={handleContinueAfterLogin}
                    className="flex-1 px-6 py-3 bg-green-500 hover:bg-green-600 text-white font-bold rounded-lg transition-colors"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    I've Logged In - Continue Processing
                  </motion.button>
                </div>
              )}
            </div>

            {/* Course Summary */}
            {status.status === "completed" && status.summary && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-green-500/20 border border-green-500/50 rounded-lg p-6"
              >
                <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  <CheckCircle className="w-6 h-6 text-green-400" />
                  Course Processing Complete
                </h3>

                {/* Statistics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-black/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-blue-300 mb-1">
                      <FileText className="w-4 h-4" />
                      <span className="text-sm">Modules</span>
                    </div>
                    <div className="text-2xl font-bold text-white">
                      {status.summary.total_modules || 0}
                    </div>
                  </div>

                  <div className="bg-black/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-purple-300 mb-1">
                      <Video className="w-4 h-4" />
                      <span className="text-sm">Videos</span>
                    </div>
                    <div className="text-2xl font-bold text-white">
                      {status.summary.total_videos || 0}
                    </div>
                  </div>

                  <div className="bg-black/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-pink-300 mb-1">
                      <Headphones className="w-4 h-4" />
                      <span className="text-sm">Audio</span>
                    </div>
                    <div className="text-2xl font-bold text-white">
                      {status.summary.total_audios || 0}
                    </div>
                  </div>

                  <div className="bg-black/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-yellow-300 mb-1">
                      <Download className="w-4 h-4" />
                      <span className="text-sm">Files</span>
                    </div>
                    <div className="text-2xl font-bold text-white">
                      {status.summary.total_files || 0}
                    </div>
                  </div>
                </div>

                {/* AI Analysis */}
                {status.summary.analysis && (
                  <div className="bg-black/30 rounded-lg p-4">
                    <h4 className="text-lg font-semibold text-green-200 mb-2">
                      AI Analysis
                    </h4>
                    <p className="text-white whitespace-pre-wrap">
                      {status.summary.analysis}
                    </p>
                  </div>
                )}

                {/* Reset Button */}
                <motion.button
                  onClick={() => {
                    setSessionId(null);
                    setStatus(null);
                    setCourseUrl("");
                    setIsProcessing(false);
                  }}
                  className="mt-4 w-full px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Process Another Course
                </motion.button>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* DCV Viewer Modal */}
      {showDCVViewer &&
        status?.status === "awaiting_login" &&
        status.mcp_session_id &&
        sessionId && (
          <DCVViewerUI
            sessionId={sessionId}
            mcpSessionId={status.mcp_session_id}
            onClose={() => setShowDCVViewer(false)}
          />
        )}

      {/* Fallback Login Instructions (if no MCP session) */}
      {showDCVViewer &&
        status?.status === "awaiting_login" &&
        !status.mcp_session_id && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl border border-white/10 p-8"
            >
              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Clock className="w-8 h-8 text-blue-400 animate-pulse" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-2">
                  Browser Session Created!
                </h3>
                <p className="text-gray-300">
                  A secure browser session has been opened in AWS
                </p>
              </div>

              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-6 mb-6">
                <h4 className="text-yellow-200 font-semibold mb-3 flex items-center gap-2">
                  <span className="text-2xl">⚠️</span>
                  Manual Login Required
                </h4>
                <p className="text-yellow-100 text-sm mb-4">
                  The agent has opened the course URL in a secure browser in
                  AWS. You need to log in manually to the course platform.
                </p>

                {status.console_url && (
                  <a
                    href={status.console_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors mb-4"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      />
                    </svg>
                    Open Browser Session in AWS Console
                  </a>
                )}

                <p className="text-yellow-100 text-xs">
                  After logging in to the course, click "I've Logged In -
                  Continue" below to start processing.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowDCVViewer(false)}
                  className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={handleContinueAfterLogin}
                  className="flex-1 px-6 py-3 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <CheckCircle className="w-5 h-5" />
                  I've Logged In - Continue
                </button>
              </div>
            </motion.div>
          </div>
        )}

      {/* Instructions */}
      {!isProcessing && (
        <div className="mt-6 bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-200 mb-3">
            How it works:
          </h3>
          <ol className="space-y-2 text-blue-100">
            <li>1. Enter course URL and click "Start Processing"</li>
            <li>2. Agent opens browser session via MCP</li>
            <li>3. You log in to the course platform</li>
            <li>4. Agent discovers all modules automatically</li>
            <li>
              5. Each module is processed: text, videos, audio, files extracted
            </li>
            <li>6. AI analyzes complete course and creates summary</li>
            <li>7. View comprehensive course breakdown and resources</li>
          </ol>
        </div>
      )}
    </div>
  );
};
