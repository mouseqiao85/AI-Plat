import axios from 'axios'
import type { User, LoginRequest, RegisterRequest, Token, OAuthProvider } from '../types/auth'

const API_BASE_URL = '/auth'

const authApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

authApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

authApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/refresh`, {
            refresh_token: refreshToken,
          })
          const { access_token } = response.data
          localStorage.setItem('access_token', access_token)
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return authApi(originalRequest)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export const authService = {
  login: async (data: LoginRequest): Promise<Token> => {
    const response = await authApi.post<Token>('/login', data)
    return response.data
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response = await authApi.post<User>('/register', data)
    return response.data
  },

  logout: async (): Promise<void> => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      await authApi.post('/logout', { refresh_token: refreshToken })
    }
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await authApi.get<User>('/me')
    return response.data
  },

  updateCurrentUser: async (data: Partial<User>): Promise<User> => {
    const response = await authApi.put<User>('/me', data)
    return response.data
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await authApi.post('/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },

  refreshToken: async (refreshToken: string): Promise<Token> => {
    const response = await authApi.post<Token>('/refresh', { refresh_token: refreshToken })
    return response.data
  },

  getOAuthProviders: async (): Promise<OAuthProvider[]> => {
    const response = await authApi.get<{ providers: string[] }>('/oauth/providers')
    return response.data.providers.map((name) => ({
      name,
      display_name: name.charAt(0).toUpperCase() + name.slice(1),
      icon: name === 'google' ? 'google' : name === 'github' ? 'github' : 'login',
    }))
  },

  getOAuthAuthorizeUrl: async (provider: string): Promise<string> => {
    const response = await authApi.get<{ authorization_url: string }>(
      `/oauth/${provider}/authorize`
    )
    return response.data.authorization_url
  },

  getUserPermissions: async (userId: string): Promise<string[]> => {
    const response = await authApi.get<{ permissions: string[] }>(`/users/${userId}/permissions`)
    return response.data.permissions
  },

  validateToken: async (): Promise<boolean> => {
    try {
      await authApi.get('/validate-token')
      return true
    } catch {
      return false
    }
  },
}

export const setTokens = (token: Token) => {
  localStorage.setItem('access_token', token.access_token)
  if (token.refresh_token) {
    localStorage.setItem('refresh_token', token.refresh_token)
  }
}

export const clearTokens = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export const getAccessToken = (): string | null => {
  return localStorage.getItem('access_token')
}

export const getRefreshToken = (): string | null => {
  return localStorage.getItem('refresh_token')
}

export default authApi
