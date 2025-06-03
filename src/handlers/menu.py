from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

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


@router.callback_query(F.data.startswith("menu:"))
async def process_menu_selection(callback: CallbackQuery):
    """Обработчик выбора пункта меню."""
    await callback.answer()
    
    action = callback.data.split(":")[1]
    
    await delete_previous_messages(callback.message)
    
    if action == "background":
        await callback.message.answer(
            "🎭 <b>Удаление фона</b>\n\n"
            "Отправьте мне изображение, с которого нужно удалить фон.",
            reply_markup=InlineKeyboardBuilder().button(
                text="⬅️ Назад", callback_data="back_to_menu"
            ).as_markup()
        )
    
    elif action == "images_to_pdf":
        await callback.message.answer(
            "📸 <b>Изображения → PDF</b>\n\n"
            "Отправьте мне одно или несколько изображений, которые нужно объединить в PDF.\n"
            "После отправки всех изображений нажмите кнопку «Создать PDF».",
            reply_markup=InlineKeyboardBuilder()
            .button(text="📄 Создать PDF", callback_data="create_pdf")
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .adjust(1)
            .as_markup()
        )
    
    elif action == "merge_pdf":
        await callback.message.answer(
            "📑 <b>Объединение PDF</b>\n\n"
            "Отправьте мне два или более PDF-файла, которые нужно объединить.\n"
            "После отправки всех файлов нажмите кнопку «Объединить PDF».",
            reply_markup=InlineKeyboardBuilder()
            .button(text="📑 Объединить PDF", callback_data="merge_pdf_files")
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .adjust(1)
            .as_markup()
        )
    
    elif action == "compress_pdf":
        await callback.message.answer(
            "🗜 <b>Сжатие PDF</b>\n\n"
            "Отправьте мне PDF-файл, который нужно сжать.",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .as_markup()
        )
    
    elif action == "ocr":
        await callback.message.answer(
            "🔍 <b>Распознавание текста (OCR)</b>\n\n"
            "Отправьте мне изображение с текстом для распознавания.",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .as_markup()
        )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.answer()
    
    await delete_previous_messages(callback.message)
    
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )