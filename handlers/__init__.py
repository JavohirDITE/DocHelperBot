from aiogram import Dispatcher

from .start import register_start_handlers
from .search import register_search_handlers
from .albums import register_album_handlers
from .audio import register_audio_handlers
from .callbacks import register_callback_handlers

def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики"""
    register_start_handlers(dp)
    register_search_handlers(dp)
    register_album_handlers(dp)
    register_audio_handlers(dp)
    register_callback_handlers(dp)
