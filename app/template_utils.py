from fastapi.templating import Jinja2Templates


class _CompatJinja2Templates(Jinja2Templates):
    """Starlette >=0.47 eliminó por completo el shim de compatibilidad para
    la firma antigua `TemplateResponse(name, context)` (antes solo emitía un
    DeprecationWarning; ahora directamente rompe con un TypeError críptico
    de Jinja2, porque el dict de contexto termina posicionalmente en el
    parámetro `name`). Todo el proyecto (73 call sites en 19 routers) usa esa
    firma antigua, así que se restaura aquí — en un solo lugar — en vez de
    reescribir cada llamada."""

    def TemplateResponse(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.pop("context", None) or {}
            request = context.get("request") if isinstance(context, dict) else None
            resto = args[2:]
            return super().TemplateResponse(request, name, context, *resto, **kwargs)
        return super().TemplateResponse(*args, **kwargs)


def _fmt_fecha(value) -> str:
    """Convert YYYY-MM-DD or YYYY-MM-DD HH:MM:SS to DD/MM/YYYY [HH:MM:SS]."""
    if not value:
        return ''
    s = str(value).strip()
    if len(s) >= 10 and s[4] == '-' and s[7] == '-':
        result = f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
        if len(s) > 10 and s[10] == ' ':
            result += s[10:]
        return result
    return s


def make_templates(directory: str) -> Jinja2Templates:
    t = _CompatJinja2Templates(directory=directory)
    t.env.filters["fmt_fecha"] = _fmt_fecha
    return t
