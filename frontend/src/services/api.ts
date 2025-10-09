import axios from 'axios';
import type { AuthResponse } from '../types/index.js';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth services
export const authService = {
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/auth/login', { username, password });
    return response.data;
  },

  register: async (username: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/auth/register', { username, password });
    return response.data;
  },
};

// Course services
export const courseService = {
  createSession: async () => {
    const response = await api.post('/course/create-session');
    return response.data;
  },

  navigateToCourse: async (url: string) => {
    const response = await api.post('/course/navigate', { url });
    return response.data;
  },

  scrapeCourse: async (url: string) => {
    const response = await api.post('/course/scrape-course', { url });
    return response.data;
  },

  analyzeContent: async (content: string, images?: string[]) => {
    const response = await api.post('/course/analyze-content', { content, images });
    return response.data;
  },

  buildKnowledgeBase: async (courses: any[]) => {
    const response = await api.post('/course/build-knowledge-base', courses);
    return response.data;
  },

  processCourseFull: async (url: string) => {
    const response = await api.post('/course/process-course-full', { url });
    return response.data;
  },

  continueAfterLogin: async (courseUrl: string) => {
    const response = await api.post('/course/continue-after-login', { course_url: courseUrl });
    return response.data;
  },
};

// File upload services
export const fileUploadService = {
  uploadSingle: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  uploadMultiple: async (files: File[]) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    
    const response = await api.post('/files/upload-multiple', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  processFiles: async (fileIds: string[], processingOptions?: any) => {
    const response = await api.post('/files/process-files', {
      file_ids: fileIds,
      user_id: 'current_user', // This would be extracted from token in real implementation
      processing_options: processingOptions,
    });
    return response.data;
  },

  processLinks: async (links: string[]) => {
    const response = await api.post('/files/process-links', {
      links,
      user_id: 'current_user', // This would be extracted from token in real implementation
    });
    return response.data;
  },

  processMixed: async (data: {
    courseUrl?: string;
    fileIds?: string[];
    directLinks?: string[];
    processingOptions?: any;
  }) => {
    const response = await api.post('/files/process-mixed', {
      course_url: data.courseUrl,
      file_ids: data.fileIds,
      direct_links: data.directLinks,
      user_id: 'current_user', // This would be extracted from token in real implementation
      processing_options: data.processingOptions,
    });
    return response.data;
  },

  validateLinks: async (links: string[]) => {
    const response = await api.post('/files/validate-links', {
      links,
      user_id: 'current_user', // This would be extracted from token in real implementation
    });
    return response.data;
  },

  getUserFiles: async () => {
    const response = await api.get('/files/files');
    return response.data;
  },

  deleteFile: async (fileId: string) => {
    const response = await api.delete(`/files/files/${fileId}`);
    return response.data;
  },
};

// Knowledge Base services
export const knowledgeBaseService = {
  create: async (name: string, fileIds: string[], description?: string) => {
    const response = await api.post('/knowledge-base/create', {
      name,
      file_ids: fileIds,
      description,
    });
    return response.data;
  },

  list: async () => {
    const response = await api.get('/knowledge-base/list');
    return response.data;
  },

  get: async (kbId: string) => {
    const response = await api.get(`/knowledge-base/${kbId}`);
    return response.data;
  },

  getStatus: async (kbId: string) => {
    const response = await api.get(`/knowledge-base/${kbId}/status`);
    return response.data;
  },

  startTraining: async (kbId: string) => {
    const response = await api.post('/knowledge-base/training/start', {
      knowledge_base_id: kbId,
    });
    return response.data;
  },

  answerQuestion: async (sessionId: string, answer: string) => {
    const response = await api.post('/knowledge-base/training/answer', {
      session_id: sessionId,
      answer,
    });
    return response.data;
  },

  getTrainingSession: async (sessionId: string) => {
    const response = await api.get(`/knowledge-base/training/${sessionId}`);
    return response.data;
  },

  endTrainingSession: async (sessionId: string) => {
    const response = await api.post(`/knowledge-base/training/${sessionId}/end`);
    return response.data;
  },

  delete: async (kbId: string) => {
    const response = await api.delete(`/knowledge-base/${kbId}`);
    return response.data;
  },

  // Training History endpoints
  getUserTrainingHistory: async () => {
    const response = await api.get('/knowledge-base/training/history/user');
    return response.data;
  },

  getKnowledgeBaseTrainingHistory: async (kbId: string) => {
    const response = await api.get(`/knowledge-base/${kbId}/training/history`);
    return response.data;
  },
};

export default api;
