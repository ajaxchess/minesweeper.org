"""
Phase 5 Bootcamp frontend — main.py changes
============================================

Two additions to ~/git/minesweeper.org/main.py to serve the bootcamp page.

  1. Route handler — renders templates/bootcamp.html (place near the other
     page routes around line 3490, next to quests_page).
  2. (Optional) Navigation link — add 'bootcamp' to the navigation menu in
     base.html if the codebase has a nav-links list. Not strictly required
     for the deploy; the page is reachable at /bootcamp directly.
"""

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1 — Add the route handler
# Location: main.py, near other page routes (e.g. line ~3490, by quests_page)
# ─────────────────────────────────────────────────────────────────────────────

# Imports — all already present in main.py. Listed here for clarity:
# from fastapi import Request
# from fastapi.responses import HTMLResponse
# from main import templates, get_current_user, get_lang, get_t


@app.get("/bootcamp", response_class=HTMLResponse)
async def bootcamp_page(request: Request):
    """
    Renders the Bootcamp coaching page. All player-specific data is fetched
    client-side from /api/bootcamp/diagnosis after page load, so this handler
    only needs to provide the template skeleton + translation strings.
    """
    return templates.TemplateResponse(request, "bootcamp.html", {
        "mode": "bootcamp",
        "user": get_current_user(request),
        "lang": get_lang(request),
        "t": get_t(request),
    })


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2 (optional) — Navigation link
#
# If templates/base.html contains a navigation menu (look for a list of
# <a> tags pointing to /quests, /variants, etc.), add an entry for Bootcamp.
# Example pattern based on quests:
#
#   <a href="/bootcamp" class="nav-link {% if mode == 'bootcamp' %}nav-active{% endif %}">
#     {{ t.nav_bootcamp | default("Bootcamp") }}
#   </a>
#
# The 'mode' variable comes from the route handler above. Skip this if your
# navigation is data-driven from a Python list — in that case, add 'bootcamp'
# to that list with the appropriate icon.
# ─────────────────────────────────────────────────────────────────────────────
