"""
Configuration module for Certbox.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


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
    
    # Directory configuration
    root_dir: str = ""
    
    # API Authentication
    api_token: str = ""

    class Config:
        env_prefix = "CERTBOX_"
        env_file = ".env"
        env_file_encoding = "utf-8"


def create_config(config_file: Optional[str] = None) -> CertConfig:
    """Create a configuration instance with optional custom config file."""
    if config_file:
        return CertConfig(_env_file=config_file)
    return CertConfig()


def get_directories(config_instance: CertConfig):
    """Get directory paths based on configuration."""
    if config_instance.root_dir:
        base_dir = Path(config_instance.root_dir).expanduser().resolve()
    else:
        # Default to project directory for backward compatibility
        base_dir = Path(__file__).parent.parent
    
    ca_dir = base_dir / "ca"
    crts_dir = base_dir / "crts"
    private_dir = base_dir / "private"
    clients_dir = base_dir / "clients"
    requests_dir = base_dir / "requests"
    
    # Ensure directories exist
    for directory in [ca_dir, crts_dir, private_dir, clients_dir, requests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    return {
        'base_dir': base_dir,
        'ca_dir': ca_dir,
        'crts_dir': crts_dir,
        'private_dir': private_dir,
        'clients_dir': clients_dir,
        'requests_dir': requests_dir
    }


# Global configuration instance
config = CertConfig()

# Legacy constants for backward compatibility
CERT_VALIDITY_DAYS = config.cert_validity_days
CA_VALIDITY_DAYS = config.ca_validity_days
KEY_SIZE = config.key_size

# Directory paths (for backward compatibility)
directories = get_directories(config)
BASE_DIR = directories['base_dir']
CA_DIR = directories['ca_dir']
CRTS_DIR = directories['crts_dir']
PRIVATE_DIR = directories['private_dir']
CLIENTS_DIR = directories['clients_dir']
REQUESTS_DIR = directories['requests_dir']