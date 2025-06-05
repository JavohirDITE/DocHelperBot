from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text

from vk_client import VKClient
from utils.keyboards import get_search_results_keyboard, get_main_keyboard
from utils.states import BotStates
from utils.logger import setup_logger

logger = setup_logger(__name__)

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
        await message.answer(
            "Поиск отменен",
            reply_markup=get_main_keyboard()
        )
        return
    
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите корректный запрос")
        return
    
    # Показываем индикатор загрузки
    await message.answer("🔍 Ищу музыку...")
    
    try:
        vk_client = VKClient()
        results = await vk_client.search_audio(query, page=0)
        
        if not results:
            await message.answer(
                "😔 Ничего не найдено.\n"
                "Попробуйте изменить запрос или проверить правописание.",
                reply_markup=get_main_keyboard()
            )
            await state.finish()
            return
        
        # Сохраняем результаты в состояние
        await state.update_data(
            query=query,
            results=results,
            page=0
        )
        
        keyboard = get_search_results_keyboard(results, query, 0)
        
        await message.answer(
            f"🎵 <b>Результаты поиска:</b> {query}\n"
            f"Найдено: {len(results)} треков",
            reply_markup=keyboard
        )
        
        await message.answer(
            "Выберите трек для скачивания:",
            reply_markup=get_main_keyboard()
        )
        
        await state.finish()
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer(
            "❌ Произошла ошибка при поиске.\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=get_main_keyboard()
        )
        await state.finish()

async def handle_text_search(message: types.Message):
    """Обработка текстового поиска без команды"""
    # Проверяем, что это не команда
    if message.text.startswith('/'):
        return
    
    query = message.text.strip()
    
    # Показываем индикатор загрузки
    search_msg = await message.answer("🔍 Ищу музыку...")
    
    try:
        vk_client = VKClient()
        results = await vk_client.search_audio(query, page=0)
        
        if not results:
            await search_msg.edit_text(
                "😔 Ничего не найдено.\n"
                "Попробуйте изменить запрос или проверить правописание."
            )
            return
        
        keyboard = get_search_results_keyboard(results, query, 0)
        
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

def register_search_handlers(dp: Dispatcher):
    """Регистрирует обработчики поиска"""
    dp.register_message_handler(cmd_search, Command("search"))
    dp.register_message_handler(
        process_search_query, 
        state=BotStates.waiting_for_search
    )
    dp.register_message_handler(
        handle_text_search,
        content_types=types.ContentType.TEXT
    )
