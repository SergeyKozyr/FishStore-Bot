## Description

Telegram bot for e-commerce, that integrates with CMS, using ![ElasticPath API](https://documentation.elasticpath.com/commerce-cloud/docs/api/index.html).

This bot can:
- List all the wares
- Display a product's picture, price, stock availability and provide a short description
- Add the selected quantity of the product to the cart
- Display the items and a total price in the cart
- Ask for user's email to create a customer in CMS

Each bot's logs are sent to Logging bot via telegram.

## Demo

Start the dialog with this [Telegram bot](https://t.me/FishStoreBot).

![Telegram bot]()

## How to install

1) **Running on a local machine**

Create .env file with the variables:

```
TG_FISHSTORE_BOT_TOKEN
TG_LOGGING_BOT_TOKEN
TG_CHAT_ID
REDIS_HOST
REDIS_PASSWORD
REDIS_PORT
MOLTIN_CLIENT_ID
MOLTIN_CLIENT_SECRET
```

Telegram bot tokens are available after creation in [@BotFather](https://telegram.me/botfather) chat. For your chat id send, a message to [@userinfobot](https://telegram.me/userinfobot).

Create [Redis database](https://redislabs.com/).

Sign up at [ElasticPath(ex-Moltin)](https://elasticpath.com/) and get your credentials [here](https://dashboard.elasticpath.com/).

Install dependencies.

`pip install -r requirements.txt`

Run the script, send a message to the bot.

`python tg-bot.py`

---

2) **Deploying with Heroku**

Clone the repository, sign up or log in at [Heroku](https://www.heroku.com/).

Create a new Heroku app, click on Deploy tab and connect your Github account.

Type in the repository name and click Deploy Branch at the bottom of the page.

Set up environment variables at the Settings tab in Config Vars 

Turn on the `bot` process at Resources tab.

--- 

## Project Goals
The code is written for educational purposes at online-course for web-developers [dvmn.org](https://dvmn.org).
