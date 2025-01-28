import argparse
import os
from time import sleep
import trafilatura
import sys
import json
import requests
import pymupdf 

from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from trafilatura.settings import DEFAULT_CONFIG

# Increase max file size to 50MB
DEFAULT_CONFIG['DEFAULT']['MAX_FILE_SIZE'] = "50000000"
DEFAULT_CONFIG['DEFAULT']['SLEEP_TIME'] = "5"

class WebpageProcessor:
    def __init__(self):
        self.driver = None
        
    def initialize_driver(self):
        if self.driver is not None:
            return
            
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.add_argument('--disable-animations')
        # chrome_options.add_argument('--disable-javascript')  # Disable JavaScript if not needed
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 2,  # Changed from 1 to 2 to disable images
            # "profile.managed_default_content_settings.javascript": 2,  # Disable JavaScript
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            # Prevent detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                            'AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/131.0.0.0 Safari/537.36'
            })
        except WebDriverException as e:
            print(f"Error initializing WebDriver: {e}", file=sys.stderr)
            self.driver = None

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def handle_cookie_popup(self, timeout=5):
        cookie_patterns = [
            # Buttons
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
            # Links
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
            # Divs that might be clickable
            "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')][@role='button']",
            # IDs and classes
            "//*[contains(@id, 'cookie') or contains(@class, 'cookie')]//button",
            # Common cookie banner IDs
            "//*[@id='cookiebanner']//button",
            "//*[@id='cookie-banner']//button",
        ]

        # Common button texts; extend this list as needed
        button_texts = ['Accept', 'I Agree', 'Agree', 'Consent', 'Allow All']
        # for pattern in button_texts:
        for pattern in cookie_patterns:
            try:
                cookie_button = WebDriverWait(self.driver, timeout).until(
                    # EC.element_to_be_clickable((By.XPATH, f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern.lower()}')]"))
                    EC.element_to_be_clickable((By.XPATH, pattern))
                )
                cookie_button.click()
                print(f"Clicked '{pattern}' button for cookie consent.", file=sys.stderr)
                return True
            except:
                continue
        # print("No cookie popup detected or unable to handle.", file=sys.stderr)
        return False


    # Add new function for scrolling
    def scroll_page(self, pause_time=0.5):
        """Scroll the page to load dynamic content."""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            attempts = 0
            max_attempts = 5  # Limit scroll attempts
            
            while attempts < max_attempts:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                sleep(pause_time)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break
                last_height = new_height
                attempts += 1
        except Exception as e:
            print(f"Scrolling error: {e}", file=sys.stderr)

    def get_page_with_selenium(self, url, timeout=5):
        if not self.driver:
            self.initialize_driver()
            print("Initialized driver")
            if not self.driver:
                return None
                
        try:
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            self.handle_cookie_popup(timeout=1)
            self.scroll_page()
            
            return self.driver.execute_script("return document.documentElement.outerHTML;")
            
        except Exception as e:
            print(f"Selenium failed for {url}: {e}", file=sys.stderr)
            # Reinitialize driver on failure
            self.cleanup()
            self.initialize_driver()
            return None

    def get_page(self, url, method='auto'):
        page = None
        
        if method in ['auto', 'trafilatura']:
            try:
                # page = trafilatura.fetch_url(url, config=DEFAULT_CONFIG)
                page = trafilatura.fetch_response(url, config=DEFAULT_CONFIG)
            except Exception as e:
                print(f"Trafilatura failed for {url}: {str(e)}", file=sys.stderr)
        
        if page is None and method in ['auto', 'selenium']:
            page = self.get_page_with_selenium(url)
        
        return page
    

    def html2lines(self, page):
        if not page: # or len(page.strip()) == 0
            print("No page found")
            return {}

        try:
            text = trafilatura.extract(page, 
                                # favor_recall=True, 
                                with_metadata=True,    
                                no_fallback=False,
                                deduplicate=True,
                                output_format="json"
                                )
            return json.loads(text)
        except Exception as e:
            print(e)
            return {}
        
    # def extract_doc_content(self, url):
    #     """
    #     Downloads a PDF from the given URL and extracts its content.
    #     """
    #     extension = url.split(".")[-1].lower()
    #     try:
    #         response = requests.get(url, timeout=60)
    #         response.raise_for_status()  # Raise an exception for bad status codes

    #         # with BytesIO(response.content) as pdf_file:
    #         pdf_data = BytesIO(response.content)
    #         reader = pymupdf.open(stream=pdf_data, filetype=extension)
    #         text = ""
    #         for page in reader:
    #             text += page.get_text()
    #         return {"text": text}
    #     except Exception as e:
    #         print(f"Error extracting PDF content from {url}: {e}", file=sys.stderr)
    #         return {}

    def extract_doc_content(self, url):
        """
        Downloads a PDF from the given URL and extracts its content using wget.
        """
        import subprocess
        import tempfile
        import os
        
        extension = url.split(".")[-1].lower()            
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp_file:
                temp_path = tmp_file.name
            
            # Download using wget
            subprocess.run(['wget', '-O', temp_path, url], check=True, timeout=60)
            
            # Extract text
            reader = pymupdf.open(temp_path, filetype="txt")
            text = ""
            for page in reader:
                text += page.get_text()
            
            return {"text": text}
        except subprocess.TimeoutExpired:
            print(f"Timeout while downloading {url}", file=sys.stderr)
            return {}
        except Exception as e:
            print(f"Error extracting PDF content from {url}: {e}", file=sys.stderr)
            return {}
        finally:
            # Ensure the temporary file is always deleted
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def url2lines(self, url, method='auto'):
        if url.endswith(('.pdf', '.txt', '.docx')):
            return self.extract_doc_content(url)
        page = self.get_page(url, method=method)
        return self.html2lines(page)
