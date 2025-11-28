"""
Browser handler for extracting quiz tasks from JavaScript-rendered pages.
Uses Selenium with headless Chrome to navigate and extract content.
"""
import logging
import base64
import re
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def decode_base64_content(text: str) -> Optional[str]:
    """
    Extract and decode base64 content from text.
    Looks for atob() patterns and base64-encoded strings.

    Args:
        text: The text to search for base64 content

    Returns:
        Decoded string if found, None otherwise
    """
    try:
        # Pattern 1: Look for atob("...") or atob('...')
        atob_pattern = r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)'
        atob_matches = re.findall(atob_pattern, text)

        if atob_matches:
            logger.info(f"Found {len(atob_matches)} atob() encoded strings")
            decoded_parts = []
            for encoded in atob_matches:
                try:
                    decoded = base64.b64decode(encoded).decode('utf-8')
                    decoded_parts.append(decoded)
                    logger.debug(f"Decoded atob content: {decoded[:100]}...")
                except Exception as e:
                    logger.warning(f"Failed to decode atob content: {e}")

            if decoded_parts:
                return "\n".join(decoded_parts)

        # Pattern 2: Look for standalone base64 strings (at least 20 chars)
        base64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        base64_matches = re.findall(base64_pattern, text)

        if base64_matches:
            logger.info(f"Found {len(base64_matches)} potential base64 strings")
            for encoded in base64_matches:
                try:
                    decoded = base64.b64decode(encoded).decode('utf-8')
                    # Check if decoded content looks like meaningful text
                    if len(decoded) > 10 and any(c.isalpha() for c in decoded):
                        logger.debug(f"Decoded base64 content: {decoded[:100]}...")
                        return decoded
                except Exception:
                    continue

        logger.info("No base64 content found or decoded")
        return None

    except Exception as e:
        logger.error(f"Error in decode_base64_content: {e}")
        return None


async def extract_task_from_url(url: str) -> Dict[str, Optional[str]]:
    """
    Extract quiz task from a URL using headless Chrome.

    Args:
        url: The URL to extract content from

    Returns:
        Dictionary containing:
        - raw_html: The page HTML
        - page_text: The visible page text
        - decoded_text: Decoded base64 content if found
        - error: Error message if something went wrong
    """
    driver = None

    try:
        logger.info(f"Starting extraction from URL: {url}")

        # Configure Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Suppress unnecessary logging
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        logger.info("Initializing Chrome WebDriver...")

        # Initialize the driver with webdriver-manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        logger.info(f"Navigating to URL: {url}")
        driver.get(url)

        # Wait for page to load - try multiple strategies
        logger.info("Waiting for page to render...")

        try:
            # Strategy 1: Wait for body element
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logger.info("Body element found")
        except Exception as e:
            logger.warning(f"Body wait timeout: {e}")

        try:
            # Strategy 2: Wait for #result element if it exists
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "result"))
            )
            logger.info("Result element found")
        except Exception:
            logger.info("No #result element found (this is okay)")

        # Give JavaScript a moment to execute
        driver.implicitly_wait(2)

        # Extract page source and text
        logger.info("Extracting page content...")
        raw_html = driver.page_source

        # Get visible text from body
        try:
            body_element = driver.find_element(By.TAG_NAME, "body")
            page_text = body_element.text
            logger.info(f"Extracted page text ({len(page_text)} chars)")
        except Exception as e:
            logger.warning(f"Could not extract body text: {e}")
            page_text = ""

        # Try to find and decode base64 content
        logger.info("Searching for base64 content...")

        # Search in page source for atob() calls or base64
        decoded_text = decode_base64_content(raw_html)

        # Also search in page text
        if not decoded_text:
            decoded_text = decode_base64_content(page_text)

        # Try to get content from #result element specifically
        if not decoded_text:
            try:
                result_element = driver.find_element(By.ID, "result")
                result_text = result_element.text
                result_html = result_element.get_attribute('innerHTML')

                logger.info(f"Found #result element with {len(result_text)} chars")

                # Try to decode from result element
                decoded_from_result = decode_base64_content(result_html)
                if decoded_from_result:
                    decoded_text = decoded_from_result
            except Exception:
                logger.info("No #result element to extract from")

        logger.info("Extraction completed successfully")

        return {
            "raw_html": raw_html,
            "page_text": page_text,
            "decoded_text": decoded_text,
            "error": None
        }

    except Exception as e:
        error_msg = f"Error extracting content from URL: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "raw_html": None,
            "page_text": None,
            "decoded_text": None,
            "error": error_msg
        }

    finally:
        # Clean up
        if driver:
            try:
                logger.info("Closing browser...")
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {e}")


# Synchronous wrapper for compatibility
def extract_task_from_url_sync(url: str) -> Dict[str, Optional[str]]:
    """
    Synchronous version of extract_task_from_url.
    Can be called directly without async/await.
    """
    import asyncio

    # Check if we're already in an event loop
    try:
        loop = asyncio.get_running_loop()
        # If we're in a loop, we can't use asyncio.run()
        # Return a future instead
        logger.warning("Already in event loop, creating task")
        return asyncio.create_task(extract_task_from_url(url))
    except RuntimeError:
        # No event loop, safe to use asyncio.run()
        return asyncio.run(extract_task_from_url(url))
