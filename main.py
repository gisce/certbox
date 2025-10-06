#!/usr/bin/env python3
"""
Certbox - X.509 Certificate Management Service
Entry point for backward compatibility.
"""

import uvicorn

from certbox.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)