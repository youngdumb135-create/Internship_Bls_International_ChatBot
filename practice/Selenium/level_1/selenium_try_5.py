# Dealing with tables


#this method was fine but pandas gives us a much more simple flow

""" import time
from selenium import webdriver 
from bs4 import BeautifulSoup

driver = webdriver.Chrome()
driver.get("https://www.w3schools.com/html/html_tables.asp")
time.sleep(2)
html_content = driver.page_source

soup = BeautifulSoup(html_content,"lxml")

table = soup.find("table",id = "customers")


for row in table.find('tbody').find_all("tr"):
    cells = row.find_all('td')
    row_data = [cell.get_text(strip = True) for cell in cells]
    print(row_data) """



import pandas as pd
from selenium import webdriver

driver = webdriver.Chrome()
driver.get("https://www.w3schools.com/html/html_tables.asp")

list_of_tables = pd.read_html(driver.page_source)

driver.quit()

for i, df in enumerate(list_of_tables):
    print(f"table number: {i+1}")
    print(df)

# df.to_csv("company_data.csv", index=False)