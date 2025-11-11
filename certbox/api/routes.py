"""
API route definitions for Certbox.
"""

from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import FileResponse

from ..core import CertificateManager
from ..config import config, get_active_config
from ..auth import verify_token
from .. import __version__


def get_cert_manager() -> CertificateManager:
    """Get certificate manager instance with active config."""
    return CertificateManager(get_active_config())


# Create router
router = APIRouter()


@router.post("/certs/{username}")
async def create_certificate(
    username: str,
    authenticated: bool = Depends(verify_token),
    cert_manager: CertificateManager = Depends(get_cert_manager)
):
    """Create a new client certificate for the specified user."""
    try:
        result = cert_manager.create_client_certificate(username)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create certificate: {str(e)}")


@router.post("/revoke/{username}")
async def revoke_certificate(
    username: str,
    authenticated: bool = Depends(verify_token),
    cert_manager: CertificateManager = Depends(get_cert_manager)
):
    """Revoke a client certificate for the specified user."""
    try:
        result = cert_manager.revoke_certificate(username)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke certificate: {str(e)}")


@router.post("/renew/{username}")
async def renew_certificate(
    username: str,
    keep_old: bool = False,
    authenticated: bool = Depends(verify_token),
    cert_manager: CertificateManager = Depends(get_cert_manager)
):
    """Renew a client certificate for the specified user."""
    try:
        result = cert_manager.renew_certificate(username, revoke_old=not keep_old)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to renew certificate: {str(e)}")


@router.get("/crl.pem")
async def get_crl(cert_manager: CertificateManager = Depends(get_cert_manager)):
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


@router.get("/certs/{username}/info")
async def get_certificate_info(
    username: str,
    authenticated: bool = Depends(verify_token),
    cert_manager: CertificateManager = Depends(get_cert_manager)
):
    """Get information about a certificate for the specified user."""
    try:
        result = cert_manager.get_certificate_info(username)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get certificate info: {str(e)}")


@router.get("/certs/{username}/pfx")
async def download_pfx(
    username: str,
    authenticated: bool = Depends(verify_token),
    cert_manager: CertificateManager = Depends(get_cert_manager)
):
    """Download the PFX file for a user's certificate."""
    from ..config import get_directories
    directories = get_directories(cert_manager.config)
    pfx_path = directories['clients_dir'] / f"{username}.pfx"
    
    if not pfx_path.exists():
        raise HTTPException(status_code=404, detail=f"PFX file for user '{username}' not found")
    
    return FileResponse(
        path=pfx_path,
        filename=f"{username}.pfx",
        media_type="application/x-pkcs12"
    )


@router.get("/config")
async def get_config(
    authenticated: bool = Depends(verify_token),
    cert_manager: CertificateManager = Depends(get_cert_manager)
):
    """Get the current certificate configuration."""
    from ..config import get_directories
    
    active_config = cert_manager.config
    directories = get_directories(active_config)
    
    config_dict = {
        "cert_validity_days": active_config.cert_validity_days,
        "ca_validity_days": active_config.ca_validity_days,
        "key_size": active_config.key_size,
        "country": active_config.country,
        "state_province": active_config.state_province,
        "locality": active_config.locality,
        "organization": active_config.organization,
        "ca_common_name": active_config.ca_common_name
    }
    
    # Include root_dir if it's configured
    if active_config.root_dir:
        config_dict["root_dir"] = active_config.root_dir
    
    # Include directories
    config_dict["directories"] = {
        "base_dir": str(directories['base_dir']),
        "ca_dir": str(directories['ca_dir']),
        "crts_dir": str(directories['crts_dir']),
        "private_dir": str(directories['private_dir']),
        "clients_dir": str(directories['clients_dir']),
        "requests_dir": str(directories['requests_dir'])
    }
    
    return config_dict


@router.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Certbox",
        "description": "X.509 Certificate Management Service",
        "version": __version__,
        "endpoints": {
            "create_certificate": "POST /certs/{username}",
            "revoke_certificate": "POST /revoke/{username}",
            "renew_certificate": "POST /renew/{username}",
            "get_certificate_info": "GET /certs/{username}/info",
            "get_crl": "GET /crl.pem",
            "download_pfx": "GET /certs/{username}/pfx",
            "get_config": "GET /config"
        }
    }