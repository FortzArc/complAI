from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import os

def get_embedding_model():
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        raise ValueError("HUGGINGFACE_API_KEY environment variable is required")
        
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"token": api_key}
    )

def create_vectorstore(chunks, embedding_model):
    vectorstore = FAISS.from_texts(chunks, embedding_model)
    return vectorstore