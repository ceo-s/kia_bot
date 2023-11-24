import dotenv
import os
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts.prompt import PromptTemplate

from .db import DB

dotenv.load_dotenv(".env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Справка [{additional_info}]
prompt_template = """
Тебя зовут Вася. Ты обращаешься к собеседнику только по имени. Тебе 35. Носишь усы.

{chat_history}
"""

prompt = PromptTemplate(
    input_variables=["chat_history"], template=prompt_template, template_format='f-string')

retriever = DB.as_retriever()
chat = ChatOpenAI()
memory = ConversationBufferWindowMemory(k=3)
question_generator = LLMChain(
    llm=chat, prompt=prompt)
doc_chain = load_qa_with_sources_chain(llm=chat, chain_type="refine")
conversation = ConversationalRetrievalChain(
    memory=memory,
    retriever=retriever,
    question_generator=question_generator,
    combine_docs_chain=doc_chain,
    return_source_documents=True,
    verbose=True)


# async def send_request(message: str):
#     resp = await conversation.arun(message)
#     print(memory.load_memory_variables({}))
#     return resp

async def send_request(message: str):
    history = []
    result = await conversation.acall({"question": message, "chat_history": history})
    print(result)
    return result["source_documents"][0]

if __name__ == '__main__':
    while True:
        try:
            req = input("Enter prompt:\n")
            send_request(req)
        except KeyboardInterrupt:
            break
