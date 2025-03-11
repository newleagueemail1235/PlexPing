#!/usr/bin/env python3
"""
Plex Browser Monitor using Playwright

This script uses Playwright to simulate a real browser
and attempt to load and access Plex through Cloudflare protection.
"""

import os
import time
import logging
import json
import asyncio
from datetime import datetime
import requests
from playwright.async_api import async_playwright

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
        self.plex_url = os.getenv("PLEX_URL", "https://plex.xe4yhe6.com/web/index.html#!")
        self.plex_username = os.getenv("PLEX_USERNAME")
        self.plex_password = os.getenv("PLEX_PASSWORD")
        self.webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
        self.start_hour = int(os.getenv("START_HOUR", "8"))
        self.end_hour = int(os.getenv("END_HOUR", "2"))
        self.screenshot_path = "plex_page.png"
        
        if not self.plex_url:
            logging.error("Missing Plex URL! Ensure PLEX_URL is set in environment variables.")
            raise ValueError("Missing Plex URL.")
            
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured. No notifications will be sent.")

    async def setup_browser(self):
        """Set up the Playwright browser."""
        try:
            logging.info("Launching browser...")
            
            # Launch Playwright
            playwright = await async_playwright().start()
            
            # Create browser with stealth options
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                    "--disable-web-security",
                ]
            )
            
            # Create a context with specific options to evade detection
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme="no-preference",
                ignore_https_errors=True,
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not=A?Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                }
            )
            
            # Create a page
            page = await context.new_page()
            
            # Execute JS to evade bot detection
            await page.add_init_script("""
                // Override the navigator properties that are used to detect headless browsers
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                
                // Override plugins
                if (navigator.plugins) {
                    Object.defineProperty(navigator, 'plugins', { 
                        get: () => [1, 2, 3, 4, 5].map(() => ({
                            name: 'Plugin ' + Math.random().toString(),
                            description: 'Plugin description',
                            filename: 'plugin' + Math.random().toString() + '.dll'
                        }))
                    });
                }
                
                // Override languages
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                
                // Add hardware properties to make fingerprinting harder
                Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
                
                // Override permissions API
                if (navigator.permissions) {
                    navigator.permissions.query = (parameters) => {
                        return Promise.resolve({ state: 'granted' });
                    };
                }
                
                // Modify the timing API to make it less detectable
                const originalGetTime = Date.prototype.getTime;
                Date.prototype.getTime = function() {
                    const time = originalGetTime.call(this);
                    return time + Math.random() * 100;
                };
            """)
            
            logging.info("Browser setup completed")
            return {"playwright": playwright, "browser": browser, "context": context, "page": page}
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            return None

    async def check_plex_availability(self, page):
        """Check if Plex is available and responsive."""
        try:
            logging.info(f"Navigating to Plex URL: {self.plex_url}")
            
            # Set timeout
            page.set_default_timeout(60000)  # 60 seconds
            
            # Navigate to the Plex URL
            response = await page.goto(self.plex_url, wait_until="networkidle")
            
            # Check response status
            if not response:
                logging.warn("No response received from page navigation")
                return False, "No response received from server"
            
            status = response.status
            logging.info(f"Initial page loaded with status: {status}")
            
            # Take screenshot for debugging
            await page.screenshot(path=self.screenshot_path, full_page=True)
            logging.info(f"Saved screenshot to {self.screenshot_path}")
            
            # Wait for any potential Cloudflare challenges
            logging.info("Waiting for any Cloudflare challenges...")
            await page.wait_for_timeout(5000)
            
            # Check for Cloudflare challenges
            cloudflare_detected = await page.evaluate("""() => {
                return document.title.includes('Cloudflare') || 
                       document.body.innerText.includes('Checking your browser') ||
                       document.body.innerText.includes('security check') ||
                       document.body.innerText.includes('DDoS protection');
            }""")
            
            if cloudflare_detected:
                logging.info("Cloudflare challenge detected, waiting for it to complete...")
                # Wait longer for the challenge to complete
                await page.wait_for_timeout(10000)
                
                # Take another screenshot after waiting
                await page.screenshot(path="cloudflare_challenge.png", full_page=True)
                
                # Check if we're still on Cloudflare
                still_on_cloudflare = await page.evaluate("""() => {
                    return document.title.includes('Cloudflare') || 
                           document.body.innerText.includes('Checking your browser');
                }""")
                
                if still_on_cloudflare:
                    logging.warn("Still on Cloudflare challenge after waiting")
                    return False, "Blocked by Cloudflare protection"
            
            # Check for common Plex page elements
            plex_elements_found = await page.evaluate("""() => {
                // List of selectors that would indicate we're on a Plex page
                const selectors = [
                    '.page-container',
                    '.login-container',
                    '.auth-form',
                    'img[src*="plex"]',
                    '.auth-container',
                    'button:contains("Sign In")',
                    'div[class*="plex"]',
                    // Add more Plex-specific selectors as needed
                ];
                
                const foundElements = [];
                selectors.forEach(selector => {
                    try {
                        if (document.querySelector(selector)) {
                            foundElements.push(selector);
                        }
                    } catch (e) {
                        // Some selectors might be invalid, ignore errors
                    }
                });
                
                // Also check if the page title or content contains 'plex'
                const isPlexInTitle = document.title.toLowerCase().includes('plex');
                const isPlexInContent = document.body.innerText.toLowerCase().includes('plex');
                
                return {
                    foundElements,
                    isPlexInTitle,
                    isPlexInContent
                };
            }""")
            
            # Take final screenshot for verification
            await page.screenshot(path=self.screenshot_path, full_page=True)
            
            if (plex_elements_found['foundElements'] or 
                plex_elements_found['isPlexInTitle'] or 
                plex_elements_found['isPlexInContent']):
                logging.info(f"Found Plex elements: {plex_elements_found}")
                return True, "Plex web interface is accessible"
            else:
                logging.warn("No Plex-related elements found on the page")
                return False, "Could not find any Plex-related elements on the page"
                
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

    async def run_once(self):
        """Run a single check."""
        current_time = datetime.now()
        logging.info(f"Running check at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if within monitoring window
        if not self.is_within_time_window():
            logging.info(f"Outside monitoring window ({self.start_hour}:00 - {self.end_hour}:00). Skipping check.")
            return
        
        browser_setup = None
        
        try:
            # Set up the browser
            browser_setup = await self.setup_browser()
            if not browser_setup:
                message = f"⚠️ **Plex Browser Alert** ⚠️\nFailed to initialize browser at {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                logging.error("Failed to initialize browser")
                self.send_discord_notification(message)
                return
            
            # Try to access Plex
            success, message = await self.check_plex_availability(browser_setup["page"])
            
            if success:
                notification = f"✅ **Plex Web Interface OK** ✅\nPlex is accessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nStatus: {message}"
                logging.info(f"Plex check successful: {message}")
                self.send_discord_notification(notification, self.screenshot_path)
            else:
                notification = f"⚠️ **Plex Web Interface Alert** ⚠️\nPlex might not be fully accessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nError: {message}"
                logging.error(f"Plex check failed: {message}")
                self.send_discord_notification(notification, self.screenshot_path)
                
        except Exception as e:
            message = f"⚠️ **Plex Browser Error** ⚠️\nError during Plex check at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nError: {str(e)}"
            logging.error(f"Error during browser check: {e}")
            self.send_discord_notification(message)
        finally:
            # Always close the browser
            if browser_setup:
                try:
                    await browser_setup["browser"].close()
                    await browser_setup["playwright"].stop()
                    logging.info("Browser closed successfully")
                except Exception as e:
                    logging.error(f"Error closing browser: {e}")

# Run the script
async def main():
    try:
        monitor = PlexBrowserMonitor()
        await monitor.run_once()
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

if __name__ == "__main__":
    asyncio.run(main())
