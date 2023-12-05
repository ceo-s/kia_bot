import os
import dotenv
import openai
import json
from typing import Literal
from langchain.vectorstores import VectorStore
from langchain.docstore.document import Document

from .db import DB, DocumentExtractor, query_documents
from log import logger

dotenv.load_dotenv(".env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


MODEL = "gpt-3.5-turbo"


class LLM:

    PROMPT = """
Ты - личный консультант по программированию и высшей математике.
Твоя задача - отвечать на вопросы клиента четко и ясно.
Всегда следуй указаниям клиента, но отстаивай свою точку зрения если он не прав.
Ты должен давать как можно больше полезных и подробных материалов в ответ на каждый вопрос.

Если клиент не понимает материал, старайся объяснить его проще и дать интуитивное понимание с примерами.
Если клиент просит подробнее, старайся объяснить всё в мельчайших деталях.
"""

    SUMMARIZATION_PROMPT = """
Ты - суммаризатор истории сообщений чат-бота и клиента.
Тебе будут предоставлены: краткое изложение прошлых сообщений и два последних сообщения от клиента и чат-бота в разделе "История" и "Сообщения" соответственно.
Твоя задача составить максимально подробное, но краткое (не больше 400 слов) изложение истории сообщений.
Не вдавайся в подробности отдельных сообщений, только тезисно выделяй затронутые темы.

История:
{summary}
"""
    LLM = openai.AsyncOpenAI()
    EXTRACTOR = DocumentExtractor()

    @classmethod
    async def ask(cls, query: str, summary: str, prompt: str) -> tuple[str, list[Document], bool]:
        if prompt is None:
            prompt = cls.PROMPT

        documents = await query_documents(query)
        query = f"Вот краткий обзор предыдущего диалога:\n{summary}\n\nТекущий вопрос:\n{query}"

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user",
                "content": f"Документ с информацией для ответа пользователю:\n{cls.extract_documents_data(documents, 'plain')}\n\nВопрос клиента: \n{query}"},
            # {"role": "user", "content": f"История сообщений:\n{summary}"},
            # {"role": "user", "content": query},
        ]

        logger.debug(
            f"Документ с информацией для ответа пользователю: {cls.extract_documents_data(documents, 'dashed')}\n\nВопрос клиента: \n{query}")

        answer, success = await cls.__make_request(messages)
        return answer, documents, success

    @classmethod
    def extract_documents_data(cls, documents: list[Document], mode: Literal["plain", "quotes", "dashed", "xml", "json"]):
        func = getattr(cls.EXTRACTOR, f"extract_{mode}")
        return func(documents)

    @classmethod
    def documents_to_str(cls, documents: list[Document]):
        res = ""
        for i, document in enumerate(documents, 1):
            res += f"------Document {i}------\n"
            res += f"Header 1 = {document.metadata['Header 1']}\n"
            if header_2 := document.metadata.get("Header 2"):
                res += f"Header 2 = {header_2}\n"
            res += f"Content: {document.page_content}\n\n"

        return res

    @classmethod
    async def summarize_history(cls, summary: str, user_message: str, bot_message: str) -> tuple[str, bool]:
        prompt = cls.SUMMARIZATION_PROMPT.format(summary=summary)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Сообщения:\nКлиент - \"{user_message}\"\nЧат-бот - \"{bot_message}\""},
        ]

        answer, success = await cls.__make_request(messages)
        return answer, success

    @classmethod
    async def __make_request(cls, messages: list[dict]) -> tuple[str, bool]:
        success = False
        try:
            responce = await cls.LLM.chat.completions.create(model=MODEL, messages=messages)
            answer = responce.choices[0].message.content
            success = True
        except openai.BadRequestError as error:
            answer = json.loads(error.response._content)["error"]["message"]
            logger.error("Openai BadRequestError. " + answer)
        except Exception as ex:
            answer = "Просим прощения, но возникла неизвестная ошибка. Попробуйте повторить запрос позже."
            logger.error(f"Error in request to OpenAI API. {ex}")

        return answer, success
