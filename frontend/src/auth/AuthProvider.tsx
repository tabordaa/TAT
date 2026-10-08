import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import axios from 'axios'
import * as authApi from '../api/auth'
import { api } from '../api/client'
import type { LoginCredentials, User } from '../types/auth'
import { AuthContext, type AuthContextValue } from './AuthContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On first load, restore the session if the browser still has a valid cookie.
  useEffect(() => {
    let cancelled = false
    authApi
      .fetchCurrentUser()
      .then((currentUser) => {
        if (!cancelled) setUser(currentUser)
      })
      .catch(() => {
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Global 401 handling: if ANY request says "not authenticated" (token
  // expired or revoked by a logout elsewhere), drop the session. ProtectedRoute
  // then redirects to /login automatically.
  useEffect(() => {
    const interceptorId = api.interceptors.response.use(
      (response) => response,
      (error: unknown) => {
        const isAuthEndpoint =
          axios.isAxiosError(error) && (error.config?.url ?? '').startsWith('/auth/')
        if (axios.isAxiosError(error) && error.response?.status === 401 && !isAuthEndpoint) {
          setUser(null)
        }
        return Promise.reject(error)
      },
    )
    return () => {
      api.interceptors.response.eject(interceptorId)
    }
  }, [])

  const login = useCallback(async (credentials: LoginCredentials) => {
    const loggedUser = await authApi.login(credentials)
    setUser(loggedUser)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      // Clear local state even if the request fails.
      setUser(null)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, login, logout }),
    [user, isLoading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
