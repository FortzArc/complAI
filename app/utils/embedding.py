from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS

def get_embedding_model():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")



def create_vectorstore(chunks, embedding_model):
    vectorstore = FAISS.from_texts(chunks, embedding_model)
    return vectorstore
