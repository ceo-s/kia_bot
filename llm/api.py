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


# MODEL = "gpt-3.5-turbo"
MODEL = "gpt-4-1106-preview"


class LLM:

    PROMPT = """
Ты чатбот созданный компанией Neural Universiry.
Ты предназначен для консультации клиентов по поводу машин марки KIA.
Вся дополнительная информация по вопросам будет содержаться в документах. Тебе будут предоставлены "Конетнт" и "Название" документа.
"""

    PROMPT2 = """
Ты чатбот созданный компанией Neural Universiry.
Ты предназначен для консультации клиентов по поводу машин марки KIA.
Вся дополнительная информация по вопросам будет содержаться в документах. Тебе будут предоставлены "Конетнт" и "Название" документа.
История сообщений представляет собой краткое изложение всего прошлого диалога. Тебе будет представлена "История сообщений".
"""
    SUMMARIZATION_PROMPT = """
Ты - суммаризатор истории сообщений чат-бота и клиента.
Тебе будут предоставлены: краткое изложение прошлых сообщений и два последних сообщения от клиента и чат-бота в разделе "История" и "Сообщения" соответственно.
Твоя задача составить максимально подробное, но краткое (не больше 500 токенов) изложение истории сообщений.

История:
{summary}
"""
    LLM = openai.AsyncOpenAI()
    EXTRACTOR = DocumentExtractor()

    @classmethod
    async def ask(cls, query: str, summary: str) -> tuple[str, list[Document], bool]:
        documents = await query_documents(query)
        messages = [
            {"role": "system", "content": cls.PROMPT},
            {"role": "user", "content": cls.extract_documents_data(
                documents, "plain")},
            {"role": "user", "content": f"История сообщений:\n{summary}"},
            {"role": "user", "content": query},
        ]

        answer, success = await cls.__make_request(messages)
        return answer, documents, success

    @classmethod
    def extract_documents_data(cls, documents: list[Document], mode: Literal["plain", "quotes", "xml", "json"]):
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
