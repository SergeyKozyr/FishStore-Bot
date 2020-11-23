import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from textwrap import dedent
from moltin import get_cart_total_price, get_cart_items


class TelegramLogsHandler(logging.Handler):
    def __init__(self, logging_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.logging_bot = logging_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.logging_bot.send_message(chat_id=self.chat_id, text=log_entry)


def get_menu(products):
    keyboard = [
        [InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in products
    ]

    return keyboard


def get_cart_reply(access_token, cart_id):
    cart_items = get_cart_items(access_token, cart_id)
    cart_total_price = get_cart_total_price(access_token, cart_id)

    keyboard = [[InlineKeyboardButton(f'Remove {product["name"]} from the cart', callback_data=product['id'])] for product in cart_items]
    keyboard.extend(
        [
            [InlineKeyboardButton('Checkout', callback_data='pay')],
            [InlineKeyboardButton('Back to menu', callback_data='menu')],
        ]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    reply = dedent('\n'.join(f'''

        {product["name"]}
        {product["description"]}
        {product["meta"]["display_price"]["with_tax"]["unit"]["formatted"]} per kg
        {product["quantity"]}kg in cart for {product["meta"]["display_price"]["with_tax"]["value"]["formatted"]}''' for product in cart_items)

                   )

    cart_reply = '\n'.join([reply, f'Total: {cart_total_price}'])

    return cart_reply, reply_markup
