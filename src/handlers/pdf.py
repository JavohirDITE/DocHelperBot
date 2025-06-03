import os
import tempfile
import logging
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import fitz
from PIL import Image

from handlers.utils import delete_previous_messages

router = Router()
logger = logging.getLogger(__name__)

class PDFStates(StatesGroup):
    waiting_for_images = State()
    waiting_for_pdfs_to_merge = State()
    waiting_for_pdf_to_compress = State()


@router.callback_query(F.data == "menu:images_to_pdf")
async def start_images_to_pdf(callback: CallbackQuery, state: FSMContext):
    """Начало процесса конвертации изображений в PDF."""
    await callback.answer()
    
    # Устанавливаем состояние ожидания изображений
    await state.set_state(PDFStates.waiting_for_images)
    await state.update_data(images=[])
    
    await delete_previous_messages(callback.message)
    
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


@router.message(F.photo, PDFStates.waiting_for_images)
@router.message(F.document & F.document.mime_type.startswith("image/"), PDFStates.waiting_for_images)
async def process_image_for_pdf(message: Message, state: FSMContext):
    """Обработка изображения для конвертации в PDF."""
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id
        
        file = await message.bot.get_file(file_id)
        file_content = await message.bot.download_file(file.file_path)
        
        data = await state.get_data()
        images = data.get("images", [])
        images.append(file_content.read())
        
        await state.update_data(images=images)
        
        await message.answer(
            f"✅ Изображение добавлено. Всего изображений: {len(images)}.\n"
            "Отправьте еще изображения или нажмите «Создать PDF».",
            reply_markup=InlineKeyboardBuilder()
            .button(text="📄 Создать PDF", callback_data="create_pdf")
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .adjust(1)
            .as_markup()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        await message.answer(
            f"❌ Ошибка при обработке изображения: {str(e)}",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .as_markup()
        )


@router.callback_query(F.data == "create_pdf", PDFStates.waiting_for_images)
async def create_pdf_from_images(callback: CallbackQuery, state: FSMContext):
    """Создание PDF из изображений."""
    await callback.answer()
    
    data = await state.get_data()
    images = data.get("images", [])
    
    if not images:
        await callback.message.answer(
            "❌ Вы не отправили ни одного изображения. Пожалуйста, отправьте хотя бы одно изображение.",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .as_markup()
        )
        return
    
    processing_msg = await callback.message.answer("🔄 Создаю PDF из изображений...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = os.path.join(temp_dir, "result.pdf")
            
            # Используем альтернативный метод создания PDF
            create_pdf_from_images_pil(images, pdf_path)
            
            await callback.message.answer_document(
                FSInputFile(pdf_path, filename="images_to_pdf.pdf")
            )
            
            await delete_previous_messages(callback.message)
            await processing_msg.delete()
            
            await callback.message.answer(
                "✅ Готово! PDF успешно создан.",
                reply_markup=InlineKeyboardBuilder()
                .button(text="⬅️ В главное меню", callback_data="back_to_menu")
                .as_markup()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при создании PDF: {e}")
        await processing_msg.delete()
        await callback.message.answer(
            f"❌ Произошла ошибка при создании PDF: {str(e)}",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ В главное меню", callback_data="back_to_menu")
            .as_markup()
        )
    
    await state.clear()


def create_pdf_from_images_list(images_data, output_path):
    """Создает PDF из списка изображений с помощью PyMuPDF."""
    pdf = fitz.open()
    
    for img_data in images_data:
        img = Image.open(BytesIO(img_data))
        
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        
        img_doc = fitz.open("jpg", img_bytes.read())
        pdf.insert_pdf(img_doc)
    
    pdf.save(output_path)
    pdf.close()


def create_pdf_from_images_pil(images_data, output_path):
    """Создает PDF из списка изображений с помощью PIL."""
    images = []
    
    for img_data in images_data:
        img = Image.open(BytesIO(img_data))
        
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        images.append(img)
    
    if images:
        # Первое изображение сохраняем как PDF
        first_image = images[0]
        first_image.save(
            output_path, 
            "PDF", 
            resolution=100.0, 
            save_all=True,
            append_images=images[1:] if len(images) > 1 else []
        )


@router.callback_query(F.data == "menu:merge_pdf")
async def start_merge_pdf(callback: CallbackQuery, state: FSMContext):
    """Начало процесса объединения PDF-файлов."""
    await callback.answer()
    
    # Устанавливаем состояние ожидания PDF-файлов
    await state.set_state(PDFStates.waiting_for_pdfs_to_merge)
    await state.update_data(pdfs=[])
    
    await delete_previous_messages(callback.message)
    
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


@router.message(F.document & F.document.mime_type == "application/pdf", PDFStates.waiting_for_pdfs_to_merge)
async def process_pdf_for_merge(message: Message, state: FSMContext):
    """Обработка PDF-файла для объединения."""
    try:
        file = await message.bot.get_file(message.document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        
        data = await state.get_data()
        pdfs = data.get("pdfs", [])
        
        pdfs.append({
            "content": file_content.read(),
            "name": message.document.file_name
        })
        
        await state.update_data(pdfs=pdfs)
        
        await message.answer(
            f"✅ PDF-файл добавлен. Всего файлов: {len(pdfs)}.\n"
            "Отправьте еще PDF-файлы или нажмите «Объединить PDF».",
            reply_markup=InlineKeyboardBuilder()
            .button(text="📑 Объединить PDF", callback_data="merge_pdf_files")
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .adjust(1)
            .as_markup()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке PDF: {e}")
        await message.answer(
            f"❌ Ошибка при обработке PDF: {str(e)}",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .as_markup()
        )


@router.callback_query(F.data == "merge_pdf_files", PDFStates.waiting_for_pdfs_to_merge)
async def merge_pdf_files(callback: CallbackQuery, state: FSMContext):
    """Объединение PDF-файлов."""
    await callback.answer()
    
    data = await state.get_data()
    pdfs = data.get("pdfs", [])
    
    if len(pdfs) < 2:
        await callback.message.answer(
            "❌ Для объединения необходимо как минимум два PDF-файла. Пожалуйста, отправьте еще файлы.",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ Назад", callback_data="back_to_menu")
            .as_markup()
        )
        return
    
    processing_msg = await callback.message.answer("🔄 Объединяю PDF-файлы...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            merged_pdf_path = os.path.join(temp_dir, "merged.pdf")
            merge_pdfs([pdf["content"] for pdf in pdfs], merged_pdf_path)
            
            await callback.message.answer_document(
                FSInputFile(merged_pdf_path, filename="merged.pdf")
            )
            
            await delete_previous_messages(callback.message)
            await processing_msg.delete()
            
            await callback.message.answer(
                "✅ Готово! PDF-файлы успешно объединены.",
                reply_markup=InlineKeyboardBuilder()
                .button(text="⬅️ В главное меню", callback_data="back_to_menu")
                .as_markup()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при объединении PDF: {e}")
        await processing_msg.delete()
        await callback.message.answer(
            f"❌ Произошла ошибка при объединении PDF: {str(e)}",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ В главное меню", callback_data="back_to_menu")
            .as_markup()
        )
    
    await state.clear()


def merge_pdfs(pdf_contents, output_path):
    """Объединяет несколько PDF-файлов в один."""
    merged_pdf = fitz.open()
    
    for pdf_content in pdf_contents:
        pdf = fitz.open("pdf", pdf_content)
        merged_pdf.insert_pdf(pdf)
    
    merged_pdf.save(output_path)
    merged_pdf.close()


@router.callback_query(F.data == "menu:compress_pdf")
async def start_compress_pdf(callback: CallbackQuery, state: FSMContext):
    """Начало процесса сжатия PDF-файла."""
    await callback.answer()
    
    # Устанавливаем состояние ожидания PDF-файла
    await state.set_state(PDFStates.waiting_for_pdf_to_compress)
    
    await delete_previous_messages(callback.message)
    
    await callback.message.answer(
        "🗜 <b>Сжатие PDF</b>\n\n"
        "Отправьте мне PDF-файл, который нужно сжать.",
        reply_markup=InlineKeyboardBuilder()
        .button(text="⬅️ Назад", callback_data="back_to_menu")
        .as_markup()
    )


@router.message(F.document & F.document.mime_type == "application/pdf", PDFStates.waiting_for_pdf_to_compress)
async def process_pdf_for_compression(message: Message, state: FSMContext):
    """Обработка PDF-файла для сжатия."""
    processing_msg = await message.answer("🔄 Сжимаю PDF-файл...")
    
    try:
        file = await message.bot.get_file(message.document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_pdf_path = os.path.join(temp_dir, "input.pdf")
            compressed_pdf_path = os.path.join(temp_dir, "compressed.pdf")
            
            with open(input_pdf_path, "wb") as f:
                f.write(file_content.read())
            
            original_size, compressed_size = compress_pdf(input_pdf_path, compressed_pdf_path)
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            await message.answer_document(
                FSInputFile(compressed_pdf_path, filename=f"compressed_{message.document.file_name}")
            )
            
            await delete_previous_messages(message)
            await processing_msg.delete()
            
            await message.answer(
                f"✅ Готово! PDF-файл успешно сжат.\n\n"
                f"📊 Статистика сжатия:\n"
                f"• Исходный размер: {format_size(original_size)}\n"
                f"• Сжатый размер: {format_size(compressed_size)}\n"
                f"• Уменьшение: {compression_ratio:.1f}%",
                reply_markup=InlineKeyboardBuilder()
                .button(text="⬅️ В главное меню", callback_data="back_to_menu")
                .as_markup()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при сжатии PDF: {e}")
        await processing_msg.delete()
        await message.answer(
            f"❌ Произошла ошибка при сжатии PDF: {str(e)}",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ В главное меню", callback_data="back_to_menu")
            .as_markup()
        )
    
    await state.clear()


def compress_pdf(input_path, output_path):
    """Сжимает PDF-файл."""
    original_size = os.path.getsize(input_path)
    
    pdf = fitz.open(input_path)
    pdf.save(
        output_path,
        garbage=4,
        deflate=True,
        clean=True,
        linear=True
    )
    pdf.close()
    
    compressed_size = os.path.getsize(output_path)
    return original_size, compressed_size


def format_size(size_bytes):
    """Форматирует размер в байтах в человекочитаемый формат."""
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} МБ"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} ГБ"