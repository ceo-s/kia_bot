import os
import re
import uuid
from aiogram.types import Message, CallbackQuery, ContentType, File
from aiogram.methods import SendChatAction
from aiogram import Dispatcher
from aiogram import F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from llm import LLM, EMBEDDINGS_DATABASE
from db import UserDatabase
from log import logger


class States(StatesGroup):
    prompt = State()
    document = State()
    document_reset = State()


MAIN_KEYBOARD = ReplyKeyboardMarkup(keyboard=[

    [KeyboardButton(text="Установить промпт"),
     KeyboardButton(text="Сбросить промпт")],

    [KeyboardButton(text="Добавить документ"),
     KeyboardButton(text="Очистить историю сообщений")]
],
    resize_keyboard=True
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True)

DOCUMENTS_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить "),
         KeyboardButton(text="Перезаписать")],

        [KeyboardButton(text="Отмена")]
    ],
    resize_keyboard=True
)


async def save_file(path: str, file: File, message: Message):
    try:
        await message.bot.download_file(file.file_path, path)
        await message.answer("Документ успешно добавлен", reply_markup=MAIN_KEYBOARD)
    except Exception as ex:
        logger.error(f"File loading failed. {ex}")
        await message.answer("Упс. Кажется произошла ошибка. Чекай логи.", reply_markup=MAIN_KEYBOARD)

    await EMBEDDINGS_DATABASE.add_documents([path.split("/")[-1]])


def format_for_markdown_closure():
    pattern = re.compile(r"[_*\[\]()~>#+-=|{}.!]")

    def func(text) -> str:
        return pattern.sub(lambda x: f"\\{x.group()}", text)
    return func


format_for_markdown = format_for_markdown_closure()


async def get_start(message: Message) -> None:
    await message.answer("""Привет! Я твой личный консультант по матеше!""",
                         reply_markup=MAIN_KEYBOARD)


async def get_cancel_button(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено!", reply_markup=MAIN_KEYBOARD)


async def get_button_delete_history(message: Message):
    await UserDatabase.delete_message_summaries(message.from_user.id)
    await message.answer("История сообщений успешно удалена!")


async def get_button_reset_prompt(message: Message, state: FSMContext):
    res = await UserDatabase.get_prompt(message.from_user.id)
    await message.answer(f"Текущий промпт:\n\n{res or LLM.PROMPT}\n\n\nВведите новый промт!", reply_markup=CANCEL_KEYBOARD)
    await state.set_state(States.prompt)


async def get_new_prompt(message: Message, state: FSMContext):
    await state.clear()
    await UserDatabase.reset_prompt(message.from_user.id, message.text)
    await message.answer("Промпт успешно обновлён!", reply_markup=MAIN_KEYBOARD)


async def get_button_set_default_prompt(message: Message):
    await UserDatabase.reset_prompt(message.from_user.id, "")
    await message.answer("Промпт был сброшен до дефолтного!")


async def get_message(message: Message) -> None:
    user_id = message.from_user.id
    await message.bot.send_chat_action(message.chat.id, "typing")

    summary = await UserDatabase.get_summary(user_id)
    user_prompt = await UserDatabase.get_prompt(user_id) or None
    response, documents, success = await LLM.ask(message.text, summary, prompt=user_prompt)
    await message.answer(format_for_markdown(response), disable_web_page_preview=True, parse_mode="MarkdownV2")
    # await message.answer(response, disable_web_page_preview=True)

    if success:
        await UserDatabase.save_message(user_id, message.text, "user")
        await UserDatabase.save_message(user_id, response, "assistant")

        new_summary, success = await LLM.summarize_history(summary, message.text, response)
        if success:
            logger.info(f"{new_summary=}")
            await UserDatabase.save_summary(user_id, new_summary)


async def get_button_document(message: Message, state: FSMContext):
    await message.answer(f"Пришлите документы!\n\nДопустимые форматы:\n- txt\n- md\n- html", reply_markup=CANCEL_KEYBOARD)
    await state.set_state(States.document)


async def get_document(message: Message, state: FSMContext):
    await state.clear()
    file = await message.bot.get_file(message.document.file_id)

    if not os.path.exists(usr_dir := f"db/text/{message.from_user.id}"):
        os.mkdir(usr_dir)

    if not os.path.exists(f"{usr_dir}/{message.document.file_name}"):
        await save_file(f"{usr_dir}/{message.document.file_name}", file, message)
    else:
        await message.answer("Документ с таким именем уже сущесвтует. Перезаписать или добавить переименовать?", reply_markup=DOCUMENTS_KEYBOARD)
        await state.set_state(States.document_reset)
        await state.set_data({"file": file, "filename": message.document.file_name})


async def get_document_collision_override(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await save_file(f"db/text/{message.from_user.id}/{data['filename']}", data["file"], message)


async def get_document_collision_append(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    new_filename: list[str] = data["filename"].split(".")
    new_filename.insert(1, ".")
    new_filename.insert(1, f"_{uuid.uuid4()}")
    new_filename = "".join(new_filename)
    await save_file(f"db/text/{message.from_user.id}/{new_filename}", data["file"], message)


async def get_document_error(message: Message, state: FSMContext):
    await message.answer("Ты еблан? На документ не похоже. Пришли норм тему или жми отмена.")


def register_handlers(dp: Dispatcher) -> None:
    dp.message.register(get_start, Command(commands=["start"]))
    dp.message.register(get_cancel_button, F.text == "Отмена")
    dp.message.register(get_button_delete_history, F.text ==
                        "Очистить историю сообщений")
    dp.message.register(get_button_reset_prompt, F.text == "Установить промпт")
    dp.message.register(get_new_prompt, States.prompt)
    dp.message.register(get_button_set_default_prompt,
                        F.text == "Сбросить промпт")
    dp.message.register(get_button_document, F.text == "Добавить документ")
    dp.message.register(get_document, States.document, F.document)
    dp.message.register(get_document_collision_append,
                        States.document_reset, F.text == "Добавить")
    dp.message.register(get_document_collision_override,
                        States.document_reset, F.text == "Перезаписать")
    dp.message.register(get_document_error, States.document)
    dp.message.register(get_message)
