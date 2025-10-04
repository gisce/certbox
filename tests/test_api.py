#!/usr/bin/env python3
"""
Test suite for Certbox API using pytest
"""

import pytest
import time
from unittest.mock import patch, Mock

from certbox.app import app
from certbox.core.certificate_manager import CertificateManager
from certbox.config import config


class TestCertboxAPI:
    """Test cases for Certbox API endpoints."""
    
    def test_root_endpoint_data(self):
        """Test the root endpoint returns correct data structure."""
        # Test the actual route function directly
        from certbox.api.routes import root
        import asyncio
        
        result = asyncio.run(root())
        assert result["service"] == "Certbox"
        assert "description" in result
        assert "version" in result
        assert "endpoints" in result
    
    def test_config_endpoint_data(self):
        """Test configuration endpoint returns expected fields."""
        from certbox.api.routes import get_config
        import asyncio
        
        result = asyncio.run(get_config())
        assert "cert_validity_days" in result
        assert "ca_validity_days" in result
        assert "key_size" in result
        assert "country" in result
        assert "state_province" in result
        assert "locality" in result
        assert "organization" in result
        assert "ca_common_name" in result
    
    def test_config_values(self):
        """Test that config values are properly loaded."""
        # Test configuration values
        assert config.cert_validity_days == 365
        assert config.ca_validity_days == 3650
        assert config.key_size == 2048
        assert config.country == "ES"
        assert config.state_province == "Catalonia"
        assert config.locality == "Girona"
        assert config.organization == "GISCE-TI"
        assert config.ca_common_name == "GISCE-TI CA"


class TestCertificateManager:
    """Test cases for Certificate Manager."""
    
    def test_certificate_manager_initialization(self):
        """Test that CertificateManager initializes correctly."""
        manager = CertificateManager()
        assert manager.ca_cert_path.name == "ca.crt"
        assert manager.ca_key_path.name == "ca.key"
        assert manager.crl_path.name == "crl.pem"
        assert manager.revoked_serials_path.name == "revoked_serials.txt"


def test_app_creation():
    """Test that the FastAPI app is created correctly."""
    from certbox.app import create_app
    
    test_app = create_app()
    assert test_app.title == "Certbox"
    assert test_app.description == "X.509 Certificate Management Service"


def test_python_version_compatibility():
    """Test that we're running on a compatible Python version."""
    import sys
    
    # Test that we're running Python 3.8 or higher
    assert sys.version_info >= (3, 8)
    
    # Test that we support up to Python 3.12 (as per setup.py)
    assert sys.version_info < (3, 13)


def test_required_modules_import():
    """Test that all required modules can be imported."""
    try:
        import fastapi
        import uvicorn
        import cryptography
        import pydantic_settings
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import required module: {e}")


# Simple integration tests without network dependencies
class TestAPIIntegration:
    """Integration tests that don't require a running server."""
    
    @pytest.fixture
    def mock_cert_manager(self):
        """Mock certificate manager for testing."""
        with patch('certbox.api.routes.cert_manager') as mock:
            mock.create_client_certificate.return_value = {
                "username": "test_user",
                "serial_number": "12345",
                "status": "created"
            }
            mock.revoke_certificate.return_value = {
                "username": "test_user", 
                "status": "revoked"
            }
            mock.renew_certificate.return_value = {
                "username": "test_user",
                "serial_number": "67890",
                "old_serial_revoked": "12345"
            }
            mock.get_crl.return_value = b"-----BEGIN X509 CRL-----\ntest_data\n-----END X509 CRL-----"
            yield mock
    
    def test_certificate_creation_logic(self, mock_cert_manager):
        """Test certificate creation logic."""
        from certbox.api.routes import create_certificate
        import asyncio
        
        result = asyncio.run(create_certificate("test_user", authenticated=True))
        assert result["username"] == "test_user"
        assert "serial_number" in result
        mock_cert_manager.create_client_certificate.assert_called_once_with("test_user")
    
    def test_certificate_revocation_logic(self, mock_cert_manager):
        """Test certificate revocation logic."""
        from certbox.api.routes import revoke_certificate
        import asyncio
        
        result = asyncio.run(revoke_certificate("test_user", authenticated=True))
        assert result["username"] == "test_user"
        assert result["status"] == "revoked"
        mock_cert_manager.revoke_certificate.assert_called_once_with("test_user")

    def test_certificate_renewal_logic(self, mock_cert_manager):
        """Test certificate renewal logic."""
        from certbox.api.routes import renew_certificate
        import asyncio
        
        # Test renewal with revoke old (default)
        result = asyncio.run(renew_certificate("test_user", keep_old=False, authenticated=True))
        assert result["username"] == "test_user"
        assert "serial_number" in result
        mock_cert_manager.renew_certificate.assert_called_once_with("test_user", revoke_old=True)
        
        # Reset mock and test keep old
        mock_cert_manager.reset_mock()
        result = asyncio.run(renew_certificate("test_user", keep_old=True, authenticated=True))
        mock_cert_manager.renew_certificate.assert_called_once_with("test_user", revoke_old=False)

    def test_authentication_integration(self):
        """Test that authentication module integrates properly."""
        from certbox.auth import verify_token
        import asyncio
        
        # Test that authentication can be called
        result = asyncio.run(verify_token(None))
        assert result is True  # Should be True when no token is configured


if __name__ == "__main__":
    pytest.main([__file__])
