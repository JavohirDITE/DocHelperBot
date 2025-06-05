import asyncio
import aiohttp
import vk_api
from vk_api import audio
import io
from typing import List, Dict, Optional
import logging

from config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)

class VKClient:
    """Клиент для работы с VK API"""
    
    def __init__(self):
        self.config = Config()
        self.session = None
        self.vk_audio = None
        self._http_session = None
    
    async def init(self):
        """Инициализация VK клиента"""
        try:
            # Создаем сессию VK
            self.session = vk_api.VkApi(
                login=self.config.VK_LOGIN,
                password=self.config.VK_PASSWORD
            )
            self.session.auth()
            
            # Получаем доступ к аудио
            self.vk_audio = audio.VkAudio(self.session)
            
            # HTTP сессия для скачивания
            self._http_session = aiohttp.ClientSession()
            
            logger.info("VK клиент успешно инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации VK клиента: {e}")
            raise
    
    async def search_audio(self, query: str, page: int = 0) -> List[Dict]:
        """Поиск аудио в VK"""
        try:
            # VK API работает синхронно, поэтому выполняем в executor
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.vk_audio.search(
                    query, 
                    count=self.config.RESULTS_PER_PAGE,
                    offset=page * self.config.RESULTS_PER_PAGE
                )
            )
            
            processed_results = []
            for track in results:
                processed_track = {
                    'id': f"{track['owner_id']}_{track['id']}",
                    'title': track['title'],
                    'artist': track['artist'],
                    'duration': track.get('duration', 0),
                    'url': track['url'],
                    'thumb_url': track.get('album', {}).get('thumb', {}).get('photo_300')
                }
                processed_results.append(processed_track)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Ошибка поиска аудио: {e}")
            return []
    
    async def get_track_by_id(self, track_id: str) -> Optional[Dict]:
        """Получение трека по ID"""
        try:
            owner_id, audio_id = track_id.split('_')
            
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(
                None,
                lambda: self.vk_audio.get_audio_by_id(int(owner_id), int(audio_id))
            )
            
            if track:
                return {
                    'id': track_id,
                    'title': track['title'],
                    'artist': track['artist'],
                    'duration': track.get('duration', 0),
                    'url': track['url'],
                    'thumb_url': track.get('album', {}).get('thumb', {}).get('photo_300')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения трека: {e}")
            return None
    
    async def download_audio(self, url: str) -> io.BytesIO:
        """Скачивание аудио файла"""
        try:
            async with self._http_session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    return io.BytesIO(content)
                else:
                    raise Exception(f"HTTP {response.status}")
                    
        except Exception as e:
            logger.error(f"Ошибка скачивания аудио: {e}")
            raise
    
    async def download_cover(self, url: str) -> Optional[io.BytesIO]:
        """Скачивание обложки"""
        try:
            async with self._http_session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    return io.BytesIO(content)
                return None
                
        except Exception as e:
            logger.error(f"Ошибка скачивания обложки: {e}")
            return None
    
    async def close(self):
        """Закрытие соединений"""
        if self._http_session:
            await self._http_session.close()
