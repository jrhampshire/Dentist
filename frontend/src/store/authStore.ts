import { create } from 'zustand'
import type { User, AuthTokens, RegisterCredentials } from '@/types'
import { authApi } from '@/api/auth'

interface AuthState {
  // State
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (credentials: { email: string; password: string }) => Promise<void>
  oauthLogin: (provider: 'google' | 'apple', idToken: string) => Promise<void>
  register: (credentials: RegisterCredentials) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
  fetchMe: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null })
    try {
      const tokens: AuthTokens = await authApi.login(credentials)

      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)

      set({
        user: tokens.user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Error al iniciar sesión',
      })
      throw error
    }
  },

  oauthLogin: async (provider, idToken) => {
    set({ isLoading: true, error: null })
    try {
      const tokens: AuthTokens = await authApi.oauth(provider, idToken)

      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)

      set({
        user: tokens.user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Error al iniciar sesión con OAuth',
      })
      throw error
    }
  },

  register: async (credentials) => {
    set({ isLoading: true, error: null })
    try {
      const tokens: AuthTokens = await authApi.register(credentials)

      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)

      set({
        user: tokens.user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Error al registrar',
      })
      throw error
    }
  },

  logout: async () => {
    try {
      await authApi.logout()
    } catch {
      // Logout may fail if token is expired — still clear local state
    }

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')

    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  },

  refresh: async () => {
    const refreshToken = get().refreshToken
    if (!refreshToken) {
      get().logout()
      return
    }

    try {
      const tokens: AuthTokens = await authApi.refresh(refreshToken)

      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)

      set({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        user: tokens.user,
      })
    } catch {
      get().logout()
    }
  },

  fetchMe: async () => {
    set({ isLoading: true })
    try {
      const user = await authApi.me()
      set({ user, isAuthenticated: true, isLoading: false })
    } catch {
      set({ isLoading: false, isAuthenticated: false, user: null })
    }
  },

  clearError: () => set({ error: null }),
}))
