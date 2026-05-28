"""Herramientas PDF — procesamiento local, sin almacenamiento persistente."""

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, HTMLResponse
from pathlib import Path
from typing import List
import io, tempfile, os, shutil, re

from app.template_utils import make_templates
from app.auth_utils import tpl

router = APIRouter(prefix="/pdf-tools", tags=["pdf_tools"])
templates = make_templates(str(Path(__file__).parent.parent / "templates"))

# ── Detección de dependencias opcionales ──────────────────────────────────────

try:
    from pypdf import PdfReader, PdfWriter
    PYPDF_OK = True
except ImportError:
    PYPDF_OK = False

try:
    from pdf2docx import Converter as Pdf2DocxConverter
    PDF2DOCX_OK = True
except ImportError:
    PDF2DOCX_OK = False

try:
    import docx2pdf as _docx2pdf
    DOCX2PDF_OK = True
except ImportError:
    DOCX2PDF_OK = False

try:
    import fitz  # PyMuPDF
    FITZ_OK = True
except ImportError:
    FITZ_OK = False


# ── Página principal ──────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def pdf_tools_main(request: Request, msg: str = ""):
    return templates.TemplateResponse("pdf_tools.html", tpl(request, None,
        msg=msg,
        pypdf_ok=PYPDF_OK,
        pdf2docx_ok=PDF2DOCX_OK,
        docx2pdf_ok=DOCX2PDF_OK,
        fitz_ok=FITZ_OK,
    ))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_pypdf():
    if not PYPDF_OK:
        raise HTTPException(status_code=501,
            detail="La librería 'pypdf' no está instalada. Ejecute: pip install pypdf")

def _parse_paginas(s: str, total: int) -> list:
    """'1-3, 5, 7-9' → [0,1,2,4,6,7,8] (índice 0). Vacío → todas las páginas."""
    s = s.strip()
    if not s:
        return list(range(total))
    result = []
    for parte in s.split(","):
        parte = parte.strip()
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", parte)
        if m:
            a, b = int(m.group(1)) - 1, int(m.group(2)) - 1
            result.extend(range(max(0, a), min(total, b + 1)))
        elif re.fullmatch(r"\d+", parte):
            p = int(parte) - 1
            if 0 <= p < total:
                result.append(p)
    return sorted(set(result))

def _file_stem(filename: str) -> str:
    stem = Path(filename or "documento").stem
    return re.sub(r"[^\w\-]", "_", stem)

def _pdf_resp(buf: io.BytesIO, name: str) -> Response:
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'},
    )


# ── Info del PDF (conteo de páginas para UI) ──────────────────────────────────

@router.post("/info")
async def pdf_info(archivo: UploadFile = File(...)):
    if not PYPDF_OK:
        return Response(content="?", media_type="text/plain")
    try:
        content = await archivo.read()
        reader = PdfReader(io.BytesIO(content))
        return Response(content=str(len(reader.pages)), media_type="text/plain")
    except Exception:
        return Response(content="?", media_type="text/plain")


# ── 1. Unir PDFs ──────────────────────────────────────────────────────────────

@router.post("/unir")
async def pdf_unir(archivos: List[UploadFile] = File(...)):
    _require_pypdf()
    if not archivos:
        raise HTTPException(400, "Suba al menos dos archivos PDF.")
    writer = PdfWriter()
    for f in archivos:
        content = await f.read()
        try:
            reader = PdfReader(io.BytesIO(content))
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            raise HTTPException(400, f"Error en '{f.filename}': {e}")
    buf = io.BytesIO()
    writer.write(buf)
    return _pdf_resp(buf, "PDF_Unido")


# ── 2. Extraer páginas ────────────────────────────────────────────────────────

@router.post("/extraer")
async def pdf_extraer(
    archivo: UploadFile = File(...),
    paginas: str = Form(...),
):
    _require_pypdf()
    content = await archivo.read()
    reader = PdfReader(io.BytesIO(content))
    total = len(reader.pages)
    selected = _parse_paginas(paginas, total)
    if not selected:
        raise HTTPException(400, "El rango de páginas no coincide con el documento.")
    writer = PdfWriter()
    for p in selected:
        writer.add_page(reader.pages[p])
    buf = io.BytesIO()
    writer.write(buf)
    return _pdf_resp(buf, _file_stem(archivo.filename) + "_extraido")


# ── 3. Eliminar páginas ───────────────────────────────────────────────────────

@router.post("/eliminar-paginas")
async def pdf_eliminar_paginas(
    archivo: UploadFile = File(...),
    paginas: str = Form(...),
):
    _require_pypdf()
    content = await archivo.read()
    reader = PdfReader(io.BytesIO(content))
    total = len(reader.pages)
    eliminar = set(_parse_paginas(paginas, total))
    if not eliminar:
        raise HTTPException(400, "No se encontraron páginas válidas para eliminar.")
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i not in eliminar:
            writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return _pdf_resp(buf, _file_stem(archivo.filename) + "_editado")


# ── 4. Comprimir PDF ──────────────────────────────────────────────────────────

