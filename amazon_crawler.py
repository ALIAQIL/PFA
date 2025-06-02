import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

#with open("product_links.json", "w") as f:
    #json.dump([], f)

def write_json(new_data, filename='product_links.json'):
    with open(filename,'r+') as file:
          # First we load existing data into a dict.
        file_data = json.load(file)
        # Join new_data with file_data inside emp_details
        file_data.append(new_data)
        # Sets file's current position at offset.
        file.seek(0)
        # convert back to json.
        json.dump(file_data, file, indent = 4)

options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0 Safari/537.36")

browser = uc.Chrome(options=options)


browser.get("https://www.amazon.com")

wait = WebDriverWait(browser, 10)

#wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#f"))).click()
time.sleep(20)#wait for choose type of product
isNextDisabled = False

while not isNextDisabled:
    try:
        element = WebDriverWait(browser, 10).until(EC.presence_of_element_located(
            (By.XPATH, '//div[@data-component-type="s-search-result"]')))

        elem_list = browser.find_element(
            By.CSS_SELECTOR, "div.s-main-slot.s-result-list.s-search-results.sg-row")

        items = elem_list.find_elements(
            By.XPATH, '//div[@data-component-type="s-search-result"]')

        for item in items:
            link = item.find_element(
                By.CLASS_NAME, 'a-link-normal').get_attribute('href')
            print("Link: " + link + "\n")

            write_json({
                "link": link
            })


        next_btn = WebDriverWait(browser, 10).until(EC.presence_of_element_located(
            (By.CLASS_NAME, 's-pagination-next')))

        next_class = next_btn.get_attribute('class')

        if "disabled" in next_class:
            isNextDisabled = True
        else:
            browser.find_element(By.CLASS_NAME, 's-pagination-next').click()

    except Exception as e:
        print(e, "Main Error")
        isNextDisabled = True
