import os
import json
import pandas as pd
import requests
import pdfplumber
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- CONFIGURATION ---
BASE_URL = "https://www.blsslovakiavisa.com/"
DOMAIN = urlparse(BASE_URL).netloc
OUTPUT_TEXT_FILE = "all_text_content_with_pdfs.txt"
OUTPUT_JSON_FILE = "structured_data_with_pdfs.json"

def setup_driver():
    """Sets up the Selenium WebDriver in headless mode."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(20)
    return driver

def extract_text_from_pdf(pdf_url):
    """Downloads a PDF from a URL and extracts its text content."""
    print(f"  -> Parsing PDF: {pdf_url}")
    try:
        # Use requests to get the PDF content
        response = requests.get(pdf_url, timeout=20)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Use BytesIO to treat the binary content as a file
        pdf_file = io.BytesIO(response.content)

        full_text = ""
        # Open the PDF with pdfplumber
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                # Extract text from each page and append it
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        return full_text.strip()

    except requests.exceptions.RequestException as e:
        print(f"  -> Failed to download PDF {pdf_url}. Error: {e}")
        return None
    except Exception as e:
        # Catches errors from pdfplumber if the PDF is corrupt or unreadable
        print(f"  -> Failed to parse PDF {pdf_url}. Error: {e}")
        return None

def scrape_page_content(url, driver):
    """
    Scrapes a single page for its text, tables, and linked PDF content.
    """
    print(f"Scraping: {url}")
    try:
        driver.get(url)
    except TimeoutException:
        print(f"  -> Timed out loading page. Skipping.")
        return None, [], []

    soup = BeautifulSoup(driver.page_source, "lxml")

    # 1. Extract HTML text
    for element in soup(["script", "style"]):
        element.decompose()
    page_text = soup.get_text(separator='\n', strip=True)

    # 2. Find PDF links and extract their content
    pdf_data = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.lower().endswith('.pdf'):
            absolute_url = urljoin(BASE_URL, href)
            # Get the text from within the PDF
            pdf_content = extract_text_from_pdf(absolute_url)
            pdf_data.append({
                "pdf_url": absolute_url,
                "content": pdf_content if pdf_content else "Could not extract text."
            })

    # 3. Extract tables
    page_tables = []
    try:
        tables_on_page = pd.read_html(driver.page_source)
        if tables_on_page:
            print(f"  -> Found {len(tables_on_page)} table(s) on this page.")
            for table_df in tables_on_page:
                page_tables.append(table_df.to_dict('records'))
    except ValueError:
        pass
    except Exception as e:
        print(f"  -> Error reading tables: {e}")

    return page_text, pdf_data, page_tables

def crawl_site():
    """
    Main function to crawl the website and orchestrate scraping.
    """
    driver = setup_driver()
    
    urls_to_visit = {BASE_URL}
    visited_urls = set()
    
    all_scraped_text = ""
    structured_data = []

    while urls_to_visit:
        current_url = urls_to_visit.pop()
        
        if current_url in visited_urls:
            continue
        
        visited_urls.add(current_url)

        # Scrape the content
        text, pdfs, tables = scrape_page_content(current_url, driver)

        if text is not None:
            # --- Append content to the main text file ---
            all_scraped_text += f"\n\n{'='*80}\nSOURCE URL: {current_url}\n{'='*80}\n\n{text}"
            
            # Append text from any PDFs found on this page
            if pdfs:
                for pdf_info in pdfs:
                    all_scraped_text += f"\n\n{'-'*80}\n"
                    all_scraped_text += f"CONTENT FROM PDF: {pdf_info['pdf_url']}\n"
                    all_scraped_text += f"{'-'*80}\n\n{pdf_info['content']}"

            # --- Append structured data for the JSON file ---
            structured_data.append({
                "page_url": current_url,
                "linked_pdfs": pdfs,
                "tables": tables
            })

            # Find new internal links to crawl
            soup = BeautifulSoup(driver.page_source, 'lxml')
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_link = urljoin(BASE_URL, href)
                parsed_link = urlparse(absolute_link)
                link_to_add = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
                
                if (link_to_add not in visited_urls and 
                    link_to_add not in urls_to_visit and 
                    DOMAIN in link_to_add and
                    not link_to_add.endswith(('.jpg', '.png', '.zip', '.mailto'))):
                    urls_to_visit.add(link_to_add)

    # --- Save the final data ---
    print("\nCrawling finished. Saving data...")
    with open(OUTPUT_TEXT_FILE, 'w', encoding='utf-8') as f:
        f.write(all_scraped_text)
    print(f"All text content saved to: {OUTPUT_TEXT_FILE}")

    with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=4)
    print(f"Structured data saved to: {OUTPUT_JSON_FILE}")

    driver.quit()

# --- Main Execution ---
if __name__ == "__main__":
    crawl_site()