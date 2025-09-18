# Handling forms

import time
from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://www.w3schools.com/html/html_forms.asp")
time.sleep(2)

first_name = driver.find_element(By.ID, "fname")
last_name = driver.find_element(By.ID, "lname")
submit = driver.find_element(By.NAME, "submit")
first_name.send_keys("Rohit")
last_name.send_keys("Sharma")
submit.click()
print("logged in successfully")
time.sleep(2)

driver.quit()
