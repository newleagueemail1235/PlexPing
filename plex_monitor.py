#!/usr/bin/env python3
"""
Plex Server Monitor using MyPlex Account Authentication

This script checks if a Plex server is reachable and if random media is accessible
by authenticating through a Plex.tv account rather than direct server access.
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
        self.username = os.getenv("PLEX_USERNAME")
        self.password = os.getenv("PLEX_PASSWORD")
        self.server_name = os.getenv("PLEX_SERVER_NAME")
        self.webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
        self.start_hour = int(os.getenv("START_HOUR", 8))
        self.end_hour = int(os.getenv("END_HOUR", 2))
        self.last_status = True  # Track the last known status
        
    def connect_to_server(self):
        """Attempt to connect to the Plex server via Plex.tv account."""
        try:
            # First, authenticate with Plex.tv
            account = MyPlexAccount(self.username, self.password)
            
            # Then connect to the specified server
            server = account.resource(self.server_name).connect()
            
            return server
        except (requests.exceptions.ConnectionError, Unauthorized, BadRequest, NotFound) as e:
            logging.error(f"Failed to connect to Plex server: {e}")
            return None
            
    def get_random_media(self, server, media_type=None):
        """Get a random movie or TV show from the server."""
        if not server:
            return None
            
        try:
            # Get all libraries
            libraries = server.library.sections()
            
            # Filter for movie and show libraries based on requested type
            media_libraries = [lib for lib in libraries if lib.type in ('movie', 'show')]
            
            if not media_libraries:
                logging.warning(f"No libraries found for type: {media_type}")
                return None
                
            # Pick a random library of the requested type
            random_library = random.choice(media_libraries)
            
            # Get all items from the library
            all_items = random_library.all()
            
            if not all_items:
                logging.warning(f"No items found in library: {random_library.title}")
                return None
                
            # Pick a random item
            return random.choice(all_items)
            
        except Exception as e:
            logging.error(f"Error getting random media: {e}")
            return None
            
    def check_media_access(self, media_item):
        """Check if we can access the media item's details."""
        if not media_item:
            return False
            
        try:
            # Try to access media details
            media_item.title

            # For TV shows, try to get a random episode
            if media_item.type == "show":
                try:
                    seasons = media_item.seasons()
                    if seasons:
                        episodes = seasons[0].episodes()
                        if episodes:
                            episodes[0].title  # Access an episode title
                            return True
                except Exception as e:
                    logging.warning(f"Failed to access episode: {e}")
                    return False
            
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
            error_messages = "\n".join([f"❌ {result['type'].capitalize()}: '{result.get('title', 'Unknown')}'" for result in check_results if not result["success"]])
            message = f"⚠️ **Plex Server Alert** ⚠️\nSome media failed to load:\n{error_messages}"
            logging.error("Some media access failed")
            self.send_discord_notification(message)
        else:
            logging.info("All checks successful")

# Run the script once
if __name__ == "__main__":
    monitor = PlexMonitor()
    monitor.run_once()
