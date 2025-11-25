# This is the main FastAPI application for the RAG chatbot backend.
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager
import os
from cachetools import TTLCache

# --- LangChain Imports ---
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.memory import ConversationSummaryBufferMemory
from langchain_core.runnables import Runnable
from langchain_core.documents import Document as LangChainDocument

# --- CONFIGURATION (MODIFIED) ---
# Load all settings from environment variables, with sensible defaults.
DB_PATH = os.environ.get("DB_PATH", r"D:\Chatbot\practice\chroma_db")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mxbai-embed-large")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.1")
K_DOCS = int(os.environ.get("K_DOCS", 3)) # Ensure 'int'
MAX_CACHE_SIZE = int(os.environ.get("MAX_CACHE_SIZE", 100))
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 1800)) # (30 minutes)

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    """The request model for a user's query."""
    query: str
    user_id: str | None = None  

#--- Response Models ---
class Document(BaseModel):
    """A model to represent a retrieved document chunk."""
    id: str
    content: str
    source: str
    score: float  # We'll use a mock score for now

# The full response model
class QueryResponse(BaseModel):
    """The response model for a RAG query."""
    original_query: str
    response: str
    retrieved_documents: List[Document]


# --- Helper Functions ---
def load_vectorstore(db_path: str, embedding_model: OllamaEmbeddings) -> Chroma | None:
    """
    Loads an existing Chroma vector store from the specified directory.
    If the directory does not exist or an error occurs, it returns None.
    """
    if not os.path.exists(db_path):
        print(f"Vector store directory {db_path} does not exist.")
        return None

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



