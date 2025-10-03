"""
Configuration module for Certbox.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class CertConfig(BaseSettings):
    """Configuration for certificate generation."""
    # Validity periods
    cert_validity_days: int = 365
    ca_validity_days: int = 3650
    
    # Key configuration
    key_size: int = 2048
    
    # Certificate subject information
    country: str = "ES"
    state_province: str = "Catalonia"
    locality: str = "Girona"
    organization: str = "GISCE-TI"
    ca_common_name: str = "GISCE-TI CA"

    class Config:
        env_prefix = "CERTBOX_"
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global configuration instance
config = CertConfig()

# Legacy constants for backward compatibility
CERT_VALIDITY_DAYS = config.cert_validity_days
CA_VALIDITY_DAYS = config.ca_validity_days
KEY_SIZE = config.key_size

# Directory paths
BASE_DIR = Path(__file__).parent.parent
CA_DIR = BASE_DIR / "ca"
CRTS_DIR = BASE_DIR / "crts"
PRIVATE_DIR = BASE_DIR / "private"
CLIENTS_DIR = BASE_DIR / "clients"
REQUESTS_DIR = BASE_DIR / "requests"

# Ensure directories exist
for directory in [CA_DIR, CRTS_DIR, PRIVATE_DIR, CLIENTS_DIR, REQUESTS_DIR]:
    directory.mkdir(exist_ok=True)