import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.menu import router as menu_router
from handlers.background import router as background_router
from handlers.pdf import router as pdf_router
from handlers.ocr import router as ocr_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()


async def main():
    """Основная функция запуска бота."""
    # Получение токена из переменных окружения
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("Не указан BOT_TOKEN в переменных окружения!")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(menu_router)
    dp.include_router(background_router)
    dp.include_router(pdf_router)
    dp.include_router(ocr_router)

    # Удаление вебхука на случай, если бот был запущен с вебхуком ранее
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск поллинга
    logger.info("Бот запущен и работает...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())