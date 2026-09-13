import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, clearToken, getToken, setToken } from '../lib/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await api.me()
      setUser(me)
    } catch {
      clearToken()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadUser()
  }, [loadUser])

  const applyToken = useCallback(async (result) => {
    setToken(result.access_token)
    try {
      const me = await api.me()
      setUser(me)
    } catch {
      clearToken()
      setUser(null)
      throw new Error('Failed to load user profile after login')
    }
  }, [])

  const login = useCallback(
    async (email, password) => {
      await applyToken(await api.login({ email, password }))
    },
    [applyToken],
  )

  const signup = useCallback(
    async (email, password, fullName) => {
      await applyToken(await api.signup({ email, password, full_name: fullName }))
    },
    [applyToken],
  )

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, signup, logout, refresh: loadUser }),
    [user, loading, login, signup, logout, loadUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}