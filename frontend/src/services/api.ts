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

export default api;
