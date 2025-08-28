import React, { useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import toast from 'react-hot-toast'

export default function LoginForm() {
  const { login, isLoading, error } = useAuth()
  const [formData, setFormData] = useState({
    email: 'demo@velvet.ai',
    password: 'demo123'
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      await login(formData.email, formData.password)
      toast.success('¡Bienvenido a Velvet RAG!')
    } catch (error) {
      toast.error('Error al iniciar sesión')
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  return (
    <div>
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Iniciar Sesión
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Accede a tu cuenta de Velvet RAG
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Correo Electrónico
          </label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleInputChange}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-velvet-500 focus:border-velvet-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Contraseña
          </label>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleInputChange}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-velvet-500 focus:border-velvet-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
        </button>
      </form>

      <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="text-sm">
          <p className="font-medium text-blue-800">Credenciales de demo:</p>
          <p className="text-blue-600">Email: demo@velvet.ai</p>
          <p className="text-blue-600">Password: demo123</p>
        </div>
      </div>
    </div>
  )
}
