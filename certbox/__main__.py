"""
Entry point for running Certbox as a module.
Usage: python -m certbox
"""

import uvicorn

from certbox.app import app


def main():
    """Main entry point for console script."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()