import aiosqlite
import asyncio
from typing import List, Dict, Optional
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
    
    async def init_db(self):
        """Инициализация базы данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Таблица пользователей
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Таблица альбомов
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS albums (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                        UNIQUE(user_id, name)
                    )
                """)
                
                # Таблица треков
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS tracks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        duration INTEGER,
                        url TEXT,
                        thumb_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Таблица связи альбомов и треков
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS album_tracks (
                        album_id INTEGER NOT NULL,
                        track_id TEXT NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (album_id, track_id),
                        FOREIGN KEY (album_id) REFERENCES albums (id) ON DELETE CASCADE,
                        FOREIGN KEY (track_id) REFERENCES tracks (id) ON DELETE CASCADE
                    )
                """)
                
                # Таблица скачанных треков
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS downloaded_tracks (
                        user_id INTEGER NOT NULL,
                        track_id TEXT NOT NULL,
                        downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, track_id),
                        FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                        FOREIGN KEY (track_id) REFERENCES tracks (id)
                    )
                """)
                
                await db.commit()
                logger.info("База данных инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
    
    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None):
        """Создание пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
                    (telegram_id, username, first_name)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка создания пользователя: {e}")
    
    async def create_album(self, user_id: int, name: str) -> int:
        """Создание альбома"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "INSERT INTO albums (user_id, name) VALUES (?, ?)",
                    (user_id, name)
                )
                album_id = cursor.lastrowid
                await db.commit()
                return album_id
        except Exception as e:
            logger.error(f"Ошибка создания альбома: {e}")
            raise
    
    async def get_user_albums(self, user_id: int) -> List[Dict]:
        """Получение альбомов пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM albums WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,)
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения альбомов: {e}")
            return []
    
    async def get_album_by_name(self, user_id: int, name: str) -> Optional[Dict]:
        """Получение альбома по названию"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM albums WHERE user_id = ? AND name = ?",
                    (user_id, name)
                )
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения альбома: {e}")
            return None
    
    async def get_album_by_id(self, album_id: int) -> Optional[Dict]:
        """Получение альбома по ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM albums WHERE id = ?",
                    (album_id,)
                )
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения альбома: {e}")
            return None
    
    async def save_track(self, track_info: Dict):
        """Сохранение информации о треке"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO tracks 
                       (id, title, artist, duration, url, thumb_url) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        track_info['id'],
                        track_info['title'],
                        track_info['artist'],
                        track_info.get('duration', 0),
                        track_info.get('url'),
                        track_info.get('thumb_url')
                    )
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка сохранения трека: {e}")
    
    async def add_track_to_album(self, album_id: int, track_id: str):
        """Добавление трека в альбом"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO album_tracks (album_id, track_id) VALUES (?, ?)",
                    (album_id, track_id)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка добавления трека в альбом: {e}")
            raise
    
    async def track_exists_in_album(self, album_id: int, track_id: str) -> bool:
        """Проверка существования трека в альбоме"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT 1 FROM album_tracks WHERE album_id = ? AND track_id = ?",
                    (album_id, track_id)
                )
                row = await cursor.fetchone()
                return row is not None
        except Exception as e:
            logger.error(f"Ошибка проверки трека в альбоме: {e}")
            return False
    
    async def get_album_track_count(self, album_id: int) -> int:
        """Получение количества треков в альбоме"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM album_tracks WHERE album_id = ?",
                    (album_id,)
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Ошибка подсчета треков: {e}")
            return 0
    
    async def save_downloaded_track(self, user_id: int, track_id: str, track_info: Dict):
        """Сохранение информации о скачанном треке"""
        try:
            # Сначала сохраняем трек
            await self.save_track(track_info)
            
            # Затем отмечаем как скачанный
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO downloaded_tracks (user_id, track_id) VALUES (?, ?)",
                    (user_id, track_id)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка сохранения скачанного трека: {e}")
