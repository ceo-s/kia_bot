from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.methods import SendChatAction
from aiogram import Dispatcher
from aiogram.filters.command import Command
from aiogram import F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from llm import LLM
from db import UserDatabase

from log import logger


async def get_start(message: Message) -> None:
    await message.answer("""Я демонстрационный бот, созданный Университетом Искусственного Интеллекта (https://neural-university.ru/) для официального представительства Kia в России.

Задавайте свои вопросы по сайту https://www.kia.ru/""",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Очистить историю сообщений")]], resize_keyboard=True))


async def get_button_delete_history(message: Message):
    await UserDatabase.delete_message_history(message.from_user.id)
    await UserDatabase.delete_message_summaries(message.from_user.id)
    await message.answer("История сообщений успешно удалена!")


async def get_message(message: Message) -> None:
    user_id = message.from_user.id
    await message.bot.send_chat_action(message.chat.id, "typing")

    summary = await UserDatabase.get_summary(user_id)
    response, documents, success = await LLM.ask(message.text, summary)
    await message.answer(response, disable_web_page_preview=True)

    if success:
        await UserDatabase.save_message(user_id, message.text, "user")
        await UserDatabase.save_message(user_id, response, "assistant")

        new_summary, success = await LLM.summarize_history(summary, message.text, response)
        if success:
            logger.info(f"{new_summary=}")
            await UserDatabase.save_summary(user_id, new_summary)


def register_handlers(dp: Dispatcher) -> None:
    dp.message.register(get_start, Command(commands=["start"]))
    dp.message.register(get_button_delete_history, F.text ==
                        "Очистить историю сообщений")
    dp.message.register(get_message)
