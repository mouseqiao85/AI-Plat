import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, LoginRequest, RegisterRequest } from '../types/auth'
import { authService, setTokens, clearTokens, getAccessToken } from '../services/authApi'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  permissions: string[]
  
  login: (data: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => Promise<void>
  loadUser: () => Promise<void>
  updateUser: (data: Partial<User>) => Promise<void>
  checkPermission: (permission: string) => boolean
  hasRole: (role: string) => boolean
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: getAccessToken(),
      isAuthenticated: false,
      isLoading: false,
      permissions: [],

      login: async (data: LoginRequest) => {
        set({ isLoading: true })
        try {
          const token = await authService.login(data)
          setTokens(token)
          
          const user = await authService.getCurrentUser()
          const permissions = await authService.getUserPermissions(user.id)
          
          set({
            user,
            token: token.access_token,
            isAuthenticated: true,
            isLoading: false,
            permissions,
          })
        } catch (error) {
          set({ isLoading: false, isAuthenticated: false })
          throw error
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true })
        try {
          await authService.register(data)
          set({ isLoading: false })
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: async () => {
        try {
          await authService.logout()
        } catch {
        } finally {
          clearTokens()
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            permissions: [],
          })
        }
      },

      loadUser: async () => {
        const token = getAccessToken()
        if (!token) {
          set({ isLoading: false, isAuthenticated: false, user: null, permissions: [] })
          return
        }

        set({ isLoading: true })
        try {
          const user = await authService.getCurrentUser()
          const permissions = await authService.getUserPermissions(user.id)
          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
            permissions,
          })
        } catch {
          clearTokens()
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            permissions: [],
          })
        }
      },

      updateUser: async (data: Partial<User>) => {
        const updatedUser = await authService.updateCurrentUser(data)
        set({ user: updatedUser })
      },

      checkPermission: (permission: string) => {
        const { permissions, user } = get()
        if (user?.role === 'admin') return true
        return permissions.includes(permission) || permissions.includes('*')
      },

      hasRole: (role: string) => {
        const { user } = get()
        if (!user) return false
        
        const roleHierarchy = {
          admin: ['admin', 'developer', 'analyst', 'guest'],
          developer: ['developer', 'analyst', 'guest'],
          analyst: ['analyst', 'guest'],
          guest: ['guest'],
        }
        
        return roleHierarchy[user.role as keyof typeof roleHierarchy]?.includes(role) ?? false
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

export const useUser = () => useAuthStore((state) => state.user)
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated)
export const useIsLoading = () => useAuthStore((state) => state.isLoading)
export const usePermissions = () => useAuthStore((state) => state.permissions)
export const useHasRole = (role: string) => useAuthStore((state) => state.hasRole(role))
export const useHasPermission = (permission: string) => 
  useAuthStore((state) => state.checkPermission(permission))
