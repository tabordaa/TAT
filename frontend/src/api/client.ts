import axios from 'axios'

// Single configured HTTP client for the whole app.
export const api = axios.create({
  baseURL: '/api',
  // Send and accept the HttpOnly auth cookie. The token itself is NEVER
  // touched by JavaScript (no localStorage / sessionStorage).
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})
