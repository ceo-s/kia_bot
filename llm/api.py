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


class LLM:

    PROMPT = """
Ты чатбот созданный компанией Neural Universiry.
Ты предназначен для консультации клиентов по поводу машин марки KIA.
Вся дополнительная информация по вопросам будет содержаться в документах. Тебе будут предоставлены "Конетнт" и "Название" документа.
"""
    LLM = openai.AsyncOpenAI()
    EXTRACTOR = DocumentExtractor()

    @classmethod
    async def ask(cls, query: str, history: list[tuple[str, str]]) -> tuple[str, list[Document], bool]:
        documents = await query_documents(query)
        prompt = [
            {"role": "system", "content": cls.PROMPT},
            {"role": "user", "content": cls.extract_documents_data(
                documents, "plain")},
        ]

        user_message = [{"role": "user", "content": query}]
        messages = prompt + history + user_message
        try:
            responce = await cls.LLM.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
            answer = responce.choices[0].message.content
            success = True
        except openai.BadRequestError as error:
            answer = json.loads(error.response._content)["error"]["message"]
            logger.error("Openai BadRequestError. " + answer)
            success = False

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
