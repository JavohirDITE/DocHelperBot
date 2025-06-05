#!/usr/bin/env python
import asyncio
import json
import logging
import os
import sys
import requests
import socket
import traceback
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaAudio, InputFile, File
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
from telegram.ext.filters import Filters

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import BotCommand, BotCommandScope
from aiogram.utils import executor

from vk_funcs import ep_vk_search, ep_vk_audio_by_ids, ep_vk_finish, download_audio, download_cover, renew_connection
from shazam_funcs import shazam_recognize

from auths import AUTHS
from handlers import register_handlers
from config import Config
from database import Database
from vk_client import VKClient
from utils.logger import setup_logger

socket._GLOBAL_DEFAULT_TIMEOUT = 100

n_results_per_page = 6

updater = None

SAVED = {}

# Настройка логирования
logger = setup_logger(__name__)

class BotStates(StatesGroup):
    waiting_for_search = State()
    waiting_for_album_name = State()

def log(*args):
    logger.info(*args)

def info(*args):
    logger.info(*args)

def debug(*args):
    logger.debug(*args)

def warning(*args):
    logger.warning(*args)

async def set_bot_commands(bot: Bot):
    """Устанавливает меню команд бота"""
    commands = [
        BotCommand(command="start", description="🎵 Запустить бота"),
        BotCommand(command="search", description="🔍 Поиск музыки"),
        BotCommand(command="albums", description="📁 Мои альбомы"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="settings", description="⚙️ Настройки"),
    ]
    
    await bot.set_my_commands(commands, BotCommandScope(type="default"))
    logger.info("Команды бота установлены")

async def on_startup(dp: Dispatcher):
    """Выполняется при запуске бота"""
    logger.info("Бот запускается...")
    
    # Устанавливаем команды
    await set_bot_commands(dp.bot)
    
    # Инициализируем базу данных
    db = Database()
    await db.init_db()
    
    # Инициализируем VK клиент
    vk_client = VKClient()
    await vk_client.init()
    
    logger.info("Бот успешно запущен!")

async def on_shutdown(dp: Dispatcher):
    """Выполняется при остановке бота"""
    logger.info("Бот останавливается...")
    
    # Закрываем соединения
    await dp.storage.close()
    await dp.storage.wait_closed()
    
    logger.info("Бот остановлен")

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Здравствуй! Ищу и качаю музыку с вконтакте, пиши что надо найти')

def renew(update: Update, context: CallbackContext) -> None:
    try:
        renew_connection()
        update.message.reply_text('VK connection renewed')
    except:
        traceback.print_exc()
        try:
            update.message.reply_text('Error..')
        except:
            pass

MAX_MESSAGE_LEN = 500
def send_exc(message, s, print_also=True):
    if print_also:
        print(s)

    try:
        message.reply_text(s[:MAX_MESSAGE_LEN])
        if len(s) > MAX_MESSAGE_LEN:
            send_exc(message, s[MAX_MESSAGE_LEN:], print_also=False)
    except:
        traceback.print_exc()

def msg_add_text(msg, s):
    log(s)
    msg.text = msg.text + s
    msg.edit_text(msg.text)

