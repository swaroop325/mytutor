/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { API_URL } from "../services/api";

interface DCVViewerUIProps {
  sessionId: string;
  mcpSessionId: string;
  onClose: () => void;
}

// Declare global dcv object from SDK
declare global {
  interface Window {
    dcv: any;
  }
}

interface ConnectionStats {
  fps: number;
  traffic: number;
  peakTraffic: number;
  latency: number;
  currentChannels: number;
  openedChannels: number;
  channelErrors: number;
  connected: boolean;
}

export const DCVViewerUI: React.FC<DCVViewerUIProps> = ({
  sessionId,
  mcpSessionId,
  onClose,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [stats, setStats] = useState<ConnectionStats>({
    fps: 0,
    traffic: 0,
    peakTraffic: 0,
    latency: 0,
    currentChannels: 0,
    openedChannels: 0,
    channelErrors: 0,
    connected: false,
  });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const dcvContainerRef = useRef<HTMLDivElement>(null);
  const connectionRef = useRef<any>(null);
  const displayLayoutRequestedRef = useRef(false);
  const statsIntervalRef = useRef<any>(null);
  const resizeTimeoutRef = useRef<any>(null);
  const lastWidthRef = useRef(0);
  const lastHeightRef = useRef(0);


  const handleClose = () => {
    // Clear all timers
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current);
      statsIntervalRef.current = null;
    }
    if (resizeTimeoutRef.current) {
      clearTimeout(resizeTimeoutRef.current);
      resizeTimeoutRef.current = null;
    }

    // Exit fullscreen if active
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }

    // Properly close the DCV connection before closing the viewer
    if (connectionRef.current) {
      try {
        console.log("Closing DCV connection");
        // Only call disconnect, not both disconnect and close
        // The DCV SDK will handle the proper closure sequence
        if (typeof connectionRef.current.disconnect === 'function') {
          connectionRef.current.disconnect();
        }
        connectionRef.current = null;
        console.log("DCV connection closed successfully");
      } catch (e) {
        console.error("Error closing DCV connection:", e);
      }
    }
    onClose();
  };

  // Update connection statistics using official API
  const updateStats = () => {
    if (connectionRef.current) {
      try {
        const connection = connectionRef.current;

        // Use official getStats() method
        if (typeof connection.getStats === 'function') {
          const dcvStats = connection.getStats();
          console.log("DCV Stats:", dcvStats);

          setStats({
            fps: dcvStats.fps || 0,
            traffic: dcvStats.traffic || 0,
            peakTraffic: dcvStats.peakTraffic || 0,
            latency: dcvStats.latency || 0,
            currentChannels: dcvStats.currentChannels || 0,
            openedChannels: dcvStats.openedChannels || 0,
            channelErrors: dcvStats.channelErrors || 0,
            connected: true,
          });
        }
      } catch (e) {
        console.error("Error fetching stats:", e);
      }
    }
  };

  // Debounced resize display with change threshold
  const resizeDisplay = () => {
    // Clear existing timeout
    if (resizeTimeoutRef.current) {
      clearTimeout(resizeTimeoutRef.current);
    }
    // Debounce resize events by 300ms
    resizeTimeoutRef.current = setTimeout(() => {
      const display = document.getElementById("dcv-display");
      if (display && connectionRef.current) {
        const displayRect = display.getBoundingClientRect();
        const width = Math.floor(displayRect.width);
        const height = Math.floor(displayRect.height);

        console.log(`Resize triggered - Container: ${width}x${height}, Last: ${lastWidthRef.current}x${lastHeightRef.current}`);

        // Check canvas
        const canvas = display.querySelector('canvas');
        if (canvas) {
          console.log(`Current canvas: ${canvas.width}x${canvas.height}, Client: ${canvas.clientWidth}x${canvas.clientHeight}`);
        }

        // Only resize if dimensions changed significantly (>10px threshold)
        const widthChanged = Math.abs(width - lastWidthRef.current) > 10;
        const heightChanged = Math.abs(height - lastHeightRef.current) > 10;

        if ((widthChanged || heightChanged) && width > 0 && height > 0) {
          console.log(`Requesting resolution change to ${width}x${height}`);

          if (connectionRef.current.requestResolution) {
            connectionRef.current
              .requestResolution(width, height)
              .then(() => {
                console.log(
                  `Resolution successfully set to ${width}x${height}`
                );
                lastWidthRef.current = width;
                lastHeightRef.current = height;

                // Log canvas after resize
                const canvas = display.querySelector('canvas');
                if (canvas) {
                  console.log(`Canvas after resize: ${canvas.width}x${canvas.height}`);
                }
              })
              .catch((err: any) => {
                console.error("Failed to set resolution:", err);
              });
          }
        }
      }
    }, 300);
  };


  // Toggle fullscreen
  const toggleFullscreen = () => {
    const container = dcvContainerRef.current?.parentElement;
    if (!container) return;

    if (!document.fullscreenElement) {
      container.requestFullscreen().then(() => {
        setIsFullscreen(true);
        // Resize after entering fullscreen
        setTimeout(() => resizeDisplay(), 100);
      });
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
        // Resize after exiting fullscreen
        setTimeout(() => resizeDisplay(), 100);
      });
    }
  };


  useEffect(() => {
    // Add DCV canvas styling
    const style = document.createElement("style");
    style.textContent = `
      #dcv-display {
        width: 100% !important;
        height: 100% !important;
        overflow: hidden;
      }
      #dcv-display canvas {
        width: 100% !important;
        height: 100% !important;
        display: block;
        margin: 0;
        padding: 0;
      }
      #dcv-display > div {
        width: 100% !important;
        height: 100% !important;
      }
    `;
    document.head.appendChild(style);

    // Load DCV SDK using script tag (UMD version for better compatibility)
    const script = document.createElement("script");
    script.src = "/dcv-sdk/dcvjs-umd/dcv.js";
    script.async = true;

    script.onload = () => {
      console.log("DCV SDK loaded successfully", window.dcv);
      // Give a small delay for SDK initialization
      setTimeout(() => {
        initializeDCV();
      }, 100);
    };

    script.onerror = (e) => {
      console.error("Failed to load DCV SDK script:", e);
      setError("Failed to load DCV SDK. Please refresh the page.");
      setLoading(false);
    };

    document.head.appendChild(script);

    // Add window resize listener
    window.addEventListener("resize", resizeDisplay);

    // Prevent browser shortcuts during DCV session
    const preventBrowserShortcuts = (e: KeyboardEvent) => {
      if (authenticated && (e.ctrlKey || e.metaKey)) {
        // Prevent common browser shortcuts
        const preventKeys = ["w", "t", "n", "r", "f", "p", "s", "o", "j"];
        if (preventKeys.includes(e.key.toLowerCase())) {
          e.preventDefault();
          console.log(`Prevented browser shortcut: ${e.key}`);
        }
      }

      // Prevent F11 fullscreen (we have our own)
      if (e.key === "F11") {
        e.preventDefault();
        toggleFullscreen();
      }
    };

    window.addEventListener("keydown", preventBrowserShortcuts);

    // Handle fullscreen change events
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);

    return () => {
      // Cleanup on unmount - properly close connection
      if (connectionRef.current) {
        try {
          console.log("Closing DCV connection on unmount");
          // Only call disconnect - SDK handles the rest
          if (typeof connectionRef.current.disconnect === 'function') {
            connectionRef.current.disconnect();
          }
          connectionRef.current = null;
          console.log("DCV connection closed successfully");
        } catch (e) {
          console.error("Error closing DCV connection:", e);
        }
      }
      // Remove script and style on cleanup
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
      if (style.parentNode) {
        style.parentNode.removeChild(style);
      }
      // Remove listeners
      window.removeEventListener("resize", resizeDisplay);
      window.removeEventListener("keydown", preventBrowserShortcuts);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, [authenticated]);

  const initializeDCV = async () => {
    try {
      // Get presigned URL from backend
      const token = localStorage.getItem("token");
      const response = await axios.post(
        `${API_URL}/agent/get-dcv-url`,
        {
          session_id: sessionId,
          mcp_session_id: mcpSessionId,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const { presignedUrl } = response.data;

      if (!presignedUrl) {
        throw new Error("No presigned URL received");
      }

      console.log("DCV Presigned URL received:", presignedUrl);

      // Store presigned URL for callbacks
      const presignedUrlRef = { current: presignedUrl };

      // Callback to extract and preserve query parameters from presigned URL
      const httpExtraSearchParamsCb = () => {
        try {
          const urlObj = new URL(presignedUrlRef.current);
          console.log("Extracting auth params from presigned URL");
          console.log("Query params:", urlObj.searchParams.toString());
          return urlObj.searchParams;
        } catch (e) {
          console.error("Failed to extract search params:", e);
          return new URLSearchParams();
        }
      };

      // Initialize DCV with logging
      if (window.dcv) {
        window.dcv.setLogLevel(window.dcv.LogLevel.INFO);

        // Authenticate with presigned URL
        window.dcv.authenticate(presignedUrlRef.current, {
          promptCredentials: () => {
            console.log(
              "Credentials prompted (returning null for pre-authenticated)"
            );
            return null;
          },
          error: (_auth: any, error: any) => {
            console.error("DCV Authentication error:", error);
            const errorMsg =
              error?.message || error?.toString() || "Authentication failed";
            console.log(errorMsg);
          },
          success: (_auth: any, result: any[]) => {
            console.log("DCV Authentication successful", result);
            const { sessionId: dcvSid, authToken } = result[0];
            setAuthenticated(true);
            setLoading(false);
            connect(
              presignedUrlRef.current,
              dcvSid,
              authToken,
              httpExtraSearchParamsCb
            );
          },
          httpExtraSearchParams: httpExtraSearchParamsCb,
        });
      } else {
        setLoading(false);
        throw new Error("DCV SDK not loaded");
      }
    } catch (err: any) {
      console.error("DCV initialization error:", err);
      setLoading(false);
      setError(err.message || "Failed to initialize DCV viewer");
    }
  };

  const displayLayoutCallback = () => {
    // Only set resolution once on initial connection (prevents loops)
    if (!displayLayoutRequestedRef.current) {
      displayLayoutRequestedRef.current = true;

      const display = document.getElementById("dcv-display");
      if (display && connectionRef.current) {
        // Get the actual dimensions of the display element
        const displayRect = display.getBoundingClientRect();
        const width = Math.floor(displayRect.width);
        const height = Math.floor(displayRect.height);

        console.log(`Initial container dimensions: ${width}x${height}`);
        console.log(`Display rect:`, displayRect);

        // Check canvas element
        const canvas = display.querySelector('canvas');
        if (canvas) {
          console.log(`Canvas dimensions: ${canvas.width}x${canvas.height}`);
          console.log(`Canvas style: ${canvas.style.width}x${canvas.style.height}`);
          console.log(`Canvas client: ${canvas.clientWidth}x${canvas.clientHeight}`);
        }

        // Set resolution immediately on first layout
        if (connectionRef.current.requestResolution && width > 0 && height > 0) {
          console.log(`Setting initial resolution to ${width}x${height}`);
          connectionRef.current
            .requestResolution(width, height)
            .then(() => {
              console.log(
                `Initial resolution successfully set to ${width}x${height}`
              );
              lastWidthRef.current = width;
              lastHeightRef.current = height;

              // Log canvas after resolution change
              const canvas = display.querySelector('canvas');
              if (canvas) {
                console.log(`Canvas after resize: ${canvas.width}x${canvas.height}`);
              }
            })
            .catch((err: any) => {
              console.error("Failed to set initial resolution:", err);
            });
        }
      }
    }
  };

  const connect = (
    serverUrl: string,
    sessionId: string,
    authToken: string,
    httpExtraSearchParamsCb: () => URLSearchParams
  ) => {
    if (!window.dcv) {
      setError("DCV SDK not available");
      setLoading(false);
      return;
    }

    console.log("Connecting to DCV with:", { serverUrl, sessionId, authToken });

    window.dcv
      .connect({
        url: serverUrl,
        sessionId,
        authToken,
        divId: "dcv-display",
        baseUrl: `${window.location.origin}/dcv-sdk/dcvjs-umd`,
        callbacks: {
          httpExtraSearchParams: httpExtraSearchParamsCb,
          firstFrame: displayLayoutCallback,
          disconnect: (reason: any) => {
            console.log('DCV Disconnected:', reason);
            setStats(prev => ({ ...prev, connected: false }));

            // Clear stats interval on disconnect
            if (statsIntervalRef.current) {
              clearInterval(statsIntervalRef.current);
              statsIntervalRef.current = null;
            }

            // Only show error if not user-initiated
            if (reason.code !== 'USER_INITIATED') {
              const errorMsg = reason.message || 'Connection lost';
              setError(errorMsg);
              setLoading(false);
            }
          },
          featuresUpdate: (features: any) => {
            console.log('DCV Features updated:', features);
          },
        },
        enabledChannels: ['display', 'input'], // Only enable needed channels for better performance
        dynamicAudioTuning: true,
        enableWebCodecs: true,
        clientHiDpiScaling: false, // Disable HiDPI scaling to prevent canvas size issues
      })
      .then((conn: any) => {
        console.log("=== DCV Connection established successfully ===");
        console.log("Connection object:", conn);
        connectionRef.current = conn;
        setLoading(false);
        setStats(prev => ({ ...prev, connected: true }));
        setTimeout(() => resizeDisplay(), 500);

        // Start stats monitoring
        statsIntervalRef.current = setInterval(() => {
          updateStats();
        }, 5000); // Check every 5 seconds

        // Initial stats update
        setTimeout(() => updateStats(), 1000);
      })
      .catch((error: any) => {
        console.error("DCV Connection failed:", error);
        const errorMsg = error?.message || error?.toString() || "Failed to connect to DCV session";
        setError(errorMsg);
        setLoading(false);
      });
  };

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex flex-col p-4">
      <div
        className="w-full flex-1 bg-gray-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-white/10"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            <h2 className="text-white text-lg font-semibold">
              Live Browser Session
            </h2>
          </div>

          <div className="flex items-center gap-2">
            {/* Fullscreen Toggle */}
            {authenticated && (
              <button
                onClick={toggleFullscreen}
                className="text-white hover:bg-white/10 rounded-lg px-3 py-2 transition-colors text-sm"
                title={
                  isFullscreen
                    ? "Exit fullscreen (F11)"
                    : "Enter fullscreen (F11)"
                }
              >
                {isFullscreen ? "⛶ Exit Fullscreen" : "⛶ Fullscreen"}
              </button>
            )}

            <button
              onClick={handleClose}
              className="text-white hover:bg-white/10 rounded-lg px-4 py-2 transition-colors"
            >
              ✕ Close
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 relative overflow-hidden">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
              <div className="text-center">
                <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-white text-lg">
                  Connecting to browser session...
                </p>
                <p className="text-gray-400 text-sm mt-2">
                  Session ID: {mcpSessionId}
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 max-w-md">
                <h3 className="text-red-400 font-semibold mb-2">
                  Connection Error
                </h3>
                <p className="text-red-200 text-sm mb-4">{error}</p>
                <div className="flex gap-3">
                  {error.includes("Connection limit") && (
                    <button
                      onClick={() => {
                        setError(null);
                        setLoading(true);
                        setTimeout(() => initializeDCV(), 2000);
                      }}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                      Retry in 2s
                    </button>
                  )}
                  <button
                    onClick={handleClose}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
                  >
                    Close Viewer
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* DCV Display Container */}
          <div
            id="dcv-display"
            ref={dcvContainerRef}
            style={{
              display: loading || error ? "none" : "block",
              width: "100%",
              height: "100%",
              overflow: "hidden",
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
            }}
          />
        </div>

        {/* Status Bar */}
        {authenticated && (
          <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between text-xs">
            <div className="flex gap-6">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">FPS:</span>
                <span
                  className={`font-mono font-semibold ${
                    stats.fps > 25
                      ? "text-green-400"
                      : stats.fps > 15
                      ? "text-yellow-400"
                      : "text-red-400"
                  }`}
                >
                  {stats.fps.toFixed(0)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-gray-400">Latency:</span>
                <span
                  className={`font-mono font-semibold ${
                    stats.latency < 50
                      ? "text-green-400"
                      : stats.latency < 100
                      ? "text-yellow-400"
                      : "text-red-400"
                  }`}
                >
                  {stats.latency.toFixed(0)}ms
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-gray-400">Traffic:</span>
                <span className="text-blue-400 font-mono font-semibold">
                  {stats.traffic > 0
                    ? stats.traffic > 1000000
                      ? `${(stats.traffic / 1000000).toFixed(1)} Mbps`
                      : `${(stats.traffic / 1000).toFixed(0)} Kbps`
                    : stats.peakTraffic > 0
                    ? `Peak: ${stats.peakTraffic > 1000000
                        ? `${(stats.peakTraffic / 1000000).toFixed(1)} Mbps`
                        : `${(stats.peakTraffic / 1000).toFixed(0)} Kbps`}`
                    : '0 bps'}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-gray-400">Channels:</span>
                <span className="text-purple-400 font-mono font-semibold">
                  {stats.openedChannels}/{stats.currentChannels}
                </span>
              </div>

              {stats.channelErrors > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">Errors:</span>
                  <span className="text-red-400 font-mono font-semibold">
                    {stats.channelErrors}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  stats.connected ? "bg-green-400" : "bg-red-400"
                }`}
              ></div>
              <span className="text-gray-400">
                {stats.connected ? "Connected" : "Disconnected"}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
