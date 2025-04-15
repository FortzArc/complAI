from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.schema.runnable import Runnable
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

# Load API key from .env file (if not already loaded)
load_dotenv()

def build_qa_chain(vectorstore: FAISS) -> Runnable:
    llm = ChatOpenAI(
        model_name="gpt-4-turbo",
        temperature=0,
        openai_api_key="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" # Keep key safe!
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

'''
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.schema.runnable import Runnable
from langchain.prompts import PromptTemplate
import os

def build_qa_chain(vectorstore: FAISS) -> Runnable:
    llm = ChatOpenAI(
        model="gpt-4-turbo",
        temperature=0,
        openai_api_key="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"
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

'''