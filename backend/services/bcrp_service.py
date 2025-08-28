import aiohttp
import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class BCRPService:
    """Servicio para consultar la API del Banco Central de Reserva del Perú"""
    
    def __init__(self):
        self.base_url = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Inicializar cliente HTTP"""
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("✅ BCRPService inicializado")

    async def close(self):
        """Cerrar cliente HTTP"""
        if self.session:
            await self.session.close()

    async def health_check(self) -> str:
        """Verificar estado de la API del BCRP"""
        try:
            if not self.session:
                await self.initialize()
            
            # Test con serie de inflación
            test_series = "PN01288PM"
            url = f"{self.base_url}/{test_series}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return "healthy"
                else:
                    return "unhealthy"
                    
        except Exception as e:
            logger.error(f"BCRP health check falló: {str(e)}")
            return "error"

    async def get_series_data(
        self, 
        series: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Obtener datos de series del BCRP"""
        
        if not self.session:
            await self.initialize()
        
        try:
            if not series or len(series) == 0:
                raise ValueError("Debe especificar al menos una serie")
            
            # Construir URL con primera serie (simplificado)
            series_param = series[0] if len(series) == 1 else "-".join(series[:3])
            url = f"{self.base_url}/{series_param}"
            
            params = {"format": format}
            if start_date:
                params["startPeriod"] = start_date
            if end_date:
                params["endPeriod"] = end_date
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_response(data, series)
                else:
                    raise Exception(f"Error del servidor BCRP: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error consultando BCRP: {str(e)}")
            # Return mock data for demo
            return {
                "series": series,
                "data": [
                    {"date": "2024-01", "value": 2.1, "series_code": series[0] if series else "demo"},
                    {"date": "2024-02", "value": 2.3, "series_code": series[0] if series else "demo"},
                ],
                "metadata": {"source": "BCRP", "status": "demo_data"},
                "error": str(e)
            }

    def _process_response(self, data: Dict[str, Any], requested_series: List[str]) -> Dict[str, Any]:
        """Procesar respuesta del BCRP (simplificado)"""
        return {
            "series": requested_series,
            "data": [],  # Se procesaría aquí
            "metadata": {"source": "BCRP"},
            "raw_data": data
        }
