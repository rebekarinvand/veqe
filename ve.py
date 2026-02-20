"""
Browser automation script for streaming platform interactions.

This module handles geolocation-based browser automation tasks with 
support for multiple browser instances and CDP mode operations.
"""

import base64
import logging
import random
from typing import Optional, Tuple
from dataclasses import dataclass

import requests
from seleniumbase import SB

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class GeoLocation:
    """Represents geographic and timezone information."""
    latitude: float
    longitude: float
    timezone: str
    country_code: str


class StreamBrowserAutomation:
    """Handles browser automation for streaming platform interactions."""
    
    # Configuration constants
    GEOLOCATION_API = "http://ip-api.com/json/"
    TARGET_CHANNEL = "YnJ1dGFsbGVz"  # Base64 encoded channel name
    TARGET_URL_TEMPLATE = "https://www.twitch.tv/{}"
    CLICK_TIMEOUT = 4
    SLEEP_SHORT = 2
    SLEEP_MEDIUM = 10
    SLEEP_LONG_MIN = 450
    SLEEP_LONG_MAX = 800
    
    SELECTORS = {
        "accept_button": 'button:contains("Accept")',
        "start_watching": 'button:contains("Start Watching")',
        "live_stream": "#live-channel-stream-information",
    }
    
    def __init__(self):
        """Initialize the browser automation with geolocation data."""
        self.geolocation = self._fetch_geolocation()
        self.target_url = self._build_target_url()
        self.random_sleep_duration = random.randint(
            self.SLEEP_LONG_MIN, 
            self.SLEEP_LONG_MAX
        )
    
    @staticmethod
    def _fetch_geolocation() -> GeoLocation:
        """
        Fetch current geolocation information from IP-based API.
        
        Returns:
            GeoLocation: Object containing latitude, longitude, timezone, and country code.
            
        Raises:
            requests.RequestException: If API call fails.
        """
        try:
            response = requests.get(StreamBrowserAutomation.GEOLOCATION_API, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            return GeoLocation(
                latitude=data["lat"],
                longitude=data["lon"],
                timezone=data["timezone"],
                country_code=data["countryCode"].lower()
            )
        except requests.RequestException as e:
            logger.error(f"Failed to fetch geolocation: {e}")
            raise
    
    @staticmethod
    def _build_target_url() -> str:
        """
        Decode base64-encoded channel name and build target URL.
        
        Returns:
            str: Full URL to the streaming channel.
        """
        encoded_name = StreamBrowserAutomation.TARGET_CHANNEL
        decoded_name = base64.b64decode(encoded_name).decode("utf-8")
        return StreamBrowserAutomation.TARGET_URL_TEMPLATE.format(decoded_name)
    
    def _accept_dialogs(self, driver: SB) -> None:
        """
        Accept any consent/cookie dialogs present on the page.
        
        Args:
            driver: SeleniumBase driver instance.
        """
        if driver.is_element_present(self.SELECTORS["accept_button"]):
            driver.cdp.click(self.SELECTORS["accept_button"], timeout=self.CLICK_TIMEOUT)
            driver.sleep(self.SLEEP_SHORT)
    
    def _wait_for_stream_load(self, driver: SB) -> None:
        """
        Wait for stream to load and handle start watching button.
        
        Args:
            driver: SeleniumBase driver instance.
        """
        driver.sleep(self.SLEEP_MEDIUM)
        if driver.is_element_present(self.SELECTORS["start_watching"]):
            driver.cdp.click(self.SELECTORS["start_watching"], timeout=self.CLICK_TIMEOUT)
            driver.sleep(self.SLEEP_MEDIUM)
    
    def _initialize_driver(self, driver: SB, undetectable: bool = False) -> SB:
        """
        Initialize and configure a driver instance.
        
        Args:
            driver: SeleniumBase driver instance.
            undetectable: Whether to enable undetectable mode.
            
        Returns:
            SB: Configured driver instance (same as input).
        """
        driver.activate_cdp_mode(
            self.target_url,
            tzone=self.geolocation.timezone,
            geoloc=(self.geolocation.latitude, self.geolocation.longitude)
        )
        driver.sleep(self.SLEEP_SHORT)
        self._accept_dialogs(driver)
        return driver
    
    def _run_secondary_browser(self, primary_driver: SB) -> None:
        """
        Launch and manage a secondary browser instance.
        
        Args:
            primary_driver: Primary SeleniumBase driver instance.
        """
        try:
            secondary_driver = primary_driver.get_new_driver(undetectable=True)
            self._initialize_driver(secondary_driver, undetectable=True)
            self._wait_for_stream_load(secondary_driver)
            self._accept_dialogs(secondary_driver)
            primary_driver.sleep(self.random_sleep_duration)
        except Exception as e:
            logger.error(f"Secondary browser error: {e}")
        finally:
            # Cleanup if needed
            pass
    
    def run(self) -> None:
        """
        Execute the main browser automation loop.
        
        Continuously monitors the streaming page and manages multiple browser instances.
        """
        try:
            with SB(
                uc=True, 
                locale="en",
                ad_block=True,
                chromium_arg="--disable-webgl"
            ) as primary_driver:
                self._execute_automation_loop(primary_driver)
        except Exception as e:
            logger.error(f"Automation failed: {e}")
            raise
    
    def _execute_automation_loop(self, primary_driver: SB) -> None:
        """
        Main loop for browser automation.
        
        Args:
            primary_driver: Primary SeleniumBase driver instance.
        """
        while True:
            try:
                self._initialize_driver(primary_driver)
                self._wait_for_stream_load(primary_driver)
                self._accept_dialogs(primary_driver)
                
                # Check if live stream is present
                if primary_driver.is_element_present(self.SELECTORS["live_stream"]):
                    self._accept_dialogs(primary_driver)
                    self._run_secondary_browser(primary_driver)
                else:
                    logger.info("Live stream not found, ending automation")
                    break
                    
            except Exception as e:
                logger.error(f"Error in automation loop: {e}")
                break


def main():
    """Entry point for the browser automation script."""
    automation = StreamBrowserAutomation()
    automation.run()


if __name__ == "__main__":
    main()
