from langchain_community.document_loaders import RecursiveUrlLoader
from bs4 import BeautifulSoup as Soup

# Specify the starting URL and a custom BeautifulSoup parser
loader = RecursiveUrlLoader(
    url="https://india.blsspainvisa.com/",
    max_depth=10, # Control how many levels deep to crawl from the root URL
    extractor=lambda x: Soup(x, "html.parser").text,
    timeout=60
)
    


# Load all documents found by the crawler
docs = loader.load()
print(f"Loaded {len(docs)} documents.")

for i, j in enumerate(docs):
    print(f"page {i+1} \n")
    print(f"{j.page_content} \n")