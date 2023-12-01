import os
import json
import asyncio
import aiosqlite
from typing import Any, Literal

from log import logger

with open("conf.json", "r") as file:
    logger.debug("Loading relational db config")
    conf = json.load(file)

DATABASE_DIR = conf["DB"]["RELATIONAL"]["DATABASE_DIR"]
DATABASE_NAME = conf["DB"]["RELATIONAL"]["DATABASE_NAME"]


class UserDatabase:
    DATABASE_PATH = f"{DATABASE_DIR}/{DATABASE_NAME}"

    @classmethod
    async def create(cls):
        async with aiosqlite.connect(cls.DATABASE_PATH) as db:
            await db.execute("CREATE TABLE if not exists users (id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id TEXT UNIQUE, username TEXT);")
            await db.execute("CREATE TABLE if not exists message_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT NOT NULL, message TEXT NOT NULL, role TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));")
            await db.execute("CREATE TABLE if not exists message_summaries (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT NOT NULL, summary TEXT, FOREIGN KEY(user_id) REFERENCES users(id));")
            await db.commit()
        logger.info("Initialized database.sqlite")

    @classmethod
    async def execute_dml(cls, sql: str, *parameters: Any):
        async with aiosqlite.connect(cls.DATABASE_PATH) as db:
            cursor = await db.cursor()
            await cursor.execute(sql, parameters)
            await db.commit()
            return await cursor.fetchall()

    @classmethod
    async def insert_user_if_not_exist(cls, telegram_user_id: str, telegram_username: str):
        await cls.execute_dml("INSERT OR IGNORE INTO users (tg_id, username) VALUES (?, ?);", telegram_user_id, telegram_username)

    @classmethod
    async def delete_user(cls, telegram_user_id: str):
        await cls.execute_dml("DELETE FROM users WHERE tg_id=?;", telegram_user_id)

    @classmethod
    async def save_message(cls, telegram_user_id: str, message: str, role: Literal["user", "assistant", "system"]):
        await cls.execute_dml("INSERT INTO message_history (user_id, message, role) VALUES ((SELECT id FROM users WHERE tg_id=?), ?, ?);", telegram_user_id, message, role)

    @classmethod
    async def load_message_history(cls, telegram_user_id: str):
        res = await cls.execute_dml("SELECT message, role FROM message_history WHERE user_id=(SELECT id FROM users WHERE tg_id=?) ORDER BY id DESC LIMIT 6;", telegram_user_id)
        return res

    @classmethod
    async def delete_message_history(cls, telegram_user_id: str):
        await cls.execute_dml("DELETE FROM message_history WHERE user_id=(SELECT id FROM users WHERE tg_id=?)", telegram_user_id)

    @classmethod
    async def save_summary(cls, telegram_user_id: str, summary: str):
        await cls.execute_dml("INSERT INTO message_summaries (user_id, summary) VALUES ((SELECT id FROM users WHERE tg_id=?), ?);", telegram_user_id, summary)

    @classmethod
    async def get_summary(cls, telegram_user_id: str):
        res = await cls.execute_dml("SELECT summary FROM message_summaries WHERE user_id=(SELECT id FROM users WHERE tg_id=?) ORDER BY id DESC LIMIT 1;", telegram_user_id)
        return res[0][0] if res else ""

    @classmethod
    async def delete_message_summaries(cls, telegram_user_id: str):
        await cls.execute_dml("DELETE FROM message_summaries WHERE user_id=(SELECT id FROM users WHERE tg_id=?)", telegram_user_id)
