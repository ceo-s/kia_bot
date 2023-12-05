from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.methods import SendChatAction
from aiogram import Dispatcher
from aiogram.filters.command import Command
from aiogram import F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from llm import LLM
from db import UserDatabase

from log import logger


class States(StatesGroup):
    prompt = State()


main_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Установить промпт"), KeyboardButton(
    text="Сбросить промпт")], [KeyboardButton(text="Очистить историю сообщений")]], resize_keyboard=True)
cancel_state_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True)


async def get_start(message: Message) -> None:
    await message.answer("""Привет! Я твой личный консультант по матеше!""",
                         reply_markup=main_keyboard)


async def get_cancel_button(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено!", reply_markup=main_keyboard)


async def get_button_delete_history(message: Message):
    await UserDatabase.delete_message_summaries(message.from_user.id)
    await message.answer("История сообщений успешно удалена!")


async def get_button_reset_prompt(message: Message, state: FSMContext):
    res = await UserDatabase.get_prompt(message.from_user.id)
    await message.answer(f"Текущий промпт:\n\n{res or LLM.PROMPT}\n\n\nВведите новый промт!", reply_markup=cancel_state_keyboard)
    await state.set_state(States.prompt)


async def get_new_prompt(message: Message, state: FSMContext):
    await state.clear()
    await UserDatabase.reset_prompt(message.from_user.id, message.text)
    await message.answer("Промпт успешно обновлён!", reply_markup=main_keyboard)


async def get_button_set_default_prompt(message: Message):
    await UserDatabase.reset_prompt(message.from_user.id, "")
    await message.answer("Промпт был сброшен до дефолтного!")


async def get_message(message: Message) -> None:
    user_id = message.from_user.id
    await message.bot.send_chat_action(message.chat.id, "typing")

    summary = await UserDatabase.get_summary(user_id)
    user_prompt = await UserDatabase.get_prompt(user_id) or None
    response, documents, success = await LLM.ask(message.text, summary, prompt=user_prompt)
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
    dp.message.register(get_cancel_button, F.text == "Отмена")
    dp.message.register(get_button_delete_history, F.text ==
                        "Очистить историю сообщений")
    dp.message.register(get_button_reset_prompt, F.text == "Установить промпт")
    dp.message.register(get_new_prompt, States.prompt)
    dp.message.register(get_button_set_default_prompt,
                        F.text == "Сбросить промпт")
    dp.message.register(get_message)
