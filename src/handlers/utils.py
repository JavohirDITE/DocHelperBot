import logging
from aiogram.types import Message

logger = logging.getLogger(__name__)

async def delete_previous_messages(message: Message, count: int = 5) -> None:
    """Удаляет предыдущие сообщения бота для поддержания чистоты чата."""
    try:
        chat_id = message.chat.id
        message_id = message.message_id
        
        await message.delete()
        
        for i in range(1, count + 1):
            try:
                await message.bot.delete_message(chat_id, message_id - i)
            except Exception:
                pass
    
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщений: {e}")