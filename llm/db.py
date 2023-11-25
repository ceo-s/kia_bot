import os
import sys
import json
import dotenv
from typing import Literal
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter, TokenTextSplitter
from langchain.vectorstores.faiss import FAISS

from log import logger

with open("conf.json") as file:
    logger.debug("Loadin llm db config")
    config = json.load(file)["LLM"]["DB"]

dotenv.load_dotenv(".env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

TEXTS_DIR = config["TEXTS_DIR"]
EMBEDDINGS_DIR = config["EMBEDDINGS_DIR"]
FILES = config["FILES"]
CHUNK_SIZE = config["CHUNK_SIZE"]
CHUNK_OVERLAP = config["CHUNK_OVERLAP"]
DOCUMENTS_PER_QUERY = config["DOCUMENTS_PER_QUERY"]

EMBEDDINGS = OpenAIEmbeddings()


def load_documents():
    splitter = MarkdownHeaderTextSplitter(
        [("##", "Header 1"), ("###", "Header 2")])
    docs: list[Document] = []
    for filename in FILES:
        with open(f"{TEXTS_DIR}/{filename}", "r") as file:
            docs += splitter.split_text(file.read())

    token_splitter = TokenTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    docs = token_splitter.split_documents(docs)
    db = FAISS.from_documents(docs, EMBEDDINGS)
    db.save_local(EMBEDDINGS_DIR)
    return db


if os.path.exists(some_path := f"{EMBEDDINGS_DIR}/index.faiss"):
    DB = FAISS.load_local(EMBEDDINGS_DIR, EMBEDDINGS)
else:
    DB = load_documents()

logger.info("Loaded FAISS")


async def query_documents(text: str):
    return await DB.asimilarity_search(text, k=DOCUMENTS_PER_QUERY)


class DocumentExtractor:

    @staticmethod
    def extract_plain(documents: list[Document]):
        result = ""
        for document in documents:
            result += f"Контент:\n{document.metadata.get('Header 2', '')}\n{document.page_content}\n"
            result += f"Название:{document.metadata.get('Header 1', 'Kia')}\n\n"
        return result

    @staticmethod
    def extract_xml(documents: list[Document]):
        result = "<document>\n"
        for document in documents:
            result += f"<content>\n{document.metadata.get('Header 2', '')}\n{document.page_content}\n</content>\n"
            result += f"<source>\n{document.metadata.get('Header 1', 'Kia')}\n</source>\n"
        result += "</document>\n\n"
        return result
