"""Módulo Polla Mundial FIFA 2026 — completamente independiente y removable."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from app.template_utils import make_templates
from app.auth_utils import tpl
from app.database import get_db
import random, json

router = APIRouter(prefix="/mundial", tags=["mundial"])
templates = make_templates(str(Path(__file__).parent.parent / "templates"))

# ── Participantes OCDI ─────────────────────────────────────────────────────────
PARTICIPANTES = [
    "ANDRES EDUARDO SANDOVAL MAYORGA",
    "CARLOS ALFONSO PARRA MALAVER",
    "CESAR IVAN RODRIGUEZ DAMIAN",
    "DAVID FELIPE MORALES NOGUERA",
    "JANIK HERNANDO DE LA HOZ RIOS",
    "JOSE DE JESUS BARAJAS SOTELO",
    "LUNA GICELL GUZMAN YATE",
    "MABEL GICELLA HURTADO SANCHEZ",
    "MAGDA XIMENA PAREDES LIEVANO",
    "MARA LUCIA UCROS MERLANO",
    "MARTHA PATRICIA AÑEZ MAESTRE",
    "RODOLFO CARRILLO QUINTERO",
]

# ── Grupos y equipos ───────────────────────────────────────────────────────────
GRUPOS = {
    "A": {"equipos": ["México",        "Corea del Sur", "Sudáfrica",     "Rep. Checa"],
          "flags":   ["🇲🇽",           "🇰🇷",           "🇿🇦",           "🇨🇿"]},
    "B": {"equipos": ["Canadá",        "Qatar",         "Suiza",         "Bosnia-Herz."],
          "flags":   ["🇨🇦",           "🇶🇦",           "🇨🇭",           "🇧🇦"]},
    "C": {"equipos": ["Brasil",        "Marruecos",     "Haití",         "Escocia"],
          "flags":   ["🇧🇷",           "🇲🇦",           "🇭🇹",           "🏴󠁧󠁢󠁳󠁣󠁴󠁿"]},
    "D": {"equipos": ["EE.UU.",        "Australia",     "Paraguay",      "Turquía"],
          "flags":   ["🇺🇸",           "🇦🇺",           "🇵🇾",           "🇹🇷"]},
    "E": {"equipos": ["Alemania",      "C. de Marfil",  "Ecuador",       "Curazao"],
          "flags":   ["🇩🇪",           "🇨🇮",           "🇪🇨",           "🇨🇼"]},
    "F": {"equipos": ["Países Bajos",  "Japón",         "Suecia",        "Túnez"],
          "flags":   ["🇳🇱",           "🇯🇵",           "🇸🇪",           "🇹🇳"]},
    "G": {"equipos": ["Bélgica",       "Irán",          "Egipto",        "Nueva Zelanda"],
          "flags":   ["🇧🇪",           "🇮🇷",           "🇪🇬",           "🇳🇿"]},
    "H": {"equipos": ["España",        "Arabia Saudita","Uruguay",       "Cabo Verde"],
          "flags":   ["🇪🇸",           "🇸🇦",           "🇺🇾",           "🇨🇻"]},
    "I": {"equipos": ["Francia",       "Senegal",       "Noruega",       "Irak"],
          "flags":   ["🇫🇷",           "🇸🇳",           "🇳🇴",           "🇮🇶"]},
    "J": {"equipos": ["Argentina",     "Austria",       "Argelia",       "Jordania"],
          "flags":   ["🇦🇷",           "🇦🇹",           "🇩🇿",           "🇯🇴"]},
    "K": {"equipos": ["Portugal",      "Colombia",      "Uzbekistán",    "Congo RD"],
          "flags":   ["🇵🇹",           "🇨🇴",           "🇺🇿",           "🇨🇩"]},
    "L": {"equipos": ["Inglaterra",    "Croacia",       "Ghana",         "Panamá"],
          "flags":   ["🏴󠁧󠁢󠁥󠁮󠁧󠁿",       "🇭🇷",           "🇬🇭",           "🇵🇦"]},
}

TODOS_LOS_EQUIPOS = [
    f"{GRUPOS[g]['flags'][i]} {GRUPOS[g]['equipos'][i]}"
    for g in GRUPOS for i in range(4)
]

# ── Fixture de grupos — hora Colombia (UTC-5) ──────────────────────────────────
# Horarios y marcadores verificados contra Wikipedia (2026 FIFA World Cup Group A-L,
# fuente con desfase UTC explícito por partido) el 2026-06-18. Cada hora local de
# sede se convirtió a COT (UTC-5) según su huso real: Ciudad de México/Guadalajara/
# Monterrey = UTC-6 (COT = local +1h); Toronto/Boston/NY-NJ/Filadelfia/Atlanta/Miami
# = UTC-4 EDT (COT = local −1h); Dallas/Houston/Kansas City = UTC-5 CDT (COT = local);
# Los Ángeles/San Francisco/Seattle/Vancouver = UTC-7 PDT (COT = local +2h).
# "marcador" = resultado real ("GL-GV") si el partido ya se jugó, None si no.
FIXTURE_GRUPOS = [
    # GRUPO A
    {"id":"A1","g":"A","e1":"México 🇲🇽",        "e2":"Sudáfrica 🇿🇦",       "f":"Jue 11 Jun","h":"2:00 p.m.", "s":"Azteca, Ciudad México","marcador":"2-0"},
    {"id":"A2","g":"A","e1":"Corea del Sur 🇰🇷",  "e2":"Rep. Checa 🇨🇿",       "f":"Jue 11 Jun","h":"9:00 p.m.", "s":"Akron, Guadalajara","marcador":"2-1"},
    {"id":"A3","g":"A","e1":"Rep. Checa 🇨🇿",     "e2":"Sudáfrica 🇿🇦",        "f":"Jue 18 Jun","h":"11:00 a.m.","s":"Atlanta","marcador":None},
    {"id":"A4","g":"A","e1":"México 🇲🇽",         "e2":"Corea del Sur 🇰🇷",    "f":"Jue 18 Jun","h":"8:00 p.m.", "s":"Akron, Guadalajara","marcador":None},
    {"id":"A5","g":"A","e1":"Rep. Checa 🇨🇿",     "e2":"México 🇲🇽",           "f":"Mié 24 Jun","h":"8:00 p.m.", "s":"Azteca, Ciudad México","marcador":None},
    {"id":"A6","g":"A","e1":"Sudáfrica 🇿🇦",      "e2":"Corea del Sur 🇰🇷",    "f":"Mié 24 Jun","h":"8:00 p.m.", "s":"BBVA, Monterrey","marcador":None},
    # GRUPO B
    {"id":"B1","g":"B","e1":"Canadá 🇨🇦",         "e2":"Bosnia-Herz. 🇧🇦",     "f":"Vie 12 Jun","h":"2:00 p.m.", "s":"Toronto","marcador":"1-1"},
    {"id":"B2","g":"B","e1":"Qatar 🇶🇦",           "e2":"Suiza 🇨🇭",            "f":"Sáb 13 Jun","h":"2:00 p.m.", "s":"San Francisco","marcador":"1-1"},
    {"id":"B3","g":"B","e1":"Suiza 🇨🇭",           "e2":"Bosnia-Herz. 🇧🇦",     "f":"Jue 18 Jun","h":"2:00 p.m.", "s":"Los Ángeles","marcador":None},
    {"id":"B4","g":"B","e1":"Canadá 🇨🇦",          "e2":"Qatar 🇶🇦",            "f":"Jue 18 Jun","h":"5:00 p.m.", "s":"Vancouver","marcador":None},
    {"id":"B5","g":"B","e1":"Suiza 🇨🇭",           "e2":"Canadá 🇨🇦",           "f":"Mié 24 Jun","h":"2:00 p.m.", "s":"Vancouver","marcador":None},
    {"id":"B6","g":"B","e1":"Bosnia-Herz. 🇧🇦",   "e2":"Qatar 🇶🇦",            "f":"Mié 24 Jun","h":"2:00 p.m.", "s":"Seattle","marcador":None},
    # GRUPO C
    {"id":"C1","g":"C","e1":"Brasil 🇧🇷",          "e2":"Marruecos 🇲🇦",        "f":"Sáb 13 Jun","h":"5:00 p.m.", "s":"Nueva York/NJ","marcador":"1-1"},
    {"id":"C2","g":"C","e1":"Haití 🇭🇹",           "e2":"Escocia 🏴󠁧󠁢󠁳󠁣󠁴󠁿",         "f":"Sáb 13 Jun","h":"8:00 p.m.", "s":"Boston","marcador":"0-1"},
    {"id":"C3","g":"C","e1":"Escocia 🏴󠁧󠁢󠁳󠁣󠁴󠁿",        "e2":"Marruecos 🇲🇦",        "f":"Vie 19 Jun","h":"5:00 p.m.", "s":"Boston","marcador":None},
    {"id":"C4","g":"C","e1":"Brasil 🇧🇷",          "e2":"Haití 🇭🇹",            "f":"Vie 19 Jun","h":"7:30 p.m.", "s":"Filadelfia","marcador":None},
    {"id":"C5","g":"C","e1":"Escocia 🏴󠁧󠁢󠁳󠁣󠁴󠁿",        "e2":"Brasil 🇧🇷",           "f":"Mié 24 Jun","h":"5:00 p.m.", "s":"Miami","marcador":None},
    {"id":"C6","g":"C","e1":"Marruecos 🇲🇦",       "e2":"Haití 🇭🇹",            "f":"Mié 24 Jun","h":"5:00 p.m.", "s":"Atlanta","marcador":None},
    # GRUPO D
    {"id":"D1","g":"D","e1":"EE.UU. 🇺🇸",          "e2":"Paraguay 🇵🇾",         "f":"Vie 12 Jun","h":"8:00 p.m.", "s":"Los Ángeles","marcador":"4-1"},
    {"id":"D2","g":"D","e1":"Australia 🇦🇺",        "e2":"Turquía 🇹🇷",          "f":"Sáb 13 Jun","h":"11:00 p.m.","s":"Vancouver","marcador":"2-0"},
    {"id":"D3","g":"D","e1":"EE.UU. 🇺🇸",           "e2":"Australia 🇦🇺",        "f":"Vie 19 Jun","h":"2:00 p.m.", "s":"Seattle","marcador":None},
    {"id":"D4","g":"D","e1":"Turquía 🇹🇷",          "e2":"Paraguay 🇵🇾",         "f":"Vie 19 Jun","h":"10:00 p.m.","s":"San Francisco","marcador":None},
    {"id":"D5","g":"D","e1":"Turquía 🇹🇷",          "e2":"EE.UU. 🇺🇸",           "f":"Jue 25 Jun","h":"9:00 p.m.", "s":"Los Ángeles","marcador":None},
    {"id":"D6","g":"D","e1":"Paraguay 🇵🇾",         "e2":"Australia 🇦🇺",        "f":"Jue 25 Jun","h":"9:00 p.m.", "s":"San Francisco","marcador":None},
    # GRUPO E
    {"id":"E1","g":"E","e1":"Alemania 🇩🇪",         "e2":"Curazao 🇨🇼",          "f":"Dom 14 Jun","h":"12:00 p.m.","s":"Houston","marcador":"7-1"},
    {"id":"E2","g":"E","e1":"C. de Marfil 🇨🇮",    "e2":"Ecuador 🇪🇨",          "f":"Dom 14 Jun","h":"6:00 p.m.", "s":"Filadelfia","marcador":"1-0"},
    {"id":"E3","g":"E","e1":"Alemania 🇩🇪",         "e2":"C. de Marfil 🇨🇮",    "f":"Sáb 20 Jun","h":"3:00 p.m.", "s":"Toronto","marcador":None},
    {"id":"E4","g":"E","e1":"Ecuador 🇪🇨",          "e2":"Curazao 🇨🇼",          "f":"Sáb 20 Jun","h":"7:00 p.m.", "s":"Kansas City","marcador":None},
    {"id":"E5","g":"E","e1":"Curazao 🇨🇼",          "e2":"C. de Marfil 🇨🇮",    "f":"Jue 25 Jun","h":"3:00 p.m.", "s":"Filadelfia","marcador":None},
    {"id":"E6","g":"E","e1":"Ecuador 🇪🇨",          "e2":"Alemania 🇩🇪",         "f":"Jue 25 Jun","h":"3:00 p.m.", "s":"Nueva York/NJ","marcador":None},
    # GRUPO F
    {"id":"F1","g":"F","e1":"Países Bajos 🇳🇱",    "e2":"Japón 🇯🇵",            "f":"Dom 14 Jun","h":"3:00 p.m.", "s":"Dallas","marcador":"2-2"},
    {"id":"F2","g":"F","e1":"Suecia 🇸🇪",           "e2":"Túnez 🇹🇳",            "f":"Dom 14 Jun","h":"9:00 p.m.", "s":"Monterrey","marcador":"5-1"},
    {"id":"F3","g":"F","e1":"Países Bajos 🇳🇱",    "e2":"Suecia 🇸🇪",           "f":"Sáb 20 Jun","h":"12:00 p.m.","s":"Houston","marcador":None},
    {"id":"F4","g":"F","e1":"Túnez 🇹🇳",            "e2":"Japón 🇯🇵",            "f":"Sáb 20 Jun","h":"11:00 p.m.","s":"Monterrey","marcador":None},
    {"id":"F5","g":"F","e1":"Japón 🇯🇵",            "e2":"Suecia 🇸🇪",           "f":"Jue 25 Jun","h":"6:00 p.m.", "s":"Dallas","marcador":None},
    {"id":"F6","g":"F","e1":"Túnez 🇹🇳",            "e2":"Países Bajos 🇳🇱",    "f":"Jue 25 Jun","h":"6:00 p.m.", "s":"Kansas City","marcador":None},
    # GRUPO G
    {"id":"G1","g":"G","e1":"Bélgica 🇧🇪",          "e2":"Egipto 🇪🇬",           "f":"Lun 15 Jun","h":"2:00 p.m.", "s":"Seattle","marcador":"1-1"},
    {"id":"G2","g":"G","e1":"Irán 🇮🇷",             "e2":"Nueva Zelanda 🇳🇿",    "f":"Lun 15 Jun","h":"8:00 p.m.", "s":"Los Ángeles","marcador":"2-2"},
    {"id":"G3","g":"G","e1":"Bélgica 🇧🇪",          "e2":"Irán 🇮🇷",             "f":"Dom 21 Jun","h":"2:00 p.m.", "s":"Los Ángeles","marcador":None},
    {"id":"G4","g":"G","e1":"Nueva Zelanda 🇳🇿",    "e2":"Egipto 🇪🇬",           "f":"Dom 21 Jun","h":"8:00 p.m.", "s":"Vancouver","marcador":None},
    {"id":"G5","g":"G","e1":"Egipto 🇪🇬",           "e2":"Irán 🇮🇷",             "f":"Vie 26 Jun","h":"10:00 p.m.","s":"Seattle","marcador":None},
    {"id":"G6","g":"G","e1":"Nueva Zelanda 🇳🇿",    "e2":"Bélgica 🇧🇪",          "f":"Vie 26 Jun","h":"10:00 p.m.","s":"Vancouver","marcador":None},
    # GRUPO H
    {"id":"H1","g":"H","e1":"España 🇪🇸",           "e2":"Cabo Verde 🇨🇻",       "f":"Lun 15 Jun","h":"11:00 a.m.","s":"Atlanta","marcador":"0-0"},
    {"id":"H2","g":"H","e1":"Arabia Saudita 🇸🇦",  "e2":"Uruguay 🇺🇾",          "f":"Lun 15 Jun","h":"5:00 p.m.", "s":"Miami","marcador":"1-1"},
    {"id":"H3","g":"H","e1":"España 🇪🇸",           "e2":"Arabia Saudita 🇸🇦",  "f":"Dom 21 Jun","h":"11:00 a.m.","s":"Atlanta","marcador":None},
    {"id":"H4","g":"H","e1":"Uruguay 🇺🇾",          "e2":"Cabo Verde 🇨🇻",       "f":"Dom 21 Jun","h":"5:00 p.m.", "s":"Miami","marcador":None},
    {"id":"H5","g":"H","e1":"Cabo Verde 🇨🇻",       "e2":"Arabia Saudita 🇸🇦",  "f":"Vie 26 Jun","h":"7:00 p.m.", "s":"Houston","marcador":None},
    {"id":"H6","g":"H","e1":"Uruguay 🇺🇾",          "e2":"España 🇪🇸",           "f":"Vie 26 Jun","h":"7:00 p.m.", "s":"Akron, Guadalajara","marcador":None},
    # GRUPO I
    {"id":"I1","g":"I","e1":"Francia 🇫🇷",          "e2":"Senegal 🇸🇳",          "f":"Mar 16 Jun","h":"2:00 p.m.", "s":"Nueva York/NJ","marcador":"3-1"},
    {"id":"I2","g":"I","e1":"Irak 🇮🇶",             "e2":"Noruega 🇳🇴",          "f":"Mar 16 Jun","h":"5:00 p.m.", "s":"Boston","marcador":"1-4"},
    {"id":"I3","g":"I","e1":"Francia 🇫🇷",          "e2":"Irak 🇮🇶",             "f":"Lun 22 Jun","h":"4:00 p.m.", "s":"Filadelfia","marcador":None},
    {"id":"I4","g":"I","e1":"Noruega 🇳🇴",          "e2":"Senegal 🇸🇳",          "f":"Lun 22 Jun","h":"7:00 p.m.", "s":"Nueva York/NJ","marcador":None},
    {"id":"I5","g":"I","e1":"Noruega 🇳🇴",          "e2":"Francia 🇫🇷",          "f":"Vie 26 Jun","h":"2:00 p.m.", "s":"Boston","marcador":None},
    {"id":"I6","g":"I","e1":"Senegal 🇸🇳",          "e2":"Irak 🇮🇶",             "f":"Vie 26 Jun","h":"2:00 p.m.", "s":"Toronto","marcador":None},
    # GRUPO J
    {"id":"J1","g":"J","e1":"Argentina 🇦🇷",        "e2":"Argelia 🇩🇿",          "f":"Mar 16 Jun","h":"8:00 p.m.", "s":"Kansas City","marcador":"3-0"},
    {"id":"J2","g":"J","e1":"Austria 🇦🇹",          "e2":"Jordania 🇯🇴",         "f":"Mar 16 Jun","h":"11:00 p.m.","s":"San Francisco","marcador":"3-1"},
    {"id":"J3","g":"J","e1":"Argentina 🇦🇷",        "e2":"Austria 🇦🇹",          "f":"Lun 22 Jun","h":"12:00 p.m.","s":"Dallas","marcador":None},
    {"id":"J4","g":"J","e1":"Jordania 🇯🇴",         "e2":"Argelia 🇩🇿",          "f":"Lun 22 Jun","h":"10:00 p.m.","s":"San Francisco","marcador":None},
    {"id":"J5","g":"J","e1":"Argelia 🇩🇿",          "e2":"Austria 🇦🇹",          "f":"Sáb 27 Jun","h":"9:00 p.m.", "s":"Kansas City","marcador":None},
    {"id":"J6","g":"J","e1":"Jordania 🇯🇴",         "e2":"Argentina 🇦🇷",        "f":"Sáb 27 Jun","h":"9:00 p.m.", "s":"Dallas","marcador":None},
    # GRUPO K
    {"id":"K1","g":"K","e1":"Portugal 🇵🇹",        "e2":"Congo RD 🇨🇩",         "f":"Mié 17 Jun","h":"12:00 p.m.","s":"Houston","marcador":"1-1"},
    {"id":"K2","g":"K","e1":"Uzbekistán 🇺🇿",       "e2":"Colombia 🇨🇴",         "f":"Mié 17 Jun","h":"9:00 p.m.", "s":"Azteca, Ciudad México","marcador":"1-3"},
    {"id":"K3","g":"K","e1":"Portugal 🇵🇹",        "e2":"Uzbekistán 🇺🇿",       "f":"Mar 23 Jun","h":"12:00 p.m.","s":"Houston","marcador":None},
    {"id":"K4","g":"K","e1":"Colombia 🇨🇴",         "e2":"Congo RD 🇨🇩",         "f":"Mar 23 Jun","h":"9:00 p.m.", "s":"Akron, Guadalajara","marcador":None},
    {"id":"K5","g":"K","e1":"Colombia 🇨🇴",         "e2":"Portugal 🇵🇹",        "f":"Sáb 27 Jun","h":"6:30 p.m.", "s":"Miami","marcador":None},
    {"id":"K6","g":"K","e1":"Congo RD 🇨🇩",         "e2":"Uzbekistán 🇺🇿",       "f":"Sáb 27 Jun","h":"6:30 p.m.", "s":"Atlanta","marcador":None},
    # GRUPO L
    {"id":"L1","g":"L","e1":"Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿",      "e2":"Croacia 🇭🇷",           "f":"Mié 17 Jun","h":"3:00 p.m.", "s":"Dallas","marcador":"4-2"},
    {"id":"L2","g":"L","e1":"Ghana 🇬🇭",            "e2":"Panamá 🇵🇦",           "f":"Mié 17 Jun","h":"6:00 p.m.", "s":"Toronto","marcador":"1-0"},
    {"id":"L3","g":"L","e1":"Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿",      "e2":"Ghana 🇬🇭",             "f":"Mar 23 Jun","h":"3:00 p.m.", "s":"Boston","marcador":None},
    {"id":"L4","g":"L","e1":"Panamá 🇵🇦",           "e2":"Croacia 🇭🇷",           "f":"Mar 23 Jun","h":"6:00 p.m.", "s":"Toronto","marcador":None},
    {"id":"L5","g":"L","e1":"Panamá 🇵🇦",           "e2":"Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿",       "f":"Sáb 27 Jun","h":"4:00 p.m.", "s":"Nueva York/NJ","marcador":None},
    {"id":"L6","g":"L","e1":"Croacia 🇭🇷",           "e2":"Ghana 🇬🇭",             "f":"Sáb 27 Jun","h":"4:00 p.m.", "s":"Filadelfia","marcador":None},
]

# ── Fase eliminatoria — hora Colombia (UTC-5), equipos TBD ───────────────────
# Misma fuente y método de conversión que FIXTURE_GRUPOS (verificado 2026-06-18).
RONDA_32 = [
    {"id":"R32_1", "f":"Dom 28 Jun","h":"2:00 p.m.", "s":"Los Ángeles"},
    {"id":"R32_2", "f":"Lun 29 Jun","h":"12:00 p.m.","s":"Houston"},
    {"id":"R32_3", "f":"Lun 29 Jun","h":"3:30 p.m.", "s":"Boston"},
    {"id":"R32_4", "f":"Lun 29 Jun","h":"8:00 p.m.", "s":"Monterrey"},
    {"id":"R32_5", "f":"Mar 30 Jun","h":"12:00 p.m.","s":"Dallas"},
    {"id":"R32_6", "f":"Mar 30 Jun","h":"4:00 p.m.", "s":"Nueva York/NJ"},
    {"id":"R32_7", "f":"Mar 30 Jun","h":"8:00 p.m.", "s":"Azteca, Ciudad México"},
    {"id":"R32_8", "f":"Mié 1 Jul", "h":"11:00 a.m.","s":"Atlanta"},
    {"id":"R32_9", "f":"Mié 1 Jul", "h":"3:00 p.m.", "s":"Seattle"},
    {"id":"R32_10","f":"Mié 1 Jul", "h":"7:00 p.m.", "s":"San Francisco"},
    {"id":"R32_11","f":"Jue 2 Jul", "h":"2:00 p.m.", "s":"Los Ángeles"},
    {"id":"R32_12","f":"Jue 2 Jul", "h":"6:00 p.m.", "s":"Toronto"},
    {"id":"R32_13","f":"Jue 2 Jul", "h":"10:00 p.m.","s":"Vancouver"},
    {"id":"R32_14","f":"Vie 3 Jul", "h":"1:00 p.m.", "s":"Dallas"},
    {"id":"R32_15","f":"Vie 3 Jul", "h":"5:00 p.m.", "s":"Miami"},
    {"id":"R32_16","f":"Vie 3 Jul", "h":"8:30 p.m.", "s":"Kansas City"},
]
OCTAVOS = [
    {"id":"OCT_1","f":"Sáb 4 Jul","h":"12:00 p.m.","s":"Houston"},
    {"id":"OCT_2","f":"Sáb 4 Jul","h":"4:00 p.m.", "s":"Filadelfia"},
    {"id":"OCT_3","f":"Dom 5 Jul","h":"3:00 p.m.", "s":"Nueva York/NJ"},
    {"id":"OCT_4","f":"Dom 5 Jul","h":"7:00 p.m.", "s":"Azteca, Ciudad México"},
    {"id":"OCT_5","f":"Lun 6 Jul","h":"2:00 p.m.", "s":"Dallas"},
    {"id":"OCT_6","f":"Lun 6 Jul","h":"7:00 p.m.", "s":"Seattle"},
    {"id":"OCT_7","f":"Mar 7 Jul","h":"11:00 a.m.","s":"Atlanta"},
    {"id":"OCT_8","f":"Mar 7 Jul","h":"3:00 p.m.", "s":"Vancouver"},
]
CUARTOS = [
    {"id":"CF_1","f":"Jue 9 Jul","h":"3:00 p.m.", "s":"Boston"},
    {"id":"CF_2","f":"Vie 10 Jul","h":"2:00 p.m.","s":"Los Ángeles"},
    {"id":"CF_3","f":"Sáb 11 Jul","h":"4:00 p.m.", "s":"Miami"},
    {"id":"CF_4","f":"Sáb 11 Jul","h":"8:00 p.m.", "s":"Kansas City"},
]
SEMIS = [
    {"id":"SF_1","f":"Mar 14 Jul","h":"2:00 p.m.","s":"Dallas"},
    {"id":"SF_2","f":"Mié 15 Jul","h":"2:00 p.m.","s":"Atlanta"},
]
TERCER_PUESTO = {"id":"3P",    "f":"Sáb 18 Jul","h":"4:00 p.m.","s":"Miami"}
FINAL_INFO    = {"id":"FINAL","f":"Dom 19 Jul","h":"2:00 p.m.","s":"MetLife Stadium, NJ"}

# ── Fixture completo por fecha (todos los partidos, ordenados cronológicamente) ─
def _fecha_key(f: str) -> str:
    _MES = {"Jun": "06", "Jul": "07"}
    p = f.split()
    return f"2026{_MES.get(p[2], '06')}{p[1].zfill(2)}"

def _hora_key(h: str) -> int:
    t = h.replace(".", "").split()
    hr, mn = map(int, t[0].split(":"))
    ap = t[1].lower()
    if ap == "pm" and hr != 12: hr += 12
    elif ap == "am" and hr == 12: hr = 0
    return hr * 100 + mn

_ALL: list = []
for _p in FIXTURE_GRUPOS:
    _ALL.append({**_p, "tipo": "grupo", "label": f"Grupo {_p['g']}", "tbd": False})
for _p in RONDA_32:
    _ALL.append({**_p, "tipo": "elim", "label": "Ronda de 32",      "e1": "❓ TBD", "e2": "❓ TBD", "tbd": True})
for _p in OCTAVOS:
    _ALL.append({**_p, "tipo": "elim", "label": "Octavos de Final", "e1": "❓ TBD", "e2": "❓ TBD", "tbd": True})
for _p in CUARTOS:
    _ALL.append({**_p, "tipo": "elim", "label": "Cuartos de Final", "e1": "❓ TBD", "e2": "❓ TBD", "tbd": True})
for _p in SEMIS:
    _ALL.append({**_p, "tipo": "elim", "label": "Semifinal",        "e1": "❓ TBD", "e2": "❓ TBD", "tbd": True})
_ALL.append({**TERCER_PUESTO, "tipo": "elim", "label": "Tercer Puesto", "e1": "❓ TBD", "e2": "❓ TBD", "tbd": True})
_ALL.append({**FINAL_INFO,    "tipo": "elim", "label": "🏆 Gran Final",  "e1": "❓ TBD", "e2": "❓ TBD", "tbd": True})

_BY_DATE: dict = {}
for _p in _ALL:
    _BY_DATE.setdefault(_p["f"], []).append(_p)

FIXTURE_POR_FECHA = [
    {
        "fecha":    _f,
        "sort_key": _fecha_key(_f),
        "partidos": sorted(_pl, key=lambda x: _hora_key(x["h"])),
    }
    for _f, _pl in sorted(_BY_DATE.items(), key=lambda x: _fecha_key(x[0]))
]
del _ALL, _BY_DATE, _p

# ── Sorteo de marcadores — partidos disponibles ──────────────────────────────
PARTIDOS_SORTEO = [
    {"id":"CF_1",  "nombre":"⚽ Cuarto de Final 1",  "f":"Jue 9 Jul",  "h":"3:00 p.m.", "s":"Boston"},
    {"id":"CF_2",  "nombre":"⚽ Cuarto de Final 2",  "f":"Vie 10 Jul", "h":"2:00 p.m.", "s":"Los Ángeles"},
    {"id":"CF_3",  "nombre":"⚽ Cuarto de Final 3",  "f":"Sáb 11 Jul", "h":"4:00 p.m.", "s":"Miami"},
    {"id":"CF_4",  "nombre":"⚽ Cuarto de Final 4",  "f":"Sáb 11 Jul", "h":"8:00 p.m.", "s":"Kansas City"},
    {"id":"SF_1",  "nombre":"⚡ Semifinal 1",         "f":"Mar 14 Jul", "h":"2:00 p.m.", "s":"Dallas"},
    {"id":"SF_2",  "nombre":"⚡ Semifinal 2",         "f":"Mié 15 Jul", "h":"2:00 p.m.", "s":"Atlanta"},
    {"id":"3P",    "nombre":"🥉 Tercer Puesto",       "f":"Sáb 18 Jul", "h":"4:00 p.m.", "s":"Miami"},
    {"id":"FINAL", "nombre":"🏆 GRAN FINAL",          "f":"Dom 19 Jul", "h":"2:00 p.m.", "s":"MetLife, NJ"},
]

# ── Marcadores reales posibles en fútbol ─────────────────────────────────────
MARCADORES_POSIBLES = [
    (0,0),(1,0),(0,1),(1,1),(2,0),(0,2),(2,1),(1,2),(2,2),
    (3,0),(0,3),(3,1),(1,3),(3,2),(2,3),(4,0),(0,4),
    (4,1),(1,4),(4,2),(2,4),(3,3),(5,0),(0,5),(5,1),(1,5),
    (4,3),(3,4),(5,2),(2,5),(6,0),(0,6),(5,3),(3,5),(4,4),
]

PUNTOS_GANADOR  = 3   # Acertar ganador del grupo
PUNTOS_CAMPEON  = 10  # Acertar campeón mundial
PUNTOS_FINAL    = 5   # Acertar subcampeón (finalista perdedor)
PUNTOS_TERCERO  = 3   # Acertar el tercer puesto


# ── Rutas ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def mundial_inicio(request: Request, tab: str = "grupos", msg: str = "", sorteo_partido: str = ""):
    conn = get_db()
    try:
        preds  = conn.execute(
            "SELECT participante, clave, valor FROM mundial_predicciones"
        ).fetchall()
        sorteo = conn.execute(
            "SELECT * FROM mundial_sorteo ORDER BY partido_id, participante"
        ).fetchall()
        res    = conn.execute(
            "SELECT clave, valor FROM mundial_resultados"
        ).fetchall()
    finally:
        conn.close()

    pred_map: dict = {}
    for p in preds:
        d = dict(p)
        pred_map.setdefault(d["participante"], {})[d["clave"]] = d["valor"]

    sorteo_map: dict = {}
    for s in sorteo:
        d = dict(s)
        sorteo_map.setdefault(d["partido_id"], []).append(d)

    res_map = {dict(r)["clave"]: dict(r)["valor"] for r in res}
    tabla   = _calcular_tabla(pred_map, res_map)

    # Partidos que ya tienen sorteo
    partidos_ya_sorteados = set(sorteo_map.keys())

    return templates.TemplateResponse("mundial.html", tpl(request, None,
        tab=tab,
        msg=msg,
        sorteo_partido_activo=sorteo_partido,
        grupos=GRUPOS,
        fixture_grupos=FIXTURE_GRUPOS,
        fixture_por_fecha=FIXTURE_POR_FECHA,
        ronda_32=RONDA_32,
        octavos=OCTAVOS,
        cuartos=CUARTOS,
        semis=SEMIS,
        tercer_puesto=TERCER_PUESTO,
        final_info=FINAL_INFO,
        participantes=PARTICIPANTES,
        partidos_sorteo=PARTIDOS_SORTEO,
        todos_los_equipos=TODOS_LOS_EQUIPOS,
        pred_map=pred_map,
        pred_map_json=json.dumps(pred_map, ensure_ascii=False),
        sorteo_map=sorteo_map,
        res_map=res_map,
        tabla=tabla,
        partidos_ya_sorteados=partidos_ya_sorteados,
    ))


@router.post("/predicciones-bulk")
async def mundial_guardar_predicciones(request: Request):
    """Guarda todas las predicciones de un participante en un único POST."""
    form = await request.form()
    participante = form.get("participante", "").strip()
    if participante not in PARTICIPANTES:
        return RedirectResponse("/mundial/?tab=predicciones&msg=error_participante", status_code=303)

    conn = get_db()
    try:
        for key, valor in form.multi_items():
            if key == "participante" or not key or not valor:
                continue
            conn.execute(
                "INSERT INTO mundial_predicciones(participante,clave,valor) VALUES(?,?,?) "
                "ON CONFLICT(participante,clave) DO UPDATE SET valor=excluded.valor, "
                "updated_at=datetime('now','localtime')",
                (participante, key, str(valor).strip()),
            )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/mundial/?tab=predicciones&msg=ok_pred", status_code=303)


@router.post("/sorteo/{partido_id}")
async def mundial_sortear(request: Request, partido_id: str):
    ids_validos = {p["id"] for p in PARTIDOS_SORTEO}
    if partido_id not in ids_validos:
        return RedirectResponse("/mundial/?tab=sorteo&msg=error_partido", status_code=303)

    marcadores     = random.sample(MARCADORES_POSIBLES, len(PARTICIPANTES))
    mezclados      = list(range(len(PARTICIPANTES)))
    random.shuffle(mezclados)

    conn = get_db()
    try:
        conn.execute("DELETE FROM mundial_sorteo WHERE partido_id=?", (partido_id,))
        for i, idx in enumerate(mezclados):
            gl, gv = marcadores[i]
            conn.execute(
                "INSERT INTO mundial_sorteo(partido_id,participante,goles_local,goles_visita) VALUES(?,?,?,?)",
                (partido_id, PARTICIPANTES[idx], gl, gv),
            )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse(
        f"/mundial/?tab=sorteo&msg=ok_sorteo&sorteo_partido={partido_id}",
        status_code=303,
    )


@router.post("/resultado")
async def mundial_resultado(request: Request, clave: str = Form(...), valor: str = Form(...)):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO mundial_resultados(clave,valor) VALUES(?,?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, "
            "actualizado_en=datetime('now','localtime')",
            (clave.strip(), valor.strip()),
        )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/mundial/?tab=tabla&msg=ok_resultado", status_code=303)


@router.post("/admin-bulk")
async def mundial_admin_bulk(request: Request):
    """Guarda múltiples resultados reales en un solo POST."""
    form = await request.form()
    conn = get_db()
    try:
        for key, valor in form.multi_items():
            if key.startswith("_") or not key or not valor or str(valor).strip() == "":
                continue
            conn.execute(
                "INSERT INTO mundial_resultados(clave,valor) VALUES(?,?) "
                "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, "
                "actualizado_en=datetime('now','localtime')",
                (key.strip(), str(valor).strip()),
            )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/mundial/?tab=admin&msg=ok_resultado", status_code=303)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calcular_tabla(pred_map: dict, res_map: dict) -> list:
    tabla = []
    for participante in PARTICIPANTES:
        preds = pred_map.get(participante, {})
        puntos = 0
        aciertos = []

        for g in GRUPOS:
            clave = f"ganador_{g}"
            if clave in res_map and clave in preds and preds[clave] == res_map[clave]:
                puntos += PUNTOS_GANADOR
                aciertos.append(f"Grupo {g}")

        for clave, pts, label in [
            ("campeon",    PUNTOS_CAMPEON, "Campeón"),
            ("subcampeon", PUNTOS_FINAL,   "Subcampeón"),
            ("tercero",    PUNTOS_TERCERO, "3er Puesto"),
        ]:
            if clave in res_map and clave in preds and preds[clave] == res_map[clave]:
                puntos += pts
                aciertos.append(label)

        tabla.append({
            "participante": participante,
            "puntos": puntos,
            "n_predicciones": len(preds),
            "aciertos": aciertos,
        })

    tabla.sort(key=lambda x: (-x["puntos"], x["participante"]))
    for i, row in enumerate(tabla):
        row["pos"] = i + 1
    return tabla
