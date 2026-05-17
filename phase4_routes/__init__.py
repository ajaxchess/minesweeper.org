"""
phase4_routes — FastAPI routes that serve analyzer output to the mockup UIs.

Mount in main.py:

    from phase4_routes import router as analytics_router
    app.include_router(analytics_router)
"""

from .routes import router

__all__ = ["router"]
