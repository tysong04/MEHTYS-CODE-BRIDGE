export interface UserProfile {
  id: number;
  name: string;
  email: string;
  created_at: string;
  last_login_at?: string | null;
}

export interface AuthResponse {
  user: UserProfile;
  token: string;
  token_type: string;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
}

export interface LoginData {
  email: string;
  password: string;
}
