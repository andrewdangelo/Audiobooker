#!/usr/bin/env python3
"""
Test script to verify auth service proxy integration
"""
import requests
import json
import sys

PROXY_URL = "http://localhost:8000"
AUTH_URL = f"{PROXY_URL}/auth"

def test_health():
    """Test proxy health check includes auth service"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{PROXY_URL}/health", timeout=5)
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Overall Status: {data.get('status')}")
        print(f"\nServices:")
        for service, status in data.get('services', {}).items():
            print(f"  {service}: {status}")
        
        print(f"\nAuth Queue:")
        auth_queue = data.get('queues', {}).get('auth', {})
        print(f"  Queued: {auth_queue.get('queued')}")
        print(f"  Active: {auth_queue.get('active')}")
        print(f"  Max: {auth_queue.get('max')}")
        
        if data.get('services', {}).get('auth') == 'ok':
            print("\n✅ Auth service is healthy via proxy")
            return True
        else:
            print("\n❌ Auth service is not healthy")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to proxy - is it running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_metrics():
    """Test proxy metrics includes auth service"""
    print("\n" + "="*60)
    print("TEST 2: Metrics")
    print("="*60)
    
    try:
        response = requests.get(f"{PROXY_URL}/metrics", timeout=5)
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        
        if 'auth_service' in data:
            auth_metrics = data['auth_service']
            print(f"\nAuth Service Metrics:")
            print(f"  Queued Requests: {auth_metrics.get('queued_requests')}")
            print(f"  Active Requests: {auth_metrics.get('active_requests')}")
            print(f"  Max Concurrent: {auth_metrics.get('max_concurrent')}")
            print(f"  Available Slots: {auth_metrics.get('available_slots')}")
            print("\n✅ Auth metrics available")
            return True
        else:
            print("❌ Auth service metrics not found")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_signup_via_proxy():
    """Test signup through proxy"""
    print("\n" + "="*60)
    print("TEST 3: Signup via Proxy")
    print("="*60)
    
    test_user = {
        "email": "proxytest@example.com",
        "password": "ProxyTest123",
        "first_name": "Proxy",
        "last_name": "Test"
    }
    
    try:
        print(f"POST {AUTH_URL}/signup")
        response = requests.post(
            f"{AUTH_URL}/signup",
            json=test_user,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"User ID: {data.get('user', {}).get('id')}")
            print(f"Email: {data.get('user', {}).get('email')}")
            print(f"Token Type: {data.get('token_type')}")
            print(f"Access Token: {data.get('access_token')[:20]}...")
            print("\n✅ Signup successful via proxy")
            return True, data.get('access_token')
        elif response.status_code == 202:
            # Request queued
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Queue ID: {data.get('queue_id')}")
            print(f"Queue Position: {data.get('queue_position')}")
            print("\n✅ Request queued (service at capacity)")
            return True, None
        elif response.status_code == 400:
            data = response.json()
            if "already registered" in str(data.get('detail', '')).lower():
                print(f"Note: {data.get('detail')}")
                print("\n✅ User already exists (proxy working)")
                return True, None
            else:
                print(f"Validation Error: {data.get('detail')}")
                return False, None
        else:
            print(f"Response: {response.text}")
            print("\n❌ Signup failed")
            return False, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None


def test_login_via_proxy():
    """Test login through proxy"""
    print("\n" + "="*60)
    print("TEST 4: Login via Proxy")
    print("="*60)
    
    credentials = {
        "email": "proxytest@example.com",
        "password": "ProxyTest123"
    }
    
    try:
        print(f"POST {AUTH_URL}/login")
        response = requests.post(
            f"{AUTH_URL}/login",
            json=credentials,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"User ID: {data.get('user', {}).get('id')}")
            print(f"Email: {data.get('user', {}).get('email')}")
            print(f"Token Type: {data.get('token_type')}")
            print(f"Access Token: {data.get('access_token')[:20]}...")
            print("\n✅ Login successful via proxy")
            return True, data.get('access_token')
        elif response.status_code == 202:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print("\n✅ Request queued")
            return True, None
        else:
            print(f"Response: {response.text}")
            print("\n❌ Login failed")
            return False, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None


def test_get_current_user(access_token):
    """Test getting current user through proxy"""
    print("\n" + "="*60)
    print("TEST 5: Get Current User via Proxy")
    print("="*60)
    
    if not access_token:
        print("⏭️  Skipping (no access token)")
        return True
    
    try:
        print(f"GET {AUTH_URL}/me")
        response = requests.get(
            f"{AUTH_URL}/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"User ID: {data.get('id')}")
            print(f"Email: {data.get('email')}")
            print(f"Name: {data.get('first_name')} {data.get('last_name')}")
            print("\n✅ Get current user successful via proxy")
            return True
        else:
            print(f"Response: {response.text}")
            print("\n❌ Get current user failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AUTH SERVICE PROXY INTEGRATION TESTS")
    print("="*60)
    
    results = []
    
    # Test 1: Health Check
    results.append(("Health Check", test_health()))
    
    # Test 2: Metrics
    results.append(("Metrics", test_metrics()))
    
    # Test 3: Signup
    signup_success, access_token = test_signup_via_proxy()
    results.append(("Signup via Proxy", signup_success))
    
    # Test 4: Login (and get token if signup failed)
    if not access_token:
        login_success, access_token = test_login_via_proxy()
        results.append(("Login via Proxy", login_success))
    
    # Test 5: Get Current User
    if access_token:
        results.append(("Get Current User", test_get_current_user(access_token)))
    
    # Print Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Auth proxy integration is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
