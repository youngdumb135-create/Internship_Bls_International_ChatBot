# Basic code I tried from the official documentation

from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://www.blsslovakiavisa.com/")
title = driver.title
# driver.implicitly_wait(0.5)
print(title)
a = driver.find_element(by = By.NAME, value = "button")
b = a.text
print(b)
hotBot = driver.find_element(by = By.NAME, value= "chatbot_toggle")
hotBot.click()

driver.quit()
