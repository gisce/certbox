"""
Test authentication functionality for Certbox API.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from certbox.auth import verify_token
from certbox.config import config


class TestAuthentication:
    """Test cases for API authentication."""
    
    @pytest.mark.asyncio
    async def test_no_token_configured_allows_access(self):
        """Test that when no token is configured, access is allowed."""
        with patch.object(config, 'api_token', ''):
            result = await verify_token(None)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_valid_token_allows_access(self):
        """Test that a valid token allows access."""
        test_token = "test-secret-token"
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=test_token)
        
        with patch.object(config, 'api_token', test_token):
            result = await verify_token(credentials)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_invalid_token_denies_access(self):
        """Test that an invalid token denies access."""
        test_token = "test-secret-token"
        wrong_token = "wrong-token"
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=wrong_token)
        
        with patch.object(config, 'api_token', test_token):
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(credentials)
            
            assert exc_info.value.status_code == 401
            assert "Invalid authentication token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_missing_credentials_denies_access(self):
        """Test that missing credentials deny access when token is configured."""
        test_token = "test-secret-token"
        
        with patch.object(config, 'api_token', test_token):
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(None)
            
            assert exc_info.value.status_code == 401
            assert "Authentication required" in exc_info.value.detail


if __name__ == "__main__":
    pytest.main([__file__])