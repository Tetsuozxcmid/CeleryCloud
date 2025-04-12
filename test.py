import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
import requests

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()


NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
PAYMENT_CURRENCY = "usd"  # Валюта цены
CRYPTO_COIN = "btc"       # Криптовалюта для оплаты

temp_payments = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Введите /pay <сумма> для создания платежа\n"
        "Пример: /pay 10"
    )

@dp.message(Command("pay"))
async def create_payment(message: types.Message):
    try:
        amount = float(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Некорректная сумма. Пример: /pay 10")
        return


    headers = {"x-api-key": NOWPAYMENTS_API_KEY}
    data = {
        "price_amount": amount,
        "price_currency": PAYMENT_CURRENCY,
        "pay_currency": CRYPTO_COIN,
        "ipn_callback_url": "https://your-webhook-url.com/payments",  # Для автоматического подтверждения
        "order_id": f"order_{message.from_user.id}",
    }

    response = requests.post(
        "https://api.nowpayments.io/v1/invoice",
        json=data,
        headers=headers
    ).json()

    if "invoice_url" not in response:
        await message.answer("Ошибка создания платежа")
        return

    payment_id = response["id"]
    temp_payments[payment_id] = {
        "user_id": message.from_user.id,
        "amount": amount,
        "status": "pending"
    }

    await message.answer(
        f"Оплатите {amount} {PAYMENT_CURRENCY} в {CRYPTO_COIN.upper()}\n"
        f"Ссылка: {response['invoice_url']}\n\n"
        "После оплаты нажмите /check_payment"
    )

@dp.message(Command("check_payment"))
async def check_payment(message: types.Message):
    for payment_id, data in temp_payments.items():
        if data["user_id"] == message.from_user.id:
            headers = {"x-api-key": NOWPAYMENTS_API_KEY}
            status = requests.get(
                f"https://api.nowpayments.io/v1/payment/{payment_id}",
                headers=headers
            ).json().get("payment_status")

            if status == "finished":
                await message.answer("Платеж подтвержден! Спасибо!")
                user_id = message.reply_to_message.from_user.id
                await bot.ban_chat_member(
                chat_id=message.chat.id,
                user_id=user_id,
                revoke_messages=True)
                del temp_payments[payment_id]
                return

    await message.answer("Оплаченные платежи не найдены")

if __name__ == "__main__":
    from aiogram.enums import ParseMode
    dp.run_polling(bot, parse_mode=ParseMode.HTML)