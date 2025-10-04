import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Monitor, X, Loader2 } from 'lucide-react';

interface BrowserViewerProps {
  sessionId: string;
  courseUrl: string;
  onClose: () => void;
}

interface BrowserMessage {
  type: string;
  session_id?: string;
  screenshot?: string;
  url?: string;
  title?: string;
  message?: string;
}

export const BrowserViewer = ({ sessionId, courseUrl, onClose }: BrowserViewerProps) => {
  const [screenshot, setScreenshot] = useState<string>('');
  const [currentUrl, setCurrentUrl] = useState<string>(courseUrl);
  const [currentTitle, setCurrentTitle] = useState<string>('Loading...');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to browser viewer WebSocket
    const ws = new WebSocket(`ws://localhost:8081/ws/browser/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);

      // Start browser session
      ws.send(JSON.stringify({
        action: 'start_session',
        course_url: courseUrl
      }));
    };

    ws.onmessage = (event) => {
      const data: BrowserMessage = JSON.parse(event.data);

      switch (data.type) {
        case 'session_created':
          console.log('Browser session created:', data);
          setCurrentTitle(data.title || 'Course Page');
          break;

        case 'screenshot':
          // Update screenshot
          setScreenshot(data.screenshot || '');
          if (data.url) setCurrentUrl(data.url);
          if (data.title) setCurrentTitle(data.title);
          break;

        case 'error':
          setError(data.message || 'Unknown error');
          break;

        case 'streaming_stopped':
        case 'session_closed':
          console.log('Session ended');
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Failed to connect to browser viewer');
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    // Cleanup on unmount
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'close_session' }));
      }
      ws.close();
    };
  }, [sessionId, courseUrl]);

  const handleClose = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'close_session' }));
    }
    onClose();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden border border-white/10"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-black/20">
          <div className="flex items-center space-x-3">
            <Monitor className="w-6 h-6 text-blue-400" />
            <div>
              <h3 className="text-lg font-semibold text-white">Browser Session</h3>
              <p className="text-sm text-gray-400 truncate max-w-md">{currentTitle}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
              <span className="text-sm text-gray-400">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>

            {/* Close Button */}
            <button
              onClick={handleClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        {/* URL Bar */}
        <div className="px-4 py-2 bg-black/30 border-b border-white/10">
          <div className="flex items-center space-x-2 px-3 py-2 bg-white/5 rounded-lg">
            <div className="w-3 h-3 rounded-full bg-green-400" />
            <span className="text-sm text-gray-300 truncate flex-1">{currentUrl}</span>
          </div>
        </div>

        {/* Browser View */}
        <div className="relative bg-black" style={{ height: 'calc(90vh - 160px)' }}>
          {error ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-red-400 text-lg mb-2">⚠️ Error</div>
                <p className="text-gray-400">{error}</p>
              </div>
            </div>
          ) : screenshot ? (
            <img
              src={`data:image/png;base64,${screenshot}`}
              alt="Browser view"
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
                <p className="text-gray-400">Loading browser session...</p>
                <p className="text-sm text-gray-500 mt-2">Please wait while we connect</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 bg-black/30 border-t border-white/10 flex items-center justify-between">
          <div className="text-sm text-gray-400">
            Session ID: <span className="font-mono text-gray-300">{sessionId}</span>
          </div>
          <div className="text-sm text-gray-400">
            You can interact with the browser. After logging in, close this window to continue.
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};
