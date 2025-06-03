import asyncio
import os
import tempfile
import logging
from io import BytesIO
from PIL import Image

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from rembg import remove

from handlers.utils import delete_previous_messages

router = Router()
logger = logging.getLogger(__name__)

class BackgroundRemovalStates(StatesGroup):
    waiting_for_image = State()
    waiting_for_background_choice = State()


@router.callback_query(F.data == "menu:background")
async def start_background_removal(callback: CallbackQuery, state: FSMContext):
    """Начало процесса удаления фона."""
    await callback.answer()
    await state.set_state(BackgroundRemovalStates.waiting_for_image)


@router.message(F.photo & BackgroundRemovalStates.waiting_for_image)
@router.message(F.document & F.document.mime_type.startswith("image/") & BackgroundRemovalStates.waiting_for_image)
async def process_image_for_background_removal(message: Message, state: FSMContext):
    """Обработка изображения для удаления фона."""
    processing_msg = await message.answer("🔄 Обрабатываю изображение...")
    
    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id
    
    file = await message.bot.get_file(file_id)
    file_content = await message.bot.download_file(file.file_path)
    
    await state.update_data(original_image=file_content.read())
    
    await processing_msg.delete()
    
    await message.answer(
        "🎨 Выберите фон для изображения:",
        reply_markup=InlineKeyboardBuilder()
        .button(text="🔵 Голубой фон", callback_data="bg:blue")
        .button(text="⚪️ Белый фон", callback_data="bg:white")
        .button(text="🔳 Прозрачный (PNG)", callback_data="bg:transparent")
        .button(text="⬅️ Назад", callback_data="back_to_menu")
        .adjust(2, 2)
        .as_markup()
    )
    
    await state.set_state(BackgroundRemovalStates.waiting_for_background_choice)


@router.callback_query(F.data.startswith("bg:") & BackgroundRemovalStates.waiting_for_background_choice)
async def process_background_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора фона."""
    await callback.answer()
    
    bg_choice = callback.data.split(":")[1]
    
    data = await state.get_data()
    original_image = data.get("original_image")
    
    if not original_image:
        await callback.message.answer("❌ Произошла ошибка. Пожалуйста, отправьте изображение заново.")
        await state.clear()
        return
    
    processing_msg = await callback.message.answer("🔄 Удаляю фон и применяю выбранный фон...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = os.path.join(temp_dir, "result.png" if bg_choice == "transparent" else "result.jpg")
            
            await asyncio.to_thread(
                process_image_background,
                BytesIO(original_image),
                bg_choice,
                result_path
            )
            
            await callback.message.answer_document(
                FSInputFile(
                    result_path,
                    filename=f"no_background_{bg_choice}.{'png' if bg_choice == 'transparent' else 'jpg'}"
                )
            )
            
            await delete_previous_messages(callback.message)
            await processing_msg.delete()
            
            await callback.message.answer(
                "✅ Готово! Фон успешно удален.",
                reply_markup=InlineKeyboardBuilder()
                .button(text="⬅️ В главное меню", callback_data="back_to_menu")
                .as_markup()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        await processing_msg.delete()
        await callback.message.answer(
            f"❌ Произошла ошибка при обработке изображения: {str(e)}",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ В главное меню", callback_data="back_to_menu")
            .as_markup()
        )
    
    await state.clear()


def process_image_background(image_data: BytesIO, bg_choice: str, output_path: str):
    """Удаляет фон с изображения и применяет выбранный фон."""
    img = Image.open(image_data)
    result = remove(img)
    
    if bg_choice == "transparent":
        result.save(output_path, format="PNG")
    else:
        background = Image.new("RGB", result.size, (255, 255, 255) if bg_choice == "white" else (135, 206, 235))
        background.paste(result, (0, 0), result)
        background.save(output_path, format="JPEG", quality=95)
    
    return output_path