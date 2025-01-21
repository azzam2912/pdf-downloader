from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

def setup_chrome_driver():
    # Set up Chrome options
    chrome_options = webdriver.ChromeOptions()
    
    # Set download directory to current working directory
    prefs = {
        "download.default_directory": os.getcwd(),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    return webdriver.Chrome(options=chrome_options)

def download_file(driver, download_button):
    # Click download button
    download_button.click()
    time.sleep(2)  # Wait for redirect
    
    # Look for the "Download File" link on redirect page
    try:
        download_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "demo"))
        )
        download_link.click()
        time.sleep(5)  # Wait for download to start
    except Exception as e:
        print(f"Error finding download link: {e}")
        return False
    
    return True

def main():
    driver = setup_chrome_driver()
    
    try:
        # Go to main page
        driver.get("https://www.konsep-matematika.com/2021/12/download-kumpulan-soal-ksn-matematika-sd.html")
        
        # Find all download buttons (forms with submit buttons)
        download_buttons = driver.find_elements(By.CSS_SELECTOR, "form input[type='submit'][value='download soal']")
        
        print(f"Found {len(download_buttons)} download buttons")
        
        # Download each file
        for i, button in enumerate(download_buttons, 1):
            print(f"\nProcessing download {i}/{len(download_buttons)}")
            
            # Scroll button into view
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(1)
            
            if download_file(driver, button):
                print(f"Download {i} initiated successfully")
            else:
                print(f"Download {i} failed")
            
            # Go back to main page
            driver.back()
            time.sleep(2)
            
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Close browser
        driver.quit()

if __name__ == "__main__":
    main()
