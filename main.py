import os
import asyncio
from aiogram import Bot, Dispatcher, Router, types
from dotenv import load_dotenv
from bot.handlers import register_handlers
from bot.middlewares import register_middlewares
from db import UserDatabase
from log import logger

load_dotenv(".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

dp = Dispatcher()

register_handlers(dp)
register_middlewares(dp)


async def main():
    bot = Bot(BOT_TOKEN)
    await UserDatabase.create()
    logger.info("Polling beginning")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    logger.info("Closing project")
