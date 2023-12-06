import os
import json
from typing import Any
import dotenv
from enum import Enum
from threading import Thread
import asyncio
from collections.abc import Callable, Iterable, Mapping
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter, HTMLHeaderTextSplitter, TokenTextSplitter, TextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.vectorstores.faiss import FAISS

from log import logger

with open("conf.json") as file:
    logger.debug("Loading llm db config")
    config = json.load(file)["LLM"]["DB"]

dotenv.load_dotenv(".env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

TEXTS_DIR = config["TEXTS_DIR"]
EMBEDDINGS_DIR = config["EMBEDDINGS_DIR"]
FILES: list[str] = config["FILES"]
CHUNK_SIZE = config["CHUNK_SIZE"]
CHUNK_OVERLAP = config["CHUNK_OVERLAP"]
DOCUMENTS_PER_QUERY = config["DOCUMENTS_PER_QUERY"]
EMBEDDINGS_DATABASE: "EmbeddingDB"  # after class

EMBEDDINGS = OpenAIEmbeddings()


class Splitter:

    class Types(Enum):
        PDF = "pdf"
        MARKDOWN = "md"
        TEXT = "txt"
        HTML = "html"

    class SplitterThread(Thread):

        def __init__(self, group: None = None, target: Callable[..., object] | None = None, name: str | None = None, args: Iterable[Any] = ..., kwargs: Mapping[str, Any] | None = None, *, daemon: bool | None = None) -> None:
            super().__init__(group, target, name, args, kwargs, daemon=daemon)
            self.return_value = None

    MD_SPLITTER = MarkdownHeaderTextSplitter(
        [("##", "Header 1"), ("###", "Header 2")])

    HTML_SPLITTER = HTMLHeaderTextSplitter(
        [("h1", "Header 1"), ("h2", "Header 2"), ("h3", "Header 3"),])

    TOKEN_SPLITTER = TokenTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def split_files(self, filenames: list[str]) -> list[Document]:
        documents = []
        for filename in filenames:
            documents += self._split_file(filename)

        return self._split_into_chunks(documents)

    def _split_file(self, filename: str) -> list[Document]:
        ext = filename.split(".")[-1]
        if not self._validate(filename, ext):
            return []

        return getattr(self, f"_Splitter__split_{ext}")(f"{self.base_dir}/{filename}")

    def _split_into_chunks(self, documents: list[Document]) -> list[Document]:
        return self.TOKEN_SPLITTER.split_documents(documents)

    def _validate(self, filename: str, ext: str) -> bool:
        if not os.path.exists(path := f"{self.base_dir}/{filename}"):
            logger.error(
                f"Provided document path({path}) does not exist. Check conf.json")
            return False
        try:
            self.Types(ext)
        except ValueError as ex:
            logger.error(f"Failed to validate file extension of {filename}")
            return False

        return True

    def __split_pdf(self, path: str):
        return PyPDFLoader(path).load()

    def __split_md(self, path: str):
        with open(path, "r") as file:
            return self.MD_SPLITTER.split_text(file.read())

    def __split_txt(self, path: str):
        return TextLoader(path).load()

    def __split_html(self, path: str):
        with open(path, "r") as file:
            return self.HTML_SPLITTER.split_text(file.read())


class DocumentExtractor:

    @staticmethod
    def extract_plain(documents: list[Document]):
        result = ""
        for document in documents:
            result += f'Название:{document.metadata.get("Header 1", "Нет названия!")}\n\n'
            result += f'Контент:\n{document.metadata.get("Header 2", "")}\n{document.page_content}\n'
        return result

    @staticmethod
    def extract_quotes(documents: list[Document]):
        result = ''
        for i, document in enumerate(documents):
            result += f'"""Документ {i}'
            result += f'Название:{document.metadata.get("Header 1", "Нет названия!")}\n'
            result += f'Контент:\n{document.metadata.get("Header 2", "")}\n{document.page_content}\n'
            result += f'"""\n'
        return result

    @staticmethod
    def extract_xml(documents: list[Document]):
        result = "<document>\n"
        for document in documents:
            result += f"<source>\n{document.metadata.get('Header 1', 'Нет названия!')}\n</source>\n"
            result += f"<content>\n{document.metadata.get('Header 2', '')}\n{document.page_content}\n</content>\n"
        result += "</document>\n\n"
        return result

    @staticmethod
    def extract_dashed(documents: list[Document]):
        result = ""
        for i, doc in enumerate(documents):
            content = doc.page_content
            response = f'\n=====================Отрывок документа №{i + 1}=====================\n{content}\n'
            result += response
        return result


class EmbeddingDB:

    def __init__(self):
        self.__DB = self.__initialize_db()
        self.__SPLITTER = Splitter(TEXTS_DIR)

    def __initialize_db(self) -> FAISS:
        if os.path.exists(f"{EMBEDDINGS_DIR}/index.faiss"):
            DB = FAISS.load_local(EMBEDDINGS_DIR, EMBEDDINGS)
            logger.info("Loading existing embeddings")
        else:
            DB = self.__load_db()
            logger.info("Creating new embeddings")

        logger.info("Loaded FAISS")
        return DB

    def __load_db(self):
        documents = self.__SPLITTER.split_files(FILES)

        db = FAISS.from_documents(documents, EMBEDDINGS)
        db.save_local(EMBEDDINGS_DIR)
        return db

    async def query_documents(self, text: str):
        try:
            return await self.__DB.asimilarity_search(text, k=DOCUMENTS_PER_QUERY)
        except Exception as ex:
            logger.error(f"Error quering document embeddings. {ex}")
            return []

    def __add_documents(self, filenames: list[str]):
        documents = self.__SPLITTER.split_files(filenames)
        self.__DB.add_documents(documents)
        # self.__DB.save_local(EMBEDDINGS_DIR)
        # self.__DB.
        logger.debug(f"Added documents {filenames} to vector store")

    async def add_documents(self, filenames: list[str]):
        await asyncio.sleep(0)
        Thread(target=self.__add_documents, args=(filenames,)).start()


EMBEDDINGS_DATABASE = EmbeddingDB()
