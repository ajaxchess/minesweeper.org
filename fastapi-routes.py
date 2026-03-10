from datetime import date
from fastapi import Request
from fastapi.responses import Response, PlainTextResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap(request: Request):
    content = templates.TemplateResponse(
        "sitemap.xml",
        {"request": request, "today": date.today().isoformat()},
        media_type="application/xml",
    )
    return content


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n\n"
        "Disallow: /game/\n"
        "Disallow: /duel/room/\n"
        "Disallow: /api/\n"
        "Disallow: /ws/\n"
        "Disallow: /login\n"
        "Disallow: /logout\n"
        "Disallow: /register\n"
        "Disallow: /account/\n"
        "Disallow: /static/\n\n"
        "Sitemap: https://minesweeper.org/sitemap.xml\n"
    )
    return PlainTextResponse(content)
