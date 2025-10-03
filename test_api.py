#!/usr/bin/env python3
"""
Simple test script for Certbox API
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_root_endpoint():
    """Test the root endpoint."""
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Certbox"
    print("✓ Root endpoint works")

def test_certificate_creation():
    """Test certificate creation."""
    username = f"testuser_{int(time.time())}"
    response = requests.post(f"{BASE_URL}/certs/{username}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username
    assert "serial_number" in data
    print(f"✓ Certificate created for {username}")
    return username

def test_pfx_download(username):
    """Test PFX file download."""
    response = requests.get(f"{BASE_URL}/certs/{username}/pfx")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-pkcs12"
    print(f"✓ PFX file downloadable for {username}")

def test_certificate_revocation(username):
    """Test certificate revocation."""
    response = requests.post(f"{BASE_URL}/revoke/{username}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username
    assert data["status"] == "revoked"
    print(f"✓ Certificate revoked for {username}")

def test_crl_endpoint():
    """Test CRL endpoint."""
    response = requests.get(f"{BASE_URL}/crl.pem")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-pem-file"
    assert response.content.startswith(b"-----BEGIN X509 CRL-----")
    print("✓ CRL endpoint works")

def test_error_handling():
    """Test error handling."""
    # Try to create certificate that already exists
    username = "duplicate_test"
    requests.post(f"{BASE_URL}/certs/{username}")  # Create first
    response = requests.post(f"{BASE_URL}/certs/{username}")  # Try duplicate
    assert response.status_code == 409
    print("✓ Duplicate certificate error handling works")
    
    # Try to revoke non-existent certificate
    response = requests.post(f"{BASE_URL}/revoke/nonexistent")
    assert response.status_code == 404
    print("✓ Non-existent certificate error handling works")
    
    # Try to download non-existent PFX
    response = requests.get(f"{BASE_URL}/certs/nonexistent/pfx")
    assert response.status_code == 404
    print("✓ Non-existent PFX error handling works")

if __name__ == "__main__":
    print("Running Certbox API tests...")
    
    try:
        test_root_endpoint()
        username = test_certificate_creation()
        test_pfx_download(username)
        test_certificate_revocation(username)
        test_crl_endpoint()
        test_error_handling()
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)