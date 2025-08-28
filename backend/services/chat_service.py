import asyncpg
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import uuid
import json

logger = logging.getLogger(__name__)

class ChatService:
    """Servicio para gestión de chats y mensajes"""
    
    def __init__(self):
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
            logger.info("✅ ChatService inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar ChatService: {str(e)}")
            raise e

    async def close(self):
        """Cerrar conexiones de base de datos"""
        if self.db_pool:
            await self.db_pool.close()

    async def _create_tables(self):
        """Crear tablas de chats y mensajes si no existen"""
        create_tables_sql = """
        -- Tabla de chats
        CREATE TABLE IF NOT EXISTS chats (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(500) NOT NULL,
            user_id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            is_deleted BOOLEAN DEFAULT FALSE,
            metadata JSONB DEFAULT '{}'
        );

        -- Tabla de mensajes
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chat_id UUID NOT NULL,
            content TEXT NOT NULL,
            role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}',
            is_deleted BOOLEAN DEFAULT FALSE
        );

        -- Índices para optimizar consultas
        CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
        CREATE INDEX IF NOT EXISTS idx_chats_created_at ON chats(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_chats_not_deleted ON chats(is_deleted) WHERE is_deleted = FALSE;
        
        CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_not_deleted ON messages(is_deleted) WHERE is_deleted = FALSE;
        
        -- Foreign key constraints
        ALTER TABLE messages ADD CONSTRAINT IF NOT EXISTS fk_messages_chat_id 
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE;
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(create_tables_sql)
            logger.info("Tablas de chats y mensajes creadas/verificadas")

    async def create_chat(self, user_id: str, title: str = "Nuevo Chat") -> Dict[str, Any]:
        """Crear nuevo chat"""
        try:
            chat_id = str(uuid.uuid4())
            
            async with self.db_pool.acquire() as conn:
                chat = await conn.fetchrow("""
                    INSERT INTO chats (id, title, user_id, created_at, updated_at)
                    VALUES ($1, $2, $3, NOW(), NOW())
                    RETURNING id, title, user_id, created_at, updated_at
                """, chat_id, title, user_id)
                
                logger.info(f"Chat creado: {chat_id} para usuario {user_id}")
                
                return {
                    "id": str(chat['id']),
                    "title": chat['title'],
                    "user_id": str(chat['user_id']),
                    "created_at": chat['created_at'].isoformat(),
                    "updated_at": chat['updated_at'].isoformat(),
                    "message_count": 0
                }
                
        except Exception as e:
            logger.error(f"Error creando chat: {str(e)}")
            raise Exception(f"Error al crear chat: {str(e)}")

    async def get_user_chats(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtener chats del usuario"""
        try:
            async with self.db_pool.acquire() as conn:
                chats = await conn.fetch("""
                    SELECT 
                        c.id,
                        c.title,
                        c.user_id,
                        c.created_at,
                        c.updated_at,
                        COUNT(m.id) as message_count
                    FROM chats c
                    LEFT JOIN messages m ON c.id = m.chat_id AND m.is_deleted = FALSE
                    WHERE c.user_id = $1 AND c.is_deleted = FALSE
                    GROUP BY c.id, c.title, c.user_id, c.created_at, c.updated_at
                    ORDER BY c.updated_at DESC
                    LIMIT $2
                """, user_id, limit)
                
                return [
                    {
                        "id": str(chat['id']),
                        "title": chat['title'],
                        "user_id": str(chat['user_id']),
                        "created_at": chat['created_at'].isoformat(),
                        "updated_at": chat['updated_at'].isoformat(),
                        "message_count": chat['message_count']
                    }
                    for chat in chats
                ]
                
        except Exception as e:
            logger.error(f"Error obteniendo chats: {str(e)}")
            raise Exception("Error al obtener chats del usuario")

    async def get_chat_with_messages(self, chat_id: str, user_id: str) -> Dict[str, Any]:
        """Obtener chat específico con sus mensajes"""
        try:
            async with self.db_pool.acquire() as conn:
                # Verificar que el chat pertenece al usuario
                chat = await conn.fetchrow("""
                    SELECT id, title, user_id, created_at, updated_at
                    FROM chats
                    WHERE id = $1 AND user_id = $2 AND is_deleted = FALSE
                """, chat_id, user_id)
                
                if not chat:
                    raise Exception("Chat no encontrado")
                
                # Obtener mensajes del chat
                messages = await conn.fetch("""
                    SELECT id, chat_id, content, role, timestamp, metadata
                    FROM messages
                    WHERE chat_id = $1 AND is_deleted = FALSE
                    ORDER BY timestamp ASC
                """, chat_id)
                
                return {
                    "id": str(chat['id']),
                    "title": chat['title'],
                    "user_id": str(chat['user_id']),
                    "created_at": chat['created_at'].isoformat(),
                    "updated_at": chat['updated_at'].isoformat(),
                    "messages": [
                        {
                            "id": str(msg['id']),
                            "chat_id": str(msg['chat_id']),
                            "content": msg['content'],
                            "role": msg['role'],
                            "timestamp": msg['timestamp'].isoformat(),
                            "metadata": msg['metadata'] or {}
                        }
                        for msg in messages
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo chat: {str(e)}")
            raise Exception("Error al obtener chat")

    async def save_message(
        self, 
        chat_id: str, 
        user_id: str, 
        content: str, 
        role: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Guardar mensaje en el chat"""
        try:
            message_id = str(uuid.uuid4())
            
            async with self.db_pool.acquire() as conn:
                # Verificar que el chat existe y pertenece al usuario
                chat_exists = await conn.fetchval("""
                    SELECT EXISTS(
                        SELECT 1 FROM chats 
                        WHERE id = $1 AND user_id = $2 AND is_deleted = FALSE
                    )
                """, chat_id, user_id)
                
                if not chat_exists:
                    raise Exception("Chat no encontrado")
                
                # Insertar mensaje
                message = await conn.fetchrow("""
                    INSERT INTO messages (id, chat_id, content, role, timestamp, metadata)
                    VALUES ($1, $2, $3, $4, NOW(), $5)
                    RETURNING id, chat_id, content, role, timestamp, metadata
                """, message_id, chat_id, content, role, json.dumps(metadata or {}))
                
                # Actualizar timestamp del chat
                await conn.execute("""
                    UPDATE chats SET updated_at = NOW()
                    WHERE id = $1
                """, chat_id)
                
                return {
                    "id": str(message['id']),
                    "chat_id": str(message['chat_id']),
                    "content": message['content'],
                    "role": message['role'],
                    "timestamp": message['timestamp'].isoformat(),
                    "metadata": json.loads(message['metadata']) if message['metadata'] else {}
                }
                
        except Exception as e:
            logger.error(f"Error guardando mensaje: {str(e)}")
            raise Exception("Error al guardar mensaje")

    async def get_chat_history(self, chat_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtener historial de mensajes del chat"""
        try:
            async with self.db_pool.acquire() as conn:
                messages = await conn.fetch("""
                    SELECT id, chat_id, content, role, timestamp, metadata
                    FROM messages
                    WHERE chat_id = $1 AND is_deleted = FALSE
                    ORDER BY timestamp DESC
                    LIMIT $2
                """, chat_id, limit)
                
                # Revertir orden para tener cronológico
                messages = list(reversed(messages))
                
                return [
                    {
                        "id": str(msg['id']),
                        "chat_id": str(msg['chat_id']),
                        "content": msg['content'],
                        "role": msg['role'],
                        "timestamp": msg['timestamp'].isoformat(),
                        "metadata": json.loads(msg['metadata']) if msg['metadata'] else {}
                    }
                    for msg in messages
                ]
                
        except Exception as e:
            logger.error(f"Error obteniendo historial: {str(e)}")
            raise Exception("Error al obtener historial del chat")
