#!/usr/bin/env python3
"""
Trakt to Serializd Migration Script for Termux
===================================================================

This script migrates watched shows data from a Trakt account to a Serializd account.
Designed to work efficiently in Termux environments with proper error handling and rate limiting.

Usage:
    python trakt_to_serializd_migrator.py
"""

import requests
import json
import os
import time
import logging
import sys
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TraktAuthenticator:
    """Handles Trakt API authentication using device code flow"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.trakt.tv"
        self.access_token = None
        self.refresh_token = None

    def authenticate(self) -> Dict[str, Any]:
        """
        Performs OAuth device authentication for Trakt

        Returns:
            dict: Authentication data containing access and refresh tokens

        Raises:
            Exception: If authentication fails
        """
        try:
            # Step 1: Get device code
            device_response = requests.post(
                f"{self.base_url}/oauth/device/code",
                json={"client_id": self.client_id},
                headers={
                    "Content-Type": "application/json"
                }
            )

            if device_response.status_code != 200:
                raise Exception(f"Failed to get device code: {device_response.status_code}")

            device_data = device_response.json()

            print("\n" + "="*60)
            print("TRAKT AUTHENTICATION REQUIRED")
            print("="*60)
            print(f"1. Visit: {device_data['verification_url']}")
            print(f"2. Enter code: {device_data['user_code']}")
            print(f"3. You have {device_data['expires_in']} seconds to complete this")
            print("4. Press Enter after completing authorization...")
            input()

            # Step 2: Poll for access token
            expiry = int(time.time()) + device_data['expires_in']
            interval = device_data['interval']

            while int(time.time()) < expiry:
                time.sleep(interval)

                token_response = requests.post(
                    f"{self.base_url}/oauth/device/token",
                    json={
                        "code": device_data['device_code'],
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    },
                    headers={"Content-Type": "application/json"}
                )

                if token_response.status_code == 200:
                    auth_data = token_response.json()
                    self.access_token = auth_data['access_token']
                    self.refresh_token = auth_data['refresh_token']
                    logger.info("Trakt authentication successful!")
                    return auth_data
                elif token_response.status_code != 400:
                    raise Exception(f"Authentication error: {token_response.status_code}")

            raise Exception("Authentication timeout - please try again")

        except Exception as e:
            logger.error(f"Trakt authentication failed: {str(e)}")
            raise

class SerializdAuthenticator:
    """Handles Serializd API authentication using email/password"""

    def __init__(self):
        # CORRECTED: Use the actual Serializd API base URL
        self.base_url = "https://www.serializd.com/api"
        self.access_token = None
        self.session = requests.Session()

        # Set required headers as per serializd-py library
        self.session.headers.update({
            "Content-Type": "application/json",
            "Origin": "https://www.serializd.com",
            "Referer": "https://www.serializd.com",
            "X-Requested-With": "serializd_vercel"
        })

    def authenticate(self, email: str, password: str) -> str:
        """
        Authenticates with Serializd using email and password

        Args:
            email: Serializd account email
            password: Serializd account password

        Returns:
            str: Access token for API requests

        Raises:
            Exception: If authentication fails
        """
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={
                    "email": email,
                    "password": password
                }
            )

            if response.status_code != 200:
                raise Exception(f"Login failed: {response.status_code} - {response.text}")

            auth_data = response.json()
            self.access_token = auth_data.get('token')

            if not self.access_token:
                raise Exception("No access token received from Serializd")

            # Store the token in cookies as expected by Serializd API
            self.session.cookies.set(
                name='tvproject_credentials',
                value=self.access_token,
                domain='.serializd.com'
            )

            logger.info("Serializd authentication successful!")
            return self.access_token

        except Exception as e:
            logger.error(f"Serializd authentication failed: {str(e)}")
            raise

class TraktAPI:
    """Trakt API client for retrieving watched shows data"""

    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.trakt.tv"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": client_id,
            "Authorization": f"Bearer {access_token}"
        })

    def get_user_info(self) -> Dict[str, Any]:
        """
        Fetches user information for the authenticated user

        Returns:
            dict: User information

        Raises:
            Exception: If request fails
        """
        try:
            response = self.session.get(f"{self.base_url}/users/settings")

            if response.status_code != 200:
                raise Exception(f"Failed to get user info: {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise

    def get_watched_shows(self, username: str) -> List[Dict[str, Any]]:
        """
        Retrieves watched shows data for a user

        Args:
            username: Trakt username

        Returns:
            list: List of watched shows with episodes

        Raises:
            Exception: If request fails
        """
        try:
            # Use sync/watched/shows endpoint for better data
            response = self.session.get(f"{self.base_url}/sync/watched/shows")

            if response.status_code != 200:
                raise Exception(f"Failed to get watched shows: {response.status_code}")

            watched_data = response.json()
            logger.info(f"Retrieved {len(watched_data)} watched shows from Trakt")
            return watched_data

        except Exception as e:
            logger.error(f"Failed to get watched shows: {str(e)}")
            raise

class SerializdAPI:
    """Serializd API client for uploading watched episodes"""

    def __init__(self, session: requests.Session):
        # Use the authenticated session from SerializdAuthenticator
        self.session = session
        self.base_url = "https://www.serializd.com/api"

    def get_show_by_tmdb_id(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets show information from Serializd using TMDB ID

        Args:
            tmdb_id: TMDB ID of the show

        Returns:
            dict: Show information if found, None otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/show/{tmdb_id}")

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Show not found on Serializd: TMDB ID {tmdb_id}")
                return None

        except Exception as e:
            logger.warning(f"Failed to get show info for TMDB ID {tmdb_id}: {str(e)}")
            return None

    def get_season_info(self, show_id: int, season_number: int) -> Optional[Dict[str, Any]]:
        """
        Gets season information from Serializd

        Args:
            show_id: Serializd show ID (TMDB ID)
            season_number: Season number

        Returns:
            dict: Season information if found, None otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/show/{show_id}/season/{season_number}")

            if response.status_code == 200:
                season_data = response.json()
                if season_data.get('seasonId'):
                    return season_data
                else:
                    logger.warning(f"Empty season data for show {show_id} season {season_number}")
                    return None
            else:
                logger.warning(f"Season not found: show {show_id} season {season_number}")
                return None

        except Exception as e:
            logger.warning(f"Failed to get season info for show {show_id} season {season_number}: {str(e)}")
            return None

    def log_episodes(self, show_id: int, season_id: int, episode_numbers: List[int]) -> bool:
        """
        Logs watched episodes for a show on Serializd

        Args:
            show_id: TMDB show ID
            season_id: Serializd season ID
            episode_numbers: List of episode numbers to mark as watched

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            payload = {
                "episode_numbers": episode_numbers,
                "season_id": season_id,
                "show_id": show_id,
                "should_get_next_episode": False
            }

            response = self.session.post(
                f"{self.base_url}/episode_log/add",
                json=payload
            )

            if response.status_code in [200, 201]:
                logger.info(f"Successfully logged {len(episode_numbers)} episodes for show {show_id}")
                return True
            else:
                logger.warning(f"Failed to log episodes: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error logging episodes: {str(e)}")
            return False

    def log_seasons(self, show_id: int, season_ids: List[int]) -> bool:
        """
        Marks entire seasons as watched on Serializd

        Args:
            show_id: TMDB show ID
            season_ids: List of Serializd season IDs

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            payload = {
                "season_ids": season_ids,
                "show_id": show_id
            }

            response = self.session.post(
                f"{self.base_url}/watched_v2",
                json=payload
            )

            if response.status_code in [200, 201]:
                logger.info(f"Successfully logged {len(season_ids)} seasons as watched for show {show_id}")
                return True
            else:
                logger.warning(f"Failed to log seasons: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error logging seasons: {str(e)}")
            return False

