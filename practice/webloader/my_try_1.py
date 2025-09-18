from collections import deque
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import validators
from urllib.parse import urlparse, urlunparse, urljoin


base_url = "https://www.blsslovakiavisa.com/"
base_domain = urlparse(base_url).netloc
to_visit_url = deque([base_url])
visited_url = set()
# max_depth = 2


def driver_options():
    print("will provide the options for web driver")


def url_validation(url_to_be_checked):

    if not url_to_be_checked or not url_to_be_checked.startswith(("http", "https")):
        return False
    if not validators.url(url_to_be_checked): 
        return False
    
    parsed_url = urlparse(url_to_be_checked) 
    fragmentless_url = urlunparse(parsed_url._replace(fragment = ""))

    parsed_base_url = urlparse(base_url) 
    fragmentless_base_url = urlunparse(parsed_base_url._replace(fragment = ""))

    if fragmentless_url == fragmentless_base_url: 
        return False

    parsed_fragmentless_url = urlparse(fragmentless_url)

    return parsed_fragmentless_url.netloc.endswith(base_domain) 


def web_scraping(current_url, driver):
    print("Web scraper logic will go here")

    # for plain text -----------------------------------------------------







    # for tables ---------------------------------------------------------
    #provide the list of tables then pass the function
    






    # for pdfs -----------------------------------------------------------
    # provide the pdfs link the pass the function















def web_crawler():

    extracted_url = set()
    discarded_url = set() 
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    try:
        while to_visit_url:
            
            current_url = to_visit_url.popleft()
            if current_url in visited_url:
                continue
            visited_url.add(current_url)
            driver.get(current_url)
            print(driver.title)
            print(current_url)

            # scraping the page
            # web_scraping(current_url, driver)

            # Get all the urls from the page
            urls_on_this_page = driver.find_elements(By.TAG_NAME, "a")
        
            for link in urls_on_this_page:
                link_url = link.get_attribute("href")
                absolute_url = urljoin(base_url, link_url)

                if url_validation(absolute_url):
                    if absolute_url not in visited_url:
                        to_visit_url.append(absolute_url)
                        extracted_url.add(absolute_url)

                else:
                    discarded_url.add(absolute_url)

    except TimeoutException:
        print("Time out error occurred.")

    finally:
        driver.quit()


    print("\n" + "*"*50)
    print("Extracted URLs (Same Domain):")
    for url in extracted_url:
        print(url)

    print("\n" + "*"*50)
    print("Discarded URLs (External/Invalid):")
    for url in discarded_url:
        print(url)


if __name__ == "__main__":
    web_crawler()