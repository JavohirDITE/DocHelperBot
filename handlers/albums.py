from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command

from database import Database
from utils.keyboards import get_albums_keyboard, get_album_keyboard, get_main_keyboard
from utils.states import BotStates
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def cmd_albums(message: types.Message):
    """Обработчик команды /albums"""
    db = Database()
    albums = await db.get_user_albums(message.from_user.id)
    
    if not albums:
        await message.answer(
            "📁 <b>У вас пока нет альбомов</b>\n\n"
            "Создайте первый альбом, чтобы сохранять любимую музыку!",
            reply_markup=get_albums_keyboard(albums, can_create=True)
        )
    else:
        albums_text = "📁 <b>Ваши альбомы:</b>\n\n"
        for album in albums:
            track_count = await db.get_album_track_count(album['id'])
            albums_text += f"• {album['name']} ({track_count} треков)\n"
        
        await message.answer(
            albums_text,
            reply_markup=get_albums_keyboard(albums, can_create=True)
        )

async def create_album_start(message: types.Message):
    """Начало создания альбома"""
    await message.answer(
        "📝 <b>Создание нового альбома</b>\n\n"
        "Введите название альбома:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton("❌ Отмена")]],
            resize_keyboard=True
        )
    )
    await BotStates.waiting_for_album_name.set()

async def create_album_finish(message: types.Message, state: FSMContext):
    """Завершение создания альбома"""
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer(
            "Создание альбома отменено",
            reply_markup=get_main_keyboard()
        )
        return
    
    album_name = message.text.strip()
    if not album_name:
        await message.answer("Пожалуйста, введите корректное название")
        return
    
    if len(album_name) > 50:
        await message.answer("Название слишком длинное (максимум 50 символов)")
        return
    
    try:
        db = Database()
        
        # Проверяем, нет ли уже такого альбома
        existing = await db.get_album_by_name(message.from_user.id, album_name)
        if existing:
            await message.answer(
                f"❌ Альбом с названием '{album_name}' уже существует.\n"
                "Выберите другое название."
            )
            return
        
        # Создаем альбом
        album_id = await db.create_album(message.from_user.id, album_name)
        
        await message.answer(
            f"✅ Альбом '<b>{album_name}</b>' успешно создан!",
            reply_markup=get_main_keyboard()
        )
        
        await state.finish()
        
        logger.info(f"Пользователь {message.from_user.id} создал альбом '{album_name}'")
        
    except Exception as e:
        logger.error(f"Ошибка создания альбома: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании альбома.\n"
            "Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
        await state.finish()

def register_album_handlers(dp: Dispatcher):
    """Регистрирует обработчики альбомов"""
    dp.register_message_handler(cmd_albums, Command("albums"))
    dp.register_message_handler(
        create_album_finish,
        state=BotStates.waiting_for_album_name
    )
