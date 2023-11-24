import os
import json
import dotenv
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter, TokenTextSplitter
from langchain.vectorstores.faiss import FAISS


with open("conf.json") as file:
    config = json.load(file)["LLM"]["DB"]

dotenv.load_dotenv(".env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

FILES = config["FILES"]
CHUNK_SIZE = config["CHUNK_SIZE"]
CHUNK_OVERLAP = config["CHUNK_OVERLAP"]
DOCUMENTS_PER_QUERY = config["DOCUMENTS_PER_QUERY"]

EMBEDDINGS = OpenAIEmbeddings()


def load_documents():
    splitter = MarkdownHeaderTextSplitter([("###", "source")])
    docs: list[Document] = []
    for filename in FILES:
        with open(f"db/text/{filename}", "r") as file:
            docs += splitter.split_text(file.read())

    token_splitter = TokenTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    docs = token_splitter.split_documents(docs)
    db = FAISS.from_documents(docs, EMBEDDINGS)
    db.save_local("db")
    return db


if os.path.exists("db/index*"):
    DB = FAISS.load_local("db", EMBEDDINGS)
else:
    DB = load_documents()


def query_documents(text: str):
    DB.similarity_search(text, k=DOCUMENTS_PER_QUERY)
