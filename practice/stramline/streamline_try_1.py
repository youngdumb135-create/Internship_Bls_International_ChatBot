from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_huggingface import HuggingFaceEmbeddings
from glob import glob

from langchain_community.vectorstores import FAISS

import torch
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

loader = DirectoryLoader(
     'D:/Chatbot/practice/Data/',
    glob="*.txt",
    loader_cls=TextLoader
)

documents = loader.load()

full_text = " ".join([doc.page_content for doc in documents])

embedding = HuggingFaceEmbeddings(model="sentence-transformers/all-MiniLM-L6-v2")

semantic_splitter = SemanticChunker(
    embedding,
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=25,
    min_chunk_size=30
)

docs = semantic_splitter.create_documents([full_text])

""" 
for i, chunk in enumerate(docs):
    print(f"--- Chunk {i + 1} ---")
    print(chunk.page_content)
    print("\n")

vector = embedding.embed_documents(full_text)
print(vector)  """

vector_store = FAISS.from_documents(docs, embedding)
print("chunks and embedding have been stored in FAISS")

retriever = vector_store.as_retriever()
user_querry= input("Enter the user query ")
needed_chunk = retriever.invoke(user_querry)

print("Retrieved chunks related to the query:")
for i, doc in enumerate(needed_chunk):
    print(f"\n--- Chunk {i+1} ---")
    print(doc.page_content)



context = needed_chunk[0].page_content + needed_chunk[1].page_content

prompt = (f"Give direct answer to query:{user_querry} only using context :{context}, be precise ")



model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id)

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=100,
    temperature=0.5,
    do_sample=True
)

llm = HuggingFacePipeline(pipeline=pipe)

model= ChatHuggingFace(llm = llm)

result = model.invoke(prompt)

print(result.content)