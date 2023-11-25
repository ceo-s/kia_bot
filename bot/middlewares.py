from aiogram import Dispatcher
from aiogram.types import Update
from typing import Callable, Awaitable, Any
from db import UserDatabase


async def register_users(handler: Callable[[Update, dict[str, Any]], Awaitable[Any]], event: Update, data: dict[str, Any]):
    await UserDatabase.insert_user_if_not_exist(event.message.from_user.id, event.message.from_user.id)
    return await handler(event, data)


def register_middlewares(dp: Dispatcher):
    dp.update.middleware(register_users)