def button(update: Update, context: CallbackContext) -> None:
    global DEBUG
    DEBUG['context'] = context
    DEBUG['update'] = update

    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    
    msg = query.message.reply_text("думаю..")
    
    log_fun = lambda s: msg_add_text(msg, s)
    
    ids = query.data
    
    if ids[0] == '{':
        # page stuff!
        
        ts = ids[1:].split('|')
        
        r = {'q': ts[0], 'page': int(ts[1])}
        
        info('looking at page %i for %s'
             % (r['page'], r['q']))
        
        log_fun('ищу..')

        page_search(r['q'], query.message, page=int(r['page']), edit=True)
        
        msg.delete()
    else:
        global SAVED
        
        if ids not in SAVED:
            info('%s not in SAVED! getting from vk..' % ids)
            msg_add_text(msg, 'смотрю данные..')
            r = ep_vk_audio_by_ids(ids)
            SAVED[ids] = r
        
        r = SAVED[ids]
        
        DEBUG['msg'] = msg
        
        info('Getting %s : %s' % (ids, r['title_str']))
        
        print(r)
    
        try:
            content = download_audio(r['url'], log_fun)
        
            thumb = None
            if r['track_covers']:
                thumb = download_cover(r['track_covers'], log_fun)
            else:
                thumb = None
            
            log_fun('отправляю..')

            msg2 = query.message.reply_audio(
                content,
                duration=r['duration'],
                title=r['title'],
                performer=r['artist'],
                thumb=thumb,
            )
            
            DEBUG['reply_audio'] = msg2
            
            info('Got %s : %s' % (ids, r['title_str']))

            msg.delete()
        except Exception as e:
            log_fun('ошибка')
            warning(str(r))
            warning(traceback.format_exc())
            # send_exc(query.message, traceback.format_exc())

            try:
                query.message.reply_audio(
                    r['url'],
                    title=r['title'],
                    performer=r['artist'],
                )
            except:
                traceback.print_exc()

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Use /start to test this bot.")

def page_button(q, page, delta_n):
    return InlineKeyboardButton(
        "<" if delta_n < 0 else ">", 
        callback_data='{'+q+'|'+str(page + delta_n) # json.dumps({'q':q,'page':page+1})
    )

def prepare_keyboard(q, R, page):
    global SAVED
    
    keyboard = [
        [InlineKeyboardButton(
            r['title_str'],
            callback_data=r['ids_string']
        )]
        for j, r in enumerate(R)
    ]
    
    prev_page_btn = page_button(q, page, -1)
    next_page_btn = page_button(q, page, 1)
    
    page_btns = []
    if page > 0:
        page_btns.append(prev_page_btn)
    if len(R) >= n_results_per_page:
        page_btns.append(next_page_btn)
    
    if len(page_btns) > 0:
        keyboard.append(page_btns)
    
    return keyboard

def audio_or_voice(update: Update, context: CallbackContext) -> None:
    
    print(update.message)

    DEBUG['msgs'].append(update.message)    
    
    file_data = update.message.audio or update.message.voice
    file = update.message.bot.get_file(file_data.file_id)
    
    content = file.download_as_bytearray()
    print('recognizing file..')
    rec = shazam_recognize(content)
    
    print(rec)
    DEBUG['rec'] = rec
    
    if len(rec['matches']) == 0:
        update.message.reply_text('Nothing found, sorry..')     
   
    else:
        page_search(
            rec['track']['title']+' - '+rec['track']['subtitle'],
            update.message
        )

def message(update: Update, context: CallbackContext) -> None:
    page_search(update.message.text, update.message)

def page_search(s, message, page=0, edit=False):
    info('Looking for ' + s)
    
    R = ep_vk_search(s, n_results_per_page=n_results_per_page, page=page)
    info('Found : %i results' % len(R))
    
    if len(R) == 0:
        info('nothing..')
        message.reply_text('Ничего не нашлось..')
    else:
        global SAVED
        for r in R:
            SAVED[r['callback_data']] = {k: r[k] for k in r}
       
        keyboard = prepare_keyboard(s, R, page)
        reply_markup = InlineKeyboardMarkup(keyboard)
        if edit:
            message.edit_reply_markup(reply_markup)
        else:
            message.reply_text('Вот что нашёл:', reply_markup=reply_markup)

def main():
    global updater
    # Create the Updater and pass it your bot's token.
    updater = Updater(AUTHS[2])

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('renew', renew))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, message))
    updater.dispatcher.add_handler(MessageHandler(Filters.audio | Filters.voice, audio_or_voice))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))

    me = updater.bot.getMe()
    
    print(f'I am:\nname:{me.first_name} username:{me.username} id:{me.id}\nSecurity token:\n{AUTHS[2]}')
    
    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()
    
    ep_vk_finish()

if __name__ == '__main__':
    print('This is ep_vk_music__bot')
    main()
