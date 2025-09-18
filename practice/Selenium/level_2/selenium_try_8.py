# using explicit wait
# error handling using try, except, finally

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException

driver = webdriver.Chrome()
driver.get("https://www.w3schools.com/html/html_tables.asp")

try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME,"h2"))
    )


    html_content = driver.page_source
    soup = BeautifulSoup(html_content,"lxml")
    headings = soup.find_all("h2")


    if headings: 
        print("All the headings are;")
        for i, heading in enumerate(headings):
            print(f"Heading number: {i+1}")
            print(heading.get_text(strip=True))
    else:
        print("No headings were to be found.")


except TimeoutException:
    print("Time out waiting for <h2> tags to appear.")


finally:
    driver.quit()