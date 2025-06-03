import os
import tempfile
import logging
import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import pytesseract
from PIL import Image

from handlers.utils import delete_previous_messages

router = Router()
logger = logging.getLogger(__name__)

class OCRStates(StatesGroup):
    waiting_for_image = State()


@router.callback_query(F.data == "menu:ocr")
async def start_ocr(callback: CallbackQuery, state: FSMContext):
    """Начало процесса распознавания текста."""
    await callback.answer()
    await state.set_state(OCRStates.waiting_for_image)


@router.message(F.photo & OCRStates.waiting_for_image)
@router.message(F.document & F.document.mime_type.startswith("image/") & OCRStates.waiting_for_image)
async def process_image_for_ocr(message: Message, state: FSMContext):
    """Обработка изображения для распознавания текста."""
    processing_msg = await message.answer("🔄 Распознаю текст на изображении...")
    
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id
        
        file = await message.bot.get_file(file_id)
        file_content = await message.bot.download_file(file.file_path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = os.path.join(temp_dir, "image.png")
            
            with open(image_path, "wb") as f:
                f.write(file_content.read())
            
            text = await asyncio.to_thread(recognize_text, image_path)
            
            await delete_previous_messages(message)
            await processing_msg.delete()
            
            if text.strip():
                await message.answer(
                    "✅ Текст успешно распознан:\n\n"
                    f"<pre>{text}</pre>",
                    reply_markup=InlineKeyboardBuilder()
                    .button(text="⬅️ В главное меню", callback_data="back_to_menu")
                    .as_markup()
                )
            else:
                await message.answer(
                    "❌ Не удалось распознать текст на изображении. "
                    "Попробуйте отправить изображение с более четким текстом.",
                    reply_markup=InlineKeyboardBuilder()
                    .button(text="⬅️ В главное меню", callback_data="back_to_menu")
                    .as_markup()
                )
    
    except Exception as e:
        logger.error(f"Ошибка при распознавании текста: {e}")
        await processing_msg.delete()
        await message.answer(
            f"❌ Произошла ошибка при распознавании текста: {str(e)}",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ В главное меню", callback_data="back_to_menu")
            .as_markup()
        )
    
    await state.clear()


def recognize_text(image_path):
    """Распознает текст на изображении."""
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang='rus+eng')
    return text