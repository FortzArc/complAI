from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.schema.runnable import Runnable
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

def build_qa_chain(vectorstore: FAISS) -> Runnable:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required but not set")

    llm = ChatOpenAI(
        model_name="gpt-4-turbo",
        temperature=0,
        openai_api_key=api_key
    )

    prompt_template = PromptTemplate.from_template(
        """You are a healthcare compliance assistant. Answer the question based on the provided context. 
If unsure, say 'I don't know.' Provide explanations and alternatives if applicable.

Context:
{context}

Question: {question}
Answer:"""
    )

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 2}),
        chain_type_kwargs={"prompt": prompt_template}
    )

    return chain