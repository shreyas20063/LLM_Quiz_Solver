"""
Data extraction module for handling PDFs, web pages, and API calls.
Provides async functions for downloading files and extracting structured data.
"""
import logging
import asyncio
from typing import Optional, Dict, List, Union
import httpx
import pandas as pd
import pdfplumber
from io import BytesIO
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def download_file(url: str, max_retries: int = 3) -> bytes:
    """
    Download any file from URL using httpx with retry logic.

    Args:
        url: The URL to download from
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        Raw bytes of the downloaded file

    Raises:
        Exception: If download fails after all retries
    """
    logger.info(f"Starting download from URL: {url}")

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                content = response.content
                logger.info(f"Successfully downloaded {len(content)} bytes from {url}")
                return content

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on attempt {attempt + 1}/{max_retries}: {e.response.status_code}")
            if attempt == max_retries - 1:
                raise Exception(f"Failed to download file after {max_retries} attempts: HTTP {e.response.status_code}")

        except httpx.RequestError as e:
            logger.error(f"Network error on attempt {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                raise Exception(f"Failed to download file after {max_retries} attempts: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                raise Exception(f"Failed to download file after {max_retries} attempts: {str(e)}")

        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            logger.info(f"Waiting {wait_time} seconds before retry...")
            await asyncio.sleep(wait_time)


async def extract_pdf_tables(pdf_bytes: bytes, page_num: Optional[int] = None) -> pd.DataFrame:
    """
    Extract tables from PDF using pdfplumber.

    Args:
        pdf_bytes: Raw bytes of the PDF file
        page_num: Optional page number (0-indexed). If None, extract from all pages

    Returns:
        pandas DataFrame containing extracted table data
        Returns empty DataFrame on error or if no tables found
    """
    logger.info(f"Starting PDF table extraction (page: {page_num if page_num is not None else 'all'})")

    try:
        # Open PDF from bytes
        pdf_file = BytesIO(pdf_bytes)

        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"PDF has {total_pages} pages")

            all_tables = []

            # Determine which pages to process
            if page_num is not None:
                if page_num < 0 or page_num >= total_pages:
                    logger.error(f"Invalid page number {page_num}. PDF has {total_pages} pages")
                    return pd.DataFrame()
                pages_to_process = [page_num]
            else:
                pages_to_process = range(total_pages)

            # Extract tables from specified pages
            for page_idx in pages_to_process:
                page = pdf.pages[page_idx]
                tables = page.extract_tables()

                if tables:
                    logger.info(f"Found {len(tables)} table(s) on page {page_idx}")

                    for table_idx, table in enumerate(tables):
                        if table:
                            # Convert table to DataFrame
                            df = pd.DataFrame(table[1:], columns=table[0])
                            all_tables.append(df)
                            logger.debug(f"Table {table_idx} on page {page_idx}: {df.shape}")
                else:
                    logger.debug(f"No tables found on page {page_idx}")

            # Concatenate all tables
            if all_tables:
                result = pd.concat(all_tables, ignore_index=True)
                logger.info(f"Successfully extracted {len(all_tables)} table(s), total shape: {result.shape}")
                return result
            else:
                logger.warning("No tables found in PDF")
                return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error extracting PDF tables: {str(e)}", exc_info=True)
        return pd.DataFrame()


