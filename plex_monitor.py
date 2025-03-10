#!/usr/bin/env python3
"""
Plex Server Monitor using API Token Authentication

This script checks if a Plex server is reachable and if random media is accessible
by authenticating via API Token instead of a username/password.
"""

import os
import requests
import random
import logging
import json
from datetime import datetime
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
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
        self.base_url = os.getenv("PLEX_BASE_URL")  # Direct URL to Plex server (e.g., https://192.168.1.100:32400)
        self.server_name = os.getenv("PLEX_SERVER_NAME")
        self.webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
        self.start_hour = int(os.getenv("START_HOUR", "8"))
        self.end_hour = int(os.getenv("END_HOUR", "2"))
        
        if not self.api_token:
            logging.error("Missing Plex API Token! Ensure PLEX_API_TOKEN is set in environment variables.")
            raise ValueError("Missing Plex API Token.")
            
        if not self.webhook_url:
            logging.warning("Discord webhook URL not configured. No notifications will be sent.")

    def connect_to_server(self):
        """
        Attempt to connect to the Plex server using multiple connection methods.
        """
        # Try connecting using direct base URL if provided
        if self.base_url:
            try:
                logging.info(f"Attempting direct connection to {self.base_url}")
                server = PlexServer(self.base_url, self.api_token, timeout=30)
                logging.info(f"Connected directly to Plex server")
                return server
            except Exception as e:
                logging.warning(f"Direct connection failed: {e}")
        
        # Try connecting through Plex.tv account
        try:
            logging.info("Attempting connection through Plex.tv account")
            account = MyPlexAccount(token=self.api_token)
            if self.server_name:
                server = account.resource(self.server_name).connect(ssl_verify=False, timeout=30)
            else:
                # If server name not provided, try connecting to the first available server
                servers = account.resources()
                if not servers:
                    logging.error("No servers found in your Plex account")
                    return None
                    
                server = servers[0].connect(ssl_verify=False, timeout=30)
                
            logging.info(f"Connected to Plex server: {server.friendlyName}")
            return server
        except Exception as e:
            logging.error(f"Failed to connect to Plex server: {e}")
            return None
            
    def get_random_media(self, server, media_type=None):
        """Get a random movie or TV show from the server."""
        if not server:
            return None
            
        try:
            # Get all libraries
            libraries = server.library.sections()
            
            if media_type:
                # If media type specified, filter for that type
                media_libraries = [lib for lib in libraries if lib.type == media_type]
            else:
                # Otherwise get both movie and show libraries
                media_libraries = [lib for lib in libraries if lib.type in ('movie', 'show')]
            
            if not media_libraries:
                logging.warning(f"No libraries found for type: {media_type}")
                return None
                
            # Pick a random library
            random_library = random.choice(media_libraries)
            
            # Get all items from the library (with a reasonable limit)
            all_items = random_library.all(maxresults=100)
            
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
            media_title = media_item.title
            
            # For TV shows, try to get a random episode
            if media_item.type == 'show':
                try:
                    seasons = media_item.seasons()
                    if seasons:
                        random_season = random.choice(seasons)
                        episodes = random_season.episodes()
                        if episodes:
                            random_episode = random.choice(episodes)
                            # Try to access episode title
                            episode_title = random_episode.title
                except Exception as e:
                    logging.warning(f"Failed to access episode: {e}")
                    return False
            
            # For movies, try to access additional info
            elif media_item.type == 'movie':
                media_item.duration  # Access duration
            
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
            data = {
                "content": message,
                "username": "Plex Monitor"
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
        
        # Connect to server
        server = self.connect_to_server()
        
        if not server:
            server_name = self.server_name or "Plex server"
            message = f"⚠️ **Plex Server Alert** ⚠️\n{server_name} is unreachable at {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
            logging.error(f"Plex server is unreachable")
            self.send_discord_notification(message)
            return
            
        # Check both a movie and a TV show
        check_results = []
        media_types = ['movie', 'show']
        
        for media_type in media_types:
            random_media = self.get_random_media(server, media_type)
            
            if not random_media:
                check_results.append({
                    'type': media_type,
                    'success': False,
                    'message': f"Failed to find {media_type} content"
                })
                continue
                
            media_access = self.check_media_access(random_media)
            
            # Try to get path if available
            try:
                media_path = random_media.locations[0] if hasattr(random_media, 'locations') and random_media.locations else "Path not available"
            except:
                media_path = "Path not accessible"
            
            if not media_access:
                check_results.append({
                    'type': media_type,
                    'success': False,
                    'title': random_media.title,
                    'path': media_path,
                    'message': f"Failed to access {media_type} '{random_media.title}'"
                })
            else:
                check_results.append({
                    'type': media_type,
                    'success': True,
                    'title': random_media.title,
                    'path': media_path
                })
                logging.info(f"Successfully accessed {media_type} '{random_media.title}'")
        
        # Determine overall status
        all_success = all(result['success'] for result in check_results)
        any_success = any(result['success'] for result in check_results)
        
        if not any_success:
            error_messages = "\n".join([f"- {result['message']}" for result in check_results if not result['success']])
            message = f"⚠️ **Plex Server Alert** ⚠️\nFailed to access any media at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n{error_messages}"
            logging.error("Failed to access any media")
            self.send_discord_notification(message)
        elif not all_success:
            # Partial success - some media types accessible, others not
            success_items = [f"✅ {result['type'].capitalize()}: '{result['title']}'" for result in check_results if result['success']]
            error_items = [f"❌ {result['type'].capitalize()}: {result['message']}" for result in check_results if not result['success']]
            status_message = "\n".join(success_items + error_items)
            
            message = f"⚠️ **Plex Server Partial Access** ⚠️\nSome media types are inaccessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n{status_message}"
            logging.warning("Partial media access")
            self.send_discord_notification(message)
        else:
            # All checks successful
            success_items = [f"✅ {result['type'].capitalize()}: '{result['title']}'" for result in check_results if result['success']]
            status_message = "\n".join(success_items)
            
            # Send success notifications on GitHub Actions since we're only running periodically
            message = f"✅ **Plex Server Working** ✅\nAll media types accessible at {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n{status_message}"
            logging.info(f"All checks successful:\n{status_message}")
            self.send_discord_notification(message)

# Run the script
if __name__ == "__main__":
    try:
        monitor = PlexMonitor()
        monitor.run_once()
    except Exception as e:
        logging.error(f"Fatal error in Plex Monitor: {e}")
        try:
            webhook_url = os.getenv("PLEX_DISCORD_WEBHOOK")
            if webhook_url:
                data = {
                    "content": f"⚠️ **Plex Monitor Error** ⚠️\nThe monitoring script encountered an error: {str(e)}",
                    "username": "Plex Monitor"
                }
                requests.post(
                    webhook_url,
                    data=json.dumps(data),
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
        except:
            pass
