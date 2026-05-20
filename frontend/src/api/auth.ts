import apiClient from './client'
import type { User, AuthTokens, LoginCredentials } from '@/types'

export const authApi = {
  login: (credentials: LoginCredentials) =>
    apiClient.post<AuthTokens>('/auth/login/', credentials).then((r) => r.data),

  refresh: (refreshToken: string) =>
    apiClient.post<AuthTokens>('/auth/refresh/', { refresh_token: refreshToken }).then((r) => r.data),

  logout: () =>
    apiClient.post('/auth/logout/').then((r) => r.data),

  me: () =>
    apiClient.get<User>('/auth/me/').then((r) => r.data),

  // OAuth login (Google/Apple)
  oauth: (provider: 'google' | 'apple', code: string, codeVerifier: string) =>
    apiClient
      .post<AuthTokens>(`/auth/oauth/${provider}/`, {
        code,
        code_verifier: codeVerifier,
      })
      .then((r) => r.data),

  // Admin: invite user
  inviteUser: (data: { email: string; role: string }) =>
    apiClient.post<User>('/auth/users/invite/', data).then((r) => r.data),

  // Admin: update user
  updateUser: (id: string, data: Partial<User>) =>
    apiClient.patch<User>(`/auth/users/${id}/`, data).then((r) => r.data),

  // Admin: deactivate user
  deactivateUser: (id: string) =>
    apiClient.delete(`/auth/users/${id}/`).then((r) => r.data),

  // Admin: list users
  listUsers: (params?: { page?: number; role?: string }) =>
    apiClient.get<{ results: User[]; count: number }>('/auth/users/', { params }).then((r) => r.data),
}
