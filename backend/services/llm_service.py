import aiohttp
import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class LLMService:
    """Servicio para interactuar con Velvet 14B mediante vLLM"""
    
    def __init__(self):
        self.base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001")
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_initialized = False
        
    async def initialize(self):
        """Inicializar el servicio LLM"""
        try:
            timeout = aiohttp.ClientTimeout(total=300)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self.is_initialized = True
            logger.info("✅ LLMService inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar LLMService: {str(e)}")
            raise e

    async def close(self):
        """Cerrar el servicio"""
        if self.session:
            await self.session.close()
        self.is_initialized = False

    async def health_check(self) -> str:
        """Health check del servicio"""
        if not self.is_initialized:
            return "not_initialized"
        
        try:
            url = f"{self.base_url}/health"
            async with self.session.get(url) as response:
                return "healthy" if response.status == 200 else "unhealthy"
        except Exception as e:
            logger.error(f"Health check falló: {str(e)}")
            return "unhealthy"

    async def generate_response(
        self,
        user_message: str,
        chat_history: List[Dict] = None,
        context: str = None,
        include_bcrp_data: bool = False,
        **kwargs
    ) -> str:
        """Generar respuesta usando Velvet 14B"""
        
        if not self.is_initialized:
            raise Exception("LLM Service no está inicializado")
        
        try:
            # Construir prompt básico
            prompt = user_message
            if context:
                prompt = f"Contexto: {context}\n\nPregunta: {user_message}"
            
            # Configuración de generación
            generation_config = {
                "model": "Almawave/Velvet-14B",
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 2048),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
            }
            
            # Llamar a vLLM
            url = f"{self.base_url}/generate"
            
            async with self.session.post(url, json=generation_config) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error en vLLM: {response.status} - {error_text}")
                    # Fallback response
                    return "Lo siento, no puedo procesar tu solicitud en este momento. El modelo Velvet 14B está cargando o no está disponible."
                
                result = await response.json()
                
                # Extraer respuesta
                if "text" in result:
                    return result["text"].strip()
                else:
                    return "Respuesta generada pero en formato inesperado."
                    
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}")
            # Fallback response
            return f"Gracias por tu mensaje: '{user_message}'. El sistema Velvet RAG está funcionando pero el modelo LLM está inicializándose. Esto puede tomar varios minutos en el primer arranque."
