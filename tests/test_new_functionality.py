#!/usr/bin/env python3
"""
Test suite for the new configurable root directory and config file functionality.
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch

from certbox.config import create_config, get_directories, CertConfig
from certbox.core.certificate_manager import CertificateManager


class TestConfigurableRootDir:
    """Test cases for configurable root directory functionality."""

    def test_default_config_behavior(self):
        """Test that default configuration behaves as before."""
        config = create_config()
        directories = get_directories(config)
        
        # Default should use project directory
        assert 'ca' in str(directories['ca_dir'])
        assert 'crts' in str(directories['crts_dir'])
        assert 'private' in str(directories['private_dir'])
        assert 'clients' in str(directories['clients_dir'])
        assert 'requests' in str(directories['requests_dir'])
    
    def test_custom_root_dir_via_config_object(self):
        """Test custom root directory via configuration object."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config with custom root directory
            config = CertConfig(root_dir=temp_dir)
            directories = get_directories(config)
            
            # Verify paths use custom root directory
            assert str(directories['ca_dir']) == str(Path(temp_dir) / "ca")
            assert str(directories['crts_dir']) == str(Path(temp_dir) / "crts")
            assert str(directories['private_dir']) == str(Path(temp_dir) / "private")
            assert str(directories['clients_dir']) == str(Path(temp_dir) / "clients")
            assert str(directories['requests_dir']) == str(Path(temp_dir) / "requests")
            
            # Verify directories are created
            assert directories['ca_dir'].exists()
            assert directories['crts_dir'].exists()
            assert directories['private_dir'].exists()
            assert directories['clients_dir'].exists()
            assert directories['requests_dir'].exists()
    
    def test_custom_root_dir_via_config_file(self):
        """Test custom root directory via configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary config file
            config_file = Path(temp_dir) / "test.env"
            cert_dir = Path(temp_dir) / "certs"
            
            config_file.write_text(f"CERTBOX_ROOT_DIR={cert_dir}\nCERTBOX_ORGANIZATION=Test Org")
            
            # Load config from file
            config = create_config(str(config_file))
            directories = get_directories(config)
            
            # Verify custom settings
            assert config.root_dir == str(cert_dir)
            assert config.organization == "Test Org"
            assert str(directories['ca_dir']) == str(cert_dir / "ca")
    
    def test_certificate_manager_with_custom_config(self):
        """Test CertificateManager with custom configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = CertConfig(
                root_dir=temp_dir,
                organization="Test Company",
                locality="Test City"
            )
            
            cert_manager = CertificateManager(config)
            
            # Verify manager uses custom configuration
            assert cert_manager.config.organization == "Test Company"
            assert cert_manager.config.locality == "Test City"
            assert str(cert_manager.ca_cert_path).startswith(temp_dir)
            assert str(cert_manager.ca_key_path).startswith(temp_dir)
            
            # Verify CA files are created in custom directory
            assert cert_manager.ca_cert_path.exists()
            assert cert_manager.ca_key_path.exists()
    
    def test_expanduser_in_root_dir(self):
        """Test that ~ is expanded in root directory paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock expanduser to return our temp directory
            with patch('pathlib.Path.expanduser') as mock_expanduser:
                mock_expanduser.return_value = Path(temp_dir)
                
                config = CertConfig(root_dir="~/test_certs")
                directories = get_directories(config)
                
                # Verify expanduser was called and path is resolved
                mock_expanduser.assert_called()
                assert str(directories['ca_dir']).startswith(temp_dir)
    
    def test_config_includes_root_dir_when_set(self):
        """Test that configuration includes root_dir when it's set."""
        config = CertConfig(root_dir="/custom/path")
        
        # Test the config dict includes root_dir
        assert config.root_dir == "/custom/path"
    
    def test_config_empty_root_dir_uses_default(self):
        """Test that empty root_dir falls back to default behavior."""
        config = CertConfig(root_dir="")
        directories = get_directories(config)
        
        # Should fall back to project directory
        assert 'certbox' in str(directories['base_dir'])


if __name__ == '__main__':
    pytest.main([__file__, "-v"])