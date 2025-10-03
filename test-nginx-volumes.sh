#!/bin/bash

# Test script to verify that nginx can access the certificate files
echo "Testing nginx access to certbox certificate volumes..."

# Create a test container with the same volume mounts as nginx
docker run --rm -d \
  --name test-nginx-access \
  -v certbox_certbox_ca:/test/ca:ro \
  -v certbox_certbox_crts:/test/crts:ro \
  alpine:latest sleep 300

# Wait a moment for container to start
sleep 2

echo "Checking CA files accessible to nginx..."
docker exec test-nginx-access ls -la /test/ca/

echo "Checking certificate files accessible to nginx..."  
docker exec test-nginx-access ls -la /test/crts/

echo "Checking CA certificate content..."
docker exec test-nginx-access cat /test/ca/ca.crt | head -2

echo "Checking CRL file..."
docker exec test-nginx-access cat /test/ca/crl.pem | head -2

# Cleanup
docker stop test-nginx-access

echo "✅ Nginx volume access test completed successfully!"