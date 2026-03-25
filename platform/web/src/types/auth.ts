export interface User {
  id: string
  username: string
  email: string
  full_name?: string
  avatar_url?: string
  bio?: string
  role: 'admin' | 'developer' | 'analyst' | 'guest'
  is_active: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  full_name?: string
}

export interface Token {
  access_token: string
  token_type: string
  refresh_token?: string
  expires_in: number
}

export interface Permission {
  name: string
  description?: string
  resource: string
  action: string
}

export interface Role {
  name: string
  description?: string
  permissions: Permission[];
}

export interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  permissions: string[]
}

export interface OAuthProvider {
  name: string
  display_name: string
  icon: string
}
