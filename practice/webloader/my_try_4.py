# handling pdf
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import pypdf
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin

url ="https://www.blsslovakiavisa.com/azerbaijan/schengen-tourism-visa.php"


download_directory = os.path.join(os.getcwd(),'pdfs')
if not os.path.exists(download_directory):
    os.makedirs(download_directory)


chrome_options = Options()
chrome_prefs = {
    "download.default_directory": download_directory,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
}
chrome_options.add_experimental_option("prefs", chrome_prefs)
driver = webdriver.Chrome(options= chrome_options)



def wait_for_new_file(directory, initial_files, timeout = 30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        current_files = set(os.listdir(directory))
        new_files = current_files - initial_files

        
        for filename in new_files:
            new_filepath = os.path.join(directory,filename)
            if not new_filepath.endswith(('.crdownload', '.tmp')):
                return new_filepath
        time.sleep(0.5)
    raise TimeoutException(f"Time out waiting for a new file in {directory}")






try:
    pdf_texts = {}
    driver.get(url)
    print(f"Navigating to next page: {url}")

    if driver.current_url != url:
        print("Failed to navigate to specified url")
        
    
    pdf_links = [link.get_attribute("href") for link in driver.find_elements(By.XPATH,"//a[contains(@href,'.pdf')]")]

    
    original_window = driver.current_window_handle

    for pdf_url in pdf_links:
        absolute_url = urljoin(driver.current_url, pdf_url)
        if not pdf_url:
            continue
        file_name = os.path.basename(pdf_url.split('?')[0])
        if os.path.exists(os.path.join(download_directory,file_name)):
            print(f"Skipping the already downloaded pdf: {pdf_url}")
            continue

        print(f"Initiating the pdf download: {absolute_url}")
        initial_files = set(os.listdir(download_directory))


        try:
            driver.execute_script("window.open(arguments[0],'_blank');",absolute_url)

            num_windows_before = len(driver.window_handles)
            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(num_windows_before + 1))

            driver.switch_to.window(driver.window_handles[-1])

            download_file_path = wait_for_new_file(download_directory,initial_files,)

            with open(download_file_path,"rb") as file:
                reader = pypdf.PdfReader(file)
                text_pages = []
                for page in reader.pages:
                    extracted_text = page.extract_text()
                    if extracted_text:
                        text_pages.append(extracted_text)
                text = "".join(text_pages)  


                pdf_texts[os.path.basename(download_file_path)] = text
        except Exception as e:
            print(f"There was an error in opening and processing the pdf files: {e}")
        finally:
            try:
                driver.close()
                driver.switch_to.window(original_window)
            except Exception as close_e:
                print(f"There was an error in opening and processing the pdf file from {pdf_url}: {close_e}")

except Exception as e:
    print(f"Error occured in scraping pdf: {e}")

finally:
    driver.quit()
    print(pdf_texts)



