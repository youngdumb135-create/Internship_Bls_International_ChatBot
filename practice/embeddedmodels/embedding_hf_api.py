import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpointEmbeddings

load_dotenv()

model= "sentence-transformers/all-MiniLM-L6-v2"

huggingface_api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

embedding = HuggingFaceEndpointEmbeddings(
    model = model,
    task = "feature-extraction",
    huggingfacehub_api_token = huggingface_api_token
)
text = "Delhi is the capital of India"

vector = embedding.embed_query(text)

print(str(vector))