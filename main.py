import os
import asyncio
from aiogram import Bot, Dispatcher, Router, types
from dotenv import load_dotenv
from bot.handlers import register_handlers

load_dotenv(".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

print(BOT_TOKEN)

dp = Dispatcher()
register_handlers(dp)


async def main():
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
