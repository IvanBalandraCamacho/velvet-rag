from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import Optional, List
import logging

# Importar servicios
from services.auth_service import AuthService
from services.chat_service import ChatService
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.file_processor import FileProcessor
from services.bcrp_service import BCRPService
from models.schemas import (
    ChatMessage, ChatResponse, UserProfile, 
    FileUploadResponse, BCRPDataRequest
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar servicios globales
auth_service = AuthService()
chat_service = ChatService()
llm_service = LLMService()
rag_service = RAGService()
file_processor = FileProcessor()
bcrp_service = BCRPService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Contexto de vida de la aplicación"""
    # Startup
    logger.info("🚀 Iniciando Velvet RAG Backend...")
    await llm_service.initialize()
    await rag_service.initialize()
    logger.info("✅ Servicios inicializados correctamente")
    
    yield
    
    # Shutdown  
    logger.info("🔄 Cerrando servicios...")
    await llm_service.close()
    await rag_service.close()
    logger.info("✅ Servicios cerrados correctamente")

# Crear aplicación FastAPI
app = FastAPI(
    title="Velvet RAG API",
    description="API para plataforma RAG con Velvet 14B y datos del BCRP",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtener usuario actual desde el token JWT"""
    try:
        user_id = await auth_service.verify_token(credentials.credentials)
        return user_id
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token inválido")

# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.post("/auth/login")
async def login(email: str, password: str):
    """Autenticar usuario"""
    try:
        token = await auth_service.authenticate(email, password)
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

@app.post("/auth/register")
async def register(email: str, password: str, name: str):
    """Registrar nuevo usuario"""
    try:
        user_id = await auth_service.create_user(email, password, name)
        token = await auth_service.generate_token(user_id)
        return {"access_token": token, "token_type": "bearer", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error al registrar usuario")

@app.get("/auth/profile")
async def get_profile(user_id: str = Depends(get_current_user)):
    """Obtener perfil del usuario"""
    try:
        profile = await auth_service.get_user_profile(user_id)
        return profile
    except Exception as e:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

@app.put("/auth/profile")
async def update_profile(profile: UserProfile, user_id: str = Depends(get_current_user)):
    """Actualizar perfil del usuario"""
    try:
        updated_profile = await auth_service.update_profile(user_id, profile)
        return updated_profile
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error al actualizar perfil")

# ==================== RUTAS DE CHAT ====================

@app.get("/chats")
async def get_chats(user_id: str = Depends(get_current_user)):
    """Obtener todos los chats del usuario"""
    try:
        chats = await chat_service.get_user_chats(user_id)
        return chats
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al obtener chats")

@app.post("/chats")
async def create_chat(title: str = "Nuevo Chat", user_id: str = Depends(get_current_user)):
    """Crear nuevo chat"""
    try:
        chat = await chat_service.create_chat(user_id, title)
        return chat
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al crear chat")

@app.get("/chats/{chat_id}")
async def get_chat(chat_id: str, user_id: str = Depends(get_current_user)):
    """Obtener chat específico con mensajes"""
    try:
        chat = await chat_service.get_chat_with_messages(chat_id, user_id)
        return chat
    except Exception as e:
        raise HTTPException(status_code=404, detail="Chat no encontrado")

@app.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: str,
    message: ChatMessage,
    user_id: str = Depends(get_current_user)
):
    """Enviar mensaje y obtener respuesta del LLM"""
    try:
        # Guardar mensaje del usuario
        user_msg = await chat_service.save_message(chat_id, user_id, message.content, "user")
        
        # Obtener contexto del chat
        chat_history = await chat_service.get_chat_history(chat_id, limit=10)
        
        # Procesamiento RAG si hay archivos subidos
        context = ""
        if message.file_ids:
            context = await rag_service.get_context_for_query(
                message.content, 
                file_ids=message.file_ids
            )
        
        # Generar respuesta con Velvet 14B
        response = await llm_service.generate_response(
            message.content,
            chat_history=chat_history,
            context=context,
            include_bcrp_data=message.include_bcrp_data
        )
        
        # Guardar respuesta del asistente
        assistant_msg = await chat_service.save_message(
            chat_id, user_id, response, "assistant"
        )
        
        return ChatResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
            context_used=bool(context)
        )
        
    except Exception as e:
        logger.error(f"Error al procesar mensaje: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al procesar mensaje")

# ==================== RUTAS DE ARCHIVOS ====================

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """Subir y procesar archivo (PDF, CSV, Excel)"""
    try:
        # Validar tipo de archivo
        allowed_types = ['application/pdf', 'text/csv', 
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="Tipo de archivo no soportado. Use PDF, CSV o Excel"
            )
        
        # Procesar archivo
        file_info = await file_processor.process_file(file, user_id)
        
        # Generar embeddings y almacenar en vector DB
        await rag_service.index_document(file_info)
        
        return FileUploadResponse(
            file_id=file_info['id'],
            filename=file_info['filename'],
            file_type=file_info['type'],
            size=file_info['size'],
            status="processed"
        )
        
    except Exception as e:
        logger.error(f"Error al procesar archivo: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al procesar archivo")

@app.get("/health")
async def health_check():
    """Health check de la aplicación"""
    try:
        # Verificar conexión con Velvet 14B
        llm_status = await llm_service.health_check()
        
        # Verificar vector database
        rag_status = await rag_service.health_check()
        
        return {
            "status": "healthy",
            "services": {
                "llm": llm_status,
                "rag": rag_status,
                "bcrp": await bcrp_service.health_check()
            }
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/")
async def root():
    """Ruta raíz"""
    return {
        "message": "🚀 Velvet RAG API",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
