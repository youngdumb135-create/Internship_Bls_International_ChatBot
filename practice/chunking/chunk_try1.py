from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_huggingface import HuggingFaceEmbeddings
from glob import glob


loader = DirectoryLoader(
     'D:/Chatbot/practice/Data/',
    glob="*.txt",
    loader_cls=TextLoader
)

documents = loader.load()
full_text = " ".join([doc.page_content for doc in documents])

""" text_files = glob("D:/Chatbot/practice/Data/")
loader = TextLoader("D:/Chatbot/practice/Data/KB_1.txt")
documents = loader.load()
full_text = documents[0].page_content """ 

embedding = HuggingFaceEmbeddings(model="sentence-transformers/all-MiniLM-L6-v2")

semantic_splitter = SemanticChunker(embedding)

docs = semantic_splitter.create_documents([full_text])



for i, chunk in enumerate(docs):
    print(f"--- Chunk {i + 1} ---")
    print(chunk.page_content)
    print("\n")