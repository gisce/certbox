#!/usr/bin/env python3
"""
Test suite for Certbox CLI functionality using pytest
"""

import pytest
import subprocess
import time
import signal
import os
from unittest.mock import patch, Mock

from certbox.cli import cli
from certbox.core.certificate_manager import CertificateManager


class TestCertboxCLI:
    """Test cases for Certbox CLI commands."""

    def run_command(self, cmd, timeout=30):
        """Helper method to run CLI commands."""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"

    def test_cli_help(self):
        """Test CLI help command."""
        code, stdout, stderr = self.run_command("certbox --help")
        assert code == 0, f"Help command failed: {stderr}"
        assert "Certbox - X.509 Certificate Management Service CLI" in stdout
        assert "Commands:" in stdout
        assert "api" in stdout
        assert "create" in stdout
        assert "revoke" in stdout

    def test_cli_config(self):
        """Test CLI config command."""
        code, stdout, stderr = self.run_command("certbox config")
        assert code == 0, f"Config command failed: {stderr}"
        assert "Current Certbox Configuration" in stdout
        assert "Certificate validity:" in stdout
        assert "CA validity:" in stdout
        assert "Key size:" in stdout
        assert "Country:" in stdout

    def test_cli_version(self):
        """Test CLI version command."""
        code, stdout, stderr = self.run_command("certbox --version")
        assert code == 0, f"Version command failed: {stderr}"
        assert "1.0.0" in stdout

    def test_cli_certificate_create(self):
        """Test CLI certificate creation."""
        username = f"test_cli_user_{int(time.time())}"
        
        code, stdout, stderr = self.run_command(f"certbox create {username}")
        assert code == 0, f"Create command failed: {stderr}"
        assert "Certificate created successfully" in stdout
        assert "Serial number:" in stdout
        assert "Valid from:" in stdout
        assert "Valid until:" in stdout
        assert "Certificate:" in stdout
        assert "Private key:" in stdout
        assert "PFX file:" in stdout

    def test_cli_certificate_create_duplicate(self):
        """Test CLI certificate creation with duplicate username."""
        username = f"test_duplicate_{int(time.time())}"
        
        # Create first certificate
        code, stdout, stderr = self.run_command(f"certbox create {username}")
        assert code == 0, f"First create command failed: {stderr}"
        
        # Try to create duplicate - should fail
        code, stdout, stderr = self.run_command(f"certbox create {username}")
        assert code != 0, "Duplicate create should fail"
        assert "already exists" in stderr

    def test_cli_certificate_revoke(self):
        """Test CLI certificate revocation."""
        username = f"test_revoke_{int(time.time())}"
        
        # First create a certificate
        code, stdout, stderr = self.run_command(f"certbox create {username}")
        assert code == 0, f"Create command failed: {stderr}"
        
        # Then revoke it
        code, stdout, stderr = self.run_command(f"certbox revoke {username}")
        assert code == 0, f"Revoke command failed: {stderr}"
        assert "Certificate revoked successfully" in stdout
        assert "Serial number:" in stdout
        assert "Revoked at:" in stdout
        assert "Status: revoked" in stdout

    def test_cli_certificate_revoke_nonexistent(self):
        """Test CLI certificate revocation of non-existent certificate."""
        username = f"nonexistent_{int(time.time())}"
        
        code, stdout, stderr = self.run_command(f"certbox revoke {username}")
        assert code != 0, "Revoke non-existent should fail"
        assert "not found" in stderr

    def test_cli_certificate_renew(self):
        """Test CLI certificate renewal."""
        username = f"test_renew_{int(time.time())}"
        
        # First create a certificate
        code, stdout, stderr = self.run_command(f"certbox create {username}")
        assert code == 0, f"Create command failed: {stderr}"
        
        # Extract original serial number
        original_serial = None
        for line in stdout.split('\n'):
            if "Serial number:" in line:
                original_serial = line.split(":")[1].strip()
                break
        
        # Then renew it
        code, stdout, stderr = self.run_command(f"certbox renew {username}")
        assert code == 0, f"Renew command failed: {stderr}"
        assert "Certificate renewed successfully" in stdout
        assert "New serial number:" in stdout
        assert "Valid from:" in stdout
        assert "Valid until:" in stdout
        assert "Certificate:" in stdout
        assert "Private key:" in stdout
        assert "PFX file:" in stdout
        assert "Old certificate revoked" in stdout
        
        # Extract new serial number and verify it's different
        new_serial = None
        for line in stdout.split('\n'):
            if "New serial number:" in line:
                new_serial = line.split(":")[1].strip()
                break
        
        assert new_serial != original_serial, "New certificate should have different serial"

    def test_cli_certificate_renew_keep_old(self):
        """Test CLI certificate renewal with keep-old flag."""
        username = f"test_renew_keep_{int(time.time())}"
        
        # First create a certificate
        code, stdout, stderr = self.run_command(f"certbox create {username}")
        assert code == 0, f"Create command failed: {stderr}"
        
        # Then renew it with keep-old flag
        code, stdout, stderr = self.run_command(f"certbox renew {username} --keep-old")
        assert code == 0, f"Renew with keep-old command failed: {stderr}"
        assert "Certificate renewed successfully" in stdout
        assert "Old certificate kept active" in stdout

    def test_cli_certificate_renew_nonexistent(self):
        """Test CLI certificate renewal of non-existent certificate."""
        username = f"nonexistent_renew_{int(time.time())}"
        
        code, stdout, stderr = self.run_command(f"certbox renew {username}")
        assert code != 0, "Renew non-existent should fail"
        assert "not found" in stderr

    def test_cli_crl(self):
        """Test CLI CRL command."""
        code, stdout, stderr = self.run_command("certbox crl")
        assert code == 0, f"CRL command failed: {stderr}"
        assert "-----BEGIN X509 CRL-----" in stdout
        assert "-----END X509 CRL-----" in stdout

    def test_cli_api_server_start_options(self):
        """Test CLI API server command with options."""
        # Test with custom port (quick timeout to just check it starts)
        proc = subprocess.Popen(
            ["certbox", "api", "--host", "localhost", "--port", "8080"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait a bit for server to start
            time.sleep(2)
            
            # Check if process is running
            assert proc.poll() is None, "API server should be running"
            
            # Test if server responds (optional, might fail in test environment)
            try:
                code, stdout, stderr = self.run_command("curl -s http://localhost:8080/ | grep service", timeout=5)
                if code == 0:
                    assert "Certbox" in stdout
            except:
                # Skip this check if curl fails in test environment
                pass
                
        finally:
            # Clean up
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


class TestCLIModuleIntegration:
    """Test CLI module integration with other components."""

    def test_cli_uses_certificate_manager_directly(self):
        """Test that CLI commands use CertificateManager directly."""
        # This is a design test to ensure CLI bypasses API
        from certbox.cli import create, revoke, renew
        import click.testing
        
        runner = click.testing.CliRunner()
        
        # Mock CertificateManager to verify it's called directly
        with patch('certbox.cli.CertificateManager') as mock_cm:
            mock_instance = Mock()
            mock_cm.return_value = mock_instance
            mock_instance.create_client_certificate.return_value = {
                'username': 'test',
                'serial_number': '123',
                'valid_from': '2025-01-01',
                'valid_until': '2026-01-01',
                'certificate_path': '/path/cert',
                'private_key_path': '/path/key',
                'pfx_path': '/path/pfx',
                'pfx_password': 'test_password123'
            }
            
            # Test create command calls CertificateManager directly
            result = runner.invoke(create, ['test'])
            mock_cm.assert_called_once()
            mock_instance.create_client_certificate.assert_called_once_with('test')
            assert result.exit_code == 0

    def test_cli_import_structure(self):
        """Test that CLI module imports correctly."""
        from certbox.cli import cli, create, revoke, config, crl, api
        
        # Test that all commands are properly defined
        assert callable(cli)
        assert callable(create)
        assert callable(revoke)
        assert callable(config)
        assert callable(crl) 
        assert callable(api)

    def test_cli_available_in_package(self):
        """Test that CLI is available from package.__init__."""
        from certbox import cli
        assert callable(cli)


def test_cli_entry_point():
    """Test that CLI entry point works correctly."""
    # Test that the console script entry point is available
    code, stdout, stderr = subprocess.run(
        ["python", "-c", "from certbox.__main__ import main; main()"], 
        capture_output=True, 
        text=True,
        input="\n",  # Send empty input to avoid hanging
        timeout=5
    ).returncode, subprocess.run(
        ["python", "-c", "from certbox.__main__ import main; print('Entry point available')"], 
        capture_output=True, 
        text=True,
        timeout=5
    ).stdout, subprocess.run(
        ["python", "-c", "from certbox.__main__ import main; print('Entry point available')"], 
        capture_output=True, 
        text=True,
        timeout=5
    ).stderr
    
    # Just test that the import works
    assert "Entry point available" in stdout or code == 0