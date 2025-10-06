#!/usr/bin/env python3
"""
Certbox - X.509 Certificate Management Service
Entry point for backward compatibility.
"""

import os
import uvicorn

from certbox.app import app

if __name__ == "__main__":
    # Get host and port from environment variables or use defaults
    host = os.getenv("CERTBOX_HOST", "0.0.0.0")
    port = int(os.getenv("CERTBOX_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)