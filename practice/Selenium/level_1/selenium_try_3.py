# Code from Google Gemini probably the better approach
# Opens the browser goes to duckduckgo and searches giant panda

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


driver  =webdriver.Chrome()
driver.get("https://duckduckgo.com")

time.sleep(2)

searchbox = driver.find_element(By.NAME,'q')

searchbox.send_keys("giant panda")
searchbox.send_keys(Keys.RETURN)

print(f"The title of the page is: {driver.title}")
time.sleep(5)
driver.quit()
print("Script finished sucessfully")