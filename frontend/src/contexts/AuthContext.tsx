import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

// Types
interface User {
  id: string
  name: string
  email: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  error: string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initialize auth state
  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      // In a real app, validate token with backend
      setUser({ id: '1', name: 'Demo User', email: 'demo@velvet.ai' })
    }
    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    try {
      setError(null)
      setIsLoading(true)

      // Simple demo authentication
      if (email === 'demo@velvet.ai' && password === 'demo123') {
        const demoUser = { id: '1', name: 'Demo User', email: 'demo@velvet.ai' }
        localStorage.setItem('auth_token', 'demo-token')
        setUser(demoUser)
      } else {
        throw new Error('Credenciales inválidas')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de login')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setUser(null)
    setError(null)
  }

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    error,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
