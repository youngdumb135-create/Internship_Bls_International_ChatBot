import os
import shutil
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np 

BASE_DIR = os.environ.get("BASE_DIR", r"D:\Chatbot\practice\Knowledge_Base")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mxbai-embed-large")
SIM_THRESHOLD = os.environ.get("SIM_THRESHOLD", 0.53)


def semantic_chunker(doc: Document, embeddings: OllamaEmbeddings, similarity_threshold: float) -> list[Document]:
    """
    Splits a document into semantic chunks based on cosine similarity of sentence embeddings.
    Args:
        doc (Document): The document to be chunked.
        embeddings (OllamaEmbeddings): The embedding model to generate sentence embeddings.
        similarity_threshold (float): The cosine similarity threshold to determine chunk boundaries.
    Returns:
        list[Document]: A list of semantic chunk documents.
    """

    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
        separator=". ", chunk_size=50, chunk_overlap=0
    )
    sentences = text_splitter.split_text(doc.page_content)
    
    if not sentences:
        return []

    sentence_embeddings = embeddings.embed_documents(sentences)

    embeddings_array = np.array(sentence_embeddings)
    
    similarities = np.diag(
        cosine_similarity(embeddings_array[:-1], embeddings_array[1:])
    ).tolist()

    split_points = [0]
    for i, sim in enumerate(similarities):
        if sim < similarity_threshold:
            split_points.append(i + 1)
    split_points.append(len(sentences))

    semantic_chunks = []
    for i in range(len(split_points) - 1):
        start_index = split_points[i]
        end_index = split_points[i+1]
        
        chunk_text = " ".join(sentences[start_index:end_index])
        
        new_doc = Document(page_content=chunk_text, metadata=doc.metadata)
        
        semantic_chunks.append(new_doc)
        
    return semantic_chunks



def ingest_and_chunk_documents(base_dir: str, embeddings: OllamaEmbeddings, similarity_threshold: float) -> list[Document]:
    """
    Ingests .docx documents from country-specific subdirectories, chunks them semantically, and returns all chunks.
    Args:
        base_dir (str): The base directory containing country subdirectories with 'docx' folders.
        embeddings (OllamaEmbeddings): The embedding model to use for chunking.
        similarity_threshold (float): The cosine similarity threshold for chunking.
    Returns:
        list[Document]: A list of all semantic chunk documents.
    """

    all_chunks = []
    
    for country_folder in os.listdir(base_dir):
        country_path = os.path.join(base_dir, country_folder)
        
        if os.path.isdir(country_path) and not country_folder.startswith('.'):
            country_name = country_folder
            docx_path = os.path.join(country_path, 'docx')
            
            if os.path.isdir(docx_path):
                print(f"Processing documents for {country_name}...")
                
                for file_name in os.listdir(docx_path):
                    if file_name.endswith('.docx'):
                        file_path = os.path.join(docx_path, file_name)
                        
                        try:

                            loader = UnstructuredWordDocumentLoader(file_path)
                            loaded_docs = loader.load()
                            
                            for doc in loaded_docs:
                                
                                doc.metadata['country'] = country_name
                                
                                chunks = semantic_chunker(doc, embeddings, similarity_threshold)
                                all_chunks.extend(chunks)
                                
                        except Exception as e:
                            print(f"Error processing {file_name} in {country_name}: {e}")
                            
    return all_chunks


def initiating_vectorstore(db_path: str, embedding_model, chunked_documents) -> Chroma | None:
    """
    Creates and persists a Chroma vector store from chunked documents.
    Args:
        db_path (str): The directory path where the Chroma vector store will be persisted.
        embedding_model: The embedding model to use with the vector store.
        chunked_documents (list[Document]): The list of chunked documents to be added to the vector store.
    Returns:
        Chroma or None: The created Chroma vector store or None if creation fails."""
    
    try:
        print(f"Creating and persisting vector store at {db_path}...")
        vectorstore = Chroma.from_documents(
            documents=chunked_documents, 
            embedding=embedding_model,
            persist_directory=db_path
        )
        print("Vector store created successfully.")

    except Exception as e:
        print(f"Error creating vector store: {e}")
        vectorstore = None
    return vectorstore



def main():

    try:
        print("Initializing embedding model...")
        embedding_model = OllamaEmbeddings(model= OLLAMA_MODEL)
    except Exception as e:
        print(f"Error initializing embedding model: {e}")
        return


    chunked_documents = ingest_and_chunk_documents(BASE_DIR, embedding_model, SIM_THRESHOLD)


    original_doc_sources = set(
        doc.metadata.get('source') 
        for doc in chunked_documents 
        if doc.metadata.get('source') is not None
    )
    

    print(f"\nFinished ingesting and chunking.")
    print(f"Total original documents processed: {len(original_doc_sources)}")
    print(f"Total semantic chunks created: {len(chunked_documents)}")


    db_path = "./chroma_db"
    if os.path.exists(db_path):
        print(f"!!! WARNING: Removing existing database at {db_path} to perform full rebuild. !!!")
        shutil.rmtree(db_path)

    vectorstore = initiating_vectorstore(db_path, embedding_model, chunked_documents)

if __name__ == "__main__":
    main()
