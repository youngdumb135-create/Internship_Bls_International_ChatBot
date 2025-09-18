# worked on extracting table using pandas and printing them
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

url = "https://www.blsslovakiavisa.com/azerbaijan/schengen-tourism-visa.php"
driver = webdriver.Chrome()
driver.find_element


def table_extractor(table_list):
    for i, df in enumerate(table_list):
            print(f"table no. {i+1}")
            print(df)
    tables_on_page = [table.values.tolist() for table in table_list]
    return tables_on_page


def web_scraper(driver,url):
    data = {"url": url}
    try:
        driver.get(url)
        body_element = driver.find_element(By.TAG_NAME, "body")
        data["body_data"] = body_element.text
        

        html_content= driver.page_source
        table_list = pd.read_html(html_content)
        data["tables"]= table_extractor(table_list)


    except Exception as e:
        print(f"[{url}] An unexpected error occurred while scraping tables with pandas: {e}")
        data["tables"] = None

    finally:
        driver.quit()
        return data


if __name__ == "__main__":
    print(web_scraper(driver, url))
    