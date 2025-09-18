# PDF downloading extracting text from them can be done by using PyPDF2 or pdfplumber

import os 
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

download_dir = os.path.join(os.getcwd(), "D:\Chatbot\practice\Selenium\downloads")
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

chrome_options = Options()
prefs = {
    "download.default_directory": download_dir,
    "plugins.always_open_pdf_externally": True
}

chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options = chrome_options)

driver.get("https://ontheline.trincoll.edu/images/bookdown/sample-local-pdf.pdf")
print("PDF should start downloading...")

time.sleep(10)
driver.quit()

print(f"The PDF has been downloaded to {download_dir}")