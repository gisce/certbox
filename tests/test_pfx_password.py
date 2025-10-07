#!/usr/bin/env python3
"""
Test suite for PFX password functionality
"""

import pytest
import tempfile
import os
import string
from pathlib import Path

from certbox.core.certificate_manager import CertificateManager
from certbox.config import create_config


class TestPFXPassword:
    """Test cases for PFX password functionality."""
    
    def test_pfx_password_generation(self):
        """Test that PFX passwords are generated correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = create_config()
            config.root_dir = temp_dir
            manager = CertificateManager(config)
            
            # Generate multiple passwords to ensure they're different
            password1 = manager._generate_pfx_password()
            password2 = manager._generate_pfx_password()
            
            # Check password properties
            assert len(password1) == config.pfx_password_length
            assert len(password2) == config.pfx_password_length
            assert password1 != password2  # Should be different
            
            # Check character set
            allowed_chars = string.ascii_letters + string.digits + "!@#$%^&*"
            assert all(c in allowed_chars for c in password1)
            assert all(c in allowed_chars for c in password2)
    
    def test_certificate_creation_includes_password(self):
        """Test that certificate creation returns a PFX password."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = create_config()
            config.root_dir = temp_dir
            manager = CertificateManager(config)
            
            result = manager.create_client_certificate('testuser')
            
            # Check that password is included in response
            assert 'pfx_password' in result
            assert isinstance(result['pfx_password'], str)
            assert len(result['pfx_password']) == config.pfx_password_length
            
            # Check that PFX file was created
            pfx_path = Path(result['pfx_path'])
            assert pfx_path.exists()
            assert pfx_path.stat().st_size > 0
    
    def test_certificate_renewal_includes_password(self):
        """Test that certificate renewal returns a new PFX password."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = create_config()
            config.root_dir = temp_dir
            manager = CertificateManager(config)
            
            # Create original certificate
            original_result = manager.create_client_certificate('testuser')
            original_password = original_result['pfx_password']
            
            # Renew certificate
            renewed_result = manager.renew_certificate('testuser')
            renewed_password = renewed_result['pfx_password']
            
            # Check that new password is included and different
            assert 'pfx_password' in renewed_result
            assert isinstance(renewed_password, str)
            assert len(renewed_password) == config.pfx_password_length
            assert renewed_password != original_password
    
    def test_custom_password_length(self):
        """Test that custom password length configuration works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = create_config()
            config.root_dir = temp_dir
            config.pfx_password_length = 16  # Custom length
            manager = CertificateManager(config)
            
            result = manager.create_client_certificate('testuser')
            
            # Check that password has custom length
            assert len(result['pfx_password']) == 16
    
    def test_pfx_file_is_encrypted(self):
        """Test that PFX files are actually encrypted with passwords."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = create_config()
            config.root_dir = temp_dir
            manager = CertificateManager(config)
            
            result = manager.create_client_certificate('testuser')
            pfx_path = Path(result['pfx_path'])
            password = result['pfx_password']
            
            # Read the PFX file and try to load it
            with open(pfx_path, 'rb') as f:
                pfx_data = f.read()
            
            # Try to load with correct password (should work)
            from cryptography.hazmat.primitives import serialization
            try:
                private_key, cert, additional_certs = serialization.pkcs12.load_key_and_certificates(
                    pfx_data, password.encode('utf-8')
                )
                assert private_key is not None
                assert cert is not None
            except Exception as e:
                pytest.fail(f"Failed to load PFX with correct password: {e}")
            
            # Try to load with wrong password (should fail)
            try:
                private_key, cert, additional_certs = serialization.pkcs12.load_key_and_certificates(
                    pfx_data, b'wrongpassword'
                )
                pytest.fail("Should have failed with wrong password")
            except Exception:
                # Expected to fail with wrong password
                pass
    
    def test_backward_compatibility_api_structure(self):
        """Test that API response structure is maintained with new pfx_password field."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = create_config()
            config.root_dir = temp_dir
            manager = CertificateManager(config)
            
            result = manager.create_client_certificate('testuser')
            
            # Check that all expected fields are present
            expected_fields = {
                'username', 'serial_number', 'valid_from', 'valid_until',
                'certificate_path', 'private_key_path', 'pfx_path', 'pfx_password'
            }
            assert set(result.keys()) == expected_fields
            
            # Check field types
            assert isinstance(result['username'], str)
            assert isinstance(result['serial_number'], str)
            assert isinstance(result['valid_from'], str)
            assert isinstance(result['valid_until'], str)
            assert isinstance(result['certificate_path'], str)
            assert isinstance(result['private_key_path'], str)
            assert isinstance(result['pfx_path'], str)
            assert isinstance(result['pfx_password'], str)