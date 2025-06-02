import time
import random
import logging
import requests
import os
from datetime import datetime, timedelta

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("amazon_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

class ProxyManager:
    """Manages and rotates proxies for web scraping with time-based rotation."""
    
    def __init__(self, rotation_minutes: int = 2):
        """
        Initialize the proxy manager with time-based rotation.
        
        Args:
            rotation_minutes: Minutes to use a proxy before rotating
        """
        self.proxies = []
        self.last_refresh = 0
        self.refresh_interval = 300  # Seconds between API refreshes
        
        # Time-based rotation
        self.rotation_seconds = rotation_minutes * 60
        self.current_proxy = None
        self.current_proxy_start_time = None
        
        # Track used proxies
        self.used_proxies = set()
        self.available_proxies = []
        
        # These can also be set via env vars
        self.api_url = os.getenv("PROXY_API_URL")
        self.api_key = os.getenv("PROXY_API_KEY")
        
        # Load initial proxies
        self.load_proxies()
    
    def load_proxies(self, filepath="valid_proxies.txt"):
        """Initial load from file or environment variables."""
        # Try file first
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                logger.info(f"Successfully loaded {len(self.proxies)} proxies from {filepath}")
            except Exception as e:
                logger.error(f"Error reading proxy file '{filepath}': {e}")
        
        # Then try environment variable if no proxies loaded
        if not self.proxies:
            env = os.getenv("PROXY_URLS", "")
            self.proxies = [p.strip() for p in env.split(",") if p.strip()]
            if self.proxies:
                logger.info(f"Loaded {len(self.proxies)} proxies from environment")
        
        # If still no proxies, try to get from API
        if not self.proxies and self.api_url:
            self.refresh_proxies_from_api()
            
        if not self.proxies:
            logger.warning("No proxies configured; scraping may proceed without proxies.")
        else:
            # Initialize available proxies
            self.available_proxies = self.proxies.copy()
            logger.info(f"Available proxies: {len(self.available_proxies)}")
    
    def refresh_proxies_from_api(self):
        """Fetch fresh proxies from an API, if configured."""
        if not self.api_url or not self.api_key:
            return
        
        now = time.time()
        if now - self.last_refresh < self.refresh_interval:
            return  # too soon
        
        logger.info("Refreshing proxies from API...")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        try:
            resp = requests.get(self.api_url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            # adapt to your provider's JSON format:
            if isinstance(data, list):
                new_list = data
            elif isinstance(data, dict) and "proxies" in data:
                new_list = data["proxies"]
            elif isinstance(data, dict) and "data" in data:
                new_list = data["data"]
            else:
                new_list = []
            
            if new_list:
                old_count = len(self.proxies)
                self.proxies = new_list
                self.last_refresh = now
                
                # Update available proxies with new ones
                self.reset_proxy_rotation()
                logger.info(f"Successfully refreshed proxies: {old_count} → {len(self.proxies)}")
            else:
                logger.warning("API returned no proxies")
        
        except Exception as e:
            logger.error(f"Failed to refresh proxies from API: {e}")
    
    def reset_proxy_rotation(self):
        """Reset proxy rotation, making all proxies available again."""
        self.available_proxies = self.proxies.copy()
        self.used_proxies = set()
        self.current_proxy = None
        self.current_proxy_start_time = None
        logger.info(f"Reset proxy rotation. {len(self.available_proxies)} proxies available.")
    
    def should_rotate_proxy(self):
        """Check if the current proxy should be rotated based on time."""
        if not self.current_proxy or not self.current_proxy_start_time:
            return True
            
        now = time.time()
        elapsed = now - self.current_proxy_start_time
        
        if elapsed >= self.rotation_seconds:
            logger.info(f"Time to rotate proxy. Used for {elapsed:.1f} seconds")
            return True
            
        return False
    
    def get_next_proxy(self):
        """Get the next unused proxy, or reset if all are used."""
        if not self.available_proxies:
            # All proxies used, reset rotation
            logger.info("All proxies have been used. Resetting rotation.")
            self.reset_proxy_rotation()
            
        if not self.available_proxies:
            # Still no proxies available
            return None
            
        # Get a random proxy from available ones
        proxy = random.choice(self.available_proxies)
        self.available_proxies.remove(proxy)
        self.used_proxies.add(proxy)
        
        # Update tracking
        self.current_proxy = proxy
        self.current_proxy_start_time = time.time()
        
        logger.info(f"Using new proxy: {proxy}")
        logger.info(f"Proxies: {len(self.used_proxies)} used, {len(self.available_proxies)} available")
        
        return proxy
    
    def get_current_proxy(self):
        """
        Get the current proxy, rotating if needed based on time.
        Returns a proxy string or None if no proxies available.
        """
        if self.should_rotate_proxy():
            return self.get_next_proxy()
        
        return self.current_proxy
        
    def get_proxy_for_selenium(self):
        """
        Returns a proxy suitable for Selenium, rotating as needed.
        """
        return self.get_current_proxy()
    
    def __len__(self):
        """Return the number of total proxies."""
        return len(self.proxies)