"""
Simple examples demonstrating the data_extractor module.
Shows how to use each function independently.
"""
import asyncio
from data_extractor import (
    download_file,
    extract_pdf_tables,
    extract_web_table,
    call_api,
    download_file_sync,
    extract_web_table_sync,
    call_api_sync
)


# Example 1: Download a file asynchronously
async def example_download():
    print("Example 1: Download a PDF file")
    print("-" * 40)

    url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    file_bytes = await download_file(url)

    print(f"Downloaded {len(file_bytes)} bytes")
    print(f"Is PDF: {file_bytes.startswith(b'%PDF')}")
    print()

    return file_bytes


# Example 2: Extract tables from PDF
async def example_pdf_extraction(pdf_bytes):
    print("Example 2: Extract tables from PDF")
    print("-" * 40)

    df = await extract_pdf_tables(pdf_bytes)

    if not df.empty:
        print(f"Extracted table with {len(df)} rows and {len(df.columns)} columns")
        print(df.head())
    else:
        print("No tables found in this PDF")
    print()


# Example 3: Extract table from web page
async def example_web_extraction():
    print("Example 3: Extract table from Wikipedia")
    print("-" * 40)

    url = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
    df = await extract_web_table(url)

    if not df.empty:
        print(f"Extracted table with {len(df)} rows and {len(df.columns)} columns")
        print("\nColumns:", list(df.columns))
        print("\nFirst 3 rows:")
        print(df.head(3))
    else:
        print("No tables found")
    print()


# Example 4: Call an API
async def example_api_call():
    print("Example 4: Call JSONPlaceholder API")
    print("-" * 40)

    # GET request
    url = "https://jsonplaceholder.typicode.com/users/1"
    result = await call_api(url)

    if "error" not in result:
        print(f"User: {result.get('name')}")
        print(f"Email: {result.get('email')}")
        print(f"Company: {result.get('company', {}).get('name')}")
    else:
        print(f"Error: {result['error']}")
    print()


# Example 5: Using synchronous wrappers
def example_sync_usage():
    print("Example 5: Using synchronous wrappers")
    print("-" * 40)

    # Call API synchronously
    url = "https://api.github.com/users/github"
    result = call_api_sync(url)

    if "error" not in result:
        print(f"GitHub User: {result.get('name')}")
        print(f"Public Repos: {result.get('public_repos')}")
        print(f"Followers: {result.get('followers')}")
    else:
        print(f"Error: {result['error']}")
    print()


async def run_async_examples():
    """Run all async examples"""
    print("=" * 60)
    print("DATA EXTRACTOR USAGE EXAMPLES")
    print("=" * 60)
    print()

    # Run examples
    pdf_bytes = await example_download()
    await example_pdf_extraction(pdf_bytes)
    await example_web_extraction()
    await example_api_call()


if __name__ == "__main__":
    print("\nRunning async examples...\n")
    asyncio.run(run_async_examples())

    print("\nRunning sync examples...\n")
    example_sync_usage()

    print("=" * 60)
    print("Examples completed!")
    print("=" * 60)
