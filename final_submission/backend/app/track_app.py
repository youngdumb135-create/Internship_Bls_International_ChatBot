import uvicorn
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Annotated, TypedDict
from contextlib import asynccontextmanager
import os
import sys
import operator
import asyncio
from cachetools import TTLCache

# --- LangChain & LangGraph Imports ---
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# --- Selenium Imports ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- CONFIGURATION ---
DB_PATH = os.environ.get("DB_PATH", r"D:\Chatbot\practice\chroma_db")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mxbai-embed-large")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.1")
K_DOCS = int(os.environ.get("K_DOCS", 3))
MAX_CACHE_SIZE = int(os.environ.get("MAX_CACHE_SIZE", 100))
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 1800)) # 30 mins

# --- Pydantic Models for FastAPI ---

class QueryRequest(BaseModel):
    """The request model for a user's query."""
    query: str
    user_id: str | None = None  # Optional user ID for chat history

class QueryResponse(BaseModel):
    """The response model for the query."""
    original_query: str
    response: str
    # Note: We can't guarantee retrieved_documents anymore,
    # as the agent might not do RAG.
    # We can add logic to extract them from tool calls later if needed.
    
# --- Vector Store Loading (No Changes) ---

def load_vectorstore(db_path: str, embedding_model: OllamaEmbeddings) -> Chroma | None:
    """Loads an existing Chroma vector store."""
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
    """Sets up a retriever from the vector store."""
    if vectorstore is None:
        print("Vector store is None, cannot set up retriever.")
        return None
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": K_DOCS}
    )

# -----------------------------------------------------------------
# --- AGENT TOOLS ---
# -----------------------------------------------------------------

@tool
async def track_visa_status_tool(reference_no: str, date_of_birth: str) -> str:
    """
    Use this tool *only* when a user asks to track their visa application status.
    You MUST have both the 'reference_no' (application reference number)
    and 'date_of_birth' (in YYYY-MM-DD format) before calling this.
    If you don't have them, ask the user for them.
    """
    print(f"--- Calling Visa Tracker Tool for {reference_no} ---")
    
    # This function contains blocking I/O (Selenium)
    # We must run it in a separate thread to avoid blocking FastAPI's event loop
    def blocking_selenium_call():
        TRACKING_URL = "https://www.bls-website.com/track-application" # <-- REPLACE
        REF_FIELD_ID = "application_ref_id" # <-- REPLACE
        DOB_FIELD_ID = "dob_field_id"       # <-- REPLACE
        SUBMIT_BUTTON_ID = "submit_button_id" # <-- REPLACE
        STATUS_RESULT_ID = "status_result_element_id" # <-- REPLACE

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        try:
            with webdriver.Chrome(options=options) as driver:
                driver.get(TRACKING_URL)
                ref_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, REF_FIELD_ID))
                )
                dob_field = driver.find_element(By.ID, DOB_FIELD_ID)
                ref_field.send_keys(reference_no)
                dob_field.send_keys(date_of_birth)
                
                submit_button = driver.find_element(By.ID, SUBMIT_BUTTON_ID)
                submit_button.click()
                
                status_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, STATUS_RESULT_ID))
                )
                status = status_element.text
                
                if not status:
                    return "Successfully submitted, but no status was found. Please check details."
                return f"The status for application {reference_no} is: {status}"
        except TimeoutException:
            return "Error: The tracking page timed out."
        except Exception as e:
            print(f"[Tool Error]: {e}")
            return "Sorry, I was unable to retrieve the status."

    # Run the blocking function in a thread pool
    return await asyncio.to_thread(blocking_selenium_call)

# Note: The RAG tool will be defined inside the lifespan
# to give it access to the retriever and llm

# -----------------------------------------------------------------
# --- LANGGRAPH AGENT DEFINITION ---
# -----------------------------------------------------------------

class AgentState(TypedDict):
    """This is the state of our graph, a list of messages."""
    messages: Annotated[List[BaseMessage], operator.add]

async def call_agent_node(state, llm_with_tools):
    """This node calls the LLM (agent)."""
    print("--- Calling Agent Node ---")
    messages = state['messages']
    # We use .ainvoke for async calling
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

def should_run_tools(state) -> str:
    """This is the router. It checks if the LLM called a tool."""
    print("--- Checking for Tools ---")
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        print("-> Decision: Run tools")
        return "run_tools"
    else:
        print("-> Decision: End")
        return END

