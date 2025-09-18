import os
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- CONFIGURATION ---
BASE_URL = "https://www.blsslovakiavisa.com/"
# Get the domain name to ensure we don't crawl external sites
DOMAIN = urlparse(BASE_URL).netloc
OUTPUT_TEXT_FILE = "all_text_content.txt"
OUTPUT_JSON_FILE = "structured_data.json"

def setup_driver():
    """Sets up the Selenium WebDriver in headless mode."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3") # Suppress console logs
    driver = webdriver.Chrome(options=chrome_options)
    # Set a page load timeout to prevent script from getting stuck
    driver.set_page_load_timeout(25)
    return driver

def scrape_page_content(url, driver):
    """
    Scrapes a single page for its text, PDF links, and tables.
    """
    print(f"Scraping: {url}")
    try:
        driver.get(url)
    except TimeoutException:
        print(f"  -> Timed out loading page. Skipping.")
        return None, [], [] # Return empty data for this page

    soup = BeautifulSoup(driver.page_source, "lxml")

    # 1. Extract all text
    # We remove script and style tags to get cleaner text
    for element in soup(["script", "style"]):
        element.decompose()
    page_text = soup.get_text(separator='\n', strip=True)

    # 2. Extract all PDF links
    pdf_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.lower().endswith('.pdf'):
            # Convert relative URL to absolute URL
            absolute_url = urljoin(BASE_URL, href)
            pdf_links.append(absolute_url)

    # 3. Extract all tables using Pandas
    page_tables = []
    try:
        # pd.read_html returns a list of DataFrames
        tables_on_page = pd.read_html(driver.page_source)
        if tables_on_page:
            print(f"  -> Found {len(tables_on_page)} table(s) on this page.")
            # Convert each DataFrame to a list of dictionaries for JSON serialization
            for table_df in tables_on_page:
                page_tables.append(table_df.to_dict('records'))
    except ValueError:
        # This error is raised by pandas if no tables are found
        pass 
    except Exception as e:
        print(f"  -> Error reading tables: {e}")

    return page_text, pdf_links, page_tables

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
        # Get the next URL from the set
        current_url = urls_to_visit.pop()
        
        if current_url in visited_urls:
            continue
            
        visited_urls.add(current_url)

        # Scrape the content of the current page
        text, pdfs, tables = scrape_page_content(current_url, driver)

        if text is not None:
            # Append text content for the .txt file
            all_scraped_text += f"\n\n{'='*80}\n"
            all_scraped_text += f"SOURCE URL: {current_url}\n"
            all_scraped_text += f"{'='*80}\n\n{text}"

            # Append structured data for the .json file
            structured_data.append({
                "url": current_url,
                "pdf_links": pdfs,
                "tables": tables
            })

            # Find all new internal links on the page to crawl next
            soup = BeautifulSoup(driver.page_source, 'lxml')
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Create an absolute URL from the found href
                absolute_link = urljoin(BASE_URL, href)
                
                # Parse the link to check its domain and remove fragments (#)
                parsed_link = urlparse(absolute_link)
                link_to_add = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
                
                # Ensure it's a new link, belongs to the same domain, and is a web page
                if (link_to_add not in visited_urls and 
                    link_to_add not in urls_to_visit and 
                    DOMAIN in link_to_add and
                    not link_to_add.endswith(('.jpg', '.png', '.zip'))):
                    urls_to_visit.add(link_to_add)

    # --- Save the collected data to files ---
    print("\nCrawling finished. Saving data...")

    # Save all text content
    with open(OUTPUT_TEXT_FILE, 'w', encoding='utf-8') as f:
        f.write(all_scraped_text)
    print(f"All text content saved to: {OUTPUT_TEXT_FILE}")

    # Save structured data
    with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=4)
    print(f"Structured data (PDF links, tables) saved to: {OUTPUT_JSON_FILE}")

    driver.quit()


# --- Main Execution ---
if __name__ == "__main__":
    crawl_site()