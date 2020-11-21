import requests
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from textwrap import dedent


class MyLogsHandler(logging.Handler):
    def __init__(self, logging_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.logging_bot = logging_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.logging_bot.send_message(chat_id=self.chat_id, text=log_entry)


def get_access_token(client_id, client_secret):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()
    access_token = response.json()['access_token']

    return access_token


def get_all_products(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    response.raise_for_status()
    products = response.json()['data']

    return products


def get_menu(products):
    keyboard = [
        [InlineKeyboardButton(product['name'], callback_data=product['id'])] for product in products
    ]

    return keyboard


def add_to_cart(access_token, chat_id, product_id, quantity):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    data = {
        "data": {
            "id": product_id,
            "type": "cart_item",
            "quantity": int(quantity)}
    }
    response = requests.post(f'https://api.moltin.com/v2/carts/{str(chat_id)}/items', headers=headers, json=data)
    response.raise_for_status()

    return response.json()['data']


def get_cart_items(access_token, cart_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{str(cart_id)}/items', headers=headers)
    response.raise_for_status()
    cart_items = response.json()['data']

    return cart_items


def get_cart_total_price(access_token, cart_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}', headers=headers)
    response.raise_for_status()
    cart = response.json()['data']
    cart_total_price = cart['meta']['display_price']['with_tax']['formatted']

    return cart_total_price


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


def remove_from_cart(access_token, cart_id, product_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.delete(f'https://api.moltin.com/v2/carts/{cart_id}/items/{product_id}', headers=headers)
    response.raise_for_status()


def create_customer(access_token, name, email):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    data = {
        "data": {
            "type": "customer",
            "name": name,
            "email": email,
        }
    }

    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=data)
    response.raise_for_status()
    customer = response.json()['data']

    return customer['id']
