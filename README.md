# Certbox

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
# Run just the certbox service
docker compose up -d certbox

# Run with nginx example (requires server certificates)
docker compose --profile nginx up -d
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

These volumes ensure data persistence across container restarts and enable nginx to access the certificate files for mTLS authentication.

## API Endpoints

### Root Endpoint
- **GET /** - Service information and available endpoints

### Certificate Management
- **POST /certs/{username}** - Create a new client certificate
- **POST /revoke/{username}** - Revoke a client certificate
- **GET /certs/{username}/pfx** - Download PFX file for browser installation

### Certificate Revocation List
- **GET /crl.pem** - Download the current CRL in PEM format

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

### Docker Setup for Nginx Integration

When using Docker, the certificate files are automatically available to nginx through shared volumes:

```yaml
# docker-compose.yml excerpt showing nginx integration
nginx:
  image: nginx:alpine
  ports:
    - "443:443"
  volumes:
    # Mount certificate directories from certbox service
    - certbox_ca:/etc/nginx/certs/ca:ro
    - certbox_crts:/etc/nginx/certs/crts:ro
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - certbox
```

### Nginx Configuration

To use the generated certificates and CRL with Nginx for mutual TLS authentication:

```nginx
server {
    listen 443 ssl;
    server_name example.com;
    
    # Server certificate (you need to provide these)
    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;
    
    # Client certificate verification using Certbox CA
    ssl_client_certificate /etc/nginx/certs/ca/ca.crt;
    ssl_verify_client on;
    ssl_crl /etc/nginx/certs/ca/crl.pem;
    
    location / {
        # Proxy to Certbox API
        proxy_pass http://certbox:8000;
        
        # Pass client certificate info to backend
        proxy_set_header X-Client-DN $ssl_client_s_dn;
        proxy_set_header X-Client-Verify $ssl_client_verify;
    }
}
```

**Note**: For the nginx example to work, you need to provide your own server certificate and key files.

## Testing

Run the included test suite:

```bash
python test_api.py
```

## Configuration

The service uses the following default settings:

- **Certificate Validity**: 365 days
- **CA Validity**: 3650 days (10 years)
- **Key Size**: 2048 bits
- **Hash Algorithm**: SHA-256

These can be modified in the `main.py` file if needed.

## Security Notes

- The CA private key is stored unencrypted for simplicity
- This service is designed for internal use cases
- For production use, consider implementing proper authentication and authorization
- Regularly backup the CA directory

## License

MIT License - see LICENSE file for details.
