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
from .config import config as certbox_config


@click.group()
@click.version_option(version="1.0.0", prog_name="certbox")
def cli():
    """Certbox - X.509 Certificate Management Service CLI"""
    pass


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
        cert_manager = CertificateManager()
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
        cert_manager = CertificateManager()
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
    click.echo("Current Certbox Configuration:")
    click.echo(f"  Certificate validity: {certbox_config.cert_validity_days} days")
    click.echo(f"  CA validity: {certbox_config.ca_validity_days} days")
    click.echo(f"  Key size: {certbox_config.key_size} bits")
    click.echo(f"  Country: {certbox_config.country}")
    click.echo(f"  State/Province: {certbox_config.state_province}")
    click.echo(f"  Locality: {certbox_config.locality}")
    click.echo(f"  Organization: {certbox_config.organization}")
    click.echo(f"  CA Common Name: {certbox_config.ca_common_name}")


@cli.command()
def crl():
    """Get the Certificate Revocation List."""
    try:
        cert_manager = CertificateManager()
        crl_data = cert_manager.get_crl()
        
        # Output the CRL to stdout so it can be redirected to a file
        click.echo(crl_data.decode('utf-8'), nl=False)
        
    except Exception as e:
        click.echo(f"❌ Error getting CRL: {str(e)}", err=True)
        raise click.ClickException(str(e))


if __name__ == '__main__':
    cli()