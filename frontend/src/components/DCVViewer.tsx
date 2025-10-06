import React, { useEffect, useRef, useState } from "react";
import axios from "axios";

interface DCVViewerProps {
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

export const DCVViewer: React.FC<DCVViewerProps> = ({
  sessionId,
  mcpSessionId,
  onClose,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const dcvContainerRef = useRef<HTMLDivElement>(null);
  const connectionRef = useRef<any>(null);
  const displayLayoutRequestedRef = useRef(false);

  const handleClose = () => {
    // Properly close the DCV connection before closing the viewer
    if (connectionRef.current) {
      try {
        console.log("Closing DCV connection");
        connectionRef.current.disconnect();
        connectionRef.current.close();
        connectionRef.current = null;
        console.log("DCV connection closed successfully");
      } catch (e) {
        console.error("Error closing DCV connection:", e);
      }
    }
    onClose();
  };

  const resizeDisplay = () => {
    const display = document.getElementById("dcv-display");
    if (display && connectionRef.current) {
      // Get the actual dimensions of the display element
      const displayRect = display.getBoundingClientRect();
      const width = Math.floor(displayRect.width);
      const height = Math.floor(displayRect.height);

      console.log(`Requesting resolution change to ${width}x${height}`);

      if (connectionRef.current.setResolution) {
        connectionRef.current
          .setResolution(width, height)
          .then(() => {
            console.log(`Resolution successfully set to ${width}x${height}`);
          })
          .catch((err: any) => {
            console.error("Failed to set resolution:", err);
          });
      } else {
        console.error("connection.setResolution is not available");
      }
    }
  };

  useEffect(() => {
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

    return () => {
      // Cleanup on unmount - properly close connection
      if (connectionRef.current) {
        try {
          console.log("Closing DCV connection on unmount");
          connectionRef.current.disconnect();
          connectionRef.current.close();
          connectionRef.current = null;
          console.log("DCV connection closed successfully");
        } catch (e) {
          console.error("Error closing DCV connection:", e);
        }
      }
      // Remove script on cleanup
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
      // Remove resize listener
      window.removeEventListener("resize", resizeDisplay);
    };
  }, []);

  const initializeDCV = async () => {
    try {
      // Get presigned URL from backend
      const token = localStorage.getItem("token");
      const response = await axios.post(
        "http://localhost:8000/api/v1/agent/get-dcv-url",
        {
          session_id: sessionId,
          mcp_session_id: mcpSessionId,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const { presignedUrl, sessionId: dcvSessionId } = response.data;

      if (!presignedUrl) {
        throw new Error("No presigned URL received");
      }

      console.log("DCV Presigned URL received:", presignedUrl);

      // Store presigned URL for callbacks
      const presignedUrlRef = { current: presignedUrl };

      // Callback to extract and preserve query parameters from presigned URL
      const httpExtraSearchParamsCb = (
        method: string,
        url: string,
        body: any
      ) => {
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
          error: (auth: any, error: any) => {
            console.error("DCV Authentication error:", error);
            const errorMsg =
              error?.message || error?.toString() || "Unknown error";
          },
          success: (auth: any, result: any[]) => {
            console.log("DCV Authentication successful", result);
            const { sessionId: dcvSid, authToken } = result[0];
            setAuthenticated(true);
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
        throw new Error("DCV SDK not loaded");
      }
    } catch (err: any) {
      console.error("DCV initialization error:", err);
      setError(err.message || "Failed to initialize DCV viewer");
      setLoading(false);
    }
  };

  const displayLayoutCallback = (
    serverWidth: number,
    serverHeight: number,
    _heads: any[]
  ) => {
    console.log(`Display layout callback: ${serverWidth}x${serverHeight}`);

    const display = document.getElementById("dcv-display");
    if (display && connectionRef.current) {
      // Get the actual dimensions of the display element
      const displayRect = display.getBoundingClientRect();
      const width = Math.floor(displayRect.width);
      const height = Math.floor(displayRect.height);

      console.log(`Container dimensions: ${width}x${height}`);

      // Set resolution immediately in callback
      if (connectionRef.current.setResolution && width > 0 && height > 0) {
        console.log(`Setting resolution to ${width}x${height}`);
        connectionRef.current
          .setResolution(width, height)
          .then(() => {
            console.log(`Resolution successfully set to ${width}x${height}`);
          })
          .catch((err: any) => {
            console.error("Failed to set resolution:", err);
          });
      }
    }
  };

  const connect = (
    serverUrl: string,
    sessionId: string,
    authToken: string,
    httpExtraSearchParamsCb: (
      method: string,
      url: string,
      body: any
    ) => URLSearchParams
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
          displayLayout: displayLayoutCallback,
        },
      })
      .then((conn: any) => {
        console.log("DCV Connection established successfully");
        connectionRef.current = conn;
        setLoading(false);
        setTimeout(() => resizeDisplay(), 500);
      })
      .catch((error: any) => {
        console.error("DCV Connection failed:", error);
        // setError(`Connection failed: ${error?.message || 'Unknown error'}`);
        // setLoading(false);
      });
  };

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-8 pt-16">
      <div
        className="w-full max-w-7xl bg-gray-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-white/10"
        style={{ height: "calc(100vh - 8rem)" }}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            <h2 className="text-white text-lg font-semibold">
              Live Browser Session
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="text-white hover:bg-white/10 rounded-lg px-4 py-2 transition-colors"
          >
            ✕ Close
          </button>
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
            className="w-full h-full"
            style={{
              display: loading || error ? "none" : "block",
              overflow: "hidden",
              position: "relative",
              margin: 0,
              padding: 0,
            }}
          />
        </div>

        {/* Status Bar */}
        {authenticated && !error && (
          <div className="bg-gray-800 border-t border-gray-700 p-2 text-center flex-shrink-0">
            <p className="text-green-400 text-sm">
              🟢 Connected • Session: {mcpSessionId}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
