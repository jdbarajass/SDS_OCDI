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
FIXTURE_GRUPOS = [
    # GRUPO A
    {"id":"A1","g":"A","e1":"México 🇲🇽",        "e2":"Sudáfrica 🇿🇦",       "f":"Jue 11 Jun","h":"1:00 p.m.", "s":"Azteca, Ciudad México"},
    {"id":"A2","g":"A","e1":"Corea del Sur 🇰🇷",  "e2":"Rep. Checa 🇨🇿",       "f":"Jue 11 Jun","h":"8:00 p.m.", "s":"Akron, Guadalajara"},
    {"id":"A3","g":"A","e1":"Rep. Checa 🇨🇿",     "e2":"Sudáfrica 🇿🇦",        "f":"Mié 18 Jun","h":"12:00 p.m.","s":"Atlanta"},
    {"id":"A4","g":"A","e1":"México 🇲🇽",         "e2":"Corea del Sur 🇰🇷",    "f":"Mié 18 Jun","h":"7:00 p.m.", "s":"Akron, Guadalajara"},
    {"id":"A5","g":"A","e1":"Rep. Checa 🇨🇿",     "e2":"México 🇲🇽",           "f":"Mar 24 Jun","h":"7:00 p.m.", "s":"Azteca, Ciudad México"},
    {"id":"A6","g":"A","e1":"Sudáfrica 🇿🇦",      "e2":"Corea del Sur 🇰🇷",    "f":"Mar 24 Jun","h":"7:00 p.m.", "s":"BBVA, Monterrey"},
    # GRUPO B
    {"id":"B1","g":"B","e1":"Canadá 🇨🇦",         "e2":"Bosnia-Herz. 🇧🇦",     "f":"Vie 13 Jun","h":"2:00 p.m.", "s":"Toronto"},
    {"id":"B2","g":"B","e1":"Qatar 🇶🇦",           "e2":"Suiza 🇨🇭",            "f":"Sáb 14 Jun","h":"12:00 p.m.","s":"San Francisco"},
    {"id":"B3","g":"B","e1":"Suiza 🇨🇭",           "e2":"Bosnia-Herz. 🇧🇦",     "f":"Mié 18 Jun","h":"12:00 p.m.","s":"Los Ángeles"},
    {"id":"B4","g":"B","e1":"Canadá 🇨🇦",          "e2":"Qatar 🇶🇦",            "f":"Mié 18 Jun","h":"3:00 p.m.", "s":"Vancouver"},
    {"id":"B5","g":"B","e1":"Suiza 🇨🇭",           "e2":"Canadá 🇨🇦",           "f":"Mar 24 Jun","h":"2:00 p.m.", "s":"Vancouver"},
    {"id":"B6","g":"B","e1":"Bosnia-Herz. 🇧🇦",   "e2":"Qatar 🇶🇦",            "f":"Mar 24 Jun","h":"2:00 p.m.", "s":"Seattle"},
    # GRUPO C
    {"id":"C1","g":"C","e1":"Haití 🇭🇹",           "e2":"Escocia 🏴󠁧󠁢󠁳󠁣󠁴󠁿",         "f":"Vie 13 Jun","h":"5:00 p.m.", "s":"Boston"},
    {"id":"C2","g":"C","e1":"Brasil 🇧🇷",          "e2":"Marruecos 🇲🇦",        "f":"Vie 13 Jun","h":"5:00 p.m.", "s":"Nueva York/NJ"},
    {"id":"C3","g":"C","e1":"Brasil 🇧🇷",          "e2":"Haití 🇭🇹",            "f":"Jue 19 Jun","h":"8:00 p.m.", "s":"Filadelfia"},
    {"id":"C4","g":"C","e1":"Escocia 🏴󠁧󠁢󠁳󠁣󠁴󠁿",        "e2":"Marruecos 🇲🇦",        "f":"Jue 19 Jun","h":"5:00 p.m.", "s":"Boston"},
    {"id":"C5","g":"C","e1":"Escocia 🏴󠁧󠁢󠁳󠁣󠁴󠁿",        "e2":"Brasil 🇧🇷",           "f":"Mar 24 Jun","h":"5:00 p.m.", "s":"Miami"},
    {"id":"C6","g":"C","e1":"Marruecos 🇲🇦",       "e2":"Haití 🇭🇹",            "f":"Mar 24 Jun","h":"5:00 p.m.", "s":"Atlanta"},
    # GRUPO D
    {"id":"D1","g":"D","e1":"EE.UU. 🇺🇸",          "e2":"Paraguay 🇵🇾",         "f":"Vie 12 Jun","h":"8:00 p.m.", "s":"Los Ángeles"},
    {"id":"D2","g":"D","e1":"Australia 🇦🇺",        "e2":"Turquía 🇹🇷",          "f":"Vie 12 Jun","h":"11:00 p.m.","s":"Vancouver"},
    {"id":"D3","g":"D","e1":"Turquía 🇹🇷",          "e2":"Paraguay 🇵🇾",         "f":"Jue 19 Jun","h":"8:00 p.m.", "s":"San Francisco"},
    {"id":"D4","g":"D","e1":"EE.UU. 🇺🇸",           "e2":"Australia 🇦🇺",        "f":"Jue 19 Jun","h":"12:00 p.m.","s":"Seattle"},
    {"id":"D5","g":"D","e1":"Turquía 🇹🇷",          "e2":"EE.UU. 🇺🇸",           "f":"Mar 24 Jun","h":"7:00 p.m.", "s":"Los Ángeles"},
    {"id":"D6","g":"D","e1":"Paraguay 🇵🇾",         "e2":"Australia 🇦🇺",        "f":"Mar 24 Jun","h":"7:00 p.m.", "s":"San Francisco"},
    # GRUPO E
    {"id":"E1","g":"E","e1":"C. de Marfil 🇨🇮",    "e2":"Ecuador 🇪🇨",          "f":"Dom 14 Jun","h":"6:00 p.m.", "s":"Filadelfia"},
    {"id":"E2","g":"E","e1":"Alemania 🇩🇪",         "e2":"Curazao 🇨🇼",          "f":"Dom 14 Jun","h":"12:00 p.m.","s":"Houston"},
    {"id":"E3","g":"E","e1":"Alemania 🇩🇪",         "e2":"C. de Marfil 🇨🇮",    "f":"Sáb 20 Jun","h":"4:00 p.m.", "s":"Toronto"},
    {"id":"E4","g":"E","e1":"Ecuador 🇪🇨",          "e2":"Curazao 🇨🇼",          "f":"Sáb 20 Jun","h":"7:00 p.m.", "s":"Kansas City"},
    {"id":"E5","g":"E","e1":"Curazao 🇨🇼",          "e2":"C. de Marfil 🇨🇮",    "f":"Mié 25 Jun","h":"4:00 p.m.", "s":"Filadelfia"},
    {"id":"E6","g":"E","e1":"Ecuador 🇪🇨",          "e2":"Alemania 🇩🇪",         "f":"Mié 25 Jun","h":"4:00 p.m.", "s":"Nueva York/NJ"},
    # GRUPO F
    {"id":"F1","g":"F","e1":"Países Bajos 🇳🇱",    "e2":"Japón 🇯🇵",            "f":"Dom 14 Jun","h":"3:00 p.m.", "s":"Dallas"},
    {"id":"F2","g":"F","e1":"Suecia 🇸🇪",           "e2":"Túnez 🇹🇳",            "f":"Dom 14 Jun","h":"8:00 p.m.", "s":"Monterrey"},
    {"id":"F3","g":"F","e1":"Países Bajos 🇳🇱",    "e2":"Suecia 🇸🇪",           "f":"Sáb 20 Jun","h":"12:00 p.m.","s":"Houston"},
    {"id":"F4","g":"F","e1":"Túnez 🇹🇳",            "e2":"Japón 🇯🇵",            "f":"Sáb 20 Jun","h":"10:00 p.m.","s":"Monterrey"},
    {"id":"F5","g":"F","e1":"Japón 🇯🇵",            "e2":"Suecia 🇸🇪",           "f":"Mié 25 Jun","h":"6:00 p.m.", "s":"Dallas"},
    {"id":"F6","g":"F","e1":"Túnez 🇹🇳",            "e2":"Países Bajos 🇳🇱",    "f":"Mié 25 Jun","h":"6:00 p.m.", "s":"Kansas City"},
    # GRUPO G
    {"id":"G1","g":"G","e1":"Irán 🇮🇷",             "e2":"Nueva Zelanda 🇳🇿",    "f":"Dom 15 Jun","h":"8:00 p.m.", "s":"Los Ángeles"},
    {"id":"G2","g":"G","e1":"Bélgica 🇧🇪",          "e2":"Egipto 🇪🇬",           "f":"Dom 15 Jun","h":"2:00 p.m.", "s":"Seattle"},
    {"id":"G3","g":"G","e1":"Bélgica 🇧🇪",          "e2":"Irán 🇮🇷",             "f":"Dom 21 Jun","h":"2:00 p.m.", "s":"Los Ángeles"},
    {"id":"G4","g":"G","e1":"Nueva Zelanda 🇳🇿",    "e2":"Egipto 🇪🇬",           "f":"Dom 21 Jun","h":"8:00 p.m.", "s":"Vancouver"},
    {"id":"G5","g":"G","e1":"Egipto 🇪🇬",           "e2":"Irán 🇮🇷",             "f":"Jue 26 Jun","h":"10:00 p.m.","s":"Seattle"},
    {"id":"G6","g":"G","e1":"Nueva Zelanda 🇳🇿",    "e2":"Bélgica 🇧🇪",          "f":"Jue 26 Jun","h":"10:00 p.m.","s":"Vancouver"},
    # GRUPO H
    {"id":"H1","g":"H","e1":"Arabia Saudita 🇸🇦",  "e2":"Uruguay 🇺🇾",          "f":"Dom 15 Jun","h":"5:00 p.m.", "s":"Miami"},
    {"id":"H2","g":"H","e1":"España 🇪🇸",           "e2":"Cabo Verde 🇨🇻",       "f":"Dom 15 Jun","h":"11:00 a.m.","s":"Atlanta"},
    {"id":"H3","g":"H","e1":"Uruguay 🇺🇾",          "e2":"Cabo Verde 🇨🇻",       "f":"Sáb 21 Jun","h":"5:00 p.m.", "s":"Miami"},
    {"id":"H4","g":"H","e1":"España 🇪🇸",           "e2":"Arabia Saudita 🇸🇦",  "f":"Sáb 21 Jun","h":"11:00 a.m.","s":"Atlanta"},
    {"id":"H5","g":"H","e1":"Cabo Verde 🇨🇻",       "e2":"Arabia Saudita 🇸🇦",  "f":"Jue 26 Jun","h":"7:00 p.m.", "s":"Houston"},
    {"id":"H6","g":"H","e1":"Uruguay 🇺🇾",          "e2":"España 🇪🇸",           "f":"Jue 26 Jun","h":"6:00 p.m.", "s":"Akron, Guadalajara"},
    # GRUPO I
    {"id":"I1","g":"I","e1":"Francia 🇫🇷",          "e2":"Senegal 🇸🇳",          "f":"Mar 16 Jun","h":"2:00 p.m.", "s":"Nueva York/NJ"},
    {"id":"I2","g":"I","e1":"Irak 🇮🇶",             "e2":"Noruega 🇳🇴",          "f":"Mar 16 Jun","h":"5:00 p.m.", "s":"Boston"},
    {"id":"I3","g":"I","e1":"Noruega 🇳🇴",          "e2":"Senegal 🇸🇳",          "f":"Lun 22 Jun","h":"7:00 p.m.", "s":"Nueva York/NJ"},
    {"id":"I4","g":"I","e1":"Francia 🇫🇷",          "e2":"Irak 🇮🇶",             "f":"Lun 22 Jun","h":"4:00 p.m.", "s":"Filadelfia"},
    {"id":"I5","g":"I","e1":"Noruega 🇳🇴",          "e2":"Francia 🇫🇷",          "f":"Jue 26 Jun","h":"2:00 p.m.", "s":"Boston"},
    {"id":"I6","g":"I","e1":"Senegal 🇸🇳",          "e2":"Irak 🇮🇶",             "f":"Jue 26 Jun","h":"2:00 p.m.", "s":"Toronto"},
    # GRUPO J
    {"id":"J1","g":"J","e1":"Argentina 🇦🇷",        "e2":"Argelia 🇩🇿",          "f":"Lun 16 Jun","h":"8:00 p.m.", "s":"Kansas City"},
    {"id":"J2","g":"J","e1":"Austria 🇦🇹",          "e2":"Jordania 🇯🇴",         "f":"Lun 16 Jun","h":"11:00 p.m.","s":"San Francisco"},
    {"id":"J3","g":"J","e1":"Argentina 🇦🇷",        "e2":"Austria 🇦🇹",          "f":"Lun 22 Jun","h":"12:00 p.m.","s":"Dallas"},
    {"id":"J4","g":"J","e1":"Jordania 🇯🇴",         "e2":"Argelia 🇩🇿",          "f":"Lun 22 Jun","h":"10:00 p.m.","s":"San Francisco"},
    {"id":"J5","g":"J","e1":"Argelia 🇩🇿",          "e2":"Austria 🇦🇹",          "f":"Vie 27 Jun","h":"9:00 p.m.", "s":"Kansas City"},
    {"id":"J6","g":"J","e1":"Jordania 🇯🇴",         "e2":"Argentina 🇦🇷",        "f":"Vie 27 Jun","h":"9:00 p.m.", "s":"Dallas"},
    # GRUPO K
    {"id":"K1","g":"K","e1":"Portugal 🇵🇹",        "e2":"Congo RD 🇨🇩",         "f":"Mar 17 Jun","h":"12:00 p.m.","s":"Houston"},
    {"id":"K2","g":"K","e1":"Uzbekistán 🇺🇿",       "e2":"Colombia 🇨🇴",         "f":"Mar 17 Jun","h":"8:00 p.m.", "s":"Azteca, Ciudad México"},
    {"id":"K3","g":"K","e1":"Portugal 🇵🇹",        "e2":"Uzbekistán 🇺🇿",       "f":"Lun 23 Jun","h":"12:00 p.m.","s":"Houston"},
    {"id":"K4","g":"K","e1":"Colombia 🇨🇴",         "e2":"Congo RD 🇨🇩",         "f":"Lun 23 Jun","h":"8:00 p.m.", "s":"Akron, Guadalajara"},
    {"id":"K5","g":"K","e1":"Colombia 🇨🇴",         "e2":"Portugal 🇵🇹",        "f":"Sáb 27 Jun","h":"6:30 p.m.", "s":"Miami"},
    {"id":"K6","g":"K","e1":"Congo RD 🇨🇩",         "e2":"Uzbekistán 🇺🇿",       "f":"Sáb 27 Jun","h":"6:30 p.m.", "s":"Atlanta"},
    # GRUPO L
    {"id":"L1","g":"L","e1":"Ghana 🇬🇭",            "e2":"Panamá 🇵🇦",           "f":"Mar 17 Jun","h":"6:00 p.m.", "s":"Toronto"},
    {"id":"L2","g":"L","e1":"Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿",      "e2":"Croacia 🇭🇷",           "f":"Mar 17 Jun","h":"3:00 p.m.", "s":"Dallas"},
    {"id":"L3","g":"L","e1":"Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿",      "e2":"Ghana 🇬🇭",             "f":"Lun 23 Jun","h":"3:00 p.m.", "s":"Boston"},
    {"id":"L4","g":"L","e1":"Panamá 🇵🇦",           "e2":"Croacia 🇭🇷",           "f":"Lun 23 Jun","h":"6:00 p.m.", "s":"Toronto"},
    {"id":"L5","g":"L","e1":"Panamá 🇵🇦",           "e2":"Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿",       "f":"Sáb 27 Jun","h":"4:00 p.m.", "s":"Nueva York/NJ"},
    {"id":"L6","g":"L","e1":"Croacia 🇭🇷",           "e2":"Ghana 🇬🇭",             "f":"Sáb 27 Jun","h":"4:00 p.m.", "s":"Filadelfia"},
]

