#!/usr/bin/env python3
"""
Advanced Cloudflare Bypass for Plex using Playwright

This script employs multiple advanced techniques to bypass Cloudflare protection:
1. Recaptcha solving
2. Browser fingerprint randomization
3. Interactive challenge handling
4. Human-like behavior simulation
"""

import os
import time
import logging
import json
import asyncio
import random
from datetime import datetime
import requests
from playwright.async_api import async_playwright, TimeoutError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("plex_browser_monitor.log"),
        logging.StreamHandler()
    ]
)

class AdvancedCloudflareBypass:
    def __init__(self):
        """
        Initialize the Cloudflare bypass monitor using environment variables.
        """
        self.plex_url = os.getenv("PLEX_URL", "https://plex.xe4yhe6.com/web/index.html#!")
        self.plex_username = os.getenv("PLEX_USERNAME")
        self.plex_password = os.getenv("PLEX_PASSWORD")
        self.webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
        self.start_hour = int(os.getenv("START_HOUR", "8"))
        self.end_hour = int(os.getenv("END_HOUR", "2"))
        self.screenshot_path = "plex_page.png"
        
        # Store cookies between runs
        self.cookies_file = "cloudflare_cookies.json"
        
        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        if not self.plex_url:
            logging.error("Missing Plex URL! Ensure PLEX_URL is set in environment variables.")
            raise ValueError("Missing Plex URL.")
            
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured. No notifications will be sent.")

    async def setup_browser(self):
        """Set up the Playwright browser with advanced anti-detection measures."""
        try:
            logging.info("Launching browser with advanced anti-detection...")
            
            # Choose a random user agent
            user_agent = random.choice(self.user_agents)
            logging.info(f"Using user agent: {user_agent}")
            
            # Launch Playwright
            playwright = await async_playwright().start()
            
            # Create browser with enhanced stealth options
            browser = await playwright.chromium.launch(
                headless=False,  # Try with headless=False first to see if it helps
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--window-position=0,0",
                    "--window-size=1920,1080",
                    "--ignore-certificate-errors",
                    "--ignore-certificate-errors-spki-list",
                    "--no-first-run",
                ]
            )
            
            # Create a context with specific options to evade detection
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme="no-preference",
                ignore_https_errors=True,
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not=A?Brand";v="99"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
            )
            
            # Load cookies if they exist
            if os.path.exists(self.cookies_file):
                try:
                    with open(self.cookies_file, "r") as f:
                        cookies = json.load(f)
                        await context.add_cookies(cookies)
                        logging.info(f"Loaded {len(cookies)} cookies from file")
                except Exception as e:
                    logging.error(f"Error loading cookies: {e}")
            
            # Create a page
            page = await context.new_page()
            
            # Execute advanced JS to evade bot detection
            await page.add_init_script("""
                // Override the navigator properties to bypass detection
                
                // Overwrite JavaScript properties that detect automation
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                
                // Add a console history
                window.console.history = [];
                window.console.log = function() { 
                    window.console.history.push({"type":"log", "message": Array.from(arguments)});
                    return window.console.__proto__.log.apply(this, arguments);
                };
                
                // Add screen properties that automated browsers might not have
                if (!window.screen.orientation) {
                    window.screen.orientation = {
                        angle: 0,
                        type: 'landscape-primary',
                        onchange: null
                    };
                }
                
                // Fake canvas fingerprinting
                const oldGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                    const imageData = oldGetImageData.call(this, x, y, w, h);
                    
                    // Add a very subtle random noise to the image data
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        if (Math.random() < 0.10) { // Only modify 10% of pixels
                            imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + (Math.random() * 2 - 1)));
                            imageData.data[i+1] = Math.max(0, Math.min(255, imageData.data[i+1] + (Math.random() * 2 - 1)));
                            imageData.data[i+2] = Math.max(0, Math.min(255, imageData.data[i+2] + (Math.random() * 2 - 1)));
                        }
                    }
                    
                    return imageData;
                };
                
                // Override fingerprinting APIs
                const originalGetParameter = AudioParam.prototype.getFrequencyResponse;
                if (originalGetParameter) {
                    AudioParam.prototype.getFrequencyResponse = function() {
                        const result = originalGetParameter.apply(this, arguments);
                        for(let i=0; i<result.length; i++) {
                            result[i] = result[i] + Math.random() * 0.0001;
                        }
                        return result;
                    }
                }
                
                // Add missing browser features that Cloudflare checks for
                if (!HTMLFormElement.prototype.requestSubmit) {
                    HTMLFormElement.prototype.requestSubmit = function() {
                        this.submit();
                        return null;
                    }
                }
            """)
            
            logging.info("Advanced browser setup completed")
            return {"playwright": playwright, "browser": browser, "context": context, "page": page}
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            return None

    async def perform_human_like_behavior(self, page):
        """Simulate human-like behavior to bypass bot detection."""
        logging.info("Performing human-like behavior to evade detection")
        
        try:
            # Random scrolling
            await page.evaluate("""
                () => {
                    const totalScrolls = 3 + Math.floor(Math.random() * 5);
                    const scrollInterval = 800 + Math.floor(Math.random() * 1200);
                    let scrollCount = 0;
                    
                    return new Promise((resolve) => {
                        const scroll = () => {
                            if (scrollCount >= totalScrolls) {
                                resolve();
                                return;
                            }
                            
                            const scrollAmount = 100 + Math.floor(Math.random() * 300);
                            window.scrollBy(0, scrollAmount);
                            scrollCount++;
                            
                            // Small variation in timing
                            setTimeout(scroll, scrollInterval + (Math.random() * 500 - 250));
                        };
                        
                        scroll();
                    });
                }
            """)
            
            # Random mouse movements (simulated)
            await page.evaluate("""
                () => {
                    const totalMoves = 5 + Math.floor(Math.random() * 10);
                    const moveInterval = 100 + Math.floor(Math.random() * 200);
                    let moveCount = 0;
                    
                    return new Promise((resolve) => {
                        const move = () => {
                            if (moveCount >= totalMoves) {
                                resolve();
                                return;
                            }
                            
                            const x = Math.floor(Math.random() * window.innerWidth);
                            const y = Math.floor(Math.random() * window.innerHeight);
                            
                            // Create a dummy element to trigger mouse events
                            const el = document.createElement('div');
                            el.style.position = 'absolute';
                            el.style.left = x + 'px';
                            el.style.top = y + 'px';
                            el.style.width = '1px';
                            el.style.height = '1px';
                            document.body.appendChild(el);
                            
                            // Dispatch mousemove event
                            el.dispatchEvent(new MouseEvent('mousemove', {
                                view: window,
                                bubbles: true,
                                cancelable: true,
                                clientX: x,
                                clientY: y
                            }));
                            
                            document.body.removeChild(el);
                            moveCount++;
                            
                            setTimeout(move, moveInterval + (Math.random() * 100 - 50));
                        };
                        
                        move();
                    });
                }
            """)
            
            logging.info("Completed human-like behavior simulation")
        except Exception as e:
            logging.error(f"Error during human-like behavior simulation: {e}")

    async def solve_cloudflare_challenge(self, page):
        """Try to detect and solve Cloudflare challenges."""
        logging.info("Attempting to solve Cloudflare challenge...")
        
        try:
            # Take screenshot of the challenge
            await page.screenshot(path="cloudflare_challenge.png", full_page=True)
            
            # Check for different types of Cloudflare challenges
            cloudflare_detected = await page.evaluate("""() => {
                const pageText = document.body.innerText.toLowerCase();
                const title = document.title.toLowerCase();
                
                const cloudflarePatterns = [
                    'cloudflare', 
                    'checking your browser',
                    'browser check',
                    'browser is being checked',
                    'security check',
                    'ddos protection',
                    'please wait',
                    'your IP',
                    'captcha',
                    'challenge',
                    'before you continue',
                    'page has been rate limited'
                ];
                
                return {
                    isCloudflare: cloudflarePatterns.some(pattern => 
                        pageText.includes(pattern) || title.includes(pattern)
                    ),
                    text: pageText.slice(0, 500),
                    title: title
                };
            }""")
            
            if cloudflareDetected['isCloudflare']:
                logging.info(f"Cloudflare detected: {cloudflareDetected['title']}")
                logging.info(f"Page text: {cloudflareDetected['text']}")
                
                # Wait longer for automatic challenge solving
                logging.info("Waiting for Cloudflare to process automatic challenge...")
                await page.wait_for_timeout(12000)  # Wait 12 seconds
                
                # Check for "I am human" checkbox or button (common in Cloudflare challenges)
                for selector in [
                    'input[type="checkbox"]', 
                    'button:has-text("I am human")',
                    'button:has-text("Verify")',
                    'button:has-text("Continue")',
                    'iframe[src*="challenges"]'
                ]:
                    try:
                        element = await page.wait_for_selector(selector, timeout=1000)
                        if element:
                            logging.info(f"Found interactive element: {selector}")
                            await element.click()
                            logging.info("Clicked on challenge element")
                            await page.wait_for_timeout(10000)  # Wait after clicking
                    except Exception:
                        pass
                
                # Perform human-like behavior
                await self.perform_human_like_behavior(page)
                
                # Final wait for challenge to complete
                logging.info("Final wait for challenge processing...")
                await page.wait_for_timeout(5000)
                
                # Check if we've passed the challenge
                still_cloudflare = await page.evaluate("""() => {
                    const pageText = document.body.innerText.toLowerCase();
                    const title = document.title.toLowerCase();
                    
                    return pageText.includes('cloudflare') || 
                           pageText.includes('checking your browser') ||
                           title.includes('cloudflare') ||
                           title.includes('attention');
                }""")
                
                if still_cloudflare:
                    logging.warning("Still on Cloudflare challenge after attempted solve")
                    return False
                else:
                    logging.info("Successfully passed Cloudflare challenge!")
                    
                    # Save cookies for future use
                    cookies = await page.context.cookies()
                    with open(self.cookies_file, "w") as f:
                        json.dump(cookies, f)
                    logging.info(f"Saved {len(cookies)} cookies to file")
                    
                    return True
            else:
                logging.info("No Cloudflare challenge detected")
                return True
                
        except Exception as e:
            logging.error(f"Error while attempting to solve Cloudflare challenge: {e}")
            return False

    async def access_plex_site(self, page):
        """Attempt to access the Plex site with Cloudflare bypass techniques."""
        try:
            logging.info(f"Navigating to Plex URL: {self.plex_url}")
            
            # Set generous timeout
            page.set_default_timeout(90000)  # 90 seconds
            
            # First try to navigate to the domain root to establish cookies
            domain_root = self.plex_url.split("/web")[0]
            logging.info(f"First visiting domain root: {domain_root}")
            
            try:
                await page.goto(domain_root, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(5000)  # Wait 5 seconds
            except Exception as e:
                logging.warning(f"Initial domain visit resulted in: {e}")
            
            # Now navigate to the actual Plex URL
            try:
                response = await page.goto(self.plex_url, wait_until="domcontentloaded", timeout=60000)
                status = response.status if response else "No response"
                logging.info(f"Initial page loaded with status: {status}")
            except TimeoutError:
                logging.warning("Page load timed out, but continuing to check for Cloudflare")
            except Exception as e:
                logging.error(f"Error during navigation: {e}")
            
            # Take screenshot for debugging
            await page.screenshot(path=self.screenshot_path, full_page=True)
            
            # Try to solve any Cloudflare challenges
            cloudflare_passed = await self.solve_cloudflare_challenge(page)
            if not cloudflare_passed:
                return False, "Blocked by Cloudflare protection"
            
            # Wait for the page to stabilize
            await page.wait_for_timeout(5000)
            
            # Take another screenshot after challenge handling
            await page.screenshot(path="after_cloudflare.png", full_page=True)
            
            # Check if we successfully reached Plex
            plex_detected = await page.evaluate("""() => {
                const pageText = document.body.innerText.toLowerCase();
                const pageHtml = document.documentElement.outerHTML.toLowerCase();
                const title = document.title.toLowerCase();
                
                // Check for Plex-specific elements
                const hasPlexInTitle = title.includes('plex');
                const hasPlexInContent = pageText.includes('plex');
                const hasPlexInHtml = pageHtml.includes('plex');
                
                // Look for specific elements that indicate Plex
                const selectors = [
                    '.page-container',
                    '.login-container',
                    '.auth-form',
                    'img[src*="plex"]',
                    '.auth-container',
                    'button:contains("Sign In")',
                    'div[class*="plex"]'
                ];
                
                const foundElements = [];
                selectors.forEach(selector => {
                    try {
                        if (document.querySelector(selector)) {
                            foundElements.push(selector);
                        }
                    } catch(e) {}
                });
                
                return {
                    hasPlexInTitle,
                    hasPlexInContent,
                    hasPlexInHtml,
                    foundElements,
                    title,
                    bodyText: pageText.slice(0, 500)
                };
            }""")
            
            logging.info(f"Plex detection result: {plex_detected}")
            
            if (plex_detected['hasPlexInTitle'] || 
                plex_detected['hasPlexInContent'] || 
                plex_detected['hasPlexInHtml'] ||
                plex_detected['foundElements'].length > 0):
                return True, "Plex web interface is accessible"
            else:
                return False, "Could not detect Plex interface elements"
                
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
        """Run a single check with Cloudflare bypass attempt."""
        current_time = datetime.now()
        logging.info(f"Running check at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if within monitoring window
        if not self.is_within_time_window():
            logging.info(f"Outside monitoring window ({self.start_hour}:00 - {self.end_hour}:00). Skipping check.")
            return
        
        browser_setup = None
        
        try:
            # Set up the browser with advanced anti-detection
            browser_setup = await self.setup_browser()
            if not browser_setup:
                message = f"⚠️ **Plex Browser Alert** ⚠️\nFailed to initialize browser at {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                logging.error("Failed to initialize browser")
                self.send_discord_notification(message)
                return
            
            # Try to access Plex with Cloudflare bypass
            success, message = await self.access_plex_site(browser_setup["page"])
            
            if success:
                notification = f"✅ **Plex Web Interface OK** ✅\nPlex is accessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nStatus: {message}"
                logging.info(f"Plex check successful: {message}")
                self.send_discord_notification(notification, "after_cloudflare.png")
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
        monitor = AdvancedCloudflareBypass()
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
