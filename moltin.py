import requests
from textwrap import dedent


def get_access_token(client_id, client_secret, db, chat_id):
    access_token = db.get(f'{chat_id}-token')

    if not access_token:
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
        response.raise_for_status()
        response_body = response.json()
        access_token = response_body['access_token']
        expires_in = response_body['expires_in']
        db.set(f'{chat_id}-token', access_token, ex=expires_in)

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


def get_product_details(access_token, product_id):
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

    caption = dedent(f'''

            {product_name}

            {product_price} per kg
            {product_stock} kg in stock

            {product_description} ''')

    return product_image, caption


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