async def extract_web_table(url: str) -> pd.DataFrame:
    """
    Extract first table from a web page using pandas.read_html().

    Args:
        url: The URL of the web page

    Returns:
        pandas DataFrame containing the first table found
        Returns empty DataFrame if no tables found or on error
    """
    logger.info(f"Starting web table extraction from: {url}")

    try:
        # Fetch HTML content with user-agent to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html_content = response.text

        logger.info(f"Fetched HTML content ({len(html_content)} chars)")

        # Extract tables using pandas
        # pandas.read_html is not async, but it's CPU-bound, so we run it in executor
        loop = asyncio.get_event_loop()
        tables = await loop.run_in_executor(
            None,
            lambda: pd.read_html(html_content)
        )

        if tables:
            logger.info(f"Found {len(tables)} table(s) on page")
            result = tables[0]
            logger.info(f"Returning first table with shape: {result.shape}")
            return result
        else:
            logger.warning("No tables found on web page")
            return pd.DataFrame()

    except ValueError as e:
        logger.warning(f"No tables found in HTML: {str(e)}")
        return pd.DataFrame()

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching web page: {e.response.status_code}")
        return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error extracting web table: {str(e)}", exc_info=True)
        return pd.DataFrame()


async def call_api(
    url: str,
    method: str = "GET",
    data: Optional[Dict] = None,
    headers: Optional[Dict] = None
) -> Dict:
    """
    Make API calls using httpx with support for GET and POST.

    Args:
        url: The API endpoint URL
        method: HTTP method ("GET" or "POST", default: "GET")
        data: Optional dictionary to send in request body (for POST)
        headers: Optional headers dictionary

    Returns:
        Dictionary containing JSON response
        Returns {"error": "message"} on failure
    """
    logger.info(f"Making {method} request to: {url}")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Prepare request parameters
            request_kwargs = {}
            if headers:
                request_kwargs['headers'] = headers

            # Make request based on method
            if method.upper() == "GET":
                response = await client.get(url, **request_kwargs)

            elif method.upper() == "POST":
                if data:
                    request_kwargs['json'] = data
                response = await client.post(url, **request_kwargs)

            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return {"error": f"Unsupported HTTP method: {method}"}

            # Check response status
            response.raise_for_status()

            # Parse JSON response
            try:
                result = response.json()
                logger.info(f"API call successful, received JSON response")
                return result

            except Exception as json_error:
                logger.warning(f"Response is not JSON: {str(json_error)}")
                return {
                    "status": "success",
                    "content": response.text,
                    "note": "Response was not JSON"
                }

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error: {e.response.status_code}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "status_code": e.response.status_code,
            "details": e.response.text[:200] if e.response.text else None
        }

    except httpx.RequestError as e:
        error_msg = f"Network error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


async def extract_all_web_tables(url: str) -> List[pd.DataFrame]:
    """
    Extract all tables from a web page.

    Args:
        url: The URL of the web page

    Returns:
        List of pandas DataFrames, one for each table found
        Returns empty list if no tables found or on error
    """
    logger.info(f"Starting extraction of all tables from: {url}")

    try:
        # Fetch HTML content with user-agent to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html_content = response.text

        # Extract all tables using pandas
        loop = asyncio.get_event_loop()
        tables = await loop.run_in_executor(
            None,
            lambda: pd.read_html(html_content)
        )

        if tables:
            logger.info(f"Found {len(tables)} table(s) on page")
            for idx, table in enumerate(tables):
                logger.debug(f"Table {idx}: {table.shape}")
            return tables
        else:
            logger.warning("No tables found on web page")
            return []

    except Exception as e:
        logger.error(f"Error extracting all web tables: {str(e)}", exc_info=True)
        return []


# Synchronous wrapper functions for convenience
def download_file_sync(url: str, max_retries: int = 3) -> bytes:
    """Synchronous wrapper for download_file"""
    return asyncio.run(download_file(url, max_retries))


def extract_pdf_tables_sync(pdf_bytes: bytes, page_num: Optional[int] = None) -> pd.DataFrame:
    """Synchronous wrapper for extract_pdf_tables"""
    return asyncio.run(extract_pdf_tables(pdf_bytes, page_num))


def extract_web_table_sync(url: str) -> pd.DataFrame:
    """Synchronous wrapper for extract_web_table"""
    return asyncio.run(extract_web_table(url))


def call_api_sync(url: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
    """Synchronous wrapper for call_api"""
    return asyncio.run(call_api(url, method, data))