# --- Lifespan Context Manager ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the startup and shutdown logic for the FastAPI app.
    Loads all RAG components on startup.
    """

    print("--- Server is starting up, loading RAG components ---")


    # 1. Load Embedding Model
    embedding_model = OllamaEmbeddings(model=OLLAMA_MODEL)
    

    # 2. Load Vector Store
    vectorstore = load_vectorstore(DB_PATH, embedding_model)
    if vectorstore is None:
        print("Failed to load vector store. RAG will not function.")
        app.state.RAG_VECTORSTORE = None
        return 
    else:
        app.state.RAG_VECTORSTORE = vectorstore
    

    # 3. Setup Retriever
    retriever = setup_retriever(vectorstore)
    if retriever is None:
        print("Failed to set up retriever. RAG will not function.")
        app.state.RAG_RETRIEVER = None
        return
    else:
        app.state.RAG_RETRIEVER = retriever
    

    # 4. Initialize LLM
    llm = ChatOllama(model=LLM_MODEL, temperature=0.4)
    app.state.RAG_LLM = llm


    # 5. Setup Prompt
    app.state.RAG_PROMPT = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant. Use the following context to answer the question concisely."),
        MessagesPlaceholder("chat_history"), 
        ("user", "Context: {context}\n\nQuestion: {question}\nAnswer briefly.")
    ])
    
    # 6. Setup Chain
    app.state.RAG_CHAIN = app.state.RAG_PROMPT | app.state.RAG_LLM

    # 7. Setup Memory (as a dictionary for per-user storage)
    # Only initialize memory if LLM loaded, as it depends on it
    if app.state.RAG_LLM:
        app.state.RAG_MEMORIES = TTLCache(
            maxsize=MAX_CACHE_SIZE,
            ttl=SESSION_TTL_SECONDS
        )
        print(f"Per-user memory manager initialized with TTLCache (size={MAX_CACHE_SIZE}, ttl={SESSION_TTL_SECONDS}s).")
    else:
        print("LLM failed to load, memory not initialized.")
        app.state.RAG_MEMORIES = None

    print("--- RAG components loaded. Server startup complete. ---")
    
    yield

    # --- Shutdown Logic ---
    print("--- Server is shutting down ---")
    if app.state.RAG_MEMORIES:
        app.state.RAG_MEMORIES.clear() # Clear the cache on shutdown
    print("--- Shutdown complete ---")


# --- FastAPI Application ---
app = FastAPI(
    title="RAG Chatbot Backend",
    description="A FastAPI backend for a RAG chatbot using LangChain and Ollama.",
    version="0.1.0",
    lifespan=lifespan  # Register the lifespan context manager
)

# --- API Endpoints ---
@app.get("/", tags=["General"])
async def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to the RAG Chatbot API"}


# --- RAG Query Endpoint ---
@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def handle_rag_query(request: Request, body: QueryRequest): # Use Request to access app.state
    """
    The main RAG endpoint.
    1. Receives a query.
    2. Retrieves relevant documents.
    3. Loads chat history.
    4. Augments the prompt with context and history.
    5. Generates a response using an LLM.
    6. Saves new history.
    """
   
    try:
         # Access components from app.state
        retriever = request.app.state.RAG_RETRIEVER
        rag_chain = request.app.state.RAG_CHAIN
        memory_dict = request.app.state.RAG_MEMORIES 
        llm = request.app.state.RAG_LLM

        # Check if RAG components are loaded
        if retriever is None or rag_chain is None or memory_dict is None or llm is None:
            return QueryResponse(
                original_query=body.query,
                response="Error: RAG components are not initialized. Check server logs.",
                retrieved_documents=[]
            )

        #--- Per-User Memory Handling ---

        # Use a default ID if none is provided (e.g., for testing)
        # (The frontend sent this!)
        user_id = body.user_id if body.user_id else "default-user"

        # Get this user's specific memory, or create it if it doesn't exist
        if user_id not in memory_dict:
            print(f"Creating new memory for user: {user_id}")
            # This is why we needed the 'llm' from app.state
            memory_dict[user_id] = ConversationSummaryBufferMemory(
                llm=llm,
                max_token_limit=500,
                memory_key="chat_history",
                return_messages=True
            )
        # Get the specific memory object for this user
        rag_memory = memory_dict[user_id]




        # 1. Retrieve relevant documents
        print("Retrieving relevant documents...")
        context_docs: List[LangChainDocument] = await retriever.ainvoke(body.query)
    
        context_text = "\n".join([doc.page_content for doc in context_docs])
        print(f"Retrieved {len(context_docs)} documents for context.")

        # 2. Load chat history (asynchronous)
        print(f"Loading chat history for user: {user_id}...")
        chat_history_dict = await rag_memory.aload_memory_variables({})
        chat_history = chat_history_dict['chat_history']
        print(f"Loaded chat history with {len(chat_history)} messages.")

        # 3. Generate response (The "G" in RAG) (asynchronous)
        print("Generating response from LLM...")
        result = await rag_chain.ainvoke({
            "context": context_text,
            "question": body.query,
            "chat_history": chat_history
        })

        response_content = result.content
        print("Response generated.")


        # 4. Save new history (asynchronous)
        print(f"Saving conversation to memory for user: {user_id}...") # <--- Added user_id to log
        await rag_memory.save_context({"question": body.query}, {"answer": response_content})
        print("Conversation saved.")


        # 5. Format retrieved docs for the response (Score set to 0.0)
        retrieved_documents_response: List[Document] = []
        # Loop through the retrieved documents
        for i, doc in enumerate(context_docs):
            retrieved_documents_response.append(
                Document(
                    id=f"doc_{i}",
                    content=doc.page_content,
                    source=doc.metadata.get("source", "unknown"),
                    score=0.0  # Score is set to 0.0 as retriever doesn't provide it
                )
            )

        # 6. Return the full response
        return QueryResponse(
            original_query=body.query,
            response=response_content,
            retrieved_documents=retrieved_documents_response
        )
        
    except Exception as e:
        # Log the full error for your own debugging
        print(f"--- UNHANDLED ERROR ---")
        print(f"Error handling query for user {body.user_id}: {e}")
        import traceback
        traceback.print_exc()
        print(f"--- END TRACEBACK ---")

        # Raise a clean HTTPException for the user
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while processing your request."
        )

# if __name__ == "__main__":
#     """
#     This allows you to run the app directly using `python main.py`
#     for development.
#     """
#     uvicorn.run(app, host="0.0.0.0", port=8000)