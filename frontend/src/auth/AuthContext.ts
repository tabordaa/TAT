import { createContext } from 'react'
import type { LoginCredentials, User } from '../types/auth'

export interface AuthContextValue {
  user: User | null
  /** true while we ask the server whether a session already exists */
  isLoading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
