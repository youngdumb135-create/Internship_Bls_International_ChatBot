""" from langchain_community.document_loaders import SeleniumURLLoader

urls= ["https://www.blsslovakiavisa.com/"]
loader = SeleniumURLLoader(urls = urls)
documents = loader.load()

for i, doc in enumerate(documents):
    print(f"Document{i+1}")
    print(doc.page_content[:1000])
    print('-'*50)
 """

import time
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from langchain_core.documents import Document

# A simple list to keep track of visited URLs to avoid infinite loops and duplicate scraping.
visited_urls = set()
documents = []

def crawl_with_selenium(start_url: str, max_depth: int = 2):
    """
    Recursively crawls a website using Selenium, following internal links up to a specified depth.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Run in headless mode

    with webdriver.Chrome(options=chrome_options) as driver:
        # Initial call to start the recursive crawl
        _recursive_crawl(driver, start_url, max_depth, 0)
        
def _recursive_crawl(driver: webdriver, url: str, max_depth: int, current_depth: int):
    """
    The core recursive function for crawling.
    """
    # Base case: stop if we have reached the max depth or if the URL has been visited.
    if current_depth > max_depth or url in visited_urls:
        return

    print(f"[{current_depth}/{max_depth}] Crawling: {url}")
    visited_urls.add(url)
    
    # Navigate to the page
    try:
        driver.get(url)
        # Wait for the page to render. You might need to adjust this value.
        time.sleep(2)

        # Get the page content and create a LangChain document
        page_content = driver.page_source
        documents.append(Document(page_content=page_content, metadata={"source": url}))
        
    except Exception as e:
        print(f"Failed to load {url}: {e}")
        return

    # Find all 'a' (anchor) tags to discover links
    try:
        links = driver.find_elements(By.TAG_NAME, "a")
    except Exception as e:
        print(f"Could not find links on {url}: {e}")
        return

    # Extract valid, internal links and crawl them recursively
    for link in links:
        href = link.get_attribute("href")
        if href:
            # Join relative paths with the base URL
            full_url = urljoin(url, href)
            
            # Filter out external links and mailto/tel links
            is_internal = urlparse(full_url).netloc == urlparse(url).netloc
            is_new = full_url not in visited_urls
            is_valid = not (full_url.startswith("mailto:") or full_url.startswith("tel:"))

            if is_internal and is_new and is_valid:
                _recursive_crawl(driver, full_url, max_depth, current_depth + 1)


# --- Execution ---
if __name__ == "__main__":
    start_url = "https://www.blsslovakiavisa.com/"
    crawl_with_selenium(start_url, max_depth=2)

    # Print the content of all collected documents
    for i, doc in enumerate(documents):
        print(f"\n--- Document {i+1} ({doc.metadata['source']}) ---")
        print(doc.page_content[:500])  # Print the first 500 characters
        print("-" * 50)
