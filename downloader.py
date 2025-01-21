from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re
import os
import time
import json
import logging
import urllib.parse

class UniversalDownloader:
    def __init__(self, download_dir="downloads"):
        self.download_dir = os.path.abspath(download_dir)
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.options = webdriver.ChromeOptions()
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True
        }
        self.options.add_experimental_option("prefs", prefs)
        
        self.driver = None

    def is_drive_link(self, url):
        """Check if a URL is a Google Drive link."""
        return bool(re.search(r'drive\.google\.com', url))

    def download_drive_file(self, drive_link):
        """Download a file from Google Drive in a new tab."""
        try:
            # Store current window handle
            main_window = self.driver.current_window_handle
            
            # Open new tab
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Load Drive link in new tab
            self.driver.get(drive_link)
            
            # Download process
            download_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "div.ndfHFb-c4YZDc-to915-LgbsSe[role='button'][aria-label='Download']"
                ))
            )
            
            time.sleep(1)
            download_button.click()
            success = self.wait_for_download()
            
            # Close the tab and switch back
            self.driver.close()
            self.driver.switch_to.window(main_window)
            
            return success
                
        except TimeoutException:
            logging.error(f"Timeout while downloading Drive file: {drive_link}")
            # Ensure we switch back to main window even if download fails
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(main_window)
            return False
        except Exception as e:
            logging.error(f"Error downloading Drive file: {str(e)}")
            # Ensure we switch back to main window even if there's an error
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(main_window)
            return False

    def download_custom_file(self, file_url):
        """Download a file from a custom URL with redirect handling."""
        try:
            # Store current window handle
            main_window = self.driver.current_window_handle
            
            # Open new tab
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Load URL in new tab
            self.driver.get(file_url)
            time.sleep(2)  # Wait for potential redirect
            
            current_url = self.driver.current_url
            success = False
            
            # Check if we've been redirected to a Drive link
            if self.is_drive_link(current_url):
                logging.info(f"Redirected to Drive link: {current_url}")
                # Close current tab and open a fresh one for Drive download
                self.driver.close()
                self.driver.switch_to.window(main_window)
                success = self.download_drive_file(current_url)
            else:
                # Regular download
                success = self.wait_for_download()
                # Close tab and switch back
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
            return success
                
        except Exception as e:
            logging.error(f"Error downloading custom file: {str(e)}")
            # Ensure we switch back to main window even if there's an error
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(main_window)
            return False

    def wait_for_download(self):
        """Wait for download to complete."""
        try:
            timeout = 60
            start_time = time.time()
            while time.time() - start_time < timeout:
                if any(fname.endswith('.crdownload') for fname in os.listdir(self.download_dir)):
                    time.sleep(1)
                    continue
                return True
            return False
        except Exception as e:
            logging.error(f"Error waiting for download: {str(e)}")
            return False

    def process_page(self, url, patterns):
        """Process a single webpage and download all matching files."""
        matched_links = self.extract_links(url, patterns)
        
        successful_downloads = 0
        failed_downloads = 0
        
        for link_info in matched_links:
            logging.info(f"Processing {link_info['type']} link: {link_info['url']}")
            
            success = False
            if link_info['type'] == 'drive':
                success = self.download_drive_file(link_info['url'])
            else:
                success = self.download_custom_file(link_info['url'])
                
            if success:
                successful_downloads += 1
            else:
                failed_downloads += 1
        
        logging.info(f"Page summary for {url}: {successful_downloads} successful, {failed_downloads} failed")
        return successful_downloads, failed_downloads

    def extract_links(self, url, patterns):
        """Extract links from webpage based on given patterns."""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            links = self.driver.find_elements(By.TAG_NAME, "a")
            matched_links = []
            
            for link in links:
                href = link.get_attribute('href')
                if not href:
                    continue
                    
                for pattern_info in patterns:
                    if re.search(pattern_info['pattern'], href):
                        matched_links.append({
                            'url': href,
                            'type': pattern_info['type']
                        })
                        break
            
            logging.info(f"Found {len(matched_links)} matching links on {url}")
            return matched_links
            
        except TimeoutException:
            logging.error(f"Timeout while loading page: {url}")
            return []
        except Exception as e:
            logging.error(f"Error extracting links from {url}: {str(e)}")
            return []

    def process_from_json(self, json_file, patterns):
        """Process multiple webpages from a JSON file."""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            if 'links' not in data:
                logging.error("JSON file must contain a 'links' array")
                return
            
            webpage_links = data['links']
            
            if not webpage_links:
                logging.error("No links found in JSON file")
                return
            
            self.start_browser()
            
            total_successful = 0
            total_failed = 0
            
            for url in webpage_links:
                logging.info(f"Processing webpage: {url}")
                successful, failed = self.process_page(url, patterns)
                total_successful += successful
                total_failed += failed
                
            logging.info(f"Final summary - Total downloads: {total_successful} successful, {total_failed} failed")
            
        except json.JSONDecodeError:
            logging.error("Invalid JSON file format")
        except FileNotFoundError:
            logging.error(f"JSON file not found: {json_file}")
        except Exception as e:
            logging.error(f"Error processing JSON file: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

    def start_browser(self):
        """Start the Chrome browser with configured options."""
        try:
            self.driver = webdriver.Chrome(options=self.options)
            logging.info("Browser started successfully")
        except Exception as e:
            logging.error(f"Failed to start browser: {str(e)}")
            raise

def main():
    patterns = [
        {'type': 'drive', 'pattern': r'drive\.google\.com'},
        {'type': 'custom', 'pattern': r'chiuchang\.org\.tw/modules/mydownloads/visit\.php\?lid=\d+'}
    ]
    
    json_file = "webpage_links.json"
    downloader = UniversalDownloader()
    downloader.process_from_json(json_file, patterns)

if __name__ == "__main__":
    main()