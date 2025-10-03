#!/usr/bin/env python3
"""
Certbox - X.509 Certificate Management Service
A FastAPI service for managing client certificates with a local CA.
"""

import os
import datetime
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12

app = FastAPI(
    title="Certbox",
    description="X.509 Certificate Management Service",
    version="1.0.0"
)

@dataclass
class CertConfig:
    """Configuration for certificate generation."""
    # Validity periods
    cert_validity_days: int = int(os.getenv("CERTBOX_CERT_VALIDITY_DAYS", "365"))
    ca_validity_days: int = int(os.getenv("CERTBOX_CA_VALIDITY_DAYS", "3650"))
    
    # Key configuration
    key_size: int = int(os.getenv("CERTBOX_KEY_SIZE", "2048"))
    
    # Certificate subject information
    country: str = os.getenv("CERTBOX_COUNTRY", "ES")
    state_province: str = os.getenv("CERTBOX_STATE_PROVINCE", "Catalonia")
    locality: str = os.getenv("CERTBOX_LOCALITY", "Girona")
    organization: str = os.getenv("CERTBOX_ORGANIZATION", "GISCE-TI")
    ca_common_name: str = os.getenv("CERTBOX_CA_COMMON_NAME", "GISCE-TI CA")

# Global configuration instance
config = CertConfig()

# Legacy constants for backward compatibility
CERT_VALIDITY_DAYS = config.cert_validity_days
CA_VALIDITY_DAYS = config.ca_validity_days
KEY_SIZE = config.key_size

# Directory paths
BASE_DIR = Path(__file__).parent
CA_DIR = BASE_DIR / "ca"
CRTS_DIR = BASE_DIR / "crts"
PRIVATE_DIR = BASE_DIR / "private"
CLIENTS_DIR = BASE_DIR / "clients"
REQUESTS_DIR = BASE_DIR / "requests"

# Ensure directories exist
for directory in [CA_DIR, CRTS_DIR, PRIVATE_DIR, CLIENTS_DIR, REQUESTS_DIR]:
    directory.mkdir(exist_ok=True)

class CertificateManager:
    """Manages X.509 certificates and CA operations."""
    
    def __init__(self):
        self.ca_cert_path = CA_DIR / "ca.crt"
        self.ca_key_path = CA_DIR / "ca.key"
        self.crl_path = CA_DIR / "crl.pem"
        self.revoked_serials_path = CA_DIR / "revoked_serials.txt"
        
        # Initialize CA if it doesn't exist
        if not self.ca_cert_path.exists() or not self.ca_key_path.exists():
            self._create_ca()
    
    def _create_ca(self):
        """Create a new Certificate Authority."""
        # Generate CA private key
        ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=config.key_size,
        )
        
        # Create CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, config.country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, config.state_province),
            x509.NameAttribute(NameOID.LOCALITY_NAME, config.locality),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, config.organization),
            x509.NameAttribute(NameOID.COMMON_NAME, config.ca_common_name),
        ])
        
        ca_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            ca_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=config.ca_validity_days)
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                key_encipherment=False,
                key_agreement=False,
                data_encipherment=False,
                content_commitment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(ca_key, hashes.SHA256())
        
        # Save CA certificate and key
        with open(self.ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(self.ca_key_path, "wb") as f:
            f.write(ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Create initial empty CRL
        self._generate_crl()
    
    def _load_ca(self):
        """Load CA certificate and private key."""
        with open(self.ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())
        
        with open(self.ca_key_path, "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), password=None)
        
        return ca_cert, ca_key
    
    def _get_revoked_serials(self):
        """Get list of revoked certificate serial numbers."""
        if not self.revoked_serials_path.exists():
            return set()
        
        with open(self.revoked_serials_path, "r") as f:
            return set(int(line.strip()) for line in f if line.strip())
    
    def _add_revoked_serial(self, serial_number: int):
        """Add a serial number to the revoked list."""
        revoked_serials = self._get_revoked_serials()
        revoked_serials.add(serial_number)
        
        with open(self.revoked_serials_path, "w") as f:
            for serial in sorted(revoked_serials):
                f.write(f"{serial}\n")
    
    def create_client_certificate(self, username: str) -> Dict[str, Any]:
        """Create a client certificate for the given username."""
        # Check if certificate already exists
        cert_path = CRTS_DIR / f"{username}.crt"
        key_path = PRIVATE_DIR / f"{username}.key"
        pfx_path = CLIENTS_DIR / f"{username}.pfx"
        
        if cert_path.exists():
            raise HTTPException(status_code=409, detail=f"Certificate for user '{username}' already exists")
        
        # Load CA
        ca_cert, ca_key = self._load_ca()
        
        # Generate client private key
        client_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=config.key_size,
        )
        
        # Create client certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, config.country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, config.state_province),
            x509.NameAttribute(NameOID.LOCALITY_NAME, config.locality),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, config.organization),
            x509.NameAttribute(NameOID.COMMON_NAME, username),
        ])
        
        client_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            client_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=config.cert_validity_days)
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(client_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                key_agreement=False,
                data_encipherment=False,
                content_commitment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(ca_key, hashes.SHA256())
        
        # Save client certificate and key
        with open(cert_path, "wb") as f:
            f.write(client_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(key_path, "wb") as f:
            f.write(client_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Create PFX file for browser installation
        pfx_data = pkcs12.serialize_key_and_certificates(
            name=username.encode('utf-8'),
            key=client_key,
            cert=client_cert,
            cas=[ca_cert],
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(pfx_path, "wb") as f:
            f.write(pfx_data)
        
        return {
            "username": username,
            "serial_number": str(client_cert.serial_number),
            "valid_from": client_cert.not_valid_before.isoformat(),
            "valid_until": client_cert.not_valid_after.isoformat(),
            "certificate_path": str(cert_path),
            "private_key_path": str(key_path),
            "pfx_path": str(pfx_path)
        }
    
    def revoke_certificate(self, username: str) -> Dict[str, Any]:
        """Revoke a client certificate."""
        cert_path = CRTS_DIR / f"{username}.crt"
        
        if not cert_path.exists():
            raise HTTPException(status_code=404, detail=f"Certificate for user '{username}' not found")
        
        # Load the certificate to get its serial number
        with open(cert_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        
        # Add to revoked serials
        self._add_revoked_serial(cert.serial_number)
        
        # Regenerate CRL
        self._generate_crl()
        
        return {
            "username": username,
            "serial_number": str(cert.serial_number),
            "revoked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "revoked"
        }
    
    def _generate_crl(self):
        """Generate Certificate Revocation List."""
        ca_cert, ca_key = self._load_ca()
        revoked_serials = self._get_revoked_serials()
        
        # Create CRL builder
        crl_builder = x509.CertificateRevocationListBuilder()
        crl_builder = crl_builder.issuer_name(ca_cert.subject)
        crl_builder = crl_builder.last_update(datetime.datetime.now(datetime.timezone.utc))
        crl_builder = crl_builder.next_update(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
        
        # Add revoked certificates
        for serial in revoked_serials:
            revoked_cert = x509.RevokedCertificateBuilder().serial_number(
                serial
            ).revocation_date(
                datetime.datetime.now(datetime.timezone.utc)
            ).build()
            crl_builder = crl_builder.add_revoked_certificate(revoked_cert)
        
        # Sign CRL
        crl = crl_builder.sign(ca_key, hashes.SHA256())
        
        # Save CRL
        with open(self.crl_path, "wb") as f:
            f.write(crl.public_bytes(serialization.Encoding.PEM))
    
    def get_crl(self) -> bytes:
        """Get the current Certificate Revocation List."""
        if not self.crl_path.exists():
            self._generate_crl()
        
        with open(self.crl_path, "rb") as f:
            return f.read()

# Initialize certificate manager
cert_manager = CertificateManager()

@app.post("/certs/{username}")
async def create_certificate(username: str):
    """Create a new client certificate for the specified user."""
    try:
        result = cert_manager.create_client_certificate(username)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create certificate: {str(e)}")

@app.post("/revoke/{username}")
async def revoke_certificate(username: str):
    """Revoke a client certificate for the specified user."""
    try:
        result = cert_manager.revoke_certificate(username)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke certificate: {str(e)}")

@app.get("/crl.pem")
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

@app.get("/certs/{username}/pfx")
async def download_pfx(username: str):
    """Download the PFX file for a user's certificate."""
    pfx_path = CLIENTS_DIR / f"{username}.pfx"
    
    if not pfx_path.exists():
        raise HTTPException(status_code=404, detail=f"PFX file for user '{username}' not found")
    
    return FileResponse(
        path=pfx_path,
        filename=f"{username}.pfx",
        media_type="application/x-pkcs12"
    )

@app.get("/config")
async def get_config():
    """Get the current certificate configuration."""
    return {
        "cert_validity_days": config.cert_validity_days,
        "ca_validity_days": config.ca_validity_days,
        "key_size": config.key_size,
        "country": config.country,
        "state_province": config.state_province,
        "locality": config.locality,
        "organization": config.organization,
        "ca_common_name": config.ca_common_name
    }

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Certbox",
        "description": "X.509 Certificate Management Service",
        "version": "1.0.0",
        "endpoints": {
            "create_certificate": "POST /certs/{username}",
            "revoke_certificate": "POST /revoke/{username}",
            "get_crl": "GET /crl.pem",
            "download_pfx": "GET /certs/{username}/pfx",
            "get_config": "GET /config"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)