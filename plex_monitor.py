#!/usr/bin/env python3
"""
Plex Server Monitor using API Token Authentication

This script checks if a Plex server is reachable and if random media is accessible
by authenticating via API Token instead of a username/password.
"""

import os
import requests
import random
import time
import logging
import json
from datetime import datetime, timedelta
from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import Unauthorized, NotFound, BadRequest
import urllib3

# Disable SSL warnings (for self-signed Plex certificates)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("plex_monitor.log"),
        logging.StreamHandler()
    ]
)

class PlexMonitor:
    def __init__(self):
        """
        Initialize the Plex monitor using environment variables.
        """
        self.api_token = os.getenv("PLEX_API_TOKEN")
        self.server_name = os.getenv("PLEX_SERVER_NAME")
        self.webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
        self.start_hour = int(os.getenv("START_HOUR", 8))
        self.end_hour = int(os.getenv("END_HOUR", 2))

        if not self.api_token:
            logging.error("Missing Plex API Token! Ensure PLEX_API_TOKEN is set in environment variables.")
            raise ValueError("Missing Plex API Token.")

        if not self.server_name:
            logging.error("Missing Plex Server Name! Ensure PLEX_SERVER_NAME is set in environment variables.")
            raise ValueError("Missing Plex Server Name.")

    def connect_to_server(self):
        """Attempt to connect to the Plex server using the API Token."""
        try:
            account = MyPlexAccount(token=self.api_token)
            server = account.resource(self.server_name).connect()
            logging.info(f"Connected to Plex server: {self.server_name}")
            return server

        except (requests.exceptions.ConnectionError, Unauthorized, BadRequest, NotFound) as e:
            logging.error(f"Failed to connect to Plex server: {e}")
            return None
            
    def get_random_media(self, server, media_type=None):
        """Get a random movie or TV show from the server."""
        if not server:
            return None
            
        try:
            libraries = server.library.sections()
            media_libraries = [lib for lib in libraries if lib.type in ('movie', 'show')]

            if not media_libraries:
                logging.warning(f"No libraries found for type: {media_type}")
                return None
                
            random_library = random.choice(media_libraries)
            all_items = random_library.all()

            if not all_items:
                logging.warning(f"No items found in library: {random_library.title}")
                return None
                
            return random.choice(all_items)
            
        except Exception as e:
            logging.error(f"Error getting random media: {e}")
            return None
            
    def check_media_access(self, media_item):
        """Check if media item details are accessible."""
        if not media_item:
            return False
            
        try:
            media_item.title  # Access title
            if media_item.type == "show":
                seasons = media_item.seasons()
                if seasons:
                    episodes = seasons[0].episodes()
                    if episodes:
                        episodes[0].title  # Access an episode title
                        return True

            return True
        except Exception as e:
            logging.error(f"Error checking media access: {e}")
            return False
    
    def send_discord_notification(self, message):
        """Send a notification via Discord webhook."""
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured")
            return
            
        try:
            data = {"content": message, "username": "Plex Monitor"}
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

    def run_once(self):
        """Run a single check (for scheduled tasks)."""
        current_time = datetime.now()
        logging.info(f"Running check at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if server is reachable
        server = self.connect_to_server()
        
        if not server:
            message = f"⚠️ **Plex Server Alert** ⚠️\nServer '{self.server_name}' is unreachable!"
            logging.error(f"Plex server '{self.server_name}' is unreachable")
            self.send_discord_notification(message)
            return
            
        # Check both a movie and a TV show
        check_results = []
        media_types = ["movie", "show"]
        
        for media_type in media_types:
            random_media = self.get_random_media(server, media_type)
            if not random_media:
                check_results.append({"type": media_type, "success": False})
                continue

            media_access = self.check_media_access(random_media)
            check_results.append({"type": media_type, "success": media_access, "title": random_media.title})

        # Determine overall status
        all_success = all(result["success"] for result in check_results)

        if not all_success:
            error_messages = "\n".join(
                [f"❌ {result['type'].capitalize()}: '{result.get('title', 'Unknown')}'"
                 for result in check_results if not result["success"]]
            )
            message = f"⚠️ **Plex Server Alert** ⚠️\nSome media failed to load:\n{error_messages}"
            logging.error("Some media access failed")
            self.send_discord_notification(message)
        else:
            logging.info("All checks successful")

# Run the script once
if __name__ == "__main__":
    monitor = PlexMonitor()
    monitor.run_once()
