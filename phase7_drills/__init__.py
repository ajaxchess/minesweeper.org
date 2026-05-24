"""
phase7_drills — Bootcamp drill runner (procedural board generation + API + UI).

Mount in main.py:

    from phase7_drills.routes import api_router as drills_api_router
    from phase7_drills.routes import page_router as drills_page_router
    app.include_router(drills_api_router)
    app.include_router(drills_page_router)

Apply schema once at deploy time:

    python3 -m phase7_drills.schema_sql --apply
"""

from .routes import api_router, page_router

__all__ = ["api_router", "page_router"]
