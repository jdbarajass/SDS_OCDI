from fastapi.templating import Jinja2Templates


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
    t = Jinja2Templates(directory=directory)
    t.env.filters["fmt_fecha"] = _fmt_fecha
    return t