class MigrationManager:
    """Main migration manager that coordinates the entire process"""

    def __init__(self):
        self.trakt_auth = None
        self.serializd_auth = None
        self.trakt_api = None
        self.serializd_api = None
        self.rate_limit_delay = 1.0  # Seconds between API calls

    def setup_authentication(self):
        """Sets up authentication for both Trakt and Serializd"""

        # Trakt setup
        print("\n" + "="*60)
        print("TRAKT SETUP")
        print("="*60)
        print("You need to create a Trakt API application first:")
        print("1. Visit: https://trakt.tv/oauth/applications/new")
        print("2. Create an application with redirect URI: urn:ietf:wg:oauth:2.0:oob")
        print("3. Copy your Client ID and Client Secret")
        print()

        trakt_client_id = input("Enter your Trakt Client ID: ").strip()
        trakt_client_secret = input("Enter your Trakt Client Secret: ").strip()

        if not trakt_client_id or not trakt_client_secret:
            raise ValueError("Trakt Client ID and Secret are required")

        # Authenticate with Trakt
        self.trakt_auth = TraktAuthenticator(trakt_client_id, trakt_client_secret)
        trakt_tokens = self.trakt_auth.authenticate()

        # Setup Trakt API client
        self.trakt_api = TraktAPI(trakt_client_id, trakt_tokens['access_token'])

        # Serializd setup
        print("\n" + "="*60)
        print("SERIALIZD SETUP")
        print("="*60)

        serializd_email = input("Enter your Serializd email: ").strip()
        serializd_password = input("Enter your Serializd password: ").strip()

        if not serializd_email or not serializd_password:
            raise ValueError("Serializd email and password are required")

        # Authenticate with Serializd
        self.serializd_auth = SerializdAuthenticator()
        serializd_token = self.serializd_auth.authenticate(serializd_email, serializd_password)

        # Setup Serializd API client using the authenticated session
        self.serializd_api = SerializdAPI(self.serializd_auth.session)

    def migrate_watched_shows(self):
        """Main migration function"""

        try:
            # Get user info
            user_info = self.trakt_api.get_user_info()
            username = user_info['user']['username']
            logger.info(f"Starting migration for user: {username}")

            # Get watched shows from Trakt
            watched_shows = self.trakt_api.get_watched_shows(username)

            successful_migrations = 0
            failed_migrations = 0

            # Process each show
            for show_data in watched_shows:
                try:
                    show_info = show_data['show']
                    show_title = show_info['title']
                    show_year = show_info.get('year')
                    tmdb_id = show_info['ids'].get('tmdb')

                    if not tmdb_id:
                        logger.warning(f"No TMDB ID for '{show_title}' - skipping")
                        failed_migrations += 1
                        continue

                    logger.info(f"Processing: {show_title} ({show_year}) - TMDB ID: {tmdb_id}")

                    # Get show info from Serializd using TMDB ID
                    serializd_show = self.serializd_api.get_show_by_tmdb_id(tmdb_id)

                    if not serializd_show:
                        logger.warning(f"Could not find '{show_title}' on Serializd - skipping")
                        failed_migrations += 1
                        continue

                    complete_seasons = []

                    # Process watched seasons
                    for season_data in show_data.get('seasons', []):
                        season_number = season_data['number']
                        watched_episodes = [ep['number'] for ep in season_data.get('episodes', [])]

                        if not watched_episodes:
                            continue

                        logger.info(f"Processing {show_title} S{season_number:02d} - {len(watched_episodes)} episodes")

                        # Get season info from Serializd
                        season_info = self.serializd_api.get_season_info(tmdb_id, season_number)

                        if not season_info:
                            logger.warning(f"Season {season_number} not found on Serializd for {show_title}")
                            continue

                        season_id = season_info.get('seasonId')
                        total_episodes = len(season_info.get('episodes', []))

                        # Check if all episodes in season are watched
                        if total_episodes > 0 and len(watched_episodes) >= total_episodes:
                            # Mark entire season as watched
                            complete_seasons.append(season_id)
                            logger.info(f"Marking complete season {season_number} as watched")
                        else:
                            # Mark individual episodes as watched
                            success = self.serializd_api.log_episodes(
                                tmdb_id, 
                                season_id, 
                                watched_episodes
                            )

                            if not success:
                                logger.warning(f"Failed to log episodes for {show_title} S{season_number}")

                        # Rate limiting
                        time.sleep(self.rate_limit_delay)

                    # Log complete seasons
                    if complete_seasons:
                        success = self.serializd_api.log_seasons(tmdb_id, complete_seasons)
                        if success:
                            logger.info(f"Successfully marked {len(complete_seasons)} complete seasons for {show_title}")

                    successful_migrations += 1
                    logger.info(f"Successfully migrated: {show_title}")

                except Exception as e:
                    logger.error(f"Error processing show '{show_title}': {str(e)}")
                    failed_migrations += 1

                # Rate limiting between shows
                time.sleep(self.rate_limit_delay)

            # Final report
            logger.info(f"Migration completed!")
            logger.info(f"Successful: {successful_migrations}")
            logger.info(f"Failed: {failed_migrations}")

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise

    def run(self):
        """Main entry point for the migration process"""

        try:
            print("Trakt to Serializd Migration Tool (FIXED VERSION)")
            print("="*60)
            print("This tool will migrate your watched shows from Trakt to Serializd.")
            print("Make sure you have active accounts on both platforms.")
            print()

            # Setup authentication
            self.setup_authentication()

            # Confirm migration
            print("\nReady to start migration.")
            confirm = input("Do you want to proceed? (y/N): ").strip().lower()

            if confirm != 'y':
                print("Migration cancelled.")
                return

            # Start migration
            self.migrate_watched_shows()

            print("\nMigration completed! Check the log file for details.")

        except KeyboardInterrupt:
            print("\nMigration cancelled by user.")

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            print(f"\nMigration failed: {str(e)}")
            print("Check the log file for more details.")

def main():
    """Main function"""

    # Check Python version
    if sys.version_info < (3, 6):
        print("Error: Python 3.6 or higher is required.")
        sys.exit(1)

    # Check for required modules
    try:
        import requests
    except ImportError:
        print("Error: 'requests' module is required. Install it with: pip install requests")
        sys.exit(1)

    # Run migration
    manager = MigrationManager()
    manager.run()

if __name__ == "__main__":
    main()
