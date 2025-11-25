import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { apiClient } from '../services/apiClient'

const AuthContext = createContext(null)
const STORAGE_KEY = 'toefl-prep-auth'

const getStoredAuth = () => {
  if (typeof window === 'undefined') {
    return { user: null, token: null }
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : { user: null, token: null }
  } catch (error) {
    console.warn('Failed to read auth state from storage', error)
    return { user: null, token: null }
  }
}

export const AuthProvider = ({ children }) => {
  const [{ user, token }, setAuthState] = useState(getStoredAuth)
  const [isAuthenticating, setIsAuthenticating] = useState(false)

  const persistState = useCallback((nextState) => {
    if (typeof window === 'undefined') {
      setAuthState(nextState)
      return
    }

    setAuthState(nextState)
    if (!nextState?.token) {
      window.localStorage.removeItem(STORAGE_KEY)
      return
    }

    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState))
  }, [])

  const authenticate = useCallback(
    async (action, payload) => {
      setIsAuthenticating(true)
      try {
        const response =
          action === 'signup'
            ? await apiClient.signup(payload)
            : await apiClient.login(payload)

        const nextState = {
          user: response?.user ?? null,
          token: response?.token ?? null,
        }

        persistState(nextState)
        return response
      } finally {
        setIsAuthenticating(false)
      }
    },
    [persistState],
  )

  const signup = useCallback(
    (formValues) => authenticate('signup', formValues),
    [authenticate],
  )

  const login = useCallback(
    (formValues) => authenticate('login', formValues),
    [authenticate],
  )

  const logout = useCallback(async () => {
    if (token) {
      try {
        await apiClient.logout(token)
      } catch (error) {
        console.warn('Logout request failed', error)
      }
    }

    persistState({ user: null, token: null })
  }, [persistState, token])

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token),
      isAuthenticating,
      signup,
      login,
      logout,
    }),
    [user, token, isAuthenticating, signup, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return context
}

