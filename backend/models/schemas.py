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
