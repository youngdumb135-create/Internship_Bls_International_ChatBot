#basecode
""" from langchain_community.document_loaders import PlaywrightURLLoader
from bs4 import BeautifulSoup as Soup

# List of URLs to load
urls = [
    "https://india.blsspainvisa.com/national_visa.php", 
]

# Initialize the loader
# Use headless=True for faster execution without a visible browser window
loader = PlaywrightURLLoader(
    urls=urls,
    headless=True,
    continue_on_failure=True, # Continue scraping other URLs if one fails
    goto_kwargs={"timeout": 120000, "wait_until": "domcontentloaded"},

)

# Load the documents
try:
    docs = loader.load()
    print(f"Loaded {len(docs)} documents.")

    # Print the content of the first loaded document
    if docs:
        print(docs.page_content)
        print("--- End Document ---")
except Exception as e:
    print(f"Failed to load documents: {e}")
 """

#increased limit
""" import os
from langchain_community.document_loaders import PlaywrightURLLoader
from unstructured.partition.html import partition_html
from playwright.sync_api import sync_playwright

# Set a custom user-agent environment variable
os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"

# URLs to be scraped
urls = ["https://india.blsspainvisa.com/national_visa.php"]

try:
    print("Starting Playwright loader with a longer timeout...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        docs = []
        for url in urls:
            try:
                # Go to the URL with an increased timeout and wait for the DOM
                page.goto(url, timeout=120000, wait_until="domcontentloaded")
                
                # Get the HTML content after the page is rendered
                html_content = page.content()
                
                # Use Unstructured to partition the HTML and extract elements
                elements = partition_html(text=html_content, url=url)
                
                # Combine elements into a single document object
                full_text = "\n\n".join([str(el) for el in elements])
                docs.append(full_text)

            except Exception as e:
                print(f"Error fetching or processing {url}: {e}")

        browser.close()

        if docs:
            print(f"Successfully loaded {len(docs)} documents.")
            print("\n--- Printing all page content ---")
            
            # Loop through the list of loaded document content and print it
            for i, doc_content in enumerate(docs):
                print(f"\n--- Document {i+1} ---")
                print(doc_content)
                print("-" * 20)
        else:
            print("Loaded 0 documents. The page may still have failed to load.")

except Exception as e:
    print(f"An error occurred: {e}") """

""" import os
import re
from urllib.parse import urljoin, urlparse
from collections import deque
from playwright.sync_api import sync_playwright
from unstructured.partition.html import partition_html
from bs4 import BeautifulSoup

def is_valid_url(url, base_url):
    
    parsed_base = urlparse(base_url)
    parsed_url = urlparse(url)
    # Check for empty URL, valid scheme, and same domain
    return bool(parsed_url.netloc) and parsed_url.scheme in ['http', 'https'] and parsed_url.netloc == parsed_base.netloc

def scrape_dynamic_website(start_url, max_pages=200):
   
    # Set a custom user-agent
    os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"

    # Queues for managing crawling
    queue = deque([start_url])
    visited = set([start_url])
    all_docs = []
    
    print(f"Starting crawl from: {start_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=os.environ["USER_AGENT"])
        page = context.new_page()

        while queue and len(all_docs) < max_pages:
            url = queue.popleft()
            print(f"Scraping URL: {url}")

            try:
                # Navigate to the page with an increased timeout
                page.goto(url, timeout=120000, wait_until="domcontentloaded")
                
                # Get the fully rendered HTML content
                html_content = page.content()

                # Extract and store the content
                elements = partition_html(text=html_content, url=url)
                full_text = "\n\n".join([str(el) for el in elements])
                all_docs.append(full_text)

                # Use BeautifulSoup to parse links efficiently
                soup = BeautifulSoup(html_content, 'html.parser')
                links = [a.get('href') for a in soup.find_all('a', href=True)]

                for link in links:
                    # Resolve relative URLs and remove anchor tags
                    full_link = urljoin(url, link).split('#')[0]
                    
                    if is_valid_url(full_link, start_url) and full_link not in visited:
                        visited.add(full_link)
                        queue.append(full_link)
            
            except Exception as e:
                print(f"Error fetching or processing {url}: {e}")
        
        browser.close()
    
    return all_docs

# --- Main execution ---
if __name__ == "__main__":
    home_url = "https://www.blsinternational.com/"
    documents = scrape_dynamic_website(home_url, max_pages=100) # Reduced max_pages for demonstration
    
    if documents:
        print(f"\nSuccessfully loaded {len(documents)} documents.")
        print("\n--- Printing all page content ---")
        for i, doc_content in enumerate(documents):
            print(f"\n--- Document {i+1} ---")
            print(doc_content)
            print("-" * 20)
    else:
        print("Failed to load any documents.") """

