import asyncio
import io
from shazamio import Shazam
from typing import Dict, Optional

from utils.logger import setup_logger

logger = setup_logger(__name__)

class ShazamClient:
    """Клиент для распознавания музыки через Shazam"""
    
    def __init__(self):
        self.shazam = Shazam()
    
    async def recognize(self, audio_data: bytes) -> Optional[Dict]:
        """Распознавание музыки из аудио данных"""
        try:
            # Создаем BytesIO объект из данных
            audio_buffer = io.BytesIO(audio_data)
            
            # Распознаем через Shazam
            result = await self.shazam.recognize_song(audio_buffer)
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка распознавания Shazam: {e}")
            return None
