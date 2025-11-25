
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager

# --- LangChain Imports ---
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.memory import ConversationSummaryBufferMemory
from langchain_core.runnables import Runnable
from langchain_core.documents import Document as LangChainDocument

# --- CONFIGURATION ---
DB_PATH = r"D:\Chatbot\practice\chroma_db"  # Note: This path is hardcoded.
OLLAMA_MODEL = "mxbai-embed-large"
LLM_MODEL = "llama3.1"
K_DOCS = 3  # Number of similar documents to retrieve


class QueryRequest(BaseModel):
    """The request model for a user's query."""
    query: str
    user_id: str | None = None  # Optional user ID for chat history

class Document(BaseModel):
    """A model to represent a retrieved document chunk."""
    id: str
    content: str
    source: str
    score: float  # We'll use a mock score for now

class QueryResponse(BaseModel):
    """The response model for a RAG query."""
    original_query: str
    response: str
    retrieved_documents: List[Document]

def load_vectorstore(db_path: str, embedding_model: OllamaEmbeddings) -> Chroma | None:
    """
    Loads an existing Chroma vector store from the specified directory.
    If the directory does not exist or an error occurs, it returns None.
    """
    try:
        print(f"Loading vector store from {db_path}...")
        vectorstore = Chroma(
            persist_directory=db_path,
            embedding_function=embedding_model
        )
        print("Vector store loaded successfully.")
        return vectorstore
    except Exception as e:
        print(f"Error loading vector store: {e}")
        return None
    
def setup_retriever(vectorstore) -> BaseRetriever | None:
    """
    Sets up a retriever from the given Chroma vector store.
    """
    if vectorstore is None:
        print("Vector store is None, cannot set up retriever.")
        return None
    
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": K_DOCS}
    )

# --- Global RAG Components ---
# These will be initialized on startup
RAG_RETRIEVER: BaseRetriever | None = None
RAG_LLM: ChatOllama | None = None
RAG_PROMPT: ChatPromptTemplate | None = None
RAG_CHAIN: Runnable | None = None
RAG_MEMORY: ConversationSummaryBufferMemory | None = None
# ToDo: In a real app, you'd want a dictionary of memories keyed by user_id
# USER_MEMORIES: Dict[str, ConversationSummaryBufferMemory] = {}



# --- Lifespan Context Manager ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the startup and shutdown logic for the FastAPI app.
    Loads all RAG components on startup.
    """
    global RAG_RETRIEVER, RAG_LLM, RAG_PROMPT, RAG_CHAIN, RAG_MEMORY

    print("--- Server is starting up, loading RAG components ---")

    # 1. Load Embedding Model
    embedding_model = OllamaEmbeddings(model=OLLAMA_MODEL)
    
    # 2. Load Vector Store
    vectorstore = load_vectorstore(DB_PATH, embedding_model)
    if vectorstore is None:
        print("Failed to load vector store. RAG will not function.")
        return 

    # 3. Setup Retriever
    RAG_RETRIEVER = setup_retriever(vectorstore)
    if RAG_RETRIEVER is None:
        print("Failed to set up retriever. RAG will not function.")
        return

    # 4. Initialize LLM
    RAG_LLM = ChatOllama(model=LLM_MODEL, temperature=0.4)
    # 5. Setup Prompt
    RAG_PROMPT = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant. Use the following context to answer the question concisely."),
        MessagesPlaceholder("chat_history"), 
        ("user", "Context: {context}\n\nQuestion: {question}\nAnswer briefly.")
    ])
    
    # 6. Setup Chain
    RAG_CHAIN = RAG_PROMPT | RAG_LLM

    # 7. Setup Memory (shared for all users in this simple example)
    # Only initialize memory if LLM loaded, as it depends on it
    if RAG_LLM:
        RAG_MEMORY = ConversationSummaryBufferMemory(
            llm=RAG_LLM,
            max_token_limit=500,
            memory_key="chat_history",
            return_messages=True
        )
    else:
        print("LLM failed to load, memory not initialized.")

    print("--- RAG components loaded. Server startup complete. ---")
    
    yield

    # --- Shutdown Logic ---
    print("--- Server is shutting down ---")
    # You can add cleanup code here if needed (e.g., closing DB connections)
    print("--- Shutdown complete ---")


app = FastAPI(
    title="RAG Chatbot Backend",
    description="A FastAPI backend for a RAG chatbot using LangChain and Ollama.",
    version="0.1.0",
    lifespan=lifespan  # Register the lifespan context manager
)

@app.get("/", tags=["General"])
async def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to the RAG Chatbot API"}


@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def handle_rag_query(request: QueryRequest):
    """
    The main RAG endpoint.
    1. Receives a query.
    2. Retrieves relevant documents.
    3. Loads chat history.
    4. Augments the prompt with context and history.
    5. Generates a response using an LLM.
    6. Saves new history.
    """
    # Check if RAG components are loaded
    if RAG_RETRIEVER is None or RAG_CHAIN is None or RAG_MEMORY is None:
        return QueryResponse(
            original_query=request.query,
            response="Error: RAG components are not initialized. Check server logs.",
            retrieved_documents=[]
        )

    # 1. Retrieve relevant documents
    context_docs: List[LangChainDocument] = RAG_RETRIEVER.invoke(request.query)

    context_text = "\n".join([doc.page_content for doc in context_docs])

    # 2. Load chat history
    # ToDo: Use a user_id-specific memory here
    # e.g., memory = USER_MEMORIES.get(request.user_id, RAG_MEMORY)
    chat_history = RAG_MEMORY.load_memory_variables({})['chat_history']

    # 3. Generate response (The "G" in RAG)
    result = RAG_CHAIN.invoke({
        "context": context_text,
        "question": request.query,
        "chat_history": chat_history
    })

    response_content = result.content

    # 4. Save new history
    RAG_MEMORY.save_context({"question": request.query}, {"answer": response_content})

    # 5. Format retrieved docs for the response
    retrieved_documents_response: List[Document] = []
    for i, doc in enumerate(context_docs):
        retrieved_documents_response.append(
            Document(
                id=f"doc_{i}",
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                # Note: as_retriever() doesn't return scores by default.
                # You'd need vectorstore.similarity_search_with_score for that.
                score=0.0 
            )
        )

    # 6. Return the full response
    return QueryResponse(
        original_query=request.query,
        response=response_content,
        retrieved_documents=retrieved_documents_response
    )


# if __name__ == "__main__":
#     """
#     This allows you to run the app directly using `python main.py`
#     for development.
#     """
#     uvicorn.run(app, host="0.0.0.0", port=8000)