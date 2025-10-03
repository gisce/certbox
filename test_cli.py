#!/usr/bin/env python3
"""
Simple test script for Certbox CLI functionality
"""

import subprocess
import sys
import tempfile
import time
import signal
import os

def run_command(cmd, timeout=30):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def test_cli_help():
    """Test CLI help command."""
    print("Testing CLI help...")
    code, stdout, stderr = run_command("certbox --help")
    assert code == 0, f"Help command failed: {stderr}"
    assert "Certbox - X.509 Certificate Management Service CLI" in stdout
    print("✓ CLI help works")

def test_cli_config():
    """Test CLI config command."""
    print("Testing CLI config...")
    code, stdout, stderr = run_command("certbox config")
    assert code == 0, f"Config command failed: {stderr}"
    assert "Current Certbox Configuration" in stdout
    assert "Certificate validity:" in stdout
    print("✓ CLI config works")

def test_cli_certificate_lifecycle():
    """Test CLI certificate create and revoke."""
    username = f"test_cli_user_{int(time.time())}"
    
    print(f"Testing CLI certificate lifecycle for {username}...")
    
    # Test create
    code, stdout, stderr = run_command(f"certbox create {username}")
    assert code == 0, f"Create command failed: {stderr}"
    assert "Certificate created successfully" in stdout
    assert "Serial number:" in stdout
    print("✓ CLI create works")
    
    # Test duplicate create (should fail)
    code, stdout, stderr = run_command(f"certbox create {username}")
    assert code != 0, "Duplicate create should fail"
    assert "already exists" in stderr
    print("✓ CLI duplicate create error handling works")
    
    # Test revoke
    code, stdout, stderr = run_command(f"certbox revoke {username}")
    assert code == 0, f"Revoke command failed: {stderr}"
    assert "Certificate revoked successfully" in stdout
    print("✓ CLI revoke works")
    
    # Test revoke non-existent (should fail)
    code, stdout, stderr = run_command(f"certbox revoke nonexistent_{int(time.time())}")
    assert code != 0, "Revoke non-existent should fail"
    assert "not found" in stderr
    print("✓ CLI revoke error handling works")

def test_cli_crl():
    """Test CLI CRL command."""
    print("Testing CLI CRL...")
    code, stdout, stderr = run_command("certbox crl")
    assert code == 0, f"CRL command failed: {stderr}"
    assert "-----BEGIN X509 CRL-----" in stdout
    assert "-----END X509 CRL-----" in stdout
    print("✓ CLI CRL works")

def test_cli_api_server():
    """Test CLI API server command."""
    print("Testing CLI API server...")
    
    # Start server in background
    proc = subprocess.Popen(["certbox", "api", "--port", "8080"], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # Wait a bit for server to start
        time.sleep(3)
        
        # Test if server is running
        code, stdout, stderr = run_command("curl -s http://localhost:8080/ | grep service")
        assert code == 0, f"API server test failed: {stderr}"
        assert "Certbox" in stdout
        print("✓ CLI API server works")
        
    finally:
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    print("Running Certbox CLI tests...")
    
    try:
        test_cli_help()
        test_cli_config()
        test_cli_certificate_lifecycle()
        test_cli_crl()
        test_cli_api_server()
        
        print("\n🎉 All CLI tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)