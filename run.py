#!/usr/bin/env python3
"""
Entry point for Certbox server.
"""

import uvicorn

from certbox.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)