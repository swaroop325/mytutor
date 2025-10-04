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
