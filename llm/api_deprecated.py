import os
import dotenv
from typing import Sequence
from pprint import pprint
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory, ConversationBufferMemory
from langchain.prompts.prompt import PromptTemplate

from .db import DB

dotenv.load_dotenv(".env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Справка [{additional_info}]
prompt_template = """
Тебя зовут Вася. Ты обращаешься к собеседнику только по имени. Тебе 35. Носишь усы.

{summaries}

{chat_history}
Алексей:
{question}
Вася:
"""

prompt = PromptTemplate(
    input_variables=["chat_history", "question", "summaries"], template=prompt_template, template_format='f-string')

retriever = DB.as_retriever()
chat = ChatOpenAI()
memory = ConversationBufferWindowMemory(
    k=1, input_key="question", memory_key="chat_history", output_key="answer", return_messages=True)
# memory = ConversationBufferMemory(
# input_key="question", memory_key="chat_history", output_key="answer", return_messages=True
# )
question_generator = LLMChain(
    llm=chat, prompt=prompt, verbose=True)

doc_chain = load_qa_with_sources_chain(
    llm=chat, chain_type="stuff", verbose=True, prompt=prompt)

conversation = ConversationalRetrievalChain(
    memory=memory,
    retriever=retriever,
    question_generator=question_generator,
    combine_docs_chain=doc_chain,
    get_chat_history=lambda x: x,
    return_source_documents=True,
    verbose=True)


# async def send_request(message: str):
#     resp = await conversation.arun(message)
#     print(memory.load_memory_variables({}))
#     return resp

async def send_request(message: str, history: Sequence = []):
    history = [
        ("What is the date Australia was founded.",
         "Australia was founded in 1901."),
    ]
    # memory.chat_memory = history
    print(memory.chat_memory)
    # conversation.memory.clear()
    print(f"\n\n{conversation.memory.dict()=}\n\n")
    result = await conversation.acall({"question": message, "chat_history": history}, return_only_outputs=True)
    pprint(result)
    return result["answer"]

if __name__ == '__main__':
    while True:
        try:
            req = input("Enter prompt:\n")
            send_request(req)
        except KeyboardInterrupt:
            break
