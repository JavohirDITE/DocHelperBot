#!/usr/bin/env python
import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command, Text

from config import Config
from vk_client import VKClient
from shazam_client import ShazamClient
from utils.logger import setup_logger

# Настройка логирования
logger = setup_logger(__name__)

# Состояния бота
class BotStates(StatesGroup):
    waiting_for_search = State()
    waiting_for_album_name = State()

# Глобальные переменные
vk_client = None
shazam_client = None

async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_name = message.from_user.first_name
    
    welcome_text = f"""
🎵 <b>Добро пожаловать, {user_name}!</b>

Я помогу вам найти и скачать музыку из ВКонтакте.

<b>Что я умею:</b>
🔍 Искать музыку по названию
🎤 Распознавать музыку из голосовых сообщений
⬇️ Скачивать музыку в высоком качестве

<b>Как пользоваться:</b>
• Отправьте название песни или исполнителя
• Запишите голосовое сообщение с музыкой
• Используйте команды из меню

Начните с поиска музыки! 🎶
    """
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton("🔍 Поиск музыки"),
        types.KeyboardButton("❓ Помощь")
    )
    
    await message.answer(welcome_text, reply_markup=keyboard)
    logger.info(f"Пользователь {message.from_user.id} запустил бота")

async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
<b>📖 Справка по командам:</b>

/start - Запустить бота
/search - Поиск музыки
/help - Показать эту справку

<b>🎵 Поиск музыки:</b>
• Просто отправьте название песни
• Используйте формат "Исполнитель - Название"
• Отправьте голосовое сообщение для распознавания

<b>🔧 Дополнительно:</b>
• Бот поддерживает высокое качество аудио
• Автоматическое распознавание через Shazam
• Быстрая загрузка и отправка файлов

