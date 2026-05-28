/**
 * useAuth.js
 * Custom hook that manages authentication state across the app.
 * Reads/writes localStorage for the JWT token.
 * Exposes: user, token, login(), logout(), loading
 */

import { useState, useEffect, useCallback } from 'react'
import { authAPI } from '../api/client'

export function useAuth() {
  const [user, setUser]       = useState(null)
  const [token, setToken]     = useState(() => localStorage.getItem('access_token'))
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  // On mount (or when token changes) — verify token and load user profile
  useEffect(() => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    setLoading(true)
    authAPI.me()
      .then(res => {
        setUser(res.data)
        setError(null)
      })
      .catch(() => {
        // Token is invalid or expired — clear everything
        localStorage.removeItem('access_token')
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [token])

  /**
   * login(email, password)
   * Calls /auth/login, stores token, sets user.
   * Returns the user object on success, throws on failure.
   */
  const login = useCallback(async (email, password) => {
    setLoading(true)
    setError(null)
    try {
      const res = await authAPI.login(email, password)
      const { access_token, user: userData } = res.data
      localStorage.setItem('access_token', access_token)
      setToken(access_token)
      setUser(userData)
      return userData
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed. Check your credentials.'
      setError(msg)
      throw new Error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * register(email, username, password, role)
   * Calls /auth/register, stores token, sets user.
   */
  const register = useCallback(async (email, username, password, role = 'customer') => {
    setLoading(true)
    setError(null)
    try {
      const res = await authAPI.register({ email, username, password, role })
      const { access_token, user: userData } = res.data
      localStorage.setItem('access_token', access_token)
      setToken(access_token)
      setUser(userData)
      return userData
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed.'
      setError(msg)
      throw new Error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * logout()
   * Clears token + user from memory and localStorage.
   */
  const logout = useCallback(() => {
    authAPI.logout().catch(() => {})
    localStorage.removeItem('access_token')
    sessionStorage.clear()
    localStorage.removeItem('session_id')
    localStorage.removeItem('conversation_id')
    setToken(null)
    setUser(null)
    setError(null)
  }, [])

  // Role helper booleans
  const isAdmin   = user?.role === 'admin'
  const isAgent   = user?.role === 'agent' || user?.role === 'admin'
  const isCustomer = user?.role === 'customer'

  return {
    user,
    token,
    loading,
    error,
    login,
    register,
    logout,
    isAdmin,
    isAgent,
    isCustomer,
    isAuthenticated: !!user,
  }
}
