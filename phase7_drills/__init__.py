"""
phase7_drills — Bootcamp drill runner (procedural board generation + API + UI).

Mount in main.py:

    from phase7_drills import api_router as drills_api_router
    from phase7_drills import page_router as drills_page_router
    app.include_router(drills_api_router)
    app.include_router(drills_page_router)

Apply schema once at deploy time (run as a script, NOT as `-m`, so the
FastAPI route imports below don't get pulled in):

    python3 phase7_drills/schema_sql.py --apply

Why lazy: the schema_sql migration script needs to run from a deploy env that
may not have FastAPI installed (or may run before deps are synced). The
routes module imports FastAPI eagerly. We defer the import so `import
phase7_drills.schema_sql` works on a bare Python install.
"""

from __future__ import annotations


def __getattr__(name):
    if name in ("api_router", "page_router"):
        from .routes import api_router, page_router
        return {"api_router": api_router, "page_router": page_router}[name]
    raise AttributeError(f"module 'phase7_drills' has no attribute {name!r}")


__all__ = ["api_router", "page_router"]
