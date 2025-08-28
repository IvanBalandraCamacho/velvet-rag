import React, { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

// Components
import ChatInterface from './components/chat/ChatInterface'
import LoginForm from './components/auth/LoginForm'
import { AuthProvider, useAuth } from './contexts/AuthContext'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <AppContent />
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  )
}

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-velvet-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-velvet-50 to-white dark:from-gray-900 dark:to-gray-800">
        <div className="flex items-center justify-center min-h-screen px-4">
          <div className="w-full max-w-md">
            {/* Logo */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center space-x-2">
                <div className="w-10 h-10 bg-velvet-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-xl">V</span>
                </div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  Velvet RAG
                </h1>
              </div>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                Tu asistente de IA para análisis económico del Perú
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 border border-gray-200 dark:border-gray-700">
              <LoginForm />
            </div>
          </div>
        </div>
        <Toaster position="top-right" />
      </div>
    )
  }

  return (
    <div className="h-screen bg-white dark:bg-gray-900">
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatInterface />} />
        <Route path="/chat/:chatId" element={<ChatInterface />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
      
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'var(--tw-color-white)',
            color: 'var(--tw-color-gray-900)',
          },
        }}
      />
    </div>
  )
}

export default App
