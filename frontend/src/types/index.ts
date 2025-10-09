export interface User {
  id: string;
  username: string;
}

export interface AuthResponse {
  message: string;
  token: string;
  user: User;
}

export interface CourseContent {
  title: string;
  sections: string[];
  topics: string[];
  summary: string;
}

export interface BrowserSession {
  session_id: string;
  dcv_url: string;
  status: string;
}

export interface TrainingQuestion {
  question: string;
  options: {
    A: string;
    B: string;
    C: string;
    D: string;
  };
  correct_answer: string;
  explanation: string;
  difficulty: string;
  topic: string;
  learning_objective: string;
}

export interface TrainingSession {
  id: string;
  knowledge_base_id: string;
  user_id: string;
  created_at: string;
  status: 'active' | 'completed';
  current_question?: TrainingQuestion;
  questions_answered: number;
  correct_answers: number;
  score: number;
}

export interface TrainingHistoryStats {
  total_sessions: number;
  total_questions_answered: number;
  total_correct_answers: number;
  average_score: number;
  best_score: number;
  recent_sessions: TrainingSession[];
}