@router.post("/comprimir")
async def pdf_comprimir(archivo: UploadFile = File(...)):
    _require_pypdf()
    content = await archivo.read()
    original_size = len(content)

    compressed = None
    if FITZ_OK:
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            compressed = doc.tobytes(garbage=4, deflate=True,
                                     deflate_images=True, deflate_fonts=True)
            doc.close()
        except Exception:
            compressed = None

    if not compressed:
        reader = PdfReader(io.BytesIO(content))
        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        compressed = buf.getvalue()

    compressed_size = len(compressed)
    reduccion = round(max(0.0, (1 - compressed_size / original_size) * 100), 1) if original_size else 0.0

    return Response(
        content=compressed,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_file_stem(archivo.filename)}_comprimido.pdf"',
            "X-Original-KB": str(original_size // 1024),
            "X-Compressed-KB": str(compressed_size // 1024),
            "X-Reduccion-Pct": str(reduccion),
            "Access-Control-Expose-Headers": "X-Original-KB,X-Compressed-KB,X-Reduccion-Pct",
        },
    )


# ── 5. Rotar páginas ──────────────────────────────────────────────────────────

@router.post("/rotar")
async def pdf_rotar(
    archivo: UploadFile = File(...),
    grados: int = Form(90),
    paginas: str = Form(""),
):
    _require_pypdf()
    if grados not in (90, 180, 270):
        raise HTTPException(400, "Los grados deben ser 90, 180 o 270.")
    content = await archivo.read()
    reader = PdfReader(io.BytesIO(content))
    total = len(reader.pages)
    rotar_idx = set(_parse_paginas(paginas, total))
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in rotar_idx:
            page.rotate(grados)
        writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return _pdf_resp(buf, _file_stem(archivo.filename) + "_rotado")


# ── 6. PDF → Word ─────────────────────────────────────────────────────────────

@router.post("/pdf-a-word")
async def pdf_a_word(archivo: UploadFile = File(...)):
    if not PDF2DOCX_OK:
        raise HTTPException(501,
            "La librería 'pdf2docx' no está instalada. Ejecute: pip install pdf2docx")
    content = await archivo.read()
    tmpdir = tempfile.mkdtemp(prefix="ocdi_pdf_")
    try:
        pdf_path  = os.path.join(tmpdir, "input.pdf")
        docx_path = os.path.join(tmpdir, "output.docx")
        with open(pdf_path, "wb") as fh:
            fh.write(content)
        cv = Pdf2DocxConverter(pdf_path)
        cv.convert(docx_path)
        cv.close()
        with open(docx_path, "rb") as fh:
            docx_bytes = fh.read()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{_file_stem(archivo.filename)}.docx"'},
    )


# ── 7. Word → PDF ─────────────────────────────────────────────────────────────

@router.post("/word-a-pdf")
async def word_a_pdf(archivo: UploadFile = File(...)):
    if not DOCX2PDF_OK:
        raise HTTPException(501,
            "La librería 'docx2pdf' no está instalada. Ejecute: pip install docx2pdf")
    content = await archivo.read()
    tmpdir = tempfile.mkdtemp(prefix="ocdi_word_")
    try:
        docx_path = os.path.join(tmpdir, "input.docx")
        pdf_path  = os.path.join(tmpdir, "output.pdf")
        with open(docx_path, "wb") as fh:
            fh.write(content)
        _docx2pdf.convert(docx_path, pdf_path)
        with open(pdf_path, "rb") as fh:
            pdf_bytes = fh.read()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_file_stem(archivo.filename)}.pdf"'},
    )


# ── 8. Agregar Sello / Marca de agua ─────────────────────────────────────────

@router.post("/sello")
async def pdf_sello(
    archivo: UploadFile = File(...),
    texto: str = Form(...),
    paginas: str = Form(""),
    posicion: str = Form("inferior-derecha"),
    color: str = Form("gris"),
):
    if not FITZ_OK:
        raise HTTPException(501,
            "La librería 'PyMuPDF' no está instalada. Ejecute: pip install PyMuPDF")

    colores = {
        "rojo":  (0.8, 0.0, 0.0),
        "azul":  (0.0, 0.2, 0.7),
        "gris":  (0.45, 0.45, 0.45),
        "negro": (0.0, 0.0, 0.0),
        "verde": (0.0, 0.5, 0.1),
    }
    rgb = colores.get(color, (0.45, 0.45, 0.45))

    content = await archivo.read()
    doc = fitz.open(stream=content, filetype="pdf")
    total = len(doc)
    paginas_idx = _parse_paginas(paginas, total)

    for i in paginas_idx:
        page = doc[i]
        r = page.rect
        es_centro = posicion == "centro"
        fontsize = 36 if es_centro else 13

        if posicion == "superior-izquierda":
            punto = fitz.Point(28, 42)
        elif posicion == "superior-derecha":
            punto = fitz.Point(r.width - 28, 42)
        elif posicion == "inferior-izquierda":
            punto = fitz.Point(28, r.height - 28)
        elif posicion == "centro":
            punto = fitz.Point(r.width / 4, r.height / 2)
        else:
            punto = fitz.Point(r.width - 28, r.height - 28)

        page.insert_text(
            punto, texto,
            fontsize=fontsize,
            color=rgb,
            rotate=45 if es_centro else 0,
        )

    pdf_bytes = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_file_stem(archivo.filename)}_sellado.pdf"'},
    )
