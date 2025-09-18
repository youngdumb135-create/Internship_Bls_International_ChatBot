#hanfdling iframes

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

driver = webdriver.Chrome()
driver.get("https://www.w3schools.com/tags/tryit.asp?filename=tryhtml_iframe")

try:
    iframe = driver.find_element(By.XPATH,"//iframe")

    driver.switch_to.frame(iframe)

    button = driver.find_element(By.ID,"tnb-login-btn")
    button.click()

    driver.switch_to.default_content()

finally:
    driver.quit()
    print("Execution is complete")