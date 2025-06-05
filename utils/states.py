from aiogram.dispatcher.filters.state import State, StatesGroup

class BotStates(StatesGroup):
    """Состояния бота"""
    waiting_for_search = State()
    waiting_for_album_name = State()
