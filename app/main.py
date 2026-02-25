from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import init_db
from app.routers import expedientes, importar, dashboard, seguimiento, autos

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="OCDI - Sistema de Gestión Disciplinaria",
    description="Secretaría Distrital de Salud - Oficina de Control Disciplinario Interno",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates accesibles globalmente para los routers
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(dashboard.router)
app.include_router(expedientes.router)
app.include_router(importar.router)
app.include_router(seguimiento.router)
app.include_router(autos.router)


@app.on_event("startup")
async def startup():
    init_db()
