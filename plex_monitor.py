#!/usr/bin/env python3
"""
Plex Server Monitor using MyPlex Account Authentication

This script checks if a Plex server is reachable and if random media is accessible
by authenticating through a Plex.tv account rather than direct server access.
"""

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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("plex_monitor.log"),
        logging.StreamHandler()
    ]
)

class PlexMonitor:
    def __init__(self, username, password, server_name, webhook_url, start_hour=8, end_hour=2):
        """
        Initialize the Plex monitor using Plex.tv account.
        
        Args:
            username (str): Your Plex.tv username or email
            password (str): Your Plex.tv password
            server_name (str): The name of your Plex server as it appears in your account
            webhook_url (str): Discord webhook URL for notifications
            start_hour (int): Hour to start checks (24-hour format)
            end_hour (int): Hour to end checks (24-hour format)
        """
        self.username = username
        self.password = password
        self.server_name = server_name
        self.webhook_url = webhook_url
        self.start_hour = start_hour
        self.end_hour = end_hour
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
            if media_type:
                media_libraries = [lib for lib in libraries if lib.type == media_type]
            else:
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
        """Check if we can access the media item's details and thumbnail."""
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
                            # Try to access episode details
                            episode_title = random_episode.title
                            return True
                except Exception as e:
                    logging.warning(f"Failed to access episode: {e}")
                    return False
            
            # For movies, try to access the media info
            elif media_item.type == 'movie':
                # Try to access media streams or duration
                media_item.duration
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
    
    def get_sleep_time(self):
        """Calculate random sleep time within the hour."""
        # Random minutes within the hour (0-59)
        return random.randint(1, 59) * 60
    
    def run_once(self):
        """Run a single check (for scheduled tasks)."""
        current_time = datetime.now()
        
        # Check if we're within the monitoring window
        if self.is_within_time_window():
            logging.info(f"Running check at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check if server is reachable
            server = self.connect_to_server()
            
            if not server:
                message = f"⚠️ **Plex Server Alert** ⚠️\nServer '{self.server_name}' is unreachable at {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                logging.error(f"Plex server '{self.server_name}' is unreachable")
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
                
                # Try to get path if available, but it might not be accessible through indirect connection
                try:
                    media_path = random_media.locations[0] if hasattr(random_media, 'locations') and random_media.locations else "Path not available"
                except:
                    media_path = "Path not accessible through indirect connection"
                
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
                success_items = [f"✅ {result['type'].capitalize()}: '{result['title']}'" for result in check_results]
                status_message = "\n".join(success_items)
                
                # Log success but don't send notification for routine successful checks
                logging.info(f"All checks successful:\n{status_message}")
        else:
            logging.info(f"Outside monitoring window at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
    def run(self):
        """Run the monitoring loop."""
        logging.info(f"Starting Plex monitor for server '{self.server_name}'")
        logging.info(f"Monitoring window: {self.start_hour}:00 to {self.end_hour}:00")
        logging.info(f"Checks will run randomly once per hour within the monitoring window")
        
        while True:
            current_time = datetime.now()
            
            # Check if we're within the monitoring window
            if self.is_within_time_window():
                # Run the check
                self.run_once()
                
                # Calculate time to the next hour
                next_hour = (current_time + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                seconds_to_next_hour = (next_hour - current_time).total_seconds()
                
                # Generate random time within the next hour
                random_seconds = self.get_sleep_time()
                
                # Sleep until the random time in the next hour
                sleep_seconds = seconds_to_next_hour + random_seconds
                next_check_time = (current_time + timedelta(seconds=sleep_seconds)).strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f"Next check scheduled for {next_check_time}")
                
                time.sleep(sleep_seconds)
            else:
                # We're outside the monitoring window, sleep until start hour
                current_time = datetime.now()
                
                # Calculate time to the next start hour
                if current_time.hour < self.start_hour:
                    # Start hour is later today
                    next_check = current_time.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
                else:
                    # Start hour is tomorrow
                    next_check = current_time.replace(hour=self.start_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
                
                # Add random minutes
                random_minutes = random.randint(0, 59)
                next_check = next_check.replace(minute=random_minutes)
                
                # Calculate seconds to sleep
                sleep_seconds = (next_check - current_time).total_seconds()
                
                logging.info(f"Outside monitoring window. Sleeping until {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(sleep_seconds)
