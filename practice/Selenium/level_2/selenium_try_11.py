# Handling multiple pages

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

driver = webdriver.Chrome()
try:
    driver.get("https://www.w3schools.com/html/html_tables.asp")

    original_window = driver.current_window_handle
    print(f"original window handle: {original_window}")
    print(f"original title: {driver.title}")


    try_button = WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.LINK_TEXT,"Try it Yourself »")))
    try_button.click()

    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))


    for window_handle in driver.window_handles:
        if window_handle!= original_window:
            driver.switch_to.window(window_handle)
            break


    print(f"New tab title: {driver.title}")
    driver.close()

    driver.switch_to.window(original_window)
    print(f"Original title = {driver.title}") 

except TimeoutException:
    print("TimeoutExceptiom")

except NoSuchElementException:
    print("NoSuchElement")

finally:
    driver.quit()