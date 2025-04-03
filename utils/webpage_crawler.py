import argparse
import os
from time import sleep
import trafilatura
import sys
import json
import pymupdf 
import subprocess
import tempfile
import os
import filetype

from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from trafilatura.settings import DEFAULT_CONFIG
from trafilatura.meta import reset_caches

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
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'got it')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]",
            
            # Links
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent')]",
            
            # Divs and spans that might be clickable
            "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')][@role='button']",
            "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')][@role='button']",
            "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')][@role='button']",
            
            # IDs and classes
            "//*[contains(@id, 'cookie') or contains(@class, 'cookie')]//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
            "//*[contains(@id, 'cookie') or contains(@class, 'cookie')]//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
            "//*[contains(@id, 'cookie') or contains(@class, 'cookie')]//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]",
            "//*[contains(@id, 'gdpr') or contains(@class, 'gdpr')]//button",
            "//*[contains(@id, 'consent') or contains(@class, 'consent')]//button",
            
            # Common cookie banner IDs
            "//*[@id='cookiebanner']//button",
            "//*[@id='cookie-banner']//button",
            "//*[@id='cookie-consent']//button",
            "//*[@id='cookie-notice']//button",
            "//*[@id='cookie-policy']//button",
            
            # Common non-English patterns (add more as needed)
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'akzeptieren')]",  # German
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accepter')]",  # French
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceptar')]",  # Spanish
        ]

        # Common button texts; extend this list as needed
        for pattern in cookie_patterns:
            try:
                cookie_button = WebDriverWait(self.driver, timeout).until(
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

    def get_page_with_selenium(self, url, timeout=10):
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
            for i in range(3):
                try:
                    page = trafilatura.fetch_url(url, config=DEFAULT_CONFIG)
                    assert page is not None
                    print("Fetched "+url, file=sys.stderr)
                    break
                except Exception as e:
                    print(f"Trafilatura failed for {url}: {i+1}/3", file=sys.stderr)
                    sleep(3)
        
        if page is None and method in ['auto', 'selenium']:
            page = self.get_page_with_selenium(url)
        return page

    def html2lines(self, page):        
        if page is None or len(page.strip()) == 0:
            return []
        try:
            text = trafilatura.extract(page, favor_recall=True, with_metadata=False)
            reset_caches()
            if text is None:
                return []
            return text.split("\n")
        except Exception as e:
            print(e)
            return []

    def extract_doc_content(self, url):
        """
        Downloads a PDF from the given URL and extracts its content using wget.
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".sav") as tmp_file:
                temp_path = tmp_file.name
            
            # Download using wget
            subprocess.run(['wget', '-O', temp_path, url], check=True, timeout=30)

            kind = filetype.guess(temp_path)
            ftype = kind.extension if kind.extension else "txt"
            print(f"Using Extension {ftype}")
            
            # Extract text
            reader = pymupdf.open(temp_path, filetype=ftype)
            text = ""
            for page in reader:
                text += page.get_text()
            
            return text.split("\n")
        except Exception as e:
            print(f"Error extracting PDF content from {url}: {e}", file=sys.stderr)
            return []
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def url2lines(self, url, method='auto'):
        l_url = url.lower()
        if l_url.endswith(('.pdf', '.txt', '.docx')):
            return self.extract_doc_content(url)
        page = self.get_page(url, method=method)
        return self.html2lines(page)