# -----------------------------------------------------------------
# --- FastAPI Lifespan (Startup/Shutdown) ---
# -----------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the startup and shutdown logic for the FastAPI app.
    Loads all RAG components and builds the LangGraph agent on startup.
    """
    print("--- Server is starting up, loading RAG components ---")

    # 1. Load Embedding Model
    embedding_model = OllamaEmbeddings(model=OLLAMA_MODEL)
    app.state.EMBEDDING_MODEL = embedding_model

    # 2. Load Vector Store
    vectorstore = load_vectorstore(DB_PATH, embedding_model)
    app.state.RAG_VECTORSTORE = vectorstore

    # 3. Setup Retriever
    retriever = setup_retriever(vectorstore)
    app.state.RAG_RETRIEVER = retriever

    # 4. Initialize LLM
    llm = ChatOllama(model=LLM_MODEL, temperature=0.4)
    app.state.RAG_LLM = llm
    
    if retriever is None or llm is None:
        print("FATAL: Failed to load LLM or Retriever. Agent will not function.")
        yield
        return # Don't continue if critical components failed

    # --- 5. Build the Agent (NEW) ---
    
    # Define the RAG tool *inside* lifespan to "close over"
    # the retriever and llm from app.state
    @tool
    async def general_visa_question_tool(query: str) -> str:
        """
        Use this tool for all general questions about visa processes,
        document requirements, fees, application centers, or any other question
        that is NOT a request to track a specific application status.
        """
        print(f"--- Calling RAG Tool for: {query} ---")
        try:
            # Use the components from app.state
            context_docs = await app.state.RAG_RETRIEVER.ainvoke(query)
            context_text = "\n".join([doc.page_content for doc in context_docs])
            
            rag_prompt = f"Context: {context_text}\n\nQuestion: {query}\nAnswer concisely."
            result = await app.state.RAG_LLM.ainvoke(rag_prompt)
            return result.content
        except Exception as e:
            print(f"[RAG Tool Error]: {e}")
            return "Sorry, I encountered an error trying to find an answer."

    # Setup tools
    tools = [track_visa_status_tool, general_visa_question_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    # Assemble the graph
    graph = StateGraph(AgentState)
    
    # We use a lambda to pass the llm_with_tools to the node
    graph.add_node(
        "agent",
        lambda state: call_agent_node(state, llm_with_tools)
    )
    graph.add_node("tools", ToolNode(tools))
    
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_run_tools, {"run_tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    
    # Compile the graph and store it in app.state
    app.state.AGENT_APP = graph.compile()
    print("--- LangGraph Agent compiled and loaded. ---")

    # 6. Setup Memory Cache
    # This cache will store `List[BaseMessage]` for each user
    app.state.RAG_MEMORIES = TTLCache(
        maxsize=MAX_CACHE_SIZE,
        ttl=SESSION_TTL_SECONDS
    )
    print(f"Per-user memory manager initialized (size={MAX_CACHE_SIZE}, ttl={SESSION_TTL_SECONDS}s).")
    
    print("--- Server startup complete. ---")
    
    yield

    # --- Shutdown Logic ---
    print("--- Server is shutting down ---")
    app.state.RAG_MEMORIES.clear()
    print("Memory cache cleared.")
    print("--- Shutdown complete ---")


# -----------------------------------------------------------------
# --- FastAPI App & Endpoints ---
# -----------------------------------------------------------------

app = FastAPI(
    title="Agentic RAG Chatbot Backend",
    description="A FastAPI backend for a RAG chatbot using LangGraph and Ollama.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", tags=["General"])
async def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to the Agentic RAG Chatbot API"}


@app.post("/query", response_model=QueryResponse, tags=["Agent"])
async def handle_agent_query(request: Request, body: QueryRequest):
    """
    The main agent endpoint.
    1. Receives a query.
    2. Loads chat history for the user.
    3. Invokes the LangGraph agent.
    4. The agent decides to use RAG, visa tracking, or just talk.
    5. Saves new history.
    6. Returns the final response.
    """
    try:
        # Access components from app.state
        agent_app = request.app.state.AGENT_APP
        memory_cache = request.app.state.RAG_MEMORIES 
        
        if agent_app is None or memory_cache is None:
            raise HTTPException(status_code=500, detail="Agent is not initialized.")

        # Get or create memory for the user
        user_id = body.user_id if body.user_id else "default-user"
        
        # .get() returns None if not found, so [] is a default
        chat_history = memory_cache.get(user_id, [])

        # Format the input for the agent
        current_messages = chat_history + [HumanMessage(content=body.query)]
        
        # 3. Invoke the agent (asynchronously)
        print(f"Invoking agent for user: {user_id}...")
        result_state = await agent_app.ainvoke(
            {"messages": current_messages},
            # Add a recursion limit
            {"recursion_limit": 10}
        )
        print("Agent invocation complete.")

        # 4. Get the full, updated history from the result
        new_chat_history = result_state['messages']

        # 5. Save the new history back to the cache
        memory_cache[user_id] = new_chat_history

        # 6. Get the final answer (it's the last message)
        response_content = new_chat_history[-1].content
        
        return QueryResponse(
            original_query=body.query,
            response=response_content
        )
        
    except Exception as e:
        print(f"--- UNHANDLED ERROR ---")
        print(f"Error handling query for user {body.user_id}: {e}")
        import traceback
        traceback.print_exc()
        print(f"--- END TRACEBACK ---")
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred."
        )

# --- To run the app ---
if __name__ == "__main__":
    """
    This allows you to run the app directly using `python main.py`
    """
    uvicorn.run(app, host="0.0.0.0", port=8000)