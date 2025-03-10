#!/usr/bin/env python3
"""
Plex Browser Monitor using Selenium

This script uses standard Selenium to simulate a browser
and attempt to load and play media from Plex.
"""

import os
import time
import logging
import json
import random
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("plex_browser_monitor.log"),
        logging.StreamHandler()
    ]
)

class PlexBrowserMonitor:
    def __init__(self):
        """
        Initialize the Plex browser monitor using environment variables.
        """
        self.plex_url = os.getenv("PLEX_URL")
        self.plex_username = os.getenv("PLEX_USERNAME")
        self.plex_password = os.getenv("PLEX_PASSWORD")
        self.webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
        self.start_hour = int(os.getenv("START_HOUR", "8"))
        self.end_hour = int(os.getenv("END_HOUR", "2"))
        
        if not self.plex_url:
            logging.error("Missing Plex URL! Ensure PLEX_URL is set in environment variables.")
            raise ValueError("Missing Plex URL.")
            
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured. No notifications will be sent.")

    def setup_browser(self):
        """Set up the Chrome browser."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Add additional fingerprinting evasion for Cloudflare
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Use specific User-Agent that mimics a real browser
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
            
            # Create the browser instance
            browser = webdriver.Chrome(options=chrome_options)
            browser.set_page_load_timeout(60)
            
            # Set additional properties to avoid detection
            browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return browser
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            return None

    def check_plex_availability(self, browser):
        """Check if Plex is available and responsive."""
        try:
            # Navigate to Plex
            browser.get(self.plex_url)
            logging.info("Loaded Plex page")
            
            # Wait for initial page load
            time.sleep(5)
            
            # Take screenshot for debugging
            browser.save_screenshot("plex_page.png")
            logging.info("Saved screenshot of Plex page")
            
            # Check for common Plex page elements
            try:
                # Look for elements that would indicate the page loaded
                elements_to_check = [
                    "//div[contains(@class, 'page-container')]",
                    "//div[contains(@class, 'login-container')]",
                    "//div[contains(@class, 'auth-form')]",
                    "//img[contains(@src, 'plex')]",
                    "//div[contains(@class, 'auth-container')]",
                    "//button[contains(text(), 'Sign In')]"
                ]
                
                found_elements = []
                for xpath in elements_to_check:
                    try:
                        element = browser.find_element(By.XPATH, xpath)
                        found_elements.append(xpath)
                    except NoSuchElementException:
                        continue
                
                if found_elements:
                    logging.info(f"Found Plex elements: {', '.join(found_elements)}")
                    return True, "Plex web interface is accessible"
                else:
                    # Check page title and content
                    page_title = browser.title
                    page_source = browser.page_source[:500]  # Get first 500 chars for logging
                    logging.info(f"Page title: {page_title}")
                    logging.info(f"Page source sample: {page_source}")
                    
                    # Check if it contains Plex-related content
                    if "plex" in page_source.lower() or "plex" in page_title.lower():
                        logging.info("Page content appears to be related to Plex")
                        return True, "Plex web interface is accessible (detected in content)"
                    else:
                        logging.warning("Page doesn't contain expected Plex elements")
                        return False, "Couldn't find any Plex-related elements on the page"
                
            except Exception as e:
                logging.error(f"Error checking page elements: {e}")
                return False, f"Error checking page elements: {str(e)}"
                
        except Exception as e:
            logging.error(f"Error accessing Plex: {e}")
            return False, f"Error: {str(e)}"
    
    def send_discord_notification(self, message, screenshot=None):
        """Send a notification via Discord webhook."""
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured")
            return
            
        try:
            data = {
                "content": message,
                "username": "Plex Browser Monitor"
            }
            
            if screenshot and os.path.exists(screenshot):
                files = {
                    'file': (screenshot, open(screenshot, 'rb'), 'image/png')
                }
                # For files, we need to send without the json content-type
                response = requests.post(
                    self.webhook_url,
                    data={"content": message, "username": "Plex Browser Monitor"},
                    files=files,
                    timeout=30
                )
            else:
                response = requests.post(
                    self.webhook_url,
                    data=json.dumps(data),
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            
            if response.status_code == 204:
                logging.info("Discord notification sent successfully")
            else:
                logging.error(f"Failed to send Discord notification: {response.status_code} - {response.text}")
                
        except Exception as e:
            logging.error(f"Error sending Discord notification: {e}")
            
    def is_within_time_window(self):
        """Check if current time is within the specified monitoring window."""
        current_hour = datetime.now().hour
        
        # Handle wrap-around case (e.g., 8:00 to 2:00)
        if self.start_hour < self.end_hour:
            return self.start_hour <= current_hour < self.end_hour
        else:
            return current_hour >= self.start_hour or current_hour < self.end_hour

    def run_once(self):
        """Run a single check."""
        current_time = datetime.now()
        logging.info(f"Running check at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if within monitoring window
        if not self.is_within_time_window():
            logging.info(f"Outside monitoring window ({self.start_hour}:00 - {self.end_hour}:00). Skipping check.")
            return
            
        # Set up the browser
        browser = self.setup_browser()
        if not browser:
            message = f"⚠️ **Plex Browser Alert** ⚠️\nFailed to initialize browser at {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
            logging.error("Failed to initialize browser")
            self.send_discord_notification(message)
            return
            
        try:
            # Try to access Plex
            success, message = self.check_plex_availability(browser)
            
            if success:
                notification = f"✅ **Plex Web Interface OK** ✅\nPlex is accessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nStatus: {message}"
                logging.info(f"Plex check successful: {message}")
                self.send_discord_notification(notification, "plex_page.png")
            else:
                notification = f"⚠️ **Plex Web Interface Alert** ⚠️\nPlex might not be fully accessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nError: {message}"
                logging.error(f"Plex check failed: {message}")
                self.send_discord_notification(notification, "plex_page.png")
                
        except Exception as e:
            message = f"⚠️ **Plex Browser Error** ⚠️\nError during Plex check at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nError: {str(e)}"
            logging.error(f"Error during browser check: {e}")
            self.send_discord_notification(message)
        finally:
            # Always close the browser
            try:
                browser.quit()
            except:
                pass

# Run the script
if __name__ == "__main__":
    try:
        monitor = PlexBrowserMonitor()
        monitor.run_once()
    except Exception as e:
        logging.error(f"Fatal error in Plex Browser Monitor: {e}")
        try:
            webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
            if webhook_url:
                data = {
                    "content": f"⚠️ **Plex Monitor Error** ⚠️\nThe monitoring script encountered an error: {str(e)}",
                    "username": "Plex Browser Monitor"
                }
                requests.post(
                    webhook_url,
                    data=json.dumps(data),
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
        except:
            pass
