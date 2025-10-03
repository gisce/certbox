# Certbox

![Logo](art/logo.png)

Certbox is a lightweight REST API for managing client X.509 certificates using a custom CA. It supports issuing and revoking certificates, exporting .pfx files for browser use, and generating a CRL for mTLS setups with Nginx. Designed for simple, internal certificate workflows.

## Features

- **Certificate Authority Management**: Automatically creates and manages a local CA
- **Client Certificate Issuance**: Create X.509 client certificates for users
- **Certificate Revocation**: Revoke certificates and update CRL
- **PFX Export**: Export certificates as .pfx files for browser installation
- **Certificate Revocation List (CRL)**: Generate CRL for Nginx mTLS setups
- **Structured Storage**: Organized directory structure for certificates and keys

## Installation

### Method 1: Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/gisce/certbox.git
cd certbox
```

2. Build and run with Docker:
```bash
# Build the Docker image
docker build -t certbox .

# Run the service
docker run -p 8000:8000 \
  -v certbox_ca:/app/ca \
  -v certbox_crts:/app/crts \
  -v certbox_private:/app/private \
  -v certbox_clients:/app/clients \
  certbox
```

3. Or use Docker Compose:
```bash
docker compose up -d
```

The service will be available at `http://localhost:8000`.

### Method 2: Local Python

1. Clone the repository:
```bash
git clone https://github.com/gisce/certbox.git
cd certbox
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the service:
```bash
python main.py
```

The service will start on `http://localhost:8000` and automatically create a CA if one doesn't exist.

## Directory Structure

The service creates and manages the following directory structure:

```
certbox/
├── ca/                 # Certificate Authority files
│   ├── ca.crt         # CA certificate
│   ├── ca.key         # CA private key
│   ├── crl.pem        # Certificate Revocation List
│   └── revoked_serials.txt # List of revoked certificate serials
├── crts/              # Client certificates
├── private/           # Client private keys
├── clients/           # PFX files for browser installation
└── requests/          # Certificate signing requests (future use)
```

### Docker Volumes

When using Docker, these directories are mounted as persistent volumes:

- `certbox_ca` - Contains the CA certificate, key and CRL
- `certbox_crts` - Contains client certificates  
- `certbox_private` - Contains client private keys
- `certbox_clients` - Contains PFX files for browser installation
- `certbox_requests` - Contains certificate signing requests

These volumes ensure data persistence across container restarts.

## API Endpoints

### Root Endpoint
- **GET /** - Service information and available endpoints

### Certificate Management
- **POST /certs/{username}** - Create a new client certificate
- **POST /revoke/{username}** - Revoke a client certificate
- **GET /certs/{username}/pfx** - Download PFX file for browser installation

### Certificate Revocation List
- **GET /crl.pem** - Download the current CRL in PEM format

### Configuration
- **GET /config** - View current configuration settings

## Usage Examples

### Create a certificate
```bash
curl -X POST http://localhost:8000/certs/alice
```

Response:
```json
{
    "username": "alice",
    "serial_number": "12345678901234567890",
    "valid_from": "2023-10-03T08:12:29",
    "valid_until": "2024-10-03T08:12:29",
    "certificate_path": "/path/to/crts/alice.crt",
    "private_key_path": "/path/to/private/alice.key",
    "pfx_path": "/path/to/clients/alice.pfx"
}
```

### Download PFX file for browser installation
```bash
curl -O -J http://localhost:8000/certs/alice/pfx
```

### Revoke a certificate
```bash
curl -X POST http://localhost:8000/revoke/alice
```

Response:
```json
{
    "username": "alice",
    "serial_number": "12345678901234567890",
    "revoked_at": "2023-10-03T08:15:00.123456",
    "status": "revoked"
}
```

### Download CRL for Nginx configuration
```bash
curl -O http://localhost:8000/crl.pem
```

## Nginx mTLS Configuration

To use the generated certificates and CRL with Nginx for mutual TLS authentication:

```nginx
server {
    listen 443 ssl;
    server_name example.com;
    
    # Server certificate
    ssl_certificate /path/to/server.crt;
    ssl_certificate_key /path/to/server.key;
    
    # Client certificate verification
    ssl_client_certificate /path/to/certbox/ca/ca.crt;
    ssl_verify_client on;
    ssl_crl /path/to/certbox/ca/crl.pem;
    
    location / {
        # Your application
        proxy_pass http://backend;
        
        # Pass client certificate info to backend
        proxy_set_header X-Client-DN $ssl_client_s_dn;
        proxy_set_header X-Client-Verify $ssl_client_verify;
    }
}
```

## Testing

Run the included test suite:

```bash
python test_api.py
```

## Configuration

The service can be configured using environment variables. All settings have sensible defaults:

### Certificate Settings
- `CERTBOX_CERT_VALIDITY_DAYS` - Client certificate validity in days (default: 365)
- `CERTBOX_CA_VALIDITY_DAYS` - CA certificate validity in days (default: 3650)
- `CERTBOX_KEY_SIZE` - RSA key size in bits (default: 2048)

### Certificate Subject Information
- `CERTBOX_COUNTRY` - Country code (default: "ES")
- `CERTBOX_STATE_PROVINCE` - State or province (default: "Catalonia")
- `CERTBOX_LOCALITY` - City or locality (default: "Girona")
- `CERTBOX_ORGANIZATION` - Organization name (default: "GISCE-TI")
- `CERTBOX_CA_COMMON_NAME` - CA common name (default: "GISCE-TI CA")

### Example Usage
```bash
# Run with custom configuration
CERTBOX_ORGANIZATION="My Company" \
CERTBOX_LOCALITY="Barcelona" \
CERTBOX_CERT_VALIDITY_DAYS=730 \
python main.py
```

### Configuration Endpoint
You can view the current configuration by accessing the `/config` endpoint:

```bash
curl http://localhost:8000/config
```

Response:
```json
{
    "cert_validity_days": 365,
    "ca_validity_days": 3650,
    "key_size": 2048,
    "country": "ES",
    "state_province": "Catalonia",
    "locality": "Girona",
    "organization": "GISCE-TI",
    "ca_common_name": "GISCE-TI CA"
}
```

## Security Notes

- The CA private key is stored unencrypted for simplicity
- This service is designed for internal use cases
- For production use, consider implementing proper authentication and authorization
- Regularly backup the CA directory

## License

MIT License - see LICENSE file for details.
