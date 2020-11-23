import requests
import os
import logging
import redis
import time

from dotenv import load_dotenv
from functools import partial
from textwrap import dedent

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Filters, Updater, CallbackQueryHandler, CommandHandler, MessageHandler

from moltin import (get_access_token, get_all_products, add_to_cart,
                    remove_from_cart, create_customer)
from telegram_bot_tools import TelegramLogsHandler, get_menu, get_cart_reply


logger = logging.getLogger(__name__)


def display_menu(bot, update):
    if update.message:
        message = update.message
        chat_id = message.from_user.id

    elif update.callback_query:
        message = update.callback_query.message
        chat_id = update.callback_query.from_user.id

    if not db.get(f'{chat_id}-token'):
        access_token = get_moltin_token()
        db.set(f'{chat_id}-token', access_token, ex=3600)

    access_token = db.get(f'{chat_id}-token')
    products = get_all_products(access_token)
    menu = get_menu(products)
    menu.append([InlineKeyboardButton('Cart', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(menu)

    message.reply_text('Please choose:', reply_markup=reply_markup)

    return 'HANDLE_MENU'


def handle_menu(bot, update):
    query = update.callback_query
    chat_id = query.from_user.id

    if not db.get(f'{chat_id}-token'):
        access_token = get_moltin_token()
        db.set(f'{chat_id}-token', access_token, ex=3600)

    access_token = db.get(f'{chat_id}-token')

    if query.data == 'cart':
        cart_reply, reply_markup = get_cart_reply(access_token, chat_id)
        query.message.reply_text(cart_reply, reply_markup=reply_markup)
        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

        return 'HANDLE_CART'

    else:
        product_id = query.data
        response = requests.get(f'https://api.moltin.com/v2/products/{product_id}', headers={'Authorization': f'Bearer {access_token}'})
        response.raise_for_status()
        product = response.json()['data']
        product_name = product['name']
        product_price = product['meta']['display_price']['with_tax']['formatted']
        product_stock = product['weight']['kg']
        product_description = product['description']
        product_image_id = product['relationships']['main_image']['data']['id']

        response = requests.get(f'https://api.moltin.com/v2/files/{product_image_id}', headers={'Authorization': f'Bearer {access_token}'})
        response.raise_for_status()
        product_image = response.json()['data']['link']['href']

        keyboard = [
            [InlineKeyboardButton('1 kg', callback_data=f'{product_id}:1'),
             InlineKeyboardButton('5 kg', callback_data=f'{product_id}:5'),
             InlineKeyboardButton('10 kg', callback_data=f'{product_id}:10')],
            [InlineKeyboardButton('Back to menu', callback_data='menu')],
            [InlineKeyboardButton('Cart', callback_data='cart')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_photo(chat_id=chat_id, photo=product_image, reply_markup=reply_markup, caption=dedent(f'''

            {product_name}

            {product_price} per kg
            {product_stock} kg in stock

            {product_description} ''')
                       )

        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

        return 'HANDLE_DESCRIPTION'


def handle_description(bot, update):
    query = update.callback_query
    chat_id = query.from_user.id

    if not db.get(f'{chat_id}-token'):
        access_token = get_moltin_token()
        db.set(f'{chat_id}-token', access_token, ex=3600)

    access_token = db.get(f'{chat_id}-token')

    if query.data == 'menu':
        display_menu(bot, update)
        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

        return 'HANDLE_MENU'

    elif query.data == 'cart':
        cart_reply, reply_markup = get_cart_reply(access_token, chat_id)
        query.message.reply_text(cart_reply, reply_markup=reply_markup)
        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

        return 'HANDLE_CART'

    elif ':' in query.data:
        product_id, quantity = query.data.split(':')
        add_to_cart(access_token, chat_id, product_id, quantity)
        query.answer('Product has been added to your cart!')

        return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update):
    query = update.callback_query
    chat_id = query.from_user.id

    if not db.get(f'{chat_id}-token'):
        access_token = get_moltin_token()
        db.set(f'{chat_id}-token', access_token, ex=3600)

    access_token = db.get(f'{chat_id}-token')

    if query.data == 'menu':
        display_menu(bot, update)
        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

        return 'HANDLE_MENU'

    elif query.data == 'pay':
        bot.send_message(chat_id=chat_id, text='Please, send your e-mail address')
        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

        return 'WAITING_EMAIL'

    else:
        product_id = query.data
        remove_from_cart(access_token, chat_id, product_id)
        query.answer('Product has been removed from your cart!')
        cart_reply, reply_markup = get_cart_reply(access_token, chat_id)
        query.message.reply_text(cart_reply, reply_markup=reply_markup)
        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

        return 'HANDLE_CART'


def handle_email(bot, update):
    user = update.message.from_user
    chat_id = user.id

    if not db.get(f'{chat_id}-token'):
        access_token = get_moltin_token()
        db.set(f'{chat_id}-token', access_token, ex=3600)

    access_token = db.get(f'{chat_id}-token')

    name = user.username if user.username else user.first_name
    email = update.message.text

    keyboard = [[InlineKeyboardButton('Back to menu', callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(f'An order was created for: {email}', reply_markup=reply_markup)
    bot.delete_message(chat_id=chat_id, message_id=update.message.message_id - 1)

    create_customer(access_token, name, email)

    return 'HANDLE_CART'


def error(bot, update, error):
    logger.error('Update "%s" caused error "%s"', update, error)


def handle_users_reply(bot, update):
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id

    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'DISPLAYING_MENU'
    else:
        user_state = db.get(chat_id)

    states_functions = {
        'DISPLAYING_MENU': display_menu,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': handle_email
    }

    state_handler = states_functions[user_state]
    next_state = state_handler(bot, update)
    db.set(chat_id, next_state)


if __name__ == '__main__':

    load_dotenv()
    fish_shop_bot_token = os.getenv('TG_FISHSTORE_BOT_TOKEN')
    tg_logging_bot_token = os.getenv('TG_LOGGING_BOT_TOKEN')
    chat_id = os.getenv('TG_CHAT_ID')
    db_host = os.getenv('REDIS_HOST')
    db_port = os.getenv('REDIS_PORT')
    db_password = os.getenv('REDIS_PASSWORD')
    moltin_client_id = os.getenv('MOLTIN_CLIENT_ID')
    moltin_client_secret = os.getenv('MOLTIN_CLIENT_SECRET')

    logging_bot = Bot(token=tg_logging_bot_token)
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(logging_bot, chat_id))
    logger.info('Бот FishStore запущен')

    get_moltin_token = partial(get_access_token, moltin_client_id, moltin_client_secret)

    db = redis.Redis(host=db_host, port=db_port, password=db_password, decode_responses=True)

    updater = Updater(fish_shop_bot_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_error_handler(error)

    while True:
        try:
            updater.start_polling()
            updater.idle()

        except Exception:
            logger.exception('Бот FishStore упал с ошибкой:')
            time.sleep(10)
