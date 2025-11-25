# This is Final_tracking.py
# A LangGraph chatbot that can answer general visa questions using RAG
# and can also track visa application status using Selenium.

import os
import sys
import operator
from typing import Annotated, TypedDict, List
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, ToolCall
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# --- Selenium Imports (same as before) ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- Your existing constants ---
DB_PATH = os.environ.get("DB_PATH", r"D:\Chatbot\practice\chroma_db")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mxbai-embed-large")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.1")
K_DOCS = os.environ.get("K_DOCS", 3)

# --- Your existing load/setup functions (no changes) ---

def load_vectorstore(DB_PATH:str, embedding_model: OllamaEmbeddings)-> Chroma | None:
    # (Same as your code)
    try:
        print(f"Loading vector store from {DB_PATH}...")
        vectorstore = Chroma(
            persist_directory = DB_PATH,
            embedding_function=embedding_model
        )
        print("Vector store loaded successfully.")
    except Exception as e:
        print(f"Error loading vector store: {e}")
        vectorstore = None
    return vectorstore

def setup_retriever(vectorstore)-> BaseRetriever | None:
    # (Same as your code)
    if vectorstore is None:
        print("Vector store is None, cannot set up retriever.")
        return None
    retriever = vectorstore.as_retriever(search_type = "similarity", search_kwargs = {"k": K_DOCS})
    return retriever

# -----------------------------------------------------------------
# --- STEP 1: DEFINE YOUR TOOLS ---
# -----------------------------------------------------------------

# --- Tool 1 (Global) ---
@tool
def track_visa_status_tool(reference_no: str, date_of_birth: str) -> str:
    """
    Use this tool *only* when a user asks to track their visa application status.
    You MUST have both the 'reference_no' (application reference number)
    and 'date_of_birth' (in YYYY-MM-DD format) before calling this.
    If you don't have them, ask the user for them.
    """
    print(f"--- Calling Visa Tracker Tool for {reference_no} ---")
    
    # !! IMPORTANT !!
    # This is a SKELETON. You MUST get the real URL, field IDs, and result ID
    # from the BLS "Track Your Application" webpage using "Inspect Element".
    
    TRACKING_URL = "httpsD://www.bls-website.com/track-application" # <-- REPLACE THIS
    REF_FIELD_ID = "application_ref_id" # <-- REPLACE THIS
    DOB_FIELD_ID = "dob_field_id"       # <-- REPLACE THIS
    SUBMIT_BUTTON_ID = "submit_button_id" # <-- REPLACE THIS
    STATUS_RESULT_ID = "status_result_element_id" # <-- REPLACE THIS

    # Setup the browser
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") # Run in background
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    try:
        with webdriver.Chrome(options=options) as driver:
            driver.get(TRACKING_URL)

            # 2. Find the form fields and fill them
            ref_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, REF_FIELD_ID))
            )
            dob_field = driver.find_element(By.ID, DOB_FIELD_ID)
            
            ref_field.send_keys(reference_no)
            dob_field.send_keys(date_of_birth) # Assumes YYYY-MM-DD format

            # 3. Find and click the submit button
            submit_button = driver.find_element(By.ID, SUBMIT_BUTTON_ID)
            submit_button.click()

            # 4. Wait for the result to appear
            status_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, STATUS_RESULT_ID))
            )

            # 5. Extract the text
            status = status_element.text
            
            if not status:
                return "Successfully submitted, but no status was found. Please check the details and try again."
                
            return f"The status for application {reference_no} is: {status}"

    except TimeoutException:
        return f"Error: The tracking page timed out. The details might be incorrect or the website is down."
    except Exception as e:
        # Handle other errors (e.g., element not found)
        print(f"[Tool Error]: {e}")
        return "Sorry, I was unable to retrieve the status. The reference number or DOB might be incorrect, or the tracking service is unavailable."


# -----------------------------------------------------------------
# --- STEP 2: DEFINE THE GRAPH STATE ---
# -----------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]

# -----------------------------------------------------------------
# --- STEP 3: DEFINE THE GRAPH NODES & ROUTER ---
# -----------------------------------------------------------------
def call_agent_node(state, llm):
    print("--- Calling Agent Node ---")
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}

def should_run_tools(state) -> str:
    print("--- Checking for Tools ---")
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        print("-> Decision: Run tools")
        return "run_tools"
    else:
        print("-> Decision: End")
        return END

# -----------------------------------------------------------------
# --- MAIN FUNCTION ---
# -----------------------------------------------------------------

def main():
    embedding_model = OllamaEmbeddings(model=OLLAMA_MODEL)
    vectorstore = load_vectorstore(DB_PATH, embedding_model)
    if vectorstore is None:
        print("Failed to load vector store. Exiting.")
        return
    retriever = setup_retriever(vectorstore)
    if retriever is None:
        print("Failed to set up retriever. Exiting.")
        return

    # --- Setup LLM ---
    llm = ChatOllama(model=LLM_MODEL, temperature=0.4)
    
    # -----------------------------------------------------------------
    # Define the RAG tool *inside* main() so it can "close over"
    # the retriever and llm variables from this scope.
    
    @tool
    def general_visa_question_tool(query: str) -> str:
        """
        Use this tool for all general questions about visa processes,
        document requirements, fees, application centers, or any other question
        that is NOT a request to track a specific application status.
        """
        print(f"--- Calling RAG Tool for: {query} ---")
        try:
            # 'retriever' and 'llm' are available from the main() scope!
            context_docs = retriever.get_relevant_documents(query)
            context_text = "\n".join([doc.page_content for doc in context_docs])
            
            rag_prompt = f"Context: {context_text}\n\nQuestion: {query}\nAnswer concisely."
            result = llm.invoke(rag_prompt) # Use the 'llm' from main()
            return result.content
        except Exception as e:
            print(f"[RAG Tool Error]: {e}")
            return "Sorry, I encountered an error trying to find an answer."
    
    # -----------------------------------------------------------------

    # --- Setup Tools ---
    # Now we just pass the two tools directly. No .bind() or partial() needed.
    tools = [track_visa_status_tool, general_visa_question_tool]
    
    llm_with_tools = llm.bind_tools(tools) # This will now work!
    
    # -----------------------------------------------------------------
    # --- STEP 4: ASSEMBLE THE GRAPH ---
    # -----------------------------------------------------------------

    graph = StateGraph(AgentState)

    graph.add_node(
        "agent",
        lambda state: call_agent_node(state, llm_with_tools)
    )
    
    tool_node = ToolNode(tools)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_run_tools,
        {
            "run_tools": "tools",
            END: END
        }
    )

    graph.add_edge("tools", "agent")

    app = graph.compile()
    
    # -----------------------------------------------------------------
    # --- STEP 5: THE MAIN LOOP
    # -----------------------------------------------------------------
    
    print("LangGraph Chatbot is ready! Ask me a general question or ask to track your visa.")
    
    chat_history = []

    while True:
        query = input("Ask your question (or type 'exit' to quit): ")
        if query.lower() in ['exit', 'quit']:
            print("Exiting the program.")
            break
        
        current_messages = chat_history + [HumanMessage(content=query)]
        
        try:
            result_state = app.invoke(
                {"messages": current_messages},
                {"recursion_limit": 10}
            )
            
            final_answer = result_state['messages'][-1]
            print(f"Answer: {final_answer.content}\n")
            
            chat_history = result_state['messages']

        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()