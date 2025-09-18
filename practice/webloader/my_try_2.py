# Worked on the validation part of URLs

from selenium import webdriver
from selenium.webdriver.common.by import By
import validators
from urllib.parse import urlparse, urljoin, urlunparse

base_url = "https://www.blsslovakiavisa.com/"
base_domain = urlparse(base_url).netloc

driver = webdriver.Chrome()
driver.get(base_url)
a_tags = driver.find_elements(By.TAG_NAME,"a")
extracted_url = set()
discarded_url = set() 


def url_validation(url_to_be_checked):

    if not url_to_be_checked or not url_to_be_checked.startswith(("http", "https")): # Checks if there is some url or empty string, checks if it starts with http or https
        return False
    
    if not validators.url(url_to_be_checked): # Uses python's validators library to check if the url is valid or not
        return False
    

    parsed_url = urlparse(url_to_be_checked) # Convert the url to parsed form then the fragment part is removed
    fragmentless_url = urlunparse(parsed_url._replace(fragment = ""))

    parsed_base_url = urlparse(base_url) # Same done for base website url 
    fragmentless_base_url = urlunparse(parsed_base_url._replace(fragment = ""))

    if fragmentless_url == fragmentless_base_url: # Check if there was no hperlink that takes us back to the homepage
        return False

    parsed_fragmentless_url = urlparse(fragmentless_url)

    return parsed_fragmentless_url.netloc.endswith(base_domain) # Finally checks if the url is not same as that of base webpage




for link in a_tags:
    link_url = link.get_attribute("href")
    print(link_url)
    
    absolute_url = urljoin(base_url, link_url)
    print(absolute_url)


    if url_validation(absolute_url):
        extracted_url.add(absolute_url)

    else:
        discarded_url.add(absolute_url)



print("*"*50)

for url in extracted_url:
    print(url)

print("*"*50)

for url in discarded_url:
    print(url)


driver.quit()

