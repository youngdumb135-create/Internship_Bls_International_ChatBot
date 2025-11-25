import os
import sys
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain.chains import create_reterieval_chain
# from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.memory import ConversationSummaryBufferMemory


BASE_DIR = os.environ.get("DB_PATH", r"D:\Chatbot\practice\chroma_db")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mxbai-embed-large")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.1")
K_DOCS = os.environ.get("K_DOCS", 3)

def load_vectorstore(BASE_DIR:str, embedding_model: OllamaEmbeddings)-> Chroma | None:
    """
    This function loads an existing Chroma vector store from the specified directory.
    If the directory does not exist or an error occurs, it returns None.

    Args:
        db_path (str): The directory path where the Chroma vector store is persisted.
        embedding_model: The embedding model to use with the vector store.
        
    Returns: 
        Chroma | None: The loaded Chroma vector store or None if loading fails. 
    """

    try:
        print(f"Loading vector store from {BASE_DIR}...")
        vectorstore = Chroma(
            persist_directory = BASE_DIR,
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
    embedding_model = OllamaEmbeddings(model=OLLAMA_MODEL)


    vectorstore = load_vectorstore(BASE_DIR, embedding_model)
    if vectorstore is None:
        print("Failed to load vector store. Exiting.")
        return
    

    retriever = setup_retriever(vectorstore)

    if retriever is None:
        print("Failed to set up retriever. Exiting.")
        return


    llm = ChatOllama(model=LLM_MODEL, temperature=0.4)

    prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant. Use the following context to answer the question concisely."),
    MessagesPlaceholder("chat_history"), 
    ("user", "Context: {context}\n\nQuestion: {question}\nAnswer briefly.")
])

    memory = ConversationSummaryBufferMemory(
        llm=llm,
        max_token_limit=500,
        memory_key="chat_history",
        return_messages=True
    )


    while True:
        query = input("Ask your question (or type 'exit' to quit): ")
        if query.lower() == 'exit' or query.lower() == 'quit':
            print("Exiting the program.")
            break
        else:
            context_docs = retriever.get_relevant_documents(query)
            context_text = "\n".join([doc.page_content for doc in context_docs])
            chat_history = memory.load_memory_variables({})['chat_history']

            chain = prompt | llm
            result = chain.invoke({
                "context": context_text,
                "question": query,
                "chat_history": chat_history 
            })
            memory.save_context({"question": query}, {"answer": result.content})

            print(f"Answer: {result.content}\n")


if __name__ == "__main__":
    main()