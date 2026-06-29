import apiClient from './client'
import type { User, AuthTokens, LoginCredentials, RegisterCredentials } from '@/types'

export const authApi = {
  login: (credentials: LoginCredentials) =>
    apiClient.post<AuthTokens>('/auth/login/', credentials).then((r) => r.data),

  register: (credentials: RegisterCredentials) =>
    apiClient.post<AuthTokens>('/auth/register/', credentials).then((r) => r.data),

  refresh: (refreshToken: string) =>
    apiClient.post<AuthTokens>('/auth/refresh/', { refresh_token: refreshToken }).then((r) => r.data),

  logout: () =>
    apiClient.post('/auth/logout/').then((r) => r.data),

  me: () =>
    apiClient.get<User>('/auth/me/').then((r) => r.data),

  // OAuth login (Google/Apple) — backend expects { id_token }
  oauth: (provider: 'google' | 'apple', idToken: string) =>
    apiClient
      .post<AuthTokens>(`/auth/oauth/${provider}/`, {
        id_token: idToken,
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
