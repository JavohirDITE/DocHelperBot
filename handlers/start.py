from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command

from utils.keyboards import get_main_keyboard
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_name = message.from_user.first_name
    
    welcome_text = f"""
🎵 <b>Добро пожаловать, {user_name}!</b>

Я помогу вам найти и скачать музыку из ВКонтакте.

<b>Что я умею:</b>
🔍 Искать музыку по названию
🎤 Распознавать музыку из голосовых сообщений
📁 Создавать альбомы для сохранения треков
⬇️ Скачивать музыку в высоком качестве

<b>Как пользоваться:</b>
• Отправьте название песни или исполнителя
• Запишите голосовое сообщение с музыкой
• Используйте команды из меню

Начните с поиска музыки! 🎶
    """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard()
    )
    
    logger.info(f"Пользователь {message.from_user.id} запустил бота")

async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
<b>📖 Справка по командам:</b>

/start - Запустить бота
/search - Поиск музыки
/albums - Управление альбомами
/help - Показать эту справку
/settings - Настройки бота

<b>🎵 Поиск музыки:</b>
• Просто отправьте название песни
• Используйте формат "Исполнитель - Название"
• Отправьте голосовое сообщение для распознавания

<b>📁 Альбомы:</b>
• Создавайте альбомы для организации музыки
• Добавляйте треки в альбомы одним нажатием
• Слушайте целые альбомы

<b>🔧 Дополнительно:</b>
• Бот поддерживает высокое качество аудио
• Автоматическое распознавание через Shazam
• Быстрая загрузка и отправка файлов

Если возникли проблемы, попробуйте команду /start
    """
    
    await message.answer(help_text)

def register_start_handlers(dp: Dispatcher):
    """Регистрирует обработчики команд start и help"""
    dp.register_message_handler(cmd_start, Command("start"))
    dp.register_message_handler(cmd_help, Command("help"))
