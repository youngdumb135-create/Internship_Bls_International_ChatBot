import os 
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

db_path = os.environ.get("DB_PATH", r"D:\Chatbot\practice\chroma_db")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mxbai-embed-large") 
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.1")
K_DOCS = int(os.environ.get("K_DOCS", 3)) # number of similar documents to retrieve

def load_vectorstore(db_path:str, embedding_model: OllamaEmbeddings)-> BaseRetriever | None:
    """
    This function loads an existing Chroma vector store from the specified directory.
    If the directory does not exist or an error occurs, it returns None.

    Args:
        db_path (str): The directory path where the Chroma vector store is persisted.
        embedding_model: The embedding model to use with the vector store.
        
    Returns: 
        Chroma | None: The loaded Chroma vector store or None if loading fails. 
    """

    if not os.path.exists(db_path):
        print(f"Vector store directory {db_path} does not exist.")
        return None
    
    try:
        print(f"Loading vector store from {db_path}...")
        vectorstore = Chroma(
            persist_directory = db_path,
            embedding_function=embedding_model
        )
        print("Vector store loaded successfully.")

    except Exception as e:
        print(f"Error loading vector store: {e}")
        vectorstore = None
    return vectorstore

def setup_retriever(vectorstore)-> BaseRetriever | None:
    """
    Sets up a retriever from the given Chroma vector store.
    Args:
        vectorstore (Chroma): The Chroma vector store from which to create the retriever.
    Returns:
        retriever or None: The configured retriever or None if setup fails.
    """

    if vectorstore is None:
        print("Vector store is None, cannot set up retriever.")
        return None
    
    retriever = vectorstore.as_retriever(
        search_type = "similarity",
        search_kwargs = {
            "k": K_DOCS
        } 
    )
    return retriever


def main():
    print("Initializing embedding model...")
    embedding_model = OllamaEmbeddings(model=OLLAMA_MODEL)

    vectorstore = load_vectorstore(db_path, embedding_model)
    if vectorstore is None:
        print("Failed to load vector store. Exiting.")
        return

    retriever = setup_retriever(vectorstore)
    if retriever is None:
        print("Failed to set up retriever. Exiting.")
        return

    # Test the retriever with a sample query
    test_query = "Should I buy my medical insurance before my visa is issued?"
    context = retriever.get_relevant_documents(test_query)


    llm = ChatOllama(model = LLM_MODEL, temperature=0.4)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that provides concise answers based on the provided context."),
        ("user", "Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. \n\n{context} \n\nQuestion: {question}")
    ])

    chain = prompt | llm

    result = chain.invoke({
        "context": context,
        "question": test_query
    })
    print("\n--- LLM Response ---")
    print(result.content)

if __name__ == "__main__":
    main()