# ── Fase eliminatoria — hora Colombia (UTC-5), equipos TBD ───────────────────
RONDA_32 = [
    {"id":"R32_1", "f":"Sáb 28 Jun","h":"2:00 p.m.", "s":"Los Ángeles"},
    {"id":"R32_2", "f":"Dom 29 Jun","h":"12:00 p.m.","s":"Houston"},
    {"id":"R32_3", "f":"Dom 29 Jun","h":"3:30 p.m.", "s":"Boston"},
    {"id":"R32_4", "f":"Dom 29 Jun","h":"9:00 p.m.", "s":"Monterrey"},
    {"id":"R32_5", "f":"Lun 30 Jun","h":"12:00 p.m.","s":"Dallas"},
    {"id":"R32_6", "f":"Lun 30 Jun","h":"4:00 p.m.", "s":"Nueva York/NJ"},
    {"id":"R32_7", "f":"Lun 30 Jun","h":"8:00 p.m.", "s":"Azteca, Ciudad México"},
    {"id":"R32_8", "f":"Mar 1 Jul", "h":"11:00 a.m.","s":"Atlanta"},
    {"id":"R32_9", "f":"Mar 1 Jul", "h":"3:00 p.m.", "s":"Seattle"},
    {"id":"R32_10","f":"Mar 1 Jul", "h":"7:00 p.m.", "s":"San Francisco"},
    {"id":"R32_11","f":"Mié 2 Jul", "h":"2:00 p.m.", "s":"Los Ángeles"},
    {"id":"R32_12","f":"Mié 2 Jul", "h":"11:00 a.m.","s":"Toronto"},
    {"id":"R32_13","f":"Mié 2 Jul", "h":"10:00 p.m.","s":"Vancouver"},
    {"id":"R32_14","f":"Jue 3 Jul", "h":"1:00 p.m.", "s":"Dallas"},
    {"id":"R32_15","f":"Jue 3 Jul", "h":"5:00 p.m.", "s":"Miami"},
    {"id":"R32_16","f":"Jue 3 Jul", "h":"8:30 p.m.", "s":"Kansas City"},
]
OCTAVOS = [
    {"id":"OCT_1","f":"Vie 4 Jul","h":"12:00 p.m.","s":"Houston"},
    {"id":"OCT_2","f":"Vie 4 Jul","h":"4:00 p.m.", "s":"Filadelfia"},
    {"id":"OCT_3","f":"Sáb 5 Jul","h":"3:00 p.m.", "s":"Nueva York/NJ"},
    {"id":"OCT_4","f":"Sáb 5 Jul","h":"7:00 p.m.", "s":"Azteca, Ciudad México"},
    {"id":"OCT_5","f":"Dom 6 Jul","h":"2:00 p.m.", "s":"Dallas"},
    {"id":"OCT_6","f":"Dom 6 Jul","h":"7:00 p.m.", "s":"Seattle"},
    {"id":"OCT_7","f":"Lun 7 Jul","h":"11:00 a.m.","s":"Atlanta"},
    {"id":"OCT_8","f":"Lun 7 Jul","h":"3:00 p.m.", "s":"Vancouver"},
]
CUARTOS = [
    {"id":"CF_1","f":"Mié 9 Jul","h":"3:00 p.m.", "s":"Boston"},
    {"id":"CF_2","f":"Jue 10 Jul","h":"2:00 p.m.","s":"Los Ángeles"},
    {"id":"CF_3","f":"Vie 11 Jul","h":"4:00 p.m.", "s":"Miami"},
    {"id":"CF_4","f":"Vie 11 Jul","h":"9:00 p.m.", "s":"Kansas City"},
]
SEMIS = [
    {"id":"SF_1","f":"Lun 14 Jul","h":"3:00 p.m.","s":"Dallas"},
    {"id":"SF_2","f":"Mar 15 Jul","h":"2:00 p.m.","s":"Atlanta"},
]
TERCER_PUESTO = {"id":"3P",    "f":"Vie 18 Jul","h":"4:00 p.m.","s":"Miami"}
FINAL_INFO    = {"id":"FINAL","f":"Dom 19 Jul","h":"2:00 p.m.","s":"MetLife Stadium, NJ"}

