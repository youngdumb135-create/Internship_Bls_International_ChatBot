# code 2 from official documentation where i realised probably not the best way

from selenium import webdriver

options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")


driver = webdriver.Chrome()
title = driver.title
assert title == "Web form"

driver.quit()