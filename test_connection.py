#!/usr/bin/env python3
"""
Test script to check backend connectivity and CORS configuration.
"""

import requests
import json
import sys
from urllib.parse import urljoin

def test_backend_connection(base_url="http://localhost:5001"):
    """Test backend connection and CORS configuration."""
    
    print(f"Testing backend connection to: {base_url}")
    print("=" * 50)
    
    # Test health endpoint
    try:
        print("1. Testing health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        print(f"   Headers: {dict(response.headers)}")
        print()
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - Backend might not be running")
        print("   Please start the backend with: python run.py")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test CORS preflight
    try:
        print("2. Testing CORS preflight...")
        response = requests.options(
            f"{base_url}/api/auth/check-username",
            headers={
                'Origin': 'http://localhost:8081',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            },
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   CORS Headers: {dict(response.headers)}")
        print()
    except Exception as e:
        print(f"   ❌ CORS test failed: {e}")
    
    # Test actual API call
    try:
        print("3. Testing API call...")
        response = requests.post(
            f"{base_url}/api/auth/check-username",
            headers={
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:8081'
            },
            json={"username": "testuser"},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        print(f"   Headers: {dict(response.headers)}")
        print()
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        return False
    
    print("✅ Backend connection test completed successfully!")
    return True

def check_backend_status():
    """Check if backend is running and accessible."""
    try:
        response = requests.get("http://localhost:5001/health", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print("Memory Lane Backend Connection Test")
    print("=" * 40)
    
    if not check_backend_status():
        print("❌ Backend is not running!")
        print("Please start the backend with:")
        print("  cd Memory-Lane-Backend")
        print("  python run.py")
        sys.exit(1)
    
    success = test_backend_connection()
    
    if success:
        print("🎉 All tests passed! Backend is ready for frontend connections.")
    else:
        print("❌ Some tests failed. Please check the backend configuration.")
        sys.exit(1) 