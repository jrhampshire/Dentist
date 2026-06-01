import { useAuthStore } from '@/store/authStore'

export function useAuth() {
  const {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    refresh,
    fetchMe,
    clearError,
  } = useAuthStore()

  const role = user?.role
  const clinicId = user?.clinic
  const userName = user ? `${user.first_name} ${user.last_name}` : ''

  // Role-based permission checks
  const hasPermission = (permission: string): boolean => {
    if (!user) return false
    if (user.role === 'admin') return true
    const permissions: Record<string, string[]> = {
      dentist: ['patients:read', 'patients:write', 'appointments:read', 'appointments:write', 'clinical_notes:read', 'clinical_notes:write'],
      recepcionista: ['patients:read', 'patients:write', 'appointments:read', 'appointments:write', 'invoices:read'],
    }
    return (permissions[user.role] || []).includes(permission)
  }

  const isAdmin = role === 'admin'
  const isDentist = role === 'dentist'
  const isRecepcionista = role === 'recepcionista'

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isLoading,
    error,
    role,
    clinicId,
    userName,
    login,
    register,
    logout,
    refresh,
    fetchMe,
    clearError,
    hasPermission,
    isAdmin,
    isDentist,
    isRecepcionista,
  }
}
