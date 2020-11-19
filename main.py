import requests
import os
import logging
import redis
from moltin_utils import (get_menu, get_access_token, get_all_products,
                          add_to_cart, remove_from_cart, get_cart_reply
                          )
from dotenv import load_dotenv
from functools import partial
from textwrap import dedent

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler


logger = logging.getLogger(__name__)


def start(bot, update):
    access_token = get_moltin_token()
    products = get_all_products(access_token)
    menu = get_menu(products)
    menu.append([InlineKeyboardButton('Корзина', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(menu)

    if update.message:
        update.message.reply_text('Please choose:', reply_markup=reply_markup)

    elif update.callback_query:
        query = update.callback_query
        chat_id = query.from_user.id
        bot.send_message(chat_id=chat_id, reply_markup=reply_markup, text='Please choose:')

    return 'HANDLE_MENU'


def handle_menu(bot, update):
    query = update.callback_query
    chat_id = query.from_user.id
    access_token = get_moltin_token()
    bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

    if query.data == 'cart':
        cart_reply, reply_markup = get_cart_reply(access_token, chat_id)
        query.message.reply_text(cart_reply, reply_markup=reply_markup)

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
            [InlineKeyboardButton('1 кг', callback_data=f'{product_id}:1'),
             InlineKeyboardButton('5 кг', callback_data=f'{product_id}:5'),
             InlineKeyboardButton('10 кг', callback_data=f'{product_id}:10')],
            [InlineKeyboardButton('Назад', callback_data='back')],
            [InlineKeyboardButton('Корзина', callback_data='cart')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_photo(chat_id=chat_id, photo=product_image, reply_markup=reply_markup, caption=dedent(
            f'''
            {product_name}

            {product_price} per kg
            {product_stock} kg in stock

            {product_description}
            ''')
        )

        return 'HANDLE_DESCRIPTION'


def handle_description(bot, update):
    query = update.callback_query
    chat_id = query.from_user.id
    access_token = get_moltin_token()

    if query.data == 'back':
        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
        start(bot, update)

        return 'HANDLE_MENU'

    elif query.data == 'cart':
        bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
        cart_reply, reply_markup = get_cart_reply(access_token, chat_id)
        query.message.reply_text(cart_reply, reply_markup=reply_markup)

        return 'HANDLE_CART'

    elif ':' in query.data:
        product_id, quantity = query.data.split(':')
        add_to_cart(access_token, chat_id, product_id, quantity)
        query.answer('Product has been added to your cart!')

        return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update):
    query = update.callback_query
    chat_id = query.from_user.id
    access_token = get_moltin_token()
    bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

    if query.data == 'menu':
        start(bot, update)

        return 'HANDLE_MENU'

    else:
        product_id = query.data
        remove_from_cart(access_token, chat_id, product_id)
        query.answer('Product has been removed from your cart!')
        cart_reply, reply_markup = get_cart_reply(access_token, chat_id)
        query.message.reply_text(cart_reply, reply_markup=reply_markup)

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
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode()

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
    }
    state_handler = states_functions[user_state]

    try:
        next_state = state_handler(bot, update)
        db.set(chat_id, next_state)

    except Exception:
        logger.exception('Бот FishStore упал с ошибкой:')


if __name__ == '__main__':

    load_dotenv()
    fish_shop_bot_token = os.getenv('TG_FISHSTORE_BOT_TOKEN')
    db_host = os.getenv('REDIS_HOST')
    db_port = os.getenv('REDIS_PORT')
    db_password = os.getenv('REDIS_PASSWORD')
    moltin_client_id = os.getenv('MOLTIN_CLIENT_ID')

    get_moltin_token = partial(get_access_token, moltin_client_id)

    db = redis.Redis(host=db_host, port=db_port, password=db_password)

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    updater = Updater(fish_shop_bot_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_error_handler(error)

    updater.start_polling()

    updater.idle()
