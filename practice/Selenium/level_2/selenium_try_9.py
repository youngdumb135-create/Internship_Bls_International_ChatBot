from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")

# Every browser sends a "User-Agent" string that tells the server what it is (e.g., "Chrome on Windows"). Some websites block the default Selenium user agent. You can easily change it.

# user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
# chrome_options.add_argument(f"user-agent={user_agent}")


driver = webdriver.Chrome(options = chrome_options)
driver.get("https://www.w3schools.com/html/html_tables.asp")

try:
    print(driver.title)

finally:
    driver.quit()


"""
Sometimes, elements don't have a convenient ID or class name. For these tricky situations, you have two powerful options.

CSS Selectors:

    # Find all links that end with ".pdf"
    pdf_links = driver.find_elements(By.CSS_SELECTOR, 'a[href$=".pdf"]')

    # Find the first element with the class "login-input"
    username_field = driver.find_element(By.CSS_SELECTOR, ".login-input")

    ->  #id: Select by ID. By.CSS_SELECTOR, "#username"
    ->  .class: Select by class. By.CSS_SELECTOR, ".search-button"
    ->  tag[attribute='value']: Select by an attribute. By.CSS_SELECTOR, "input[name='query']"
    ->  parent > child: Select a direct child. By.CSS_SELECTOR, "div.results > a"


XPath:

    # Find a single element with a relative XPath
    element = driver.find_element(By.XPATH, "//input[@id='email']")

    # Find all elements matching a complex XPath
    all_links = driver.find_elements(By.XPATH, "//div[@id='content']//a")
        
    

    Absolute XPath:
    This provides the full path from the root of the HTML document (<html>) to the target element. 
    Syntax: /html/body/div/p
    

    Relative XPath:
    This starts from anywhere in the document and is the preferred method for most scraping and automation tasks. 
    Syntax: //tagname[@attribute='value']

"""