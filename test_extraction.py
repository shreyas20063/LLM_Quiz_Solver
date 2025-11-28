"""
Quick test for the full extraction pipeline via the API.
Tests that the API correctly extracts content from URLs.
"""
import requests


def test_api_extraction():
    """Test the API with browser extraction"""
    base_url = "http://localhost:8000"

    print("=" * 60)
    print("Testing API with Browser Extraction")
    print("=" * 60)

    # Test with a simple URL
    print("\n1. Testing extraction with example.com...")
    payload = {
        "email": "test@example.com",
        "secret": "test_secret_123",
        "url": "https://example.com"
    }

    try:
        response = requests.post(f"{base_url}/", json=payload)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   URL: {data.get('url')}")

            extracted = data.get('extracted_content', {})
            print(f"\n   Extracted Content:")
            print(f"   - Error: {extracted.get('error')}")
            print(f"   - Has decoded content: {extracted.get('has_decoded_content')}")
            print(f"   - Page text length: {len(extracted.get('page_text', ''))}")

            if extracted.get('page_text'):
                print(f"\n   Page text preview (first 200 chars):")
                print(f"   {extracted['page_text'][:200]}")

            if extracted.get('decoded_text'):
                print(f"\n   Decoded text preview (first 200 chars):")
                print(f"   {extracted['decoded_text'][:200]}")

            print("\n   ✓ Extraction test passed")
        else:
            print(f"   ✗ Request failed: {response.json()}")

    except requests.exceptions.ConnectionError:
        print("   ✗ ERROR: Cannot connect to the server.")
        print("   Please start the server first with: uvicorn main:app --reload")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\nMake sure the server is running first:")
    print("  uvicorn main:app --reload\n")
    test_api_extraction()
