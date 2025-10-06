#!/bin/sh

# Generate self-signed certificate for testing if it doesn't exist
if [ ! -f /etc/ssl/certs/nginx-selfsigned.crt ]; then
    echo "Generating self-signed certificate for nginx..."
    apk add --no-cache openssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/nginx-selfsigned.key \
        -out /etc/ssl/certs/nginx-selfsigned.crt \
        -subj '/C=ES/ST=Catalonia/L=Girona/O=GISCE-TI/CN=localhost'
    echo "Certificate generated successfully."
else
    echo "Certificate already exists."
fi

# Start nginx
echo "Starting nginx..."
nginx -g 'daemon off;'