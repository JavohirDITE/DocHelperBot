from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    """Основная клавиатура"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton("🔍 Поиск музыки"),
        KeyboardButton("📁 Мои альбомы")
    )
    keyboard.add(
        KeyboardButton("❓ Помощь"),
        KeyboardButton("⚙️ Настройки")
    )
    return keyboard

def get_search_results_keyboard(results, query, page):
    """Клавиатура с результатами поиска"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Добавляем треки
    for track in results:
        track_text = f"🎵 {track['artist']} - {track['title']}"
        if len(track_text) > 60:
            track_text = track_text[:57] + "..."
        
        keyboard.add(
            InlineKeyboardButton(
                track_text,
                callback_data=f"download:{track['id']}"
            )
        )
    
    # Добавляем пагинацию
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"search_page:{query}:{page-1}")
        )
    
    pagination_buttons.append(
        InlineKeyboardButton("➡️ Далее", callback_data=f"search_page:{query}:{page+1}")
    )
    
    if pagination_buttons:
        keyboard.row(*pagination_buttons)
    
    return keyboard

def get_track_actions_keyboard(track_id):
    """Клавиатура с действиями для трека"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("📁 Добавить в альбом", callback_data=f"add_album:{track_id}")
    )
    return keyboard

def get_albums_keyboard(albums, can_create=True):
    """Клавиатура со списком альбомов"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for album in albums:
        keyboard.add(
            InlineKeyboardButton(
                f"📁 {album['name']}",
                callback_data=f"album:{album['id']}"
            )
        )
    
    if can_create:
        keyboard.add(
            InlineKeyboardButton("➕ Создать альбом", callback_data="create_album")
        )
    
    return keyboard

def get_albums_selection_keyboard(albums, track_id):
    """Клавиатура для выбора альбома"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for album in albums:
        keyboard.add(
            InlineKeyboardButton(
                f"📁 {album['name']}",
                callback_data=f"album_add:{album['id']}:{track_id}"
            )
        )
    
    return keyboard

def get_album_keyboard(album_id):
    """Клавиатура для управления альбомом"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("▶️ Воспроизвести", callback_data=f"play_album:{album_id}"),
        InlineKeyboardButton("📝 Переименовать", callback_data=f"rename_album:{album_id}")
    )
    keyboard.add(
        InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_album:{album_id}")
    )
    return keyboard
