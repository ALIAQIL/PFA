# Enhanced Amazon Scraper with Improved CAPTCHA Handling
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import random
import os
import logging
import signal
import sys
from tesseract.OCR import ImageTextExtractor
from proxy_manager import ProxyManager

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Graceful shutdown
terminate = False

def signal_handler(sig, frame):
    global terminate
    terminate = True
    logger.info("Graceful shutdown initiated. Finishing current task...")

signal.signal(signal.SIGINT, signal_handler)

# Chrome Options Setup
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
]

def _setup_chrome_options(proxy=None):
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    if random.choice([True, False]):
        options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--mute-audio")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    # Remove the headless mode to make the browser visible
    options.add_argument("--headless=new")
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    return options

# Improved CAPTCHA Solver with retries
def _solve_captcha(browser, wait, max_attempts=5):
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"CAPTCHA solving attempt {attempt}/{max_attempts}")
            
            # Check if CAPTCHA is present
            captcha_present = False
            try:
                captcha_img = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.a-row.a-text-center > img'))
                )
                captcha_present = True
            except TimeoutException:
                # No CAPTCHA found, we can proceed
                logger.info("No CAPTCHA detected")
                return True
            
            if not captcha_present:
                return True
                
            # Take screenshot of CAPTCHA
            os.makedirs('captchas', exist_ok=True)
            captcha_path = f'captchas/captcha_{attempt}.png'
            captcha_img.screenshot(captcha_path)

            # Extract text from CAPTCHA
            extractor = ImageTextExtractor(captcha_path)
            captcha_text = ''.join(char for char in extractor.extract_text() if char.isalnum())
            
            if not captcha_text:
                logger.warning(f"Failed to extract text from CAPTCHA (attempt {attempt})")
                if attempt < max_attempts:
                    # Try refreshing the CAPTCHA
                    try:
                        refresh_button = browser.find_element(By.CSS_SELECTOR, 'a.a-declarative > i.a-icon.a-icon-refresh')
                        refresh_button.click()
                        time.sleep(2)  # Wait for new CAPTCHA to load
                        continue
                    except NoSuchElementException:
                        logger.warning("Could not find CAPTCHA refresh button")
            
            logger.info(f"Extracted CAPTCHA text: {captcha_text}")

            # Enter CAPTCHA text
            input_field = browser.find_element(By.ID, 'captchacharacters')
            input_field.clear()
            input_field.send_keys(captcha_text)

            # Submit CAPTCHA
            submit_button = browser.find_element(
                By.XPATH, '//button[contains(@class, "a-button-text") and contains(text(), "Continue shopping")]'
            )
            submit_button.click()
            time.sleep(3)  # Wait for response after submitting
            
            # Check if we're still on the CAPTCHA page
            try:
                still_captcha = browser.find_element(By.ID, 'captchacharacters')
                logger.warning(f"CAPTCHA solving failed on attempt {attempt}")
                # If we're still on CAPTCHA page, try again
                continue
            except NoSuchElementException:
                # CAPTCHA element not found, we've likely passed it
                logger.info(f"CAPTCHA solved successfully on attempt {attempt}")
                return True
                
        except Exception as e:
            logger.warning(f"CAPTCHA solving error on attempt {attempt}: {e}")
            if attempt >= max_attempts:
                logger.error(f"Failed to solve CAPTCHA after {max_attempts} attempts")
                return False
    
    return False

