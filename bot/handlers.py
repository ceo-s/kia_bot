from aiogram.types import Message, CallbackQuery, ContentType
from aiogram import Dispatcher
from aiogram.filters.command import Command
from llm import LLM
from db import UserDatabase


async def get_start(message: Message) -> None:
    await UserDatabase.insert_user_if_not_exist(
        message.from_user.id, message.from_user.username)
    await message.answer("Добро пожаловать!")


async def get_message(message: Message) -> None:
    message_history: list[tuple] = await UserDatabase.load_message_history(message.from_user.id)
    message_history = [{"role": el[1], "content": el[0]}
                       for el in message_history]
    response, documents = await LLM.ask(message.text, message_history)
    await UserDatabase.save_message(message.from_user.id, message.text, "user")
    await UserDatabase.save_message(message.from_user.id, response.choices[0].message.content, "assistant")

    response_string = f"Ответ нейросети:\n\n{response.choices[0].message.content}\n\n\n"
    documents_string = f"Найденные документы:\n\n{LLM.documents_to_str(documents)}"
    await message.answer(response_string + documents_string,
                         disable_web_page_preview=True)


def register_handlers(dp: Dispatcher) -> None:
    dp.message.register(get_start, Command(commands=["start"]))
    dp.message.register(get_message)
