#!/bin/bash

echo "🔧 Agregando servicios completos del backend..."

# Sobrescribir main.py con el completo
cat > backend/main.py << 'EOF'
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
EOF

# Crear schemas completos
cat > backend/models/schemas.py << 'EOF'
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ==================== ENUMS ====================

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class FileType(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"

class BCRPFormat(str, Enum):
    JSON = "json"
    XML = "xml"

# ==================== ESQUEMAS DE USUARIO ====================

class UserProfile(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = {}

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = 3600

# ==================== ESQUEMAS DE CHAT ====================

class ChatCreate(BaseModel):
    title: str = Field(default="Nuevo Chat", max_length=200)

class ChatUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)

class Chat(BaseModel):
    id: str
    title: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

class Message(BaseModel):
    id: str
    chat_id: str
    content: str
    role: MessageRole
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = {}

class ChatWithMessages(BaseModel):
    id: str
    title: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = []

# ==================== ESQUEMAS DE MENSAJES ====================

class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    file_ids: Optional[List[str]] = []
    include_bcrp_data: Optional[bool] = False
    context_preference: Optional[str] = "balanced"

class ChatResponse(BaseModel):
    user_message: Message
    assistant_message: Message
    context_used: bool = False
    sources: Optional[List[Dict[str, Any]]] = []
    bcrp_data_used: Optional[bool] = False
    processing_time: Optional[float] = None

# ==================== ESQUEMAS DE ARCHIVOS ====================

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    size: int
    status: str
    processing_time: Optional[float] = None

# ==================== ESQUEMAS DE DATOS BCRP ====================

class BCRPDataRequest(BaseModel):
    series: List[str] = Field(..., min_items=1, max_items=10)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    format: BCRPFormat = BCRPFormat.JSON
    language: str = Field(default="es")

class BCRPDataPoint(BaseModel):
    date: str
    value: float
    series_code: str

class BCRPResponse(BaseModel):
    series: List[str]
    data: List[BCRPDataPoint]
    metadata: Dict[str, Any]
    query_time: datetime
EOF

# Crear __init__.py files
touch backend/models/__init__.py
touch backend/services/__init__.py

echo "✅ Schemas y main.py completos agregados"

# AuthService completo
cat > backend/services/auth_service.py << 'EOF'
import jwt
import bcrypt
import asyncpg
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import uuid
from models.schemas import UserProfile

logger = logging.getLogger(__name__)

class AuthService:
    """Servicio de autenticación y gestión de usuarios"""
    
    def __init__(self):
        # Configuración JWT
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-this")
        self.algorithm = "HS256"
        self.token_expiry = timedelta(days=7)
        
        # Pool de conexiones a PostgreSQL
        self.db_pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Inicializar conexión a la base de datos"""
        try:
            database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/velvet_db")
            
            self.db_pool = await asyncpg.create_pool(
                database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            await self._create_tables()
            logger.info("✅ AuthService inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar AuthService: {str(e)}")
            raise e

    async def close(self):
        """Cerrar conexiones de base de datos"""
        if self.db_pool:
            await self.db_pool.close()

    async def _create_tables(self):
        """Crear tablas de usuarios si no existen"""
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            avatar_url TEXT,
            preferences JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE
        );
        
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(create_users_table)
            logger.info("Tablas de usuarios creadas/verificadas")

    def _hash_password(self, password: str) -> str:
        """Hash de contraseña usando bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verificar contraseña"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    def generate_token(self, user_id: str) -> str:
        """Generar token JWT"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + self.token_expiry,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    async def verify_token(self, token: str) -> str:
        """Verificar token JWT y devolver user_id"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            
            if not user_id:
                raise Exception("Token inválido: no contiene user_id")
            
            # Verificar que el usuario existe y está activo
            async with self.db_pool.acquire() as conn:
                user = await conn.fetchrow(
                    "SELECT id FROM users WHERE id = $1 AND is_active = TRUE",
                    user_id
                )
                
                if not user:
                    raise Exception("Usuario no encontrado o inactivo")
                
                return user_id
                
        except jwt.ExpiredSignatureError:
            raise Exception("Token expirado")
        except jwt.InvalidTokenError:
            raise Exception("Token inválido")
        except Exception as e:
            logger.error(f"Error verificando token: {str(e)}")
            raise Exception("Token inválido")

    async def create_user(self, email: str, password: str, name: str) -> str:
        """Crear nuevo usuario"""
        try:
            # Validar email único
            async with self.db_pool.acquire() as conn:
                existing_user = await conn.fetchrow(
                    "SELECT id FROM users WHERE email = $1", email.lower()
                )
                
                if existing_user:
                    raise Exception("El email ya está registrado")
                
                # Hash de la contraseña
                password_hash = self._hash_password(password)
                
                # Crear usuario
                user_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO users (id, email, password_hash, name, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, NOW(), NOW())
                """, user_id, email.lower(), password_hash, name)
                
                logger.info(f"Usuario creado: {email}")
                return user_id
                
        except Exception as e:
            logger.error(f"Error creando usuario: {str(e)}")
            raise Exception(f"Error al crear usuario: {str(e)}")

    async def authenticate(self, email: str, password: str) -> str:
        """Autenticar usuario y generar token"""
        try:
            async with self.db_pool.acquire() as conn:
                user = await conn.fetchrow("""
                    SELECT id, password_hash, is_active 
                    FROM users 
                    WHERE email = $1
                """, email.lower())
                
                if not user:
                    raise Exception("Credenciales inválidas")
                
                if not user['is_active']:
                    raise Exception("Cuenta desactivada")
                
                # Verificar contraseña
                if not self._verify_password(password, user['password_hash']):
                    raise Exception("Credenciales inválidas")
                
                # Actualizar último acceso
                await conn.execute(
                    "UPDATE users SET updated_at = NOW() WHERE id = $1",
                    user['id']
                )
                
                # Generar token
                token = self.generate_token(user['id'])
                logger.info(f"Usuario autenticado: {email}")
                
                return token
                
        except Exception as e:
            logger.error(f"Error en autenticación: {str(e)}")
            raise Exception("Error de autenticación")

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Obtener perfil del usuario"""
        try:
            async with self.db_pool.acquire() as conn:
                user = await conn.fetchrow("""
                    SELECT id, email, name, avatar_url, preferences, created_at, updated_at
                    FROM users 
                    WHERE id = $1 AND is_active = TRUE
                """, user_id)
                
                if not user:
                    raise Exception("Usuario no encontrado")
                
                return {
                    "id": user['id'],
                    "email": user['email'],
                    "name": user['name'],
                    "avatar_url": user['avatar_url'],
                    "preferences": user['preferences'] or {},
                    "created_at": user['created_at'].isoformat(),
                    "updated_at": user['updated_at'].isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo perfil: {str(e)}")
            raise Exception("Error al obtener perfil de usuario")

    async def update_profile(self, user_id: str, profile_data: UserProfile) -> Dict[str, Any]:
        """Actualizar perfil del usuario"""
        try:
            async with self.db_pool.acquire() as conn:
                # Verificar si el email está disponible (si se está cambiando)
                current_user = await conn.fetchrow(
                    "SELECT email FROM users WHERE id = $1", user_id
                )
                
                if not current_user:
                    raise Exception("Usuario no encontrado")
                
                # Si se cambia el email, verificar que no exista
                if profile_data.email.lower() != current_user['email']:
                    existing_email = await conn.fetchrow(
                        "SELECT id FROM users WHERE email = $1 AND id != $2",
                        profile_data.email.lower(), user_id
                    )
                    
                    if existing_email:
                        raise Exception("El email ya está en uso")
                
                # Actualizar perfil
                updated_user = await conn.fetchrow("""
                    UPDATE users SET 
                        email = $2,
                        name = $3,
                        avatar_url = $4,
                        preferences = $5,
                        updated_at = NOW()
                    WHERE id = $1 AND is_active = TRUE
                    RETURNING id, email, name, avatar_url, preferences, created_at, updated_at
                """, user_id, profile_data.email.lower(), profile_data.name, 
                    profile_data.avatar_url, profile_data.preferences or {})
                
                if not updated_user:
                    raise Exception("Error al actualizar perfil")
                
                logger.info(f"Perfil actualizado para usuario: {user_id}")
                
                return {
                    "id": updated_user['id'],
                    "email": updated_user['email'],
                    "name": updated_user['name'],
                    "avatar_url": updated_user['avatar_url'],
                    "preferences": updated_user['preferences'] or {},
                    "created_at": updated_user['created_at'].isoformat(),
                    "updated_at": updated_user['updated_at'].isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error actualizando perfil: {str(e)}")
            raise Exception(f"Error al actualizar perfil: {str(e)}")
EOF

echo "✅ AuthService completo agregado"
echo "🔧 Servicios básicos del backend listos"
echo ""
echo "📂 Archivos agregados:"
echo "├── backend/main.py (completo con todas las rutas)"
echo "├── backend/models/schemas.py (todos los modelos Pydantic)"  
echo "└── backend/services/auth_service.py (servicio completo de auth)"
echo ""
echo "⏳ Faltan más servicios por agregar:"
echo "- chat_service.py"
echo "- llm_service.py"  
echo "- rag_service.py"
echo "- bcrp_service.py"
echo "- file_processor.py"
EOF
