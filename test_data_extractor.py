"""
Test script for data_extractor module.
Tests downloading files, extracting PDF tables, web tables, and API calls.
"""
import asyncio
from data_extractor import (
    download_file,
    extract_pdf_tables,
    extract_web_table,
    call_api,
    extract_all_web_tables
)


async def test_download_file():
    """Test file downloading with a sample PDF"""
    print("=" * 60)
    print("Test 1: Download File")
    print("=" * 60)

    # Test with a sample PDF (Wikipedia's PDF logo)
    test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

    try:
        print(f"\nDownloading from: {test_url}")
        file_bytes = await download_file(test_url)

        print(f"✓ Successfully downloaded {len(file_bytes)} bytes")
        print(f"  File starts with: {file_bytes[:10]}")

        # Check if it's a PDF (starts with %PDF)
        if file_bytes.startswith(b'%PDF'):
            print("  ✓ Confirmed: This is a valid PDF file")
        else:
            print("  ⚠ Warning: This doesn't appear to be a PDF")

        return file_bytes

    except Exception as e:
        print(f"✗ Error downloading file: {e}")
        return None


async def test_extract_pdf_tables(pdf_bytes):
    """Test PDF table extraction"""
    print("\n" + "=" * 60)
    print("Test 2: Extract PDF Tables")
    print("=" * 60)

    if not pdf_bytes:
        print("Skipping - no PDF bytes available")
        return

    try:
        print("\nExtracting tables from PDF...")
        df = await extract_pdf_tables(pdf_bytes)

        if not df.empty:
            print(f"✓ Successfully extracted table with shape: {df.shape}")
            print(f"\nFirst few rows:")
            print(df.head())
        else:
            print("⚠ No tables found in PDF (this is okay for test PDF)")

    except Exception as e:
        print(f"✗ Error extracting PDF tables: {e}")


async def test_extract_web_table():
    """Test web table extraction"""
    print("\n" + "=" * 60)
    print("Test 3: Extract Web Table")
    print("=" * 60)

    # Test with Wikipedia page that has tables
    test_url = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"

    try:
        print(f"\nExtracting table from: {test_url}")
        df = await extract_web_table(test_url)

        if not df.empty:
            print(f"✓ Successfully extracted table with shape: {df.shape}")
            print(f"\nFirst few rows:")
            print(df.head())
            print(f"\nColumns: {list(df.columns)}")
        else:
            print("⚠ No tables found on web page")

    except Exception as e:
        print(f"✗ Error extracting web table: {e}")


async def test_call_api():
    """Test API calling"""
    print("\n" + "=" * 60)
    print("Test 4: Call API")
    print("=" * 60)

    # Test with JSONPlaceholder API
    test_url = "https://jsonplaceholder.typicode.com/posts/1"

    try:
        print(f"\nGET request to: {test_url}")
        result = await call_api(test_url, method="GET")

        if "error" not in result:
            print(f"✓ Successfully called API")
            print(f"\nResponse:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print(f"✗ API call failed: {result['error']}")

    except Exception as e:
        print(f"✗ Error calling API: {e}")

    # Test POST request
    print("\n" + "-" * 60)
    post_url = "https://jsonplaceholder.typicode.com/posts"
    post_data = {
        "title": "Test Post",
        "body": "This is a test post",
        "userId": 1
    }

    try:
        print(f"\nPOST request to: {post_url}")
        print(f"Data: {post_data}")
        result = await call_api(post_url, method="POST", data=post_data)

        if "error" not in result:
            print(f"✓ Successfully posted data")
            print(f"\nResponse:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print(f"✗ POST request failed: {result['error']}")

    except Exception as e:
        print(f"✗ Error posting data: {e}")


async def test_extract_all_web_tables():
    """Test extracting all tables from a web page"""
    print("\n" + "=" * 60)
    print("Test 5: Extract All Web Tables")
    print("=" * 60)

    # Test with a simple page with multiple tables
    test_url = "https://www.w3.org/TR/html4/struct/tables.html"

    try:
        print(f"\nExtracting all tables from: {test_url}")
        tables = await extract_all_web_tables(test_url)

        if tables:
            print(f"✓ Successfully extracted {len(tables)} table(s)")
            for idx, df in enumerate(tables):
                print(f"\nTable {idx + 1}: shape {df.shape}")
                print(f"  Columns: {list(df.columns)[:5]}")  # First 5 columns
        else:
            print("⚠ No tables found on web page")

    except Exception as e:
        print(f"✗ Error extracting all web tables: {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DATA EXTRACTOR MODULE TESTS")
    print("=" * 60)
    print("\nThis will test downloading files, PDF extraction,")
    print("web table extraction, and API calls.\n")

    try:
        # Test 1: Download file
        pdf_bytes = await test_download_file()

        # Test 2: Extract PDF tables
        await test_extract_pdf_tables(pdf_bytes)

        # Test 3: Extract web table
        await test_extract_web_table()

        # Test 4: Call API
        await test_call_api()

        # Test 5: Extract all web tables
        await test_extract_all_web_tables()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nMake sure you have installed the requirements:")
    print("  pip install httpx pdfplumber pandas openpyxl beautifulsoup4 lxml\n")

    asyncio.run(main())
