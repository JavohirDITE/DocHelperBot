import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Конфигурация бота"""
    
    # Telegram Bot
    BOT_TOKEN: str
    
    # VK
    VK_LOGIN: str
    VK_PASSWORD: str
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Bot settings
    RESULTS_PER_PAGE: int = 6
    MAX_DOWNLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    def __init__(self):
        self.BOT_TOKEN = self._get_env("BOT_TOKEN")
        self.VK_LOGIN = self._get_env("VK_LOGIN")
        self.VK_PASSWORD = self._get_env("VK_PASSWORD")
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.RESULTS_PER_PAGE = int(os.getenv("RESULTS_PER_PAGE", "6"))
        self.MAX_DOWNLOAD_SIZE = int(os.getenv("MAX_DOWNLOAD_SIZE", str(50 * 1024 * 1024)))
    
    def _get_env(self, key: str) -> str:
        """Получает переменную окружения или вызывает ошибку"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Переменная окружения {key} не установлена")
        return value
