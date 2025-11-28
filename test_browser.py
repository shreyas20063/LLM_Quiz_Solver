"""
Test script for browser extraction functionality.
Tests the headless Chrome browser with various URLs.
"""
import asyncio
from browser_handler import extract_task_from_url


async def test_simple_page():
    """Test with a simple HTML page"""
    print("=" * 60)
    print("Test 1: Simple HTML page (example.com)")
    print("=" * 60)

    url = "https://example.com"
    result = await extract_task_from_url(url)

    print(f"\nURL: {url}")
    print(f"Error: {result.get('error')}")
    print(f"Page text length: {len(result.get('page_text', ''))}")
    print(f"Decoded text found: {bool(result.get('decoded_text'))}")

    if result.get('page_text'):
        print(f"\nPage text preview (first 200 chars):")
        print(result['page_text'][:200])

    if result.get('decoded_text'):
        print(f"\nDecoded text preview (first 200 chars):")
        print(result['decoded_text'][:200])

    return result


async def test_base64_example():
    """Test with a page containing base64 content"""
    print("\n" + "=" * 60)
    print("Test 2: Page with base64 content")
    print("=" * 60)

    # Create a simple test HTML with base64
    # You can replace this with an actual URL if you have one
    url = "data:text/html,<html><body><script>document.body.innerHTML = atob('SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0Lg==')</script></body></html>"

    print(f"\nURL: Testing with data URL containing atob()")

    # For data URLs, we'll skip the actual test as Selenium might not handle them well
    # Instead, test the decode function directly
    from browser_handler import decode_base64_content

    test_html = """
    <script>
    var msg = atob('SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0Lg==');
    console.log(msg);
    </script>
    """

    decoded = decode_base64_content(test_html)
    print(f"Decoded content: {decoded}")

    return {"decoded_text": decoded}


async def test_httpbin():
    """Test with httpbin.org for HTML content"""
    print("\n" + "=" * 60)
    print("Test 3: HTTPBin HTML page")
    print("=" * 60)

    url = "https://httpbin.org/html"
    result = await extract_task_from_url(url)

    print(f"\nURL: {url}")
    print(f"Error: {result.get('error')}")
    print(f"Page text length: {len(result.get('page_text', ''))}")
    print(f"Decoded text found: {bool(result.get('decoded_text'))}")

    if result.get('page_text'):
        print(f"\nPage text preview (first 300 chars):")
        print(result['page_text'][:300])

    return result


async def main():
    """Run all browser tests"""
    print("\n" + "=" * 60)
    print("BROWSER EXTRACTION TESTS")
    print("=" * 60)
    print("\nThis will test the headless Chrome browser functionality.")
    print("Chrome WebDriver will be downloaded if not present.\n")

    try:
        # Test 1: Simple page
        await test_simple_page()

        # Test 2: Base64 decoding
        await test_base64_example()

        # Test 3: HTTPBin
        await test_httpbin()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nMake sure you have installed the requirements:")
    print("  pip install selenium webdriver-manager\n")

    asyncio.run(main())
