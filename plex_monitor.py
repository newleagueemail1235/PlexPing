#!/usr/bin/env python3
"""
Plex Full Browser Monitor

This script uses undetected-chromedriver to fully simulate a browser
and attempt to load and play media from Plex, bypassing Cloudflare protection.
"""

import os
import time
import logging
import json
import random
import requests
from datetime import datetime
import undetected_chromedriver as uc
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
        """Set up the undetected Chrome browser."""
        try:
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--remote-debugging-port=9222")
            
            # Add additional fingerprinting evasion
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Create the browser instance
            browser = uc.Chrome(options=options)
            browser.set_page_load_timeout(60)
            
            # Set additional properties to avoid detection
            browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return browser
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            return None

    def login_to_plex(self, browser):
        """Log in to Plex with provided credentials."""
        try:
            # Navigate to Plex sign-in page
            browser.get(self.plex_url)
            logging.info("Loaded Plex page")
            
            # Wait for initial page load
            time.sleep(5)
            
            # Check if we're already at the main Plex interface
            if self.is_plex_interface_loaded(browser):
                logging.info("Already logged in to Plex")
                return True
            
            # Look for a sign-in button (might be in different places depending on the Plex version)
            try:
                # Wait for a sign-in button to appear
                wait = WebDriverWait(browser, 20)
                signin_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign In') or contains(@class, 'sign-in')]"))
                )
                signin_button.click()
                logging.info("Clicked sign-in button")
                time.sleep(3)
            except TimeoutException:
                # If we can't find a sign-in button, we might already be on a login page
                # or the login flow might be different
                logging.info("No sign-in button found, checking if we're on the login page")
            
            # Check if we need to enter email first
            try:
                email_field = browser.find_element(By.ID, "email" or "username" or "login-username")
                email_field.clear()
                email_field.send_keys(self.plex_username)
                logging.info("Entered username/email")
                
                # Look for next/continue button
                try:
                    next_button = browser.find_element(By.XPATH, "//button[contains(text(), 'Next') or contains(text(), 'Continue')]")
                    next_button.click()
                    logging.info("Clicked Next/Continue button")
                    time.sleep(3)
                except NoSuchElementException:
                    logging.info("No Next/Continue button found, continuing with login flow")
            except NoSuchElementException:
                logging.info("No email/username field found, might be a different login flow")
            
            # Enter password
            try:
                password_field = browser.find_element(By.ID, "password" or "login-password")
                password_field.clear()
                password_field.send_keys(self.plex_password)
                logging.info("Entered password")
                
                # Click sign in
                signin_button = browser.find_element(By.XPATH, "//button[contains(text(), 'Sign In') or contains(@type, 'submit')]")
                signin_button.click()
                logging.info("Clicked Sign In button")
            except NoSuchElementException:
                logging.error("Password field not found")
                return False
            
            # Wait for the main interface to load
            time.sleep(10)
            
            # Check if login was successful
            return self.is_plex_interface_loaded(browser)
            
        except Exception as e:
            logging.error(f"Error during login: {e}")
            return False
    
    def is_plex_interface_loaded(self, browser):
        """Check if the main Plex interface is loaded."""
        try:
            # Try to find elements that would indicate we're on the Plex interface
            # This could be libraries, the sidebar, or other Plex-specific elements
            elements_to_check = [
                "//div[contains(@class, 'sidebar')]",
                "//div[contains(@class, 'hub-scroll-list')]",
                "//button[contains(@class, 'user-menu-button')]",
                "//a[contains(@title, 'Home') or contains(@title, 'Library')]"
            ]
            
            for xpath in elements_to_check:
                try:
                    browser.find_element(By.XPATH, xpath)
                    return True
                except NoSuchElementException:
                    continue
            
            return False
        except Exception as e:
            logging.error(f"Error checking Plex interface: {e}")
            return False
    
    def attempt_to_play_media(self, browser):
        """Try to find and play a media item."""
        try:
            # Wait for content to load
            wait = WebDriverWait(browser, 30)
            
            # First, try to find a library section (Movies, TV Shows, etc.)
            library_elements = browser.find_elements(By.XPATH, "//a[contains(@class, 'server-library-item')]")
            
            if not library_elements:
                # Try alternative selectors for library items
                library_elements = browser.find_elements(By.XPATH, "//div[contains(@class, 'sidebar')]//a")
            
            if not library_elements:
                logging.error("No library elements found")
                return False, "No libraries found"
            
            # Filter for movie or TV libraries
            media_libraries = []
            for lib in library_elements:
                text = lib.text.lower()
                if "movie" in text or "tv" in text or "show" in text or "series" in text or "video" in text:
                    media_libraries.append(lib)
            
            if not media_libraries:
                # If we couldn't identify specific media libraries, just use all libraries
                media_libraries = library_elements
                
            # Click on a random library
            random_library = random.choice(media_libraries)
            random_library.click()
            logging.info(f"Clicked on library: {random_library.text}")
            time.sleep(5)
            
            # Look for media items
            media_items = browser.find_elements(By.XPATH, "//div[contains(@class, 'Card-face--main') or contains(@class, 'MetadataPosterCard')]")
            
            if not media_items:
                # Try alternative selectors for media items
                media_items = browser.find_elements(By.XPATH, "//div[contains(@class, 'PosterCard') or contains(@class, 'MetadataCard')]")
            
            if not media_items:
                logging.error("No media items found in the library")
                return False, "No media items found"
                
            # Click on a random media item
            random_media = random.choice(media_items)
            media_title = random_media.get_attribute("aria-label") or "Unknown title"
            random_media.click()
            logging.info(f"Clicked on media: {media_title}")
            time.sleep(5)
            
            # Check if media details loaded
            try:
                # Look for play button or other elements indicating the media details loaded
                play_button = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(@class, 'play-btn') or contains(@class, 'PlayButton')]")
                ))
                
                # Click the play button
                play_button.click()
                logging.info("Clicked play button")
                time.sleep(5)
                
                # Check if player is loaded
                player_element = browser.find_elements(By.XPATH, "//div[contains(@class, 'Player') or contains(@class, 'VideoPlayer')]")
                if player_element:
                    logging.info("Player loaded successfully")
                    # Let it play for a few seconds
                    time.sleep(10)
                    return True, f"Successfully played: {media_title}"
                else:
                    logging.warning("Play button clicked but player didn't load")
                    return False, "Player didn't load"
                    
            except TimeoutException:
                logging.error("Couldn't find play button")
                return False, "Play button not found"
            except Exception as e:
                logging.error(f"Error during play attempt: {e}")
                return False, f"Error during playback: {str(e)}"
                
        except Exception as e:
            logging.error(f"Error attempting to play media: {e}")
            return False, f"Error: {str(e)}"
    
    def send_discord_notification(self, message):
        """Send a notification via Discord webhook."""
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured")
            return
            
        try:
            data = {
                "content": message,
                "username": "Plex Browser Monitor"
            }
            
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
            login_success = self.login_to_plex(browser)
            
            if not login_success:
                message = f"⚠️ **Plex Browser Alert** ⚠️\nFailed to log in to Plex at {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                logging.error("Failed to log in to Plex")
                self.send_discord_notification(message)
                return
                
            # Try to play media
            play_success, play_message = self.attempt_to_play_media(browser)
            
            if play_success:
                message = f"✅ **Plex Media Playback OK** ✅\nSuccessfully accessed and played media at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n{play_message}"
                logging.info(f"Media playback successful: {play_message}")
                self.send_discord_notification(message)
            else:
                message = f"⚠️ **Plex Playback Alert** ⚠️\nFailed to play media at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nError: {play_message}"
                logging.error(f"Media playback failed: {play_message}")
                self.send_discord_notification(message)
                
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
