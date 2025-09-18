import os
import pypdf
import requests 
from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib.parse import urljoin

url = "https://www.blsslovakiavisa.com/azerbaijan/schengen-tourism-visa.php"


download_directory = os.path.join(os.getcwd(), 'pdfs')
if not os.path.exists(download_directory):
    os.makedirs(download_directory)


driver = webdriver.Chrome()

pdf_texts = {}

try:
    print(f"Navigating to: {url}")
    driver.get(url)

    # 1. Use Selenium to find all the PDF links
    pdf_links_elements = driver.find_elements(By.XPATH, "//a[contains(@href,'.pdf')]")
    pdf_relative_urls = [link.get_attribute("href") for link in pdf_links_elements]
    
    # --- Selenium's job is done, we can close it ---
    
    print(f"Found {len(pdf_relative_urls)} PDF links. Starting download and extraction.")

    # 2. Loop through the found URLs and use 'requests' to download them
    for relative_url in pdf_relative_urls:
        if not relative_url:
            continue
            
        absolute_url = urljoin(url, relative_url)
        file_name = os.path.basename(absolute_url.split('?')[0])
        download_file_path = os.path.join(download_directory, file_name)

        # Skip if already downloaded
        if os.path.exists(download_file_path):
            print(f"Skipping already downloaded file: {file_name}")
            # Still process the existing file
        else:
            try:
                print(f"Downloading: {absolute_url}")
                # Get the PDF content
                response = requests.get(absolute_url, timeout=30, verify = False)
                response.raise_for_status()  # This will raise an error for bad responses (like 404)

                # Save the PDF to a file
                with open(download_file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Successfully downloaded {file_name}")

            except requests.exceptions.RequestException as e:
                print(f"Failed to download {absolute_url}: {e}")
                continue # Skip to the next file if download fails
        

        try:
            with open(download_file_path, "rb") as file:
                reader = pypdf.PdfReader(file)
                text_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
                text = "".join(text_pages)
                pdf_texts[file_name] = text
        except Exception as e:
            print(f"Could not read or process PDF {file_name}: {e}")


except Exception as e:
    print(f"An unexpected error occurred: {e}")
    if 'driver' in locals() and driver.service.is_connectable():
        driver.quit()

finally:
    driver.quit()
    print("\n--- Extraction Complete ---")


    for filename, text in pdf_texts.items():
        print(f"\n--- Content for: {filename} ---")
        print(text[:] + "...")