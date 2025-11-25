import os
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.retrievers import BaseRetriever
import streamlit as st
from typing import List, Tuple
from langchain_core.documents import Document

# --- Configuration Constants ---
db_path = os.environ.get("DB_PATH", r"D:\Chatbot\practice\chroma_db")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mxbai-embed-large")
K_DOCS = os.environ.get("K_DOCS", 3)
FETCH_K = 20 # for MMR diversity search

# --- Core Functions (Optimized and Robust) ---

# Using st.cache_resource to load the expensive components only once
@st.cache_resource
def initialize_embedding_model(model_name: str) -> OllamaEmbeddings | None:
    """Initializes the Ollama embedding model and handles connection errors."""
    try:
        # Streamlit print messages go to the terminal running the app
        print(f"Initializing embedding model: {model_name}...")
        return OllamaEmbeddings(model=model_name)
    except Exception as e:
        st.error(f"FATAL ERROR: Could not initialize Ollama Embeddings model '{model_name}'.")
        st.error(f"Ensure the Ollama server is running and the model is pulled. Details: {e}")
        return None

@st.cache_resource
def load_vectorstore(db_path: str, embedding_model: OllamaEmbeddings) -> Chroma | None:
    """Loads an existing Chroma vector store."""
    if embedding_model is None:
        return None
        
    if not os.path.exists(db_path):
        st.warning(f"Vector store directory '{db_path}' does not exist. Please run the ingestion script.")
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
        st.error(f"Error loading vector store: {e}")
        return None

def setup_retriever(vectorstore: Chroma) -> BaseRetriever | None:
    """Sets up a Max Marginal Relevance (MMR) retriever."""
    if vectorstore is None:
        return None
    
    # Implementing MMR for better diversity in retrieval
    retriever = vectorstore.as_retriever(
        search_type="mmr", 
        search_kwargs={
            "k": K_DOCS,
            "fetch_k": FETCH_K,
            "lambda_mult": 0.5 
        } 
    )
    return retriever

# --- Streamlit Frontend Logic ---

def display_results(relevant_docs: List[Tuple[Document, float]]):
    """Displays the retrieved documents and scores in the Streamlit interface."""
    if not relevant_docs:
        st.info("No relevant documents found for your query.")
        return

    st.subheader(f"Top {len(relevant_docs)} Relevant Chunks Found:")

    # Use st.expander for a cleaner display of chunks
    for i, (doc, score) in enumerate(relevant_docs):
        # Chroma scores are distances, lower is better. Convert to similarity for better UX (1 - distance)
        similarity = 1 - score 
        
        with st.expander(f"**Result {i+1}: Similarity Score: {similarity:.4f}** (Distance: {score:.4f})"):
            
            st.markdown(f"**Source:** {doc.metadata.get('source', 'N/A')}")
            # Use st.markdown for metadata if available
            if 'country' in doc.metadata:
                 st.markdown(f"**Country:** **:flag-gb:{doc.metadata['country']}**")
            
            st.markdown("---")
            st.write(doc.page_content)


def streamlit_main():
    """Main function for the Streamlit application."""
    st.set_page_config(page_title="RAG Knowledge Base Search", layout="wide")
    st.title("📚 Knowledge Base Retriever")
    st.caption(f"Using **{OLLAMA_MODEL}** and **MMR** to retrieve top **{K_DOCS}** documents.")

    # 1. Initialize models and vector store
    embedding_model = initialize_embedding_model(OLLAMA_MODEL)
    vectorstore = load_vectorstore(db_path, embedding_model)

    if vectorstore is None:
        st.stop() # Stop the app if the core components aren't loaded

    # 2. Setup the MMR retriever
    # Note: We don't strictly need the BaseRetriever object if we use vectorstore.similarity_search_with_score directly
    # but we'll use it here to keep the function signatures consistent.
    retriever = setup_retriever(vectorstore) 
    
    if retriever is None:
        st.error("Retriever could not be set up.")
        st.stop()

    # 3. Streamlit UI: Search Box and Button
    with st.form(key='search_form'):
        query = st.text_input("Enter your search query:", placeholder="e.g., What are the tax requirements for foreigners?")
        search_button = st.form_submit_button(label='Search Knowledge Base 🔍')

    # 4. Handle Search Submission
    if search_button and query:
        st.write("---")
        with st.spinner(f"Searching for relevant documents using '{query}'..."):
            
            # Using similarity_search_with_score to display score, not retriever.invoke()
            relevant_docs = vectorstore.similarity_search_with_score(query, k=K_DOCS)

        display_results(relevant_docs)


if __name__ == "__main__":
    streamlit_main()