Если возникли проблемы, попробуйте команду /start
    """
    
    await message.answer(help_text)

async def cmd_search(message: types.Message):
    """Обработчик команды /search"""
    await message.answer(
        "🔍 <b>Поиск музыки</b>\n\n"
        "Отправьте название песни или исполнителя:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton("❌ Отмена")]],
            resize_keyboard=True
        )
    )
    await BotStates.waiting_for_search.set()

async def process_search_query(message: types.Message, state: FSMContext):
    """Обработка поискового запроса"""
    if message.text == "❌ Отмена":
        await state.finish()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(
            types.KeyboardButton("🔍 Поиск музыки"),
            types.KeyboardButton("❓ Помощь")
        )
        await message.answer("Поиск отменен", reply_markup=keyboard)
        return
    
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите корректный запрос")
        return
    
    await handle_search(message, query)
    await state.finish()

async def handle_search(message: types.Message, query: str):
    """Обработка поиска музыки"""
    # Показываем индикатор загрузки
    search_msg = await message.answer("🔍 Ищу музыку...")
    
    try:
        global vk_client
        if not vk_client:
            await search_msg.edit_text("❌ VK клиент не инициализирован")
            return
            
        results = await vk_client.search_audio(query, page=0)
        
        if not results:
            await search_msg.edit_text(
                "😔 Ничего не найдено.\n"
                "Попробуйте изменить запрос или проверить правописание."
            )
            return
        
        # Создаем клавиатуру с результатами
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        for i, track in enumerate(results[:6]):  # Показываем первые 6 результатов
            track_text = f"🎵 {track['artist']} - {track['title']}"
            if len(track_text) > 60:
                track_text = track_text[:57] + "..."
            
            keyboard.add(
                types.InlineKeyboardButton(
                    track_text,
                    callback_data=f"download:{track['id']}"
                )
            )
        
        await search_msg.edit_text(
            f"🎵 <b>Результаты поиска:</b> {query}\n"
            f"Найдено: {len(results)} треков"
        )
        
        await message.answer(
            "Выберите трек для скачивания:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await search_msg.edit_text(
            "❌ Произошла ошибка при поиске.\n"
            "Попробуйте позже."
        )

async def handle_text_search(message: types.Message):
    """Обработка текстового поиска без команды"""
    # Проверяем, что это не команда и не кнопка
    if message.text.startswith('/') or message.text in ["🔍 Поиск музыки", "❓ Помощь", "❌ Отмена"]:
        return
    
    query = message.text.strip()
    await handle_search(message, query)

async def handle_voice_message(message: types.Message):
    """Обработка голосовых сообщений для распознавания музыки"""
    processing_msg = await message.answer("🎤 Распознаю музыку...")
    
    try:
        # Скачиваем голосовое сообщение
        file_info = await message.bot.get_file(message.voice.file_id)
        file_data = await message.bot.download_file(file_info.file_path)
        
        # Распознаем через Shazam
        await processing_msg.edit_text("🔍 Анализирую аудио...")
        
        global shazam_client
        if not shazam_client:
            await processing_msg.edit_text("❌ Shazam клиент не инициализирован")
            return
            
        recognition_result = await shazam_client.recognize(file_data.read())
        
        if not recognition_result or not recognition_result.get('matches'):
            await processing_msg.edit_text(
                "😔 Не удалось распознать музыку.\n"
                "Попробуйте записать более четкое голосовое сообщение."
            )
            return
        
        # Получаем информацию о треке
        track_info = recognition_result.get('track', {})
        title = track_info.get('title', '')
        artist = track_info.get('subtitle', '')
        
        if not title or not artist:
            await processing_msg.edit_text(
                "😔 Не удалось получить информацию о треке."
            )
            return
        
        # Формируем поисковый запрос
        query = f"{artist} - {title}"
        
        await processing_msg.edit_text(
            f"✅ Распознано: <b>{query}</b>\n"
            "🔍 Ищу в ВКонтакте..."
        )
        
        # Ищем в VK
        global vk_client
        results = await vk_client.search_audio(query, page=0)
        
        if not results:
            await processing_msg.edit_text(
                f"✅ Распознано: <b>{query}</b>\n"
                "😔 К сожалению, не найдено в ВКонтакте."
            )
            return
        
        # Показываем результаты
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        for track in results[:3]:  # Показываем первые 3 результата
            track_text = f"🎵 {track['artist']} - {track['title']}"
            if len(track_text) > 60:
                track_text = track_text[:57] + "..."
            
            keyboard.add(
                types.InlineKeyboardButton(
                    track_text,
                    callback_data=f"download:{track['id']}"
                )
            )
        
        await processing_msg.edit_text(
            f"✅ Распознано: <b>{query}</b>\n"
            f"🎵 Найдено: {len(results)} треков"
        )
        
        await message.answer(
            "Выберите нужный трек:",
            reply_markup=keyboard
        )
        
        logger.info(f"Пользователь {message.from_user.id} распознал: {query}")
        
    except Exception as e:
        logger.error(f"Ошибка распознавания: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при распознавании.\n"
            "Попробуйте позже."
        )

async def handle_download_track(callback_query: types.CallbackQuery):
    """Обработка скачивания трека"""
    await callback_query.answer()
    
    # Извлекаем ID трека из callback_data
    track_id = callback_query.data.split(':')[1]
    
    # Показываем индикатор загрузки
    loading_msg = await callback_query.message.answer("⬇️ Скачиваю трек...")
    
    try:
        global vk_client
        track_info = await vk_client.get_track_by_id(track_id)
        
        if not track_info:
            await loading_msg.edit_text("❌ Трек не найден")
            return
        
        # Скачиваем аудио
        await loading_msg.edit_text("📥 Загружаю аудио файл...")
        audio_data = await vk_client.download_audio(track_info['url'])
        
        # Скачиваем обложку (если есть)
        thumb_data = None
        if track_info.get('thumb_url'):
            try:
                thumb_data = await vk_client.download_cover(track_info['thumb_url'])
            except:
                pass
        
        # Отправляем аудио
        await loading_msg.edit_text("📤 Отправляю...")
        
        await callback_query.message.answer_audio(
            audio_data,
            duration=track_info.get('duration', 0),
            performer=track_info['artist'],
            title=track_info['title'],
            thumb=thumb_data.getvalue() if thumb_data else None
        )
        
        await loading_msg.delete()
        
        logger.info(f"Пользователь {callback_query.from_user.id} скачал трек {track_id}")
        
    except Exception as e:
        logger.error(f"Ошибка скачивания трека: {e}")
        await loading_msg.edit_text(
            "❌ Произошла ошибка при скачивании.\n"
            "Попробуйте позже."
        )

async def handle_button_press(message: types.Message):
    """Обработка нажатий кнопок"""
    if message.text == "🔍 Поиск музыки":
        await cmd_search(message)
    elif message.text == "❓ Помощь":
        await cmd_help(message)

async def set_bot_commands(bot: Bot):
    """Устанавливает меню команд бота"""
    commands = [
        types.BotCommand(command="start", description="🎵 Запустить бота"),
        types.BotCommand(command="search", description="🔍 Поиск музыки"),
        types.BotCommand(command="help", description="❓ Помощь"),
    ]
    
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")

async def on_startup(dp: Dispatcher):
    """Выполняется при запуске бота"""
    logger.info("Бот запускается...")
    
    # Устанавливаем команды
    await set_bot_commands(dp.bot)
    
    # Инициализируем VK клиент
    global vk_client, shazam_client
    try:
        vk_client = VKClient()
        await vk_client.init()
        logger.info("VK клиент инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации VK клиента: {e}")
    
    # Инициализируем Shazam клиент
    try:
        shazam_client = ShazamClient()
        logger.info("Shazam клиент инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации Shazam клиента: {e}")
    
    logger.info("Бот успешно запущен!")

async def on_shutdown(dp: Dispatcher):
    """Выполняется при остановке бота"""
    logger.info("Бот останавливается...")
    
    # Закрываем соединения
    global vk_client
    if vk_client:
        await vk_client.close()
    
    await dp.storage.close()
    await dp.storage.wait_closed()
    
    logger.info("Бот остановлен")

def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики"""
    # Команды
    dp.register_message_handler(cmd_start, Command("start"))
    dp.register_message_handler(cmd_help, Command("help"))
    dp.register_message_handler(cmd_search, Command("search"))
    
    # Состояния
    dp.register_message_handler(
        process_search_query, 
        state=BotStates.waiting_for_search
    )
    
    # Callback запросы
    dp.register_callback_query_handler(
        handle_download_track,
        Text(startswith="download:")
    )
    
    # Голосовые сообщения
    dp.register_message_handler(
        handle_voice_message,
        content_types=types.ContentType.VOICE
    )
    
    # Кнопки
    dp.register_message_handler(
        handle_button_press,
        Text(equals=["🔍 Поиск музыки", "❓ Помощь"])
    )
    
    # Текстовые сообщения (поиск)
    dp.register_message_handler(
        handle_text_search,
        content_types=types.ContentType.TEXT
    )

def main():
    """Главная функция запуска бота"""
    try:
        # Загружаем конфигурацию
        config = Config()
        logger.info("Конфигурация загружена")
        
        # Создаем бота и диспетчер
        bot = Bot(token=config.BOT_TOKEN, parse_mode=types.ParseMode.HTML)
        storage = MemoryStorage()
        dp = Dispatcher(bot, storage=storage)
        
        # Регистрируем обработчики
        register_handlers(dp)
        logger.info("Обработчики зарегистрированы")
        
        # Запускаем бота
        executor.start_polling(
            dp,
            skip_updates=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown
        )
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
