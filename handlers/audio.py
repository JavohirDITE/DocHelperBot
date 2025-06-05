import io
from aiogram import Dispatcher, types

from shazam_client import ShazamClient
from vk_client import VKClient
from utils.keyboards import get_search_results_keyboard
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def handle_voice_message(message: types.Message):
    """Обработка голосовых сообщений для распознавания музыки"""
    # Показываем индикатор обработки
    processing_msg = await message.answer("🎤 Распознаю музыку...")
    
    try:
        # Скачиваем голосовое сообщение
        file_info = await message.bot.get_file(message.voice.file_id)
        file_data = await message.bot.download_file(file_info.file_path)
        
        # Распознаем через Shazam
        await processing_msg.edit_text("🔍 Анализирую аудио...")
        
        shazam_client = ShazamClient()
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
        vk_client = VKClient()
        results = await vk_client.search_audio(query, page=0)
        
        if not results:
            await processing_msg.edit_text(
                f"✅ Распознано: <b>{query}</b>\n"
                "😔 К сожалению, не найдено в ВКонтакте."
            )
            return
        
        # Показываем результаты
        keyboard = get_search_results_keyboard(results, query, 0)
        
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

async def handle_audio_message(message: types.Message):
    """Обработка аудио сообщений"""
    await handle_voice_message(message)

def register_audio_handlers(dp: Dispatcher):
    """Регистрирует обработчики аудио"""
    dp.register_message_handler(
        handle_voice_message,
        content_types=types.ContentType.VOICE
    )
    dp.register_message_handler(
        handle_audio_message,
        content_types=types.ContentType.AUDIO
    )
