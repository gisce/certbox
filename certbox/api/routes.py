"""
API route definitions for Certbox.
"""

from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import FileResponse

from ..core import CertificateManager
from ..config import config
from ..auth import verify_token

# Initialize certificate manager
cert_manager = CertificateManager()

# Create router
router = APIRouter()


@router.post("/certs/{username}")
async def create_certificate(username: str, authenticated: bool = Depends(verify_token)):
    """Create a new client certificate for the specified user."""
    try:
        result = cert_manager.create_client_certificate(username)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create certificate: {str(e)}")


@router.post("/revoke/{username}")
async def revoke_certificate(username: str, authenticated: bool = Depends(verify_token)):
    """Revoke a client certificate for the specified user."""
    try:
        result = cert_manager.revoke_certificate(username)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke certificate: {str(e)}")


@router.post("/renew/{username}")
async def renew_certificate(username: str, keep_old: bool = False, authenticated: bool = Depends(verify_token)):
    """Renew a client certificate for the specified user."""
    try:
        result = cert_manager.renew_certificate(username, revoke_old=not keep_old)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to renew certificate: {str(e)}")


@router.get("/crl.pem")
async def get_crl():
    """Get the Certificate Revocation List in PEM format."""
    try:
        crl_data = cert_manager.get_crl()
        return Response(
            content=crl_data,
            media_type="application/x-pem-file",
            headers={"Content-Disposition": "attachment; filename=crl.pem"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get CRL: {str(e)}")


@router.get("/certs/{username}/pfx")
async def download_pfx(username: str, authenticated: bool = Depends(verify_token)):
    """Download the PFX file for a user's certificate."""
    # Get directories for the default configuration
    from ..config import get_directories
    directories = get_directories(config)
    pfx_path = directories['clients_dir'] / f"{username}.pfx"
    
    if not pfx_path.exists():
        raise HTTPException(status_code=404, detail=f"PFX file for user '{username}' not found")
    
    return FileResponse(
        path=pfx_path,
        filename=f"{username}.pfx",
        media_type="application/x-pkcs12"
    )


@router.get("/config")
async def get_config():
    """Get the current certificate configuration."""
    config_dict = {
        "cert_validity_days": config.cert_validity_days,
        "ca_validity_days": config.ca_validity_days,
        "key_size": config.key_size,
        "country": config.country,
        "state_province": config.state_province,
        "locality": config.locality,
        "organization": config.organization,
        "ca_common_name": config.ca_common_name
    }
    
    # Include root_dir if it's configured
    if config.root_dir:
        config_dict["root_dir"] = config.root_dir
    
    return config_dict


@router.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Certbox",
        "description": "X.509 Certificate Management Service",
        "version": "1.0.0",
        "endpoints": {
            "create_certificate": "POST /certs/{username}",
            "revoke_certificate": "POST /revoke/{username}",
            "renew_certificate": "POST /renew/{username}",
            "get_crl": "GET /crl.pem",
            "download_pfx": "GET /certs/{username}/pfx",
            "get_config": "GET /config"
        }
    }