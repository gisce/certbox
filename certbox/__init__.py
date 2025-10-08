"""
Certbox - X.509 Certificate Management Service
A FastAPI service for managing client certificates with a local CA.
"""

__version__ = "1.1.0"
__author__ = "GISCE-TI"
__email__ = "devel@gisce.net"

from .app import app
from .config import config
from .core import CertificateManager
from .cli import cli

__all__ = ["app", "config", "CertificateManager", "cli", "__version__"]