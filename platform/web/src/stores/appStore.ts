import { create } from 'zustand'

interface AppState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  currentProject: string | null
  setCurrentProject: (project: string | null) => void
  notifications: Array<{ id: string; message: string; type: 'info' | 'success' | 'error' }>
  addNotification: (message: string, type: 'info' | 'success' | 'error') => void
  removeNotification: (id: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),
  notifications: [],
  addNotification: (message, type) => set((state) => ({
    notifications: [
      ...state.notifications,
      { id: Date.now().toString(), message, type }
    ]
  })),
  removeNotification: (id) => set((state) => ({
    notifications: state.notifications.filter((n) => n.id !== id)
  })),
}))
