#!/usr/bin/env python3
"""
Plex Web Interface Monitor

This script checks if the Plex web interface is responding
by making HTTP requests and checking the response.
"""

import os
import requests
import logging
import json
from datetime import datetime
import random
import time
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("plex_web_monitor.log"),
        logging.StreamHandler()
    ]
)

class PlexWebMonitor:
    def __init__(self):
        """
        Initialize the Plex web interface monitor using environment variables.
        """
        self.plex_url = os.getenv("PLEX_URL")
        self.webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
        self.start_hour = int(os.getenv("START_HOUR", "8"))
        self.end_hour = int(os.getenv("END_HOUR", "2"))
        
        if not self.plex_url:
            logging.error("Missing Plex URL! Ensure PLEX_URL is set in environment variables.")
            raise ValueError("Missing Plex URL.")
            
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured. No notifications will be sent.")

    def check_web_interface(self):
        """
        Check if the Plex web interface is accessible.
        """
        try:
            # Try to access the Plex web interface
            logging.info(f"Checking Plex web interface at {self.plex_url}")
            
            # Create a session to handle cookies and redirects
            session = requests.Session()
            
            # Set a user agent to mimic a browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # First request to get initial cookies and redirects
            response = session.get(
                self.plex_url,
                headers=headers,
                timeout=30,
                verify=False,
                allow_redirects=True
            )
            
            # Check if the response indicates a working Plex interface
            if response.status_code == 200:
                # Look for indicators that this is actually Plex
                if "Plex" in response.text and ("<title>Plex</title>" in response.text or "plex.tv" in response.text):
                    logging.info("Plex web interface is accessible and working")
                    return True, "Plex web interface is accessible"
                else:
                    logging.warning("Got 200 response but content doesn't look like Plex")
                    return False, "Got response but content doesn't look like Plex"
            elif response.status_code == 401 or response.status_code == 302:
                # 401 or redirect might indicate login is required, which is still a good sign
                if "Unauthorized" in response.text or "plex.tv/sign-in" in response.text:
                    logging.info("Plex web interface requires login (normal behavior)")
                    return True, "Plex web interface requires login (normal behavior)"
                else:
                    logging.warning(f"Got {response.status_code} response but content doesn't look like Plex")
                    return False, f"Got {response.status_code} response but content doesn't look like Plex"
            else:
                logging.error(f"Plex web interface returned status code: {response.status_code}")
                return False, f"Plex web interface returned status code: {response.status_code}"
                
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error accessing Plex web interface: {e}")
            return False, f"Connection error: {str(e)}"
        except requests.exceptions.Timeout:
            logging.error("Timeout accessing Plex web interface")
            return False, "Connection timed out"
        except Exception as e:
            logging.error(f"Error checking Plex web interface: {e}")
            return False, f"Error: {str(e)}"
    
    def send_discord_notification(self, message):
        """Send a notification via Discord webhook."""
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured")
            return
            
        try:
            data = {
                "content": message,
                "username": "Plex Web Monitor"
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
            
        # Check Plex web interface
        success, message = self.check_web_interface()
        
        if success:
            # Web interface is accessible
            notification = f"✅ **Plex Web Interface OK** ✅\nPlex is accessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nStatus: {message}"
            self.send_discord_notification(notification)
        else:
            # Web interface is not accessible
            notification = f"⚠️ **Plex Web Interface Alert** ⚠️\nPlex is not accessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nError: {message}"
            self.send_discord_notification(notification)

# Run the script
if __name__ == "__main__":
    try:
        monitor = PlexWebMonitor()
        monitor.run_once()
    except Exception as e:
        logging.error(f"Fatal error in Plex Web Monitor: {e}")
        try:
            webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
            if webhook_url:
                data = {
                    "content": f"⚠️ **Plex Monitor Error** ⚠️\nThe monitoring script encountered an error: {str(e)}",
                    "username": "Plex Web Monitor"
                }
                requests.post(
                    webhook_url,
                    data=json.dumps(data),
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
        except:
            pass
