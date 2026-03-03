from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date

from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def hub(request: Request):
    conn = get_db()

    total_base = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]
    total_digitales = conn.execute("SELECT COUNT(*) FROM exp_digitales").fetchone()[0]

    hoy = date.today().isoformat()
    prox_sala = conn.execute(
        "SELECT fecha, franja, titulo, estado FROM sala_agenda WHERE fecha >= ? ORDER BY fecha, franja LIMIT 1",
        (hoy,)
    ).fetchone()

    conn.close()

    return templates.TemplateResponse("portal.html", {
        "request": request,
        "total_base": total_base,
        "total_digitales": total_digitales,
        "prox_sala": dict(prox_sala) if prox_sala else None,
    })
