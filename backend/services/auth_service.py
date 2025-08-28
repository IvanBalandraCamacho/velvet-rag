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
