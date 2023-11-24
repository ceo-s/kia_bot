from aiogram.types import Message, CallbackQuery, ContentType
from aiogram import Dispatcher
from aiogram.filters.command import Command
from llm import send_request


async def get_start(message: Message) -> None:
    await message.answer("Добро пожаловать!")


async def get_message(message: Message) -> None:
    await message.answer(await send_request(message.text))


def register_handlers(dp: Dispatcher) -> None:
    dp.message.register(get_start, Command(commands=["start"]))
    dp.message.register(get_message)
