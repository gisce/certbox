"""
Main application module for Certbox.
"""

from fastapi import FastAPI

from certbox import __version__
from certbox.api import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Certbox",
        description="X.509 Certificate Management Service",
        version=__version__
    )
    
    # Include API routes
    app.include_router(router)
    
    return app


# Create the application instance
app = create_app()