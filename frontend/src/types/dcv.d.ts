// Type declarations for Amazon DCV Web SDK

declare module 'dcv' {
  export enum LogLevel {
    TRACE = 0,
    DEBUG = 1,
    INFO = 2,
    WARN = 3,
    ERROR = 4,
    FATAL = 5,
  }

  export interface AuthenticationCallbacks {
    promptCredentials?: () => { username: string; password: string } | null;
    error?: (auth: unknown, error: unknown) => void;
    success?: (auth: unknown, result: AuthResult[]) => void;
    httpExtraSearchParams?: (method: string, url: string, body: unknown) => URLSearchParams;
  }

  export interface AuthResult {
    sessionId: string;
    authToken: string;
  }

  export interface ConnectionOptions {
    url: string;
    sessionId: string;
    authToken: string;
    divId: string;
    baseUrl: string;
    callbacks?: {
      httpExtraSearchParams?: (method: string, url: string, body: unknown) => URLSearchParams;
      displayLayout?: (serverWidth: number, serverHeight: number, heads: unknown[]) => void;
    };
  }

  export interface Connection {
    disconnect: () => void;
    close: () => void;
    setResolution: (width: number, height: number) => Promise<void>;
  }

  export function setLogLevel(level: LogLevel): void;
  export function authenticate(url: string, callbacks: AuthenticationCallbacks): void;
  export function connect(options: ConnectionOptions): Promise<Connection>;

  const dcv: {
    LogLevel: typeof LogLevel;
    setLogLevel: typeof setLogLevel;
    authenticate: typeof authenticate;
    connect: typeof connect;
  };

  export default dcv;
}

// Global window extensions
declare global {
  interface Window {
    dcv: {
      LogLevel: {
        TRACE: number;
        DEBUG: number;
        INFO: number;
        WARN: number;
        ERROR: number;
        FATAL: number;
      };
      setLogLevel: (level: number) => void;
      authenticate: (url: string, callbacks: {
        promptCredentials?: () => { username: string; password: string } | null;
        error?: (auth: unknown, error: unknown) => void;
        success?: (auth: unknown, result: Array<{ sessionId: string; authToken: string }>) => void;
        httpExtraSearchParams?: (method: string, url: string, body: unknown) => URLSearchParams;
      }) => void;
      connect: (options: {
        url: string;
        sessionId: string;
        authToken: string;
        divId: string;
        baseUrl: string;
        callbacks?: {
          httpExtraSearchParams?: (method: string, url: string, body: unknown) => URLSearchParams;
          displayLayout?: (serverWidth: number, serverHeight: number, heads: unknown[]) => void;
        };
      }) => Promise<{
        disconnect: () => void;
        close: () => void;
        setResolution: (width: number, height: number) => Promise<void>;
      }>;
    };
    DCVViewer: {
      DCVViewer: React.ComponentType<{
        ref?: React.Ref<unknown>;
        dcvUrl: string;
        sessionId: string;
        authToken: string;
        onConnected?: () => void;
        onDisconnected?: (reason: unknown) => void;
        onError?: (error: unknown) => void;
      }>;
    };
    React: typeof import('react');
    ReactDOM: typeof import('react-dom');
  }
}

export {};
