from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI


def create_rag_layer():
    """
    Create RAG layer for model explanations
    """
    docs = [
        "Churn prediction is based on customer behavior and contract details",
        "Important features include tenure, monthly charges, and contract type",
        "Higher monthly charges increase churn risk",
        "Longer tenure reduces churn probability",
        "Month-to-month contracts have higher churn risk",
        "Contracts are of different types: Month-to-month=0, One year=1, Two year=2"
        "Online security, backup, and tech support are important for churn prediction"
        "Online backup [Yes=1, No=0]",
        "Tech support [Yes=1, No=0]",
        "Online security [Yes=1, No=0]"
    ]
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_texts(docs, embeddings)
    return RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model="gpt-4", temperature=0),
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )
