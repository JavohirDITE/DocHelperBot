from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from vk_client import VKClient
from database import Database
from utils.keyboards import (
    get_track_actions_keyboard, 
    get_albums_selection_keyboard,
    get_search_results_keyboard
)
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def handle_download_track(callback_query: types.CallbackQuery):
    """Обработка скачивания трека"""
    await callback_query.answer()
    
    # Извлекаем ID трека из callback_data
    track_id = callback_query.data.split(':')[1]
    
    # Показываем индикатор загрузки
    loading_msg = await callback_query.message.answer("⬇️ Скачиваю трек...")
    
    try:
        vk_client = VKClient()
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
        
        audio_file = types.InputFile(
            audio_data,
            filename=f"{track_info['artist']} - {track_info['title']}.mp3"
        )
        
        await callback_query.message.answer_audio(
            audio_file,
            duration=track_info.get('duration', 0),
            performer=track_info['artist'],
            title=track_info['title'],
            thumb=thumb_data,
            reply_markup=get_track_actions_keyboard(track_id)
        )
        
        await loading_msg.delete()
        
        # Сохраняем в базу данных
        db = Database()
        await db.save_downloaded_track(
            callback_query.from_user.id,
            track_id,
            track_info
        )
        
        logger.info(f"Пользователь {callback_query.from_user.id} скачал трек {track_id}")
        
    except Exception as e:
        logger.error(f"Ошибка скачивания трека: {e}")
        await loading_msg.edit_text(
            "❌ Произошла ошибка при скачивании.\n"
            "Попробуйте позже."
        )

async def handle_add_to_album(callback_query: types.CallbackQuery):
    """Обработка добавления трека в альбом"""
    await callback_query.answer()
    
    track_id = callback_query.data.split(':')[1]
    
    # Получаем альбомы пользователя
    db = Database()
    albums = await db.get_user_albums(callback_query.from_user.id)
    
    if not albums:
        await callback_query.message.answer(
            "📁 У вас нет альбомов.\n"
            "Создайте альбом командой /albums"
        )
        return
    
    keyboard = get_albums_selection_keyboard(albums, track_id)
    
    await callback_query.message.answer(
        "📁 Выберите альбом для добавления трека:",
        reply_markup=keyboard
    )

async def handle_album_selection(callback_query: types.CallbackQuery):
    """Обработка выбора альбома для добавления трека"""
    await callback_query.answer()
    
    # Парсим данные: album_add:album_id:track_id
    parts = callback_query.data.split(':')
    album_id = int(parts[1])
    track_id = parts[2]
    
    try:
        db = Database()
        
        # Проверяем, нет ли уже этого трека в альбоме
        exists = await db.track_exists_in_album(album_id, track_id)
        if exists:
            await callback_query.message.edit_text(
                "ℹ️ Этот трек уже есть в выбранном альбоме"
            )
            return
        
        # Добавляем трек в альбом
        await db.add_track_to_album(album_id, track_id)
        
        # Получаем название альбома
        album = await db.get_album_by_id(album_id)
        
        await callback_query.message.edit_text(
            f"✅ Трек добавлен в альбом '<b>{album['name']}</b>'"
        )
        
        logger.info(f"Трек {track_id} добавлен в альбом {album_id}")
        
    except Exception as e:
        logger.error(f"Ошибка добавления в альбом: {e}")
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при добавлении в альбом"
        )

async def handle_search_pagination(callback_query: types.CallbackQuery):
    """Обработка пагинации результатов поиска"""
    await callback_query.answer()
    
    # Парсим данные: search_page:query:page
    parts = callback_query.data.split(':')
    query = parts[1]
    page = int(parts[2])
    
    try:
        vk_client = VKClient()
        results = await vk_client.search_audio(query, page=page)
        
        if not results:
            await callback_query.answer("Больше результатов нет", show_alert=True)
            return
        
        keyboard = get_search_results_keyboard(results, query, page)
        
        await callback_query.message.edit_text(
            f"🎵 <b>Результаты поиска:</b> {query}\n"
            f"Страница {page + 1}",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка пагинации: {e}")
        await callback_query.answer("Произошла ошибка", show_alert=True)

def register_callback_handlers(dp: Dispatcher):
    """Регистрирует обработчики callback запросов"""
    dp.register_callback_query_handler(
        handle_download_track,
        Text(startswith="download:")
    )
    dp.register_callback_query_handler(
        handle_add_to_album,
        Text(startswith="add_album:")
    )
    dp.register_callback_query_handler(
        handle_album_selection,
        Text(startswith="album_add:")
    )
    dp.register_callback_query_handler(
        handle_search_pagination,
        Text(startswith="search_page:")
    )
