from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from handlers.utils import delete_previous_messages

router = Router()

def get_main_menu_keyboard():
    """Создает клавиатуру главного меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎭 Удаление фона", callback_data="menu:background")
    builder.button(text="📸 Изображения → PDF", callback_data="menu:images_to_pdf")
    builder.button(text="📑 Объединить PDF", callback_data="menu:merge_pdf")
    builder.button(text="🗜 Сжать PDF", callback_data="menu:compress_pdf")
    builder.button(text="🔍 Распознать текст (OCR)", callback_data="menu:ocr")
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    await message.answer(
        "👋 Добро пожаловать в DocHelperBot!\n\n"
        "Я помогу вам с обработкой документов и изображений:\n"
        "• Удаление фона с изображений\n"
        "• Конвертация изображений в PDF\n"
        "• Объединение PDF-файлов\n"
        "• Сжатие PDF-файлов\n"
        "• Распознавание текста на изображениях (OCR)\n\n"
        "Выберите нужную функцию:",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()
    
    # Очищаем состояние
    await state.clear()
    
    await delete_previous_messages(callback.message)
    
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )