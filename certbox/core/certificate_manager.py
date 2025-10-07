"""
Certificate management module for Certbox.
"""

import datetime
import secrets
import string
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from fastapi import HTTPException
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12

from ..config import config, get_directories, CertConfig


class CertificateManager:
    """Manages X.509 certificates and CA operations."""
    
    def __init__(self, config_instance: Optional[CertConfig] = None):
        # Use provided config or default global config
        self.config = config_instance or config
        
        # Get directories based on configuration
        self.directories = get_directories(self.config)
        
        self.ca_cert_path = self.directories['ca_dir'] / "ca.crt"
        self.ca_key_path = self.directories['ca_dir'] / "ca.key"
        self.crl_path = self.directories['ca_dir'] / "crl.pem"
        self.revoked_serials_path = self.directories['ca_dir'] / "revoked_serials.txt"
        
        # Initialize CA if it doesn't exist
        if not self.ca_cert_path.exists() or not self.ca_key_path.exists():
            self._create_ca()
    
    def _create_ca(self):
        """Create a new Certificate Authority."""
        # Generate CA private key
        ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.config.key_size,
        )
        
        # Create CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, self.config.country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, self.config.state_province),
            x509.NameAttribute(NameOID.LOCALITY_NAME, self.config.locality),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.config.organization),
            x509.NameAttribute(NameOID.COMMON_NAME, self.config.ca_common_name),
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
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=self.config.ca_validity_days)
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
    
    def _generate_pfx_password(self) -> str:
        """Generate a secure random password for PFX files."""
        # Create a character set that includes letters, digits, and some safe special characters
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        # Generate a cryptographically secure random password
        password = ''.join(secrets.choice(alphabet) for _ in range(self.config.pfx_password_length))
        return password
    
    def _generate_and_save_certificate(self, username: str, cert_path: Path, key_path: Path, pfx_path: Path) -> Tuple[x509.Certificate, str]:
        """Generate and save a client certificate and private key."""
        # Load CA
        ca_cert, ca_key = self._load_ca()
        
        # Generate client private key
        client_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.config.key_size,
        )
        
        # Create client certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, self.config.country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, self.config.state_province),
            x509.NameAttribute(NameOID.LOCALITY_NAME, self.config.locality),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.config.organization),
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
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=self.config.cert_validity_days)
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
        
        # Generate secure password for PFX file
        pfx_password = self._generate_pfx_password()
        
        # Create PFX file for browser installation
        pfx_data = pkcs12.serialize_key_and_certificates(
            name=username.encode('utf-8'),
            key=client_key,
            cert=client_cert,
            cas=[ca_cert],
            encryption_algorithm=serialization.BestAvailableEncryption(pfx_password.encode('utf-8'))
        )
        
        with open(pfx_path, "wb") as f:
            f.write(pfx_data)
        
        return client_cert, pfx_password

    def create_client_certificate(self, username: str) -> Dict[str, Any]:
        """Create a client certificate for the given username."""
        # Check if certificate already exists
        cert_path = self.directories['crts_dir'] / f"{username}.crt"
        key_path = self.directories['private_dir'] / f"{username}.key"
        pfx_path = self.directories['clients_dir'] / f"{username}.pfx"
        
        if cert_path.exists():
            raise HTTPException(status_code=409, detail=f"Certificate for user '{username}' already exists")
        
        client_cert, pfx_password = self._generate_and_save_certificate(username, cert_path, key_path, pfx_path)
        
        return {
            "username": username,
            "serial_number": str(client_cert.serial_number),
            "valid_from": client_cert.not_valid_before_utc.isoformat(),
            "valid_until": client_cert.not_valid_after_utc.isoformat(),
            "certificate_path": str(cert_path),
            "private_key_path": str(key_path),
            "pfx_path": str(pfx_path),
            "pfx_password": pfx_password
        }
    
    def revoke_certificate(self, username: str) -> Dict[str, Any]:
        """Revoke a client certificate."""
        cert_path = self.directories['crts_dir'] / f"{username}.crt"
        
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
    
    def renew_certificate(self, username: str, revoke_old: bool = True) -> Dict[str, Any]:
        """Renew a client certificate for the given username.
        
        Args:
            username: The username for which to renew the certificate
            revoke_old: Whether to revoke the old certificate (default: True)
            
        Returns:
            Dict containing certificate information
        """
        # Check if certificate exists
        cert_path = self.directories['crts_dir'] / f"{username}.crt"
        key_path = self.directories['private_dir'] / f"{username}.key"
        pfx_path = self.directories['clients_dir'] / f"{username}.pfx"
        
        if not cert_path.exists():
            raise HTTPException(status_code=404, detail=f"Certificate for user '{username}' not found")
        
        old_serial = None
        if revoke_old:
            # Load the old certificate to get its serial number
            with open(cert_path, "rb") as f:
                old_cert = x509.load_pem_x509_certificate(f.read())
            old_serial = old_cert.serial_number
        
        # Generate and save new certificate (overwriting existing files)
        client_cert, pfx_password = self._generate_and_save_certificate(username, cert_path, key_path, pfx_path)
        
        # Revoke old certificate if requested
        if revoke_old and old_serial:
            self._add_revoked_serial(old_serial)
            self._generate_crl()
        
        return {
            "username": username,
            "serial_number": str(client_cert.serial_number),
            "valid_from": client_cert.not_valid_before_utc.isoformat(),
            "valid_until": client_cert.not_valid_after_utc.isoformat(),
            "certificate_path": str(cert_path),
            "private_key_path": str(key_path),
            "pfx_path": str(pfx_path),
            "pfx_password": pfx_password,
            "old_serial_revoked": str(old_serial) if revoke_old and old_serial else None
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
    
    def get_certificate_info(self, username: str) -> Dict[str, Any]:
        """Get information about an existing certificate."""
        cert_path = self.directories['crts_dir'] / f"{username}.crt"
        key_path = self.directories['private_dir'] / f"{username}.key"
        pfx_path = self.directories['clients_dir'] / f"{username}.pfx"
        
        if not cert_path.exists():
            raise HTTPException(status_code=404, detail=f"Certificate for user '{username}' not found")
        
        # Load the certificate to get its information
        with open(cert_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        
        # Check if certificate is revoked
        revoked_serials = self._get_revoked_serials()
        is_revoked = cert.serial_number in revoked_serials
        
        # Get subject information
        subject_info = {}
        for attribute in cert.subject:
            if attribute.oid == NameOID.COMMON_NAME:
                subject_info['common_name'] = attribute.value
            elif attribute.oid == NameOID.ORGANIZATION_NAME:
                subject_info['organization'] = attribute.value
            elif attribute.oid == NameOID.COUNTRY_NAME:
                subject_info['country'] = attribute.value
            elif attribute.oid == NameOID.STATE_OR_PROVINCE_NAME:
                subject_info['state_province'] = attribute.value
            elif attribute.oid == NameOID.LOCALITY_NAME:
                subject_info['locality'] = attribute.value
        
        # Get issuer information
        issuer_info = {}
        for attribute in cert.issuer:
            if attribute.oid == NameOID.COMMON_NAME:
                issuer_info['common_name'] = attribute.value
            elif attribute.oid == NameOID.ORGANIZATION_NAME:
                issuer_info['organization'] = attribute.value
        
        # Determine certificate status
        now = datetime.datetime.now(datetime.timezone.utc)
        if is_revoked:
            status = "revoked"
        elif now < cert.not_valid_before_utc:
            status = "not_yet_valid"
        elif now > cert.not_valid_after_utc:
            status = "expired"
        else:
            status = "valid"
        
        return {
            "username": username,
            "serial_number": str(cert.serial_number),
            "subject": subject_info,
            "issuer": issuer_info,
            "valid_from": cert.not_valid_before_utc.isoformat(),
            "valid_until": cert.not_valid_after_utc.isoformat(),
            "status": status,
            "is_revoked": is_revoked,
            "certificate_path": str(cert_path),
            "private_key_path": str(key_path) if key_path.exists() else None,
            "pfx_path": str(pfx_path) if pfx_path.exists() else None,
            "key_usage": self._get_key_usage_info(cert),
            "extensions": self._get_extension_info(cert)
        }
    
    def _get_key_usage_info(self, cert: x509.Certificate) -> Dict[str, bool]:
        """Extract key usage information from certificate."""
        try:
            key_usage = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
            result = {
                "digital_signature": key_usage.digital_signature,
                "key_encipherment": key_usage.key_encipherment,
                "key_agreement": key_usage.key_agreement,
                "key_cert_sign": key_usage.key_cert_sign,
                "crl_sign": key_usage.crl_sign,
                "content_commitment": key_usage.content_commitment,
                "data_encipherment": key_usage.data_encipherment,
            }
            
            # These properties are only valid when key_agreement is True
            if key_usage.key_agreement:
                result["encipher_only"] = key_usage.encipher_only
                result["decipher_only"] = key_usage.decipher_only
            
            return result
        except x509.ExtensionNotFound:
            return {}
    
    def _get_extension_info(self, cert: x509.Certificate) -> Dict[str, Any]:
        """Extract extension information from certificate."""
        extensions = {}
        
        try:
            basic_constraints = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS).value
            extensions["basic_constraints"] = {
                "ca": basic_constraints.ca,
                "path_length": basic_constraints.path_length
            }
        except x509.ExtensionNotFound:
            pass
        
        try:
            extended_key_usage = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
            extensions["extended_key_usage"] = [eku._name for eku in extended_key_usage]
        except x509.ExtensionNotFound:
            pass
        
        try:
            subject_key_id = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_KEY_IDENTIFIER).value
            extensions["subject_key_identifier"] = subject_key_id.digest.hex()
        except x509.ExtensionNotFound:
            pass
        
        try:
            authority_key_id = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_KEY_IDENTIFIER).value
            extensions["authority_key_identifier"] = authority_key_id.key_identifier.hex() if authority_key_id.key_identifier else None
        except x509.ExtensionNotFound:
            pass
        
        return extensions