#with pdf interpretation

import os
import re
import requests
from urllib.parse import urljoin, urlparse
from collections import deque
from playwright.sync_api import sync_playwright
from unstructured.partition.html import partition_html
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyPDFLoader
from time import sleep
import random
import tempfile

def is_valid_url(url, base_url):
    """Check if a URL is valid, a full URL, and belongs to the same domain."""
    if not isinstance(url, str):
        return False
    
    parsed_base = urlparse(base_url)
    parsed_url = urlparse(url)
    
    # Check for valid scheme (http/https), a network location, and same domain
    return (
        parsed_url.scheme in ['http', 'https'] and
        parsed_url.netloc and
        parsed_url.netloc == parsed_base.netloc
    )

def process_pdf(pdf_url):
    """Downloads and extracts text from a PDF URL."""
    try:
        response = requests.get(pdf_url, timeout=60, headers={"User-Agent": os.environ["USER_AGENT"]})
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            loader = PyPDFLoader(temp_file_path)
            docs = loader.load()
            
            # Clean up the temporary file
            os.remove(temp_file_path)
            
            if docs:
                # Combine text from all PDF pages into a single document string
                full_text = "\n\n".join([doc.page_content for doc in docs])
                return {"content": full_text, "source": pdf_url}
        else:
            print(f"Failed to download PDF from {pdf_url}: Status code {response.status_code}")
    except Exception as e:
        print(f"Error processing PDF from {pdf_url}: {e}")
    return None

def scrape_dynamic_website(start_url, max_pages=10):
    """Scrapes a dynamic website starting from a home URL."""
    os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"

    queue = deque([start_url])
    visited = set()
    all_docs = []
    
    print(f"Starting crawl from: {start_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=os.environ["USER_AGENT"], viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        while queue and len(all_docs) < max_pages:
            url = queue.popleft()
            full_url = url.split('#')[0] if '#' in url else url
            if full_url in visited:
                continue
            visited.add(full_url)
            print(f"Scraping URL: {full_url} (Queue: {len(queue)}, Visited: {len(visited)})")

            if full_url.lower().endswith('.pdf'):
                # Process PDF files
                doc = process_pdf(full_url)
                if doc:
                    all_docs.append(doc)
                sleep(random.uniform(2, 5)) # Add delay for PDF processing
                continue
            
            try:
                page.goto(full_url, timeout=120000, wait_until="domcontentloaded")
                
                # --- Link Discovery and Queue Management ---
                soup = BeautifulSoup(page.content(), 'html.parser')
                links = [a.get('href') for a in soup.find_all('a', href=True)]
                for link in links:
                    next_url = urljoin(full_url, link).split('#')[0]
                    if is_valid_url(next_url, start_url) and next_url not in visited:
                        queue.append(next_url)
                
                # --- Content Extraction from HTML ---
                elements = partition_html(text=page.content(), url=full_url)
                full_text = "\n\n".join([str(el) for el in elements])
                all_docs.append({"content": full_text, "source": full_url})
                
                sleep(random.uniform(2, 5))
            
            except Exception as e:
                print(f"Error fetching or processing {full_url}: {e}")
        
        browser.close()
    
    return all_docs

# --- Main execution ---
if __name__ == "__main__":
    home_url = "https://www.blsinternational.com/"
    documents = scrape_dynamic_website(home_url, max_pages=100) # Set a reasonable limit
    
    if documents:
        print(f"\nSuccessfully loaded {len(documents)} documents.")
        print("\n--- Printing all page content ---")
        for i, doc in enumerate(documents):
            print(f"\n--- Document {i+1} ---")
            print(f"Source: {doc['source']}")
            print(doc['content'][:500] + "...") # Print a snippet for readability
            print("-" * 20)
    else:
        print("Failed to load any documents.")

