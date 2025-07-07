#!/usr/bin/env python3
"""
Test script to verify CORS and API functionality
"""

import requests
import json

def test_backend():
    base_url = "http://localhost:5001"
    
    print("Testing Memory Lane Backend")
    print("=" * 30)
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        print(f"   CORS Headers: {dict(response.headers)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: CORS preflight
    print("\n2. Testing CORS preflight...")
    try:
        response = requests.options(
            f"{base_url}/api/auth/check-username",
            headers={
                'Origin': 'http://localhost:8081',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
        )
        print(f"   Status: {response.status_code}")
        print(f"   CORS Headers: {dict(response.headers)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Actual API call
    print("\n3. Testing API call...")
    try:
        response = requests.post(
            f"{base_url}/api/auth/check-username",
            headers={
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:8081'
            },
            json={"username": "testuser"}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        print(f"   CORS Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Parsed response: {data}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n✅ All tests completed!")
    return True

if __name__ == "__main__":
    test_backend() 