# ── Sorteo de marcadores — partidos disponibles ──────────────────────────────
PARTIDOS_SORTEO = [
    {"id":"CF_1",  "nombre":"⚽ Cuarto de Final 1",  "f":"Mié 9 Jul",  "h":"3:00 p.m.", "s":"Boston"},
    {"id":"CF_2",  "nombre":"⚽ Cuarto de Final 2",  "f":"Jue 10 Jul", "h":"2:00 p.m.", "s":"Los Ángeles"},
    {"id":"CF_3",  "nombre":"⚽ Cuarto de Final 3",  "f":"Vie 11 Jul", "h":"4:00 p.m.", "s":"Miami"},
    {"id":"CF_4",  "nombre":"⚽ Cuarto de Final 4",  "f":"Vie 11 Jul", "h":"9:00 p.m.", "s":"Kansas City"},
    {"id":"SF_1",  "nombre":"⚡ Semifinal 1",         "f":"Lun 14 Jul", "h":"3:00 p.m.", "s":"Dallas"},
    {"id":"SF_2",  "nombre":"⚡ Semifinal 2",         "f":"Mar 15 Jul", "h":"2:00 p.m.", "s":"Atlanta"},
    {"id":"3P",    "nombre":"🥉 Tercer Puesto",       "f":"Vie 18 Jul", "h":"4:00 p.m.", "s":"Miami"},
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
