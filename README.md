# velvet-rag
Velvet RAG - AI Assistant for Peruvian Economic Analysis with BCRP integration
# 🚀 Velvet RAG - Plataforma de IA para Análisis Económico del Perú

Una plataforma RAG (Retrieval Augmented Generation) completa que utiliza el modelo **Velvet 14B** para análisis de datos económicos del Perú, integrada con la API del BCRP.

## ✨ Características

- 🤖 **AI Avanzada**: Velvet 14B (14B parámetros)
- 📊 **Datos del BCRP**: Integración en tiempo real con API del Banco Central
- 📁 **Procesamiento de Archivos**: Soporte para PDF, CSV, Excel
- 🔍 **RAG Pipeline**: Búsqueda semántica y generación contextual
- 💬 **Chat Interface**: UI moderna estilo ChatGPT/Claude
- 🌙 **Modo Oscuro**: Tema blanco/rojo/negro personalizable
- 🔐 **Autenticación**: Sistema completo de usuarios
- 📱 **Responsive**: Adaptado para escritorio y móvil

## 🚀 Quick Start

```bash
# Clonar repositorio
git https://github.com/IvanBalandraCamacho/velvet-rag.git
cd velvet-rag

# Configurar environment
cp .env.example .env

# Iniciar servicios
docker-compose up --build -d

# Acceder a la aplicación
open http://localhost:3000
