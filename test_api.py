"""
Test script for the FastAPI quiz solver endpoint.
Run this after starting the server with: uvicorn main:app --reload
"""
import requests
import json


def test_endpoint():
    base_url = "http://localhost:8000"

    print("=" * 60)
    print("Testing LLM Quiz Solver API")
    print("=" * 60)

    # Test 1: Health check
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200
        print("   ✓ Health check passed")
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")

    # Test 2: Valid request
    print("\n2. Testing valid request...")
    try:
        payload = {
            "email": "test@example.com",
            "secret": "test_secret_123",
            "url": "https://example.com/quiz"
        }
        response = requests.post(f"{base_url}/", json=payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "received"
        assert response.json()["url"] == payload["url"]
        print("   ✓ Valid request test passed")
    except Exception as e:
        print(f"   ✗ Valid request test failed: {e}")

    # Test 3: Invalid secret
    print("\n3. Testing invalid secret...")
    try:
        payload = {
            "email": "test@example.com",
            "secret": "wrong_secret",
            "url": "https://example.com/quiz"
        }
        response = requests.post(f"{base_url}/", json=payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 403
        assert "error" in str(response.json())
        print("   ✓ Invalid secret test passed")
    except Exception as e:
        print(f"   ✗ Invalid secret test failed: {e}")

    # Test 4: Malformed request (missing field)
    print("\n4. Testing malformed request (missing url field)...")
    try:
        payload = {
            "email": "test@example.com",
            "secret": "test_secret_123"
        }
        response = requests.post(f"{base_url}/", json=payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 422  # FastAPI returns 422 for validation errors
        print("   ✓ Malformed request test passed")
    except Exception as e:
        print(f"   ✗ Malformed request test failed: {e}")

    # Test 5: Invalid email format
    print("\n5. Testing invalid email format...")
    try:
        payload = {
            "email": "not-an-email",
            "secret": "test_secret_123",
            "url": "https://example.com/quiz"
        }
        response = requests.post(f"{base_url}/", json=payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 422
        print("   ✓ Invalid email test passed")
    except Exception as e:
        print(f"   ✗ Invalid email test failed: {e}")

    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    print("\nMake sure the server is running first:")
    print("  uvicorn main:app --reload\n")

    try:
        test_endpoint()
    except requests.exceptions.ConnectionError:
        print("✗ ERROR: Cannot connect to the server.")
        print("  Please start the server first with: uvicorn main:app --reload")
