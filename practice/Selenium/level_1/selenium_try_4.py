# Scraping headlines from a news website

import time
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://news.ycombinator.com/")
time.sleep(3)

html_content = driver.page_source
driver.quit()

soup = BeautifulSoup(html_content,"lxml")

headlines = soup.find_all("span", class_= "titleline")

print("The News Headlines Are: \n")

for index, headline in enumerate(headlines):
    title_text = headline.find("a").get_text() 
    print(f"{index + 1}. {title_text}")