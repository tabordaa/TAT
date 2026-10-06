import { api } from './client'
import type { LoginCredentials, User } from '../types/auth'

export async function login(credentials: LoginCredentials): Promise<User> {
  const { data } = await api.post<User>('/auth/login', credentials)
  return data
}

// The frontend cannot read the HttpOnly cookie, so it asks the server
// "who am I?" to restore the session after a page reload.
export async function fetchCurrentUser(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}