# Data Extractor
def _extract_product_data(browser, wait, element, url):
    """Extract product data from the Amazon page"""
    data = {}
    extractors = {
        'name': [(By.CSS_SELECTOR, 'span#productTitle', 'text')],
        'price': [
            (By.XPATH, '//*[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[2]/span[2]', 'text'),
            (By.CSS_SELECTOR, 'span.a-price span.a-offscreen', 'text'),
            (By.CSS_SELECTOR, 'span.a-price', 'text')
        ],
        'rating': [
            (By.XPATH, '//*[@id="cm_cr_dp_d_rating_histogram"]/div[2]/div/div[2]/div/span/span', 'text'),
            (By.CSS_SELECTOR, 'span.a-icon-alt', 'text'),
            (By.CSS_SELECTOR, 'div.a-row a-spacing-small > span', 'text')
        ],
        'image': [(By.CSS_SELECTOR, 'img#landingImage', 'src')],
        'characteristics': [(By.XPATH, '//*[@id="poExpander"]/div[1]/div/table/tbody', 'text')],
        'about_this_item': [
            (By.XPATH, '//*[@id="feature-bullets"]/ul', 'text'),
            (By.CSS_SELECTOR, 'div#feature-bullets ul', 'text')
        ],
        'technical_details': [(By.XPATH, '//*[@id="productDetails_techSpec_section_1"]/tbody', 'text')],
        'product_description': [
            (By.XPATH, '//*[@id="productDescription"]/p/span', 'text'),
            (By.CSS_SELECTOR, 'div#productDescription p', 'text')
        ],
        'additional_information': [(By.XPATH, '//*[@id="productDetails_db_sections"]', 'text')],
        'warranty': [(By.XPATH, '//*[@id="productSpecifications_dp_warranty_and_support"]/div/div[1]/span[3]', 'text')],
        'compare_with_similar_items':[(By.XPATH,'//div[@class="_product-comparison-desktop_desktopFaceoutStyle_comparison-table-wrapper__1UCJ-"]','text')]
    }

    for key, selector_list in extractors.items():
        value = "N/A"
        for by, selector, attr in selector_list:
            try:
                found_element = browser.find_element(by, selector)
                value = found_element.get_attribute('src') if attr == 'src' else found_element.text
                if value:
                    break
            except NoSuchElementException:
                continue

        if key == 'name' and value != "N/A":
            parts = value.split("\"", 1)
            data['name'] = parts[0].strip()
            data['resume'] = parts[1].strip() if len(parts) > 1 else ""
        else:
            data[key] = value.replace("\n", ",") if key == 'characteristics' else value

    data['url'] = url
    return data

# JSON Writer
def _write_json(data_list, filename='scraped_products.json'):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data_list, file, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"JSON write error: {e}")

# Main Scraper
def main():
    proxy_manager = ProxyManager(rotation_minutes=2)
    scraped_products = []
    os.makedirs('captchas', exist_ok=True)

    try:
        with open('scraped_products.json', 'r', encoding='utf-8') as f:
            scraped_products = json.load(f)
    except:
        pass

    with open('product_links.json', 'r', encoding='utf-8') as f:
        urls_to_scrape = [item['link'] for item in json.load(f) if isinstance(item, dict) and 'link' in item]

    scraped_urls = {item['url'] for item in scraped_products}
    urls_to_scrape = [url for url in urls_to_scrape if url not in scraped_urls]

    for i, url in enumerate(urls_to_scrape):
        if terminate:
            break

        logger.info(f"Scraping ({i+1}/{len(urls_to_scrape)}): {url}")
        proxy = proxy_manager.get_proxy_for_selenium()
        options = _setup_chrome_options(proxy)
        browser = None
        captcha_solved = False
        page_loaded = False
        max_page_load_attempts = 3
        
        for attempt in range(1, max_page_load_attempts + 1):
            try:
                if browser:
                    browser.quit()
                    
                logger.info(f"Page load attempt {attempt}/{max_page_load_attempts}")
                browser = uc.Chrome(options=options)
                wait = WebDriverWait(browser, 15)
                browser.get(url)
                
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                page_loaded = True
                
                # Try to solve CAPTCHA (if present)
                captcha_solved = _solve_captcha(browser, wait, max_attempts=5)
                if not captcha_solved:
                    logger.warning(f"Failed to solve CAPTCHA on attempt {attempt}, trying with a new session")
                    continue
                
                # Now try to find the product container
                product_container_found = False
                for selector in ['div#ppd', 'div#dp-container', 'div#centerCol']:
                    try:
                        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        product_container_found = True
                        break
                    except TimeoutException:
                        continue
                
                if not product_container_found:
                    logger.warning(f"Product container not found on attempt {attempt}")
                    continue
                    
                # Add some random scrolling to appear more human-like
                browser.execute_script(f"window.scrollTo(0, {random.randint(300, 700)});")
                time.sleep(random.uniform(1, 2))

                # Extract product data
                product_data = _extract_product_data(browser, wait, element, url)
                if product_data.get('name') != 'N/A':
                    scraped_products.append(product_data)
                    _write_json(scraped_products)
                    logger.info(f"Successfully scraped: {product_data['name']}")
                    break  # Success - exit the retry loop
                else:
                    logger.warning(f"No product name found on attempt {attempt}")
                    
            except Exception as e:
                logger.error(f"Error on attempt {attempt} for {url}: {e}")
                if attempt == max_page_load_attempts:
                    logger.error(f"Failed to scrape {url} after {max_page_load_attempts} attempts")
            
        if browser:
            browser.quit()

        # Delay between products
        delay = random.uniform(5, 10)
        logger.info(f"Waiting {delay:.2f} seconds before next product...")
        time.sleep(delay)

if __name__ == "__main__":
    main()
