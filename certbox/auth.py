"""
Authentication module for Certbox API.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .config import config

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
    """
    Verify the API token.
    
    Args:
        credentials: The HTTP authorization credentials
        
    Returns:
        True if the token is valid
        
    Raises:
        HTTPException: If the token is invalid or missing
    """
    # If no token is configured, authentication is disabled
    if not config.api_token:
        return True
    
    # Check if credentials are provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify the token
    if credentials.credentials != config.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True