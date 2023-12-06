import os
import dotenv
import openai
import json
from typing import Literal
from langchain.vectorstores import VectorStore
from langchain.docstore.document import Document

from .db import DocumentExtractor, EMBEDDINGS_DATABASE
from log import logger

dotenv.load_dotenv(".env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")


MODEL = "gpt-3.5-turbo"
MODEL = "gpt-4-1106-preview"


class LLM:

    PROMPT = """
Ты - личный консультант по программированию и высшей математике.
Твоя задача - отвечать на вопросы клиента четко и ясно.
Вы с клиентом в хороших отношениях, поэтому общайся без наигранной вежливости, просто по дружески.

Если клиент не понимает материал, старайся объяснить его проще и дать интуитивное понимание с примерами.
Если клиент просит подробнее, старайся объяснить всё в мельчайших деталях.
Следуй указаниям клиента, но отстаивай свою точку зрения если он не прав.
Никогда не ври. Если что-то не знаешь или не понимаешь, честно сообщи об этом.
Ты должен давать как можно больше полезных и подробных материалов в ответ на каждый вопрос.
Если требуется написать блок кода или формулу латекс, то пиши их в Markdown type блоке из тройных ` с указанием языка прогрмаммирования.

Тебе будут предоставлены документы с дополнительной информацией.
Тебе не обязательно на них ориентироваться, но в случае необходимсти ты всегда можешь на них положиться.
В них могут содержаться материалы по вышмату, документация к програмному обеспечению и много другиъ полезных вещей.

Документы будут перечислены перед вопросом.
Каждый документ будет заключён в тройные кавычки (\"\"\"Документ № \"\"\"), и в каждом будет название (либо фраза "Нет названия!") документа и его контент.

Так же тебе будет представлена история сообщений в виде краткого пересказа. Ты можешь использовать эту информацию чтобы чётче следовать курсу диалога.
"""

    SUMMARIZATION_PROMPT = """
Ты - суммаризатор истории сообщений чат-бота и клиента.
Тебе будут предоставлены: краткое изложение прошлых сообщений и два последних сообщения от клиента и чат-бота в разделе "История" и "Сообщения" соответственно.
Твоя задача составить максимально подробное, но достатчно краткое (не больше 800 слов) изложение истории сообщений.
Не вдавайся в подробности отдельных сообщений, только тезисно выделяй затронутые темы.
Если есть более важные темы или отдельные интересные моменты, удели им больше внимания.
Обязательно обрати больше внимания на последние сообщения. Явно укажи что клиент попросил в последнем сообщении, и что ему ответили.
"""

    LLM = openai.AsyncOpenAI()
    EXTRACTOR = DocumentExtractor()

    @classmethod
    async def ask(cls, query: str, summary: str, prompt: str) -> tuple[str, list[Document], bool]:
        if prompt is None:
            prompt = cls.PROMPT

        documents = await EMBEDDINGS_DATABASE.query_documents(query)
        documents_text = cls.extract_documents_data(documents, 'quotes')
        content = f"Документы:\n{documents_text}\nИстория диалога:\n{summary}\n\nВопрос клиента:\n{query}"

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user",   "content": content},
        ]

        logger.debug(content)

        answer, success = await cls.__make_request(messages)
        return answer, documents, success

    @classmethod
    def extract_documents_data(cls, documents: list[Document], mode: Literal["plain", "quotes", "dashed", "xml", "json", "quotes"]):
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
        messages = [
            {"role": "system", "content": cls.SUMMARIZATION_PROMPT},
            {"role": "user", "content": f"История:\n{summary}"},
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
