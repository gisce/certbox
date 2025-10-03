"""
CLI interface for Certbox - X.509 Certificate Management Service.
"""

import click
import uvicorn
import json
from typing import Optional
from fastapi import HTTPException

from .core import CertificateManager
from .app import app
from .config import config as certbox_config, create_config, CertConfig


# Global variable to store the current configuration
current_config: Optional[CertConfig] = None


@click.group()
@click.version_option(version="1.0.0", prog_name="certbox")
@click.option('--config', 'config_file', help='Path to configuration file')
def cli(config_file: Optional[str] = None):
    """Certbox - X.509 Certificate Management Service CLI"""
    global current_config
    if config_file:
        current_config = create_config(config_file)
    else:
        current_config = certbox_config


def get_cert_manager() -> CertificateManager:
    """Get a CertificateManager instance with the current configuration."""
    return CertificateManager(current_config)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind the API server to')
@click.option('--port', default=8000, help='Port to bind the API server to')
def api(host: str, port: int):
    """Start the Certbox API server."""
    click.echo(f"Starting Certbox API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.argument('username')
def create(username: str):
    """Create a new client certificate for the specified username."""
    try:
        cert_manager = get_cert_manager()
        result = cert_manager.create_client_certificate(username)
        
        click.echo(f"✓ Certificate created successfully for user: {username}")
        click.echo(f"  Serial number: {result['serial_number']}")
        click.echo(f"  Valid from: {result['valid_from']}")
        click.echo(f"  Valid until: {result['valid_until']}")
        click.echo(f"  Certificate: {result['certificate_path']}")
        click.echo(f"  Private key: {result['private_key_path']}")
        click.echo(f"  PFX file: {result['pfx_path']}")
        
    except HTTPException as e:
        click.echo(f"❌ Error creating certificate: {e.detail}", err=True)
        raise click.ClickException(e.detail)
    except Exception as e:
        click.echo(f"❌ Error creating certificate: {str(e)}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.argument('username')
def revoke(username: str):
    """Revoke a client certificate for the specified username."""
    try:
        cert_manager = get_cert_manager()
        result = cert_manager.revoke_certificate(username)
        
        click.echo(f"✓ Certificate revoked successfully for user: {username}")
        click.echo(f"  Serial number: {result['serial_number']}")
        click.echo(f"  Revoked at: {result['revoked_at']}")
        click.echo(f"  Status: {result['status']}")
        
    except HTTPException as e:
        click.echo(f"❌ Error revoking certificate: {e.detail}", err=True)
        raise click.ClickException(e.detail)
    except Exception as e:
        click.echo(f"❌ Error revoking certificate: {str(e)}", err=True)
        raise click.ClickException(str(e))


@cli.command()
def config():
    """Show current Certbox configuration."""
    config_instance = current_config or certbox_config
    click.echo("Current Certbox Configuration:")
    click.echo(f"  Certificate validity: {config_instance.cert_validity_days} days")
    click.echo(f"  CA validity: {config_instance.ca_validity_days} days")
    click.echo(f"  Key size: {config_instance.key_size} bits")
    click.echo(f"  Country: {config_instance.country}")
    click.echo(f"  State/Province: {config_instance.state_province}")
    click.echo(f"  Locality: {config_instance.locality}")
    click.echo(f"  Organization: {config_instance.organization}")
    click.echo(f"  CA Common Name: {config_instance.ca_common_name}")
    if config_instance.root_dir:
        click.echo(f"  Root Directory: {config_instance.root_dir}")


@cli.command()
def crl():
    """Get the Certificate Revocation List."""
    try:
        cert_manager = get_cert_manager()
        crl_data = cert_manager.get_crl()
        
        # Output the CRL to stdout so it can be redirected to a file
        click.echo(crl_data.decode('utf-8'), nl=False)
        
    except Exception as e:
        click.echo(f"❌ Error getting CRL: {str(e)}", err=True)
        raise click.ClickException(str(e))


if __name__ == '__main__':
    cli()