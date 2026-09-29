# -*- coding: utf-8 -*-
# ============================================================
# CRISTOFORO | CONTROL ROOM V8.5
# Stabilizzazione avvio, eliminazione loop e caricamento sicuro
# ============================================================
import hashlib
import hmac
import io
import os
import re
import secrets
import unicodedata
from datetime import date, datetime, timedelta
from datetime import time as dtime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Cristoforo | Control Room",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "users": os.path.join(BASE_DIR, "utenti_cristoforo.csv"),
    "operators": os.path.join(BASE_DIR, "anagrafica_operatori.csv"),
    "vehicles": os.path.join(BASE_DIR, "anagrafica_mezzi.csv"),
    "services": os.path.join(BASE_DIR, "servizi_cristoforo.csv"),
    "personnel": os.path.join(BASE_DIR, "dettaglio_personale_cristoforo.csv"),
    "vehicle_detail": os.path.join(BASE_DIR, "dettaglio_mezzi_cristoforo.csv"),
    "certifications": os.path.join(BASE_DIR, "certificazioni_cristoforo.csv"),
    "cert_rows": os.path.join(BASE_DIR, "certificazioni_righe_cristoforo.csv"),
    "tariffs": os.path.join(BASE_DIR, "tariffe_cristoforo.csv"),
}

SERVICE_TREE = {
    "Spazzamenti": ["Scandicci"],
    "Aree Verdi": ["Piana", "Prato"],
    "Porta a Porta": ["Prato", "Vaiano", "Campi", "Noventa", "Costabissara", "Cremona", "Mantova", "Lucca"],
    "Trasporti": ["Alia"],
    "Raccolta Cartone Selettivo": ["Firenze", "Piana", "Prato", "Campi"],
    "Ingombranti": ["Prato", "Campi Bisenzio", "Valdisieve", "Mugello"],
}
ALL_SUBSERVICES = sorted({x for values in SERVICE_TREE.values() for x in values})

DEFAULT_VEHICLE_TYPES = [
    "35 qt", "Vasca", "3 Assi", "4 Assi", "Scarrabile", "Leggero", "Furgone", "Compattatore", "Spazzatrice",
    "1. Porter", "2. Porter Costipatore", "3. 35qt Vasca", "4. 35qt Vasca Costipatore",
    "5. 75qt Vasca Costipatore", "6. Monoscocca 10/12Qt", "7. 2 Assi 12/18mc",
    "8. 3 Assi 21/27mc", "9. 4 Assi 28/32mc", "10. Semi-Rimorchio 42/48mc",
    "11. 3 Assi Scarrabile", "12. 4 Assi Scarrabile", "13. 3 Assi Scarrabile con Caricatore"
]

CONTRACTS = {
    "Servizi Ambientali - Utilitalia": [
        "Q", "A1", "A2S", "A2", "B1S", "B1", "B2S", "B2", "C1S", "C1", "C2S", "C2", "D1S", "D1", "D2S", "D2",
    ],
    "Cooperative Sociali": ["A1", "A2", "B1", "C1", "C2", "C3", "D1", "D2", "D3", "E1", "E2", "F1", "F2"],
}
ALL_LEVELS = sorted({lv for levels in CONTRACTS.values() for lv in levels})

DEFAULT_VEHICLE_COSTS = {
    "35 qt": 20.0, "Vasca": 22.0, "3 Assi": 45.0, "4 Assi": 50.0, "Scarrabile": 40.0,
    "1. Porter": 15.0, "2. Porter Costipatore": 16.5, "3. 35qt Vasca": 20.0,
    "4. 35qt Vasca Costipatore": 22.0, "5. 75qt Vasca Costipatore": 28.0,
    "6. Monoscocca 10/12Qt": 35.0, "7. 2 Assi 12/18mc": 40.0, "8. 3 Assi 21/27mc": 45.0,
    "9. 4 Assi 28/32mc": 50.0, "10. Semi-Rimorchio 42/48mc": 65.0,
    "11. 3 Assi Scarrabile": 42.0, "12. 4 Assi Scarrabile": 48.0,
    "13. 3 Assi Scarrabile con Caricatore": 55.0
}

DEFAULT_PASSWORDS = {"direzione": "admin", "resp_prato": "123", "resp_mantova": "456"}
DEFAULT_USERS_META = [
    ("direzione", "Direzione", "admin", "TUTTI"),
    ("resp_prato", "Responsabile Prato", "capocantiere", "Prato"),
    ("resp_mantova", "Responsabile Mantova", "capocantiere", "Mantova"),
]

PINE, MOSS, SIGNAL, TIDE, ALERT = "#123B33", "#2F7D5B", "#E8A317", "#2B6CB0", "#C8402F"
INK, MUTE, LINE = "#14211D", "#66756F", "#DCE4DE"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
:root {
    --paper:#F2F5F2; --card:#FFFFFF; --ink:#14211D; --ink2:#3A4A44; --mute:#66756F; --line:#DCE4DE;
    --pine:#123B33; --pine2:#1B5245; --moss:#2F7D5B; --moss-soft:#E3F1E9;
    --signal:#E8A317; --signal-soft:#FDF3D9; --alert:#C8402F; --alert-soft:#FBE7E3;
    --tide:#2B6CB0; --tide-soft:#E6EFF9;
    --display:'Bricolage Grotesque','Segoe UI',system-ui,sans-serif;
    --body:'IBM Plex Sans','Segoe UI',system-ui,sans-serif;
}
html, body, [class*="css"], .stApp { font-family: var(--body); font-variant-numeric: tabular-nums; }
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1480px; padding-top: 1.4rem; padding-bottom: 4rem; }
footer { visibility: hidden; }

.stMarkdown p, .stMarkdown li, [data-testid="stMarkdownContainer"] p { color: var(--ink) !important; }
[data-testid="stMetricLabel"] p { color: var(--mute) !important; }
[data-testid="stMetricValue"] { color: var(--ink) !important; }
[data-testid="stCheckbox"] p, [data-testid="stRadio"] p { color: var(--ink) !important; }
div[data-baseweb="select"] > div, div[data-baseweb="input"], div[data-baseweb="textarea"] { border-radius: 10px !important; }

[data-testid="stTabs"] button p { font-size: 14px; font-weight: 600; color: var(--mute) !important; }
[data-testid="stTabs"] button[aria-selected="true"] p { color: var(--pine) !important; }
[data-testid="stTabs"] button[aria-selected="true"] { border-bottom-color: var(--pine) !important; }
[data-testid="stDataFrame"], [data-testid="stDataEditor"] { border:1px solid var(--line); border-radius: 12px; overflow:hidden; }

section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0F332C 0%, #123B33 55%, #16483D 100%) !important; border-right: 0 !important; }
section[data-testid="stSidebar"] * { color: #E6EFEA !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12) !important; }
.brand { padding: 6px 4px 18px; }
.brand-name { font-family: var(--display); font-weight: 800; font-size: 25px; letter-spacing: -.5px; color: #FFFFFF !important; }
.brand-name b { color: var(--signal) !important; }
.brand-sub { font-size: 12px; color: #A9C2B8 !important; margin-top: 2px; }
.nav-title { font-size: 12px; color: #86A79A !important; margin: 4px 6px 8px; }
section[data-testid="stSidebar"] [role="radiogroup"] { gap: 3px !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label { position: relative; min-height: 40px; border-radius: 10px !important; padding: 4px 12px !important; background: transparent !important; border: 0 !important; transition: background .15s; }
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label p { font-size: 14px !important; font-weight: 500 !important; color: #C9DCD3 !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.07) !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background: rgba(255,255,255,.12) !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::before { content: ""; position: absolute; left: 0; top: 9px; bottom: 9px; width: 4px; border-radius: 0 4px 4px 0; background: var(--signal); }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color: #FFFFFF !important; font-weight: 600 !important; }
.side-user { background: rgba(255,255,255,.08); border-radius: 12px; padding: 11px 13px; }
.side-user b { font-size: 14px; color: #FFFFFF !important; }
.side-user span { display: block; font-size: 12px; color: #A9C2B8 !important; margin-top: 2px; }
section[data-testid="stSidebar"] div.stButton > button { background: rgba(255,255,255,.1) !important; color: #FFFFFF !important; border: 1px solid rgba(255,255,255,.18) !important; }
.page-head { display:flex; justify-content:space-between; align-items:flex-end; margin: 2px 0 18px; gap: 16px; }
.page-title { font-family: var(--display); font-weight: 800; font-size: 34px; letter-spacing: -1px; color: var(--ink); line-height: 1.05; }
.page-sub { color: var(--mute); font-size: 14px; margin-top: 5px; }
.who { border-radius: 999px; padding: 7px 14px; font-size: 13px; font-weight: 500; white-space: nowrap; }
.who i { display:inline-block; width:8px; height:8px; border-radius:50%; background: var(--moss); margin-right:8px; }
.section-title { font-family: var(--display); font-weight: 700; font-size: 19px; color: var(--ink); margin: 26px 0 10px; letter-spacing: -.3px; }
.section-note { color: var(--mute); font-size: 13px; margin: -6px 0 10px; }
.hero-margin { background: radial-gradient(120% 140% at 0% 0%, #1E5A4B 0%, var(--pine) 55%, #0E2F29 100%); color: #FFFFFF; border-radius: 22px; padding: 24px 26px 0; min-height: 268px; position: relative; overflow: hidden; box-shadow: 0 18px 40px rgba(18,59,51,.22); }
.hm-top { display:flex; justify-content:space-between; align-items:center; }
.hm-label { font-size: 15px; font-weight: 500; color: #BBD5CA; }
.hm-value { font-family: var(--display); font-weight: 800; font-size: 50px; letter-spacing: -2px; line-height: 1.05; margin-top: 10px; color: #FFFFFF; }
.hm-value.neg { color: #FFB4A8; }
.hm-sub { color: #CFE3DA; font-size: 14px; margin-top: 6px; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.hm-spark { position:absolute; left:0; right:0; bottom:0; height:92px; }
.hm-spark svg { width:100%; height:100%; display:block; }
.stats-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 22px 30px; padding: 6px 4px 0 6px; }
.stat { border-left: 3px solid var(--line); padding: 2px 0 2px 16px; position: relative; min-height: 96px; }
.stat.moss { border-left-color: var(--moss); } .stat.tide { border-left-color: var(--tide); }
.stat.signal { border-left-color: var(--signal); } .stat.alert { border-left-color: var(--alert); }
.stat-label { font-size: 13px; color: var(--mute); font-weight: 500; }
.stat-value { font-family: var(--display); font-weight: 700; font-size: 30px; letter-spacing: -1px; color: var(--ink); line-height: 1.15; margin-top: 3px; }
.stat-note { font-size: 12px; color: var(--mute); margin-top: 3px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.stat-spark { position:absolute; right:0; top:14px; width:96px; height:34px; opacity:.95; }
.stat-spark svg { width:100%; height:100%; display:block; }
.strip { display:grid; grid-template-columns: repeat(4, 1fr); gap: 0; border:1px solid var(--line); border-radius: 14px; margin-top: 18px; }
.strip .cell { padding: 15px 20px; border-right: 1px solid var(--line); }
.strip .cell:last-child { border-right: 0; }
.cell-label { font-size: 13px; color: var(--mute); }
.cell-value { font-family: var(--display); font-weight: 700; font-size: 23px; letter-spacing: -.5px; margin-top: 3px; color: var(--ink); }
.cell-note { font-size: 12px; color: var(--mute); margin-top: 2px; }
.chip { display:inline-block; border-radius: 999px; padding: 4px 11px; font-size: 12px; font-weight: 600; }
.chip.ok { background: var(--moss-soft); color: #1E5C41 !important; }
.chip.warn { background: var(--signal-soft); color: #7A5200 !important; }
.chip.bad { background: var(--alert-soft); color: #9B2A1D !important; }
.chip.info { background: var(--tide-soft); color: #1F548F !important; }
.chip.dark { background: rgba(255,255,255,.14); color: #FFFFFF !important; }
.delta { font-size: 12px; font-weight: 600; border-radius: 6px; padding: 1px 7px; }
.delta.ok { background: var(--moss-soft); color: #1E5C41; } .delta.bad { background: var(--alert-soft); color: #9B2A1D; }
.hero-margin .delta.ok { background: rgba(120,220,170,.2); color:#B8F0D3; } .hero-margin .delta.bad { background: rgba(255,140,120,.2); color:#FFC9BF; }
.pill { display:inline-block; border-radius: 8px; padding: 5px 10px; margin: 3px 6px 3px 0; font-size: 13px; font-weight: 500; background: #EEF2EF; color: var(--ink2) !important; }
.pill.ok { background: var(--moss-soft); color: #1E5C41 !important; }
.pill.warn { background: var(--signal-soft); color: #7A5200 !important; }
.pill.bad { background: var(--alert-soft); color: #9B2A1D !important; }
.panel { border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; margin-bottom: 12px; }
.panel-head { font-family: var(--display); font-weight: 700; font-size: 16px; color: var(--ink); }
.panel-sub { font-size: 13px; color: var(--mute); margin-top: 3px; }
.chart-head { margin: 0 2px 6px; }
.svc { padding: 12px 0; border-bottom: 1px solid var(--line); }
.svc:last-child { border-bottom: 0; }
.svc-name { font-weight: 600; font-size: 14px; color: var(--ink); margin-bottom: 2px; }
.check { display:flex; gap: 14px; align-items:flex-start; padding: 13px 16px; border:1px solid var(--line); border-left-width: 4px; border-radius: 10px; margin-bottom: 8px; }
.check.ok { border-left-color: var(--moss); } .check.warn { border-left-color: var(--signal); } .check.bad { border-left-color: var(--alert); }
.check-title { font-weight: 600; font-size: 14px; color: var(--ink); }
.check-msg { font-size: 13px; color: var(--mute); margin-top: 2px; }
.check-n { margin-left:auto; font-family: var(--display); font-weight: 700; font-size: 20px; color: var(--ink); }
.login { max-width: 460px; margin: 9vh auto 18px; background: linear-gradient(150deg, #1B5245 0%, var(--pine) 70%); color:#fff; border-radius: 24px; padding: 34px 34px 28px; box-shadow: 0 24px 60px rgba(18,59,51,.28); }
.login .brand-name { font-size: 34px; color: #FFFFFF !important; }
.login p { color: #CFE3DA; font-size: 15px; margin: 8px 0 0; }
div.stButton > button, div.stDownloadButton > button { min-height: 42px; border-radius: 10px; font-weight: 600; }
div.stButton > button[kind="primary"] { background: var(--pine) !important; color:#FFFFFF !important; border-color: var(--pine) !important; }
div.stButton > button:not([kind="primary"]), div.stDownloadButton > button { border-color: var(--line) !important; }
.foot { text-align:center; color: var(--mute); font-size: 12px; padding: 34px 0 4px; }
</style>
""",
    unsafe_allow_html=True,
)

def sx(fn, *args, **kwargs):
    try: return fn(*args, width="stretch", **kwargs)
    except Exception: return fn(*args, use_container_width=True, **kwargs)

def html(text): st.markdown(text, unsafe_allow_html=True)

def txt(value):
    if value is None: return ""
    try:
        if pd.isna(value): return ""
    except (TypeError, ValueError): pass
    return str(value).strip()

def norm_txt(value):
    t = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()

def clean_col(value):
    t = norm_txt(str(value).replace("\ufeff", ""))
    t = t.replace("€", "euro").replace("/", "_").replace("-", "_").replace(" ", "_")
    return re.sub(r"_+", "_", t).strip("_")

def normalize_columns(df):
    if df is None: return pd.DataFrame()
    out = df.copy()
    out.columns = [clean_col(c) for c in out.columns]
    return out

def aliases_rename(df, aliases):
    df = normalize_columns(df)
    mapping = {}
    for target, names in aliases.items():
        for candidate in [target] + list(names):
            c = clean_col(candidate)
            if c in df.columns:
                mapping[c] = target
                break
    return df.rename(columns=mapping) if mapping else df

def ensure(df, columns):
    out = df.copy() if df is not None else pd.DataFrame()
    for col in columns:
        if col not in out.columns: out[col] = ""
    return out

def parse_num(value):
    if value is None: return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)): return 0.0 if pd.isna(value) else float(value)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "nat"}: return 0.0
    text = text.replace("€", "").replace("EUR", "").replace("eur", "").replace(" ", "")
    if "," in text and "." in text: text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text: text = text.replace(",", ".")
    elif text.count(".") == 1:
        a, b = text.split(".")
        if len(b) == 3 and a.lstrip("-").isdigit() and len(a.lstrip("-")) <= 3 and a not in {"0", "-0"}: text = a + b 
    try: return float(text)
    except ValueError: return 0.0

def parse_hours(value, excel_fraction=False):
    if value is None: return 0.0
    if isinstance(value, dtime): return value.hour + value.minute / 60 + value.second / 3600
    if isinstance(value, (timedelta, pd.Timedelta)): return value.total_seconds() / 3600
    if isinstance(value, (int, float, np.integer, np.floating)):
        if pd.isna(value): return 0.0
        n = float(value)
        return n * 24 if (excel_fraction and 0 < n < 1) else n
    text = str(value).strip()
    if not text: return 0.0
    if ":" in text:
        parts = text.split(":")
        try: return float(parts[0]) + (float(parts[1]) if len(parts) > 1 else 0.0) / 60 + (float(parts[2]) if len(parts) > 2 else 0.0) / 3600
        except ValueError: pass
    return parse_num(text)

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

def parse_date(value):
    if isinstance(value, (pd.Timestamp, datetime, date)): return pd.Timestamp(value)
    if value is None or txt(value) == "": return pd.NaT
    t = str(value).strip()
    try:
        if ISO_RE.match(t): return pd.to_datetime(t, errors="coerce")
        return pd.to_datetime(t, dayfirst=True, errors="coerce")
    except Exception: return pd.NaT

def time_to_min(value):
    if isinstance(value, dtime): return value.hour * 60 + value.minute
    m = re.match(r"^(\d{1,2}):(\d{2})", str(value).strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None

def safe_sum(series):
    if series is None: return 0.0
    try: return float(pd.Series(series).apply(parse_num).sum())
    except Exception: return 0.0

def euro(value):
    x = parse_num(value)
    return f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def num(value, decimals=1):
    x = parse_num(value)
    return f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def pct(value):
    return f"{parse_num(value):.1f}%".replace(".", ",")

def split_list(value, seps=r"[;,|\n]+"):
    if value is None: return []
    return [p.strip() for p in re.split(seps, str(value)) if p.strip() and p.strip().lower() != "nan"]

def plate_key(value):
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())

def centro_costo(service, subservice):
    return f"{service} / {subservice}"

def is_admin():
    return str(st.session_state.get("ruolo", "")).lower() in {"admin", "direzione"}

def status_for_margin(margin, margin_pct, has_data):
    if not has_data: return "Nessun dato", "Nessun consuntivo nel periodo", "warn"
    if margin < 0: return "Critico", "Margine negativo", "bad"
    if margin_pct < 5: return "Attenzione", "Margine molto contenuto", "warn"
    return "In equilibrio", "Margine sotto controllo", "ok"

def read_csv_flexible(path):
    if not os.path.exists(path): return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        try:
            df = pd.read_csv(path, sep=None, engine="python", dtype=str, keep_default_na=False, encoding=enc)
            if len(df.columns) > 1: return normalize_columns(df)
        except Exception: continue
    return pd.DataFrame()

def _fmt_cell(v):
    if isinstance(v, (pd.Timestamp, datetime)):
        if pd.isna(v): return ""
        return v.strftime("%Y-%m-%d %H:%M:%S") if (v.hour or v.minute or v.second) else v.strftime("%Y-%m-%d")
    if isinstance(v, date): return v.isoformat()
    return v

def save_csv(df, path):
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object or pd.api.types.is_datetime64_any_dtype(out[c]): out[c] = out[c].map(_fmt_cell)
    tmp = path + ".tmp"
    out.to_csv(tmp, index=False, encoding="utf-8-sig", float_format="%.4f")
    os.replace(tmp, path)

def append_rows(key, reader, new_rows):
    if new_rows is None or len(new_rows) == 0: return
    current = reader()
    save_csv(pd.concat([current, new_rows], ignore_index=True), FILES[key])

def load_table(key, aliases, cols, text=(), dates=(), hours=(), numbers=()):
    full = {c: list(aliases.get(c, [])) for c in cols}
    df = ensure(aliases_rename(read_csv_flexible(FILES[key]), full), cols)[cols].copy()
    for c in text: df[c] = df[c].astype(str).str.strip()
    for c in dates: df[c] = pd.to_datetime(df[c].apply(parse_date), errors="coerce")
    for c in hours: df[c] = df[c].apply(parse_hours)
    for c in numbers: df[c] = df[c].apply(parse_num)
    return df

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"pbkdf2${salt}${digest}"

def check_password(stored, password):
    stored = str(stored)
    if stored.startswith("pbkdf2$"):
        try: _, salt, digest = stored.split("$")
        except ValueError: return False
        cand = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
        return hmac.compare_digest(cand, digest)
    return bool(stored) and hmac.compare_digest(stored, password)

CERT_ALIASES = {
    "ID": ["id_servizio", "id_record", "id_certificazione"], "Codice": ["codice_servizio", "codice_mezzo", "code"],
    "Descrizione": ["descrizione_servizio", "descrizione_mezzo", "description"], "Comuni": ["comune", "comuni", "territorio", "citta"],
    "Centro di Costo": ["centro_di_costo", "centro_costo", "cost_center"], "Data Pianificazione": ["data_pianificazione", "planning_date"],
    "Inizio Pianificazione": ["inizio_pianificazione", "planning_start"], "Fine Pianificazione": ["fine_pianificazione", "planning_end"],
    "Orario Previsto": ["orario_previsto", "durata_prevista", "planned_duration"], "Data Svolgimento": ["data_svolgimento", "data_esecuzione", "execution_date"],
    "Inizio Svolgimento": ["inizio_svolgimento", "inizio_esecuzione", "execution_start"], "Fine Svolgimento": ["fine_svolgimento", "fine_esecuzione", "execution_end"],
    "Durata": ["durata_svolgimento", "ore", "ore_lavorate", "duration"], "Operatori": ["operatore", "dipendente", "addetto", "operatori", "personale"],
    "Targa": ["targa", "plate"], "Attrezzatura": ["attrezzatura", "equipment", "mezzo", "veicolo"],
    "Note": ["note", "commenti"], "Stato": ["stato", "status", "stato_servizio"],
}
CERT_COLUMNS = list(CERT_ALIASES.keys())
CERT_TEXT = ["ID", "Codice", "Descrizione", "Comuni", "Centro di Costo", "Operatori", "Targa", "Attrezzatura", "Note", "Stato"]
CERT_TIMES = ["Inizio Pianificazione", "Fine Pianificazione", "Inizio Svolgimento", "Fine Svolgimento"]

def is_certified(stato): return norm_txt(stato).startswith("certific")

def cert_key(df):
    d = pd.to_datetime(df["Data Analisi"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    return (df["ID"].astype(str) + "|" + d + "|" + df["Operatori"].astype(str) + "|" + df["Targa"].astype(str)
            + "|" + df["Attrezzatura"].astype(str) + "|" + df["Inizio Svolgimento"].astype(str))

def prepare_cert(df):
    df = df.copy()
    if df.empty:
        df["Data Analisi"] = pd.Series(dtype="datetime64[ns]"); df["Scostamento"] = pd.Series(dtype=float); df["Chiave"] = pd.Series(dtype=object)
        return df
    df["Data Analisi"] = pd.to_datetime(df["Data Svolgimento"], errors="coerce").fillna(pd.to_datetime(df["Data Pianificazione"], errors="coerce"))
    def duration(row):
        if row["Durata"] > 0: return row["Durata"]
        s, e = time_to_min(row["Inizio Svolgimento"]), time_to_min(row["Fine Svolgimento"])
        return ((e - s) % 1440) / 60 if (s is not None and e is not None) else 0.0
    df["Durata"] = df.apply(duration, axis=1)
    df["Stato"] = df["Stato"].replace("", "Da verificare")
    df["Scostamento"] = np.where(df["Orario Previsto"] > 0, df["Durata"] - df["Orario Previsto"], 0.0)
    df["Chiave"] = cert_key(df)
    return df

def normalize_certification(raw, duration_mode="auto"):
    df = ensure(aliases_rename(raw, CERT_ALIASES), CERT_COLUMNS)[CERT_COLUMNS].copy()
    for col in CERT_TEXT: df[col] = df[col].map(txt).str.replace(r"\.0$", "", regex=True) if col == "ID" else df[col].map(txt)
    for col in ["Data Pianificazione", "Data Svolgimento"]: df[col] = pd.to_datetime(df[col].apply(parse_date), errors="coerce")
    for col in CERT_TIMES: df[col] = df[col].map(txt)
    def convert(col):
        s = df[col]
        numbers = [float(x) for x in s if isinstance(x, (int, float, np.integer, np.floating)) and not pd.isna(x)]
        fraction = duration_mode == "frazione" or (duration_mode == "auto" and bool(numbers) and max(numbers) <= 1.0)
        return s.apply(lambda v: parse_hours(v, excel_fraction=fraction))
    df["Orario Previsto"] = convert("Orario Previsto")
    df["Durata"] = convert("Durata")
    return prepare_cert(df)

def score_cert_header(df):
    if df is None or df.empty: return 0
    cols = {clean_col(c) for c in df.columns}
    known = set()
    for target, names in CERT_ALIASES.items():
        known.add(clean_col(target)); known.update(clean_col(x) for x in names)
    return len(cols & known)

def load_uploaded_raw(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        raw = uploaded.getvalue()
        for enc in ("utf-8-sig", "utf-8", "latin1"):
            try: text = raw.decode(enc); break
            except UnicodeDecodeError: continue
        else: raise ValueError("Codifica del CSV non riconosciuta.")
        return pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str, keep_default_na=False)
    if name.endswith((".xlsx", ".xls")):
        excel = pd.ExcelFile(uploaded)
        best, best_score = None, -1
        for sheet in excel.sheet_names:
            for header in range(0, 4):
                try:
                    sample = pd.read_excel(excel, sheet_name=sheet, header=header, nrows=30)
                    score = score_cert_header(sample)
                    if score > best_score: best, best_score = pd.read_excel(excel, sheet_name=sheet, header=header), score
                except Exception: continue
        if best is None or best_score < 3: raise ValueError("Non trovo le colonne della certificazione.")
        return best
    raise ValueError("Formato non supportato: usa CSV o Excel.")

def init_files():
    if not os.path.exists(FILES["users"]):
        save_csv(pd.DataFrame([{"username": u, "password": hash_password(DEFAULT_PASSWORDS[u]), "nome": n, "ruolo": r, "autorizzazioni": a} for u, n, r, a in DEFAULT_USERS_META]), FILES["users"])
    empties = {
        "operators": ["Matricola", "Nome", "Cognome", "Contratto", "Livello", "Sottoservizio"],
        "vehicles": ["Targa", "Mezzo", "Tipo", "Sottoservizio"],
        "services": ["ID", "Data", "Servizio", "Sottoservizio", "Centro di Costo", "Tonnellate", "Ricavi", "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Ore Uomo", "Ore Mezzi", "Note", "Creato Da", "Periodo Da", "Periodo A", "Anomalie"],
        "personnel": ["ID Consuntivo", "Certificazione ID", "Data", "Servizio", "Sottoservizio", "Matricola", "Operatore", "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale", "Stato Match"],
        "vehicle_detail": ["ID Consuntivo", "Certificazione ID", "Data", "Servizio", "Sottoservizio", "Targa", "Attrezzatura", "Tipo", "Ore", "Costo Orario", "Costo Totale", "Stato Match"],
        "certifications": ["ID Import", "Data Import", "File", "Righe", "Ore", "Stato", "Operatore"],
        "cert_rows": CERT_COLUMNS + ["ID Import"],
    }
    for key, cols in empties.items():
        if not os.path.exists(FILES[key]): save_csv(pd.DataFrame(columns=cols), FILES[key])
    if not os.path.exists(FILES["tariffs"]):
        rows = [{"Tipo": "Personale", "Contratto": c, "Livello_o_Tipo": lv, "Costo_Orario": 0.0, "Attivo": "SI"} for c, levels in CONTRACTS.items() for lv in levels]
        rows += [{"Tipo": "Mezzo", "Contratto": "", "Livello_o_Tipo": k, "Costo_Orario": v, "Attivo": "SI"} for k, v in DEFAULT_VEHICLE_COSTS.items()]
        rows += [{"Tipo": "Generale", "Contratto": "", "Livello_o_Tipo": "Overhead", "Costo_Orario": 15.0, "Attivo": "SI"},
                 {"Tipo": "Generale", "Contratto": "", "Livello_o_Tipo": "Tariffa tonnellata", "Costo_Orario": 130.0, "Attivo": "SI"},
                 {"Tipo": "Ricavo Tonnellata", "Contratto": "Ingombranti", "Livello_o_Tipo": "Prato", "Costo_Orario": 140.0, "Attivo": "SI"},
                 {"Tipo": "Ricavo Tonnellata", "Contratto": "Ingombranti", "Livello_o_Tipo": "Mugello", "Costo_Orario": 160.0, "Attivo": "SI"}]
        save_csv(pd.DataFrame(rows), FILES["tariffs"])

init_files()

def read_users():
    cols = ["username", "password", "nome", "ruolo", "autorizzazioni"]
    df = ensure(aliases_rename(read_csv_flexible(FILES["users"]), {"username": ["user", "utente", "login"], "password": ["pass", "pwd"], "nome": ["name", "nominativo"], "ruolo": ["role", "profilo"], "autorizzazioni": ["cantieri", "commesse", "cantiere", "accessi"]}), cols)[cols].copy()
    for c in cols: df[c] = df[c].astype(str).str.strip()
    return df

def read_operators():
    cols = ["Matricola", "Nome", "Cognome", "Contratto", "Livello", "Sottoservizio"]
    return load_table("operators", {"Matricola": ["id_operatore", "codice_operatore", "employee_id"], "Nome": ["first_name"], "Cognome": ["last_name"], "Contratto": ["ccnl"], "Livello": ["level", "inquadramento"], "Sottoservizio": ["cantiere", "commessa", "subservice"]}, cols, text=cols)

def read_vehicles():
    cols = ["Targa", "Mezzo", "Tipo", "Sottoservizio"]
    return load_table("vehicles", {"Targa": ["plate"], "Mezzo": ["veicolo", "vehicle"], "Tipo": ["tipo_mezzo", "categoria_mezzo"], "Sottoservizio": ["cantiere", "commessa", "subservice"]}, cols, text=cols)

def read_tariffs():
    cols = ["Tipo", "Contratto", "Livello_o_Tipo", "Costo_Orario", "Attivo"]
    df = load_table("tariffs", {"Tipo": ["tipo_costo", "categoria"], "Contratto": ["ccnl"], "Livello_o_Tipo": ["livello", "livello_o_tipo", "voce", "tipo_mezzo"], "Costo_Orario": ["costo_orario", "costo", "tariffa", "prezzo"], "Attivo": ["attiva", "active"]}, cols, numbers=["Costo_Orario"])
    df["Attivo"] = df["Attivo"].replace("", "SI")
    return df

SERVICES_COLS = ["ID", "Data", "Servizio", "Sottoservizio", "Centro di Costo", "Tonnellate", "Ricavi", "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Ore Uomo", "Ore Mezzi", "Note", "Creato Da", "Periodo Da", "Periodo A", "Anomalie"]

def read_services():
    df = load_table("services", {"ID": ["id_consuntivo"], "Data": ["data_servizio", "giorno", "date"], "Servizio": ["categoria", "servizio_principale", "tipo_servizio"], "Sottoservizio": ["sotto_servizio", "dettaglio", "cantiere", "commessa"], "Centro di Costo": ["centro_di_costo", "centro_costo"], "Tonnellate": ["ton", "tonnellaggio"], "Ricavi": ["ricavo", "ricavi_euro", "revenue", "fatturato"], "Costo Personale": ["costo_personale"], "Costo Mezzi": ["costo_mezzi"], "Costo Totale": ["costo", "costi", "costo_totale"], "Margine": ["margine_netto", "profitto"], "Ore Uomo": ["ore_personale", "ore_operatori"], "Ore Mezzi": ["ore_veicoli"], "Creato Da": ["operatore", "utente", "created_by"]}, SERVICES_COLS, text=["ID", "Servizio", "Sottoservizio", "Centro di Costo", "Note", "Creato Da"], dates=["Data", "Periodo Da", "Periodo A"], hours=["Ore Uomo", "Ore Mezzi"], numbers=["Tonnellate", "Ricavi", "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Anomalie"])
    if not df.empty:
        missing = df["Margine"].eq(0) & (df["Ricavi"].ne(0) | df["Costo Totale"].ne(0))
        df.loc[missing, "Margine"] = df.loc[missing, "Ricavi"] - df.loc[missing, "Costo Totale"]
        no_cc = df["Centro di Costo"].eq("")
        if not no_cc.empty and no_cc.any(): df.loc[no_cc, "Centro di Costo"] = df.loc[no_cc].apply(lambda r: centro_costo(r["Servizio"], r["Sottoservizio"]), axis=1)
    return df

def read_personnel():
    cols = ["ID Consuntivo", "Certificazione ID", "Data", "Servizio", "Sottoservizio", "Matricola", "Operatore", "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale", "Stato Match"]
    return load_table("personnel", {"ID Consuntivo": ["id_consuntivo"], "Certificazione ID": ["certificazione_id", "id_certificazione", "id_import"], "Servizio": ["categoria"], "Sottoservizio": ["cantiere", "commessa", "dettaglio"], "Operatore": ["dipendente", "addetto"], "Contratto": ["ccnl"], "Livello": ["level", "inquadramento"], "Ore": ["ore_lavorate", "hours"], "Costo Orario": ["tariffa"], "Costo Totale": ["costo"], "Stato Match": ["match"]}, cols, text=["ID Consuntivo", "Certificazione ID", "Servizio", "Sottoservizio", "Matricola", "Operatore", "Contratto", "Livello", "Stato Match"], dates=["Data"], hours=["Ore"], numbers=["Costo Orario", "Costo Totale"])

def read_vehicle_detail():
    cols = ["ID Consuntivo", "Certificazione ID", "Data", "Servizio", "Sottoservizio", "Targa", "Attrezzatura", "Tipo", "Ore", "Costo Orario", "Costo Totale", "Stato Match"]
    return load_table("vehicle_detail", {"ID Consuntivo": ["id_consuntivo"], "Certificazione ID": ["certificazione_id", "id_certificazione", "id_import"], "Servizio": ["categoria"], "Sottoservizio": ["cantiere", "commessa", "dettaglio"], "Tipo": ["tipo_mezzo"], "Ore": ["ore_lavorate", "hours"], "Costo Orario": ["tariffa"], "Costo Totale": ["costo"], "Stato Match": ["match"]}, cols, text=["ID Consuntivo", "Certificazione ID", "Servizio", "Sottoservizio", "Targa", "Attrezzatura", "Tipo", "Stato Match"], dates=["Data"], hours=["Ore"], numbers=["Costo Orario", "Costo Totale"])

def read_imports():
    cols = ["ID Import", "Data Import", "File", "Righe", "Ore", "Stato", "Operatore"]
    return load_table("certifications", {"ID Import": ["id_import"], "Data Import": ["data_import"]}, cols, text=["ID Import", "File", "Stato", "Operatore"], dates=["Data Import"], numbers=["Righe", "Ore"])

def read_cert_rows():
    df = ensure(aliases_rename(read_csv_flexible(FILES["cert_rows"]), {**CERT_ALIASES, "ID Import": ["id_import", "import_id"]}), CERT_COLUMNS + ["ID Import"])[CERT_COLUMNS + ["ID Import"]].copy()
    for c in CERT_TEXT + CERT_TIMES + ["ID Import"]: df[c] = df[c].map(txt)
    for c in ["Data Pianificazione", "Data Svolgimento"]: df[c] = pd.to_datetime(df[c].apply(parse_date), errors="coerce")
    df["Orario Previsto"] = df["Orario Previsto"].apply(parse_hours)
    df["Durata"] = df["Durata"].apply(parse_hours)
    return prepare_cert(df)

def split_access(value):
    raw = str(value).strip()
    if raw.upper() in {"TUTTI", "ALL", "*"}: return ALL_SUBSERVICES.copy()
    return sorted({x.strip() for x in re.split(r"[,;|]", raw) if x.strip() in ALL_SUBSERVICES})

def authorized(df, column="Sottoservizio"):
    if df is None: return pd.DataFrame()
    if df.empty or is_admin(): return df.copy()
    allowed = st.session_state.get("allowed_subservices", [])
    if not allowed or column not in df.columns: return df.iloc[0:0].copy()
    return df[df[column].astype(str).str.strip().isin(allowed)].copy()

def rate_lookup(tariffs, tipo, key, contract=None):
    m = (tariffs["Tipo"].astype(str).str.lower().eq(tipo.lower())
         & tariffs["Livello_o_Tipo"].astype(str).str.strip().str.lower().eq(str(key).strip().lower())
         & tariffs["Attivo"].astype(str).str.upper().eq("SI"))
    if contract is not None and str(contract).strip(): m &= tariffs["Contratto"].astype(str).str.strip().eq(str(contract).strip())
    d = tariffs.loc[m, "Costo_Orario"]
    return float(d.iloc[0]) if not d.empty else None

def labor_rate(tariffs, contract, level): return rate_lookup(tariffs, "personale", level, contract) or 0.0
def vehicle_rate(tariffs, kind): return rate_lookup(tariffs, "mezzo", kind) or 0.0
def general_rate(tariffs, name, default=0.0):
    v = rate_lookup(tariffs, "generale", name)
    return default if v is None else v

def _has_term(text, term): return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None

def rows_for_subservice(cert, subservice):
    if cert.empty: return cert.copy()
    target = norm_txt(subservice)
    longer = [norm_txt(s) for s in ALL_SUBSERVICES if target in norm_txt(s) and norm_txt(s) != target]
    def ok(row):
        parts = [norm_txt(p) for p in re.split(r"[;,/|]+", str(row["Comuni"])) if p.strip()]
        if target in parts: return True
        blob = norm_txt(f'{row["Centro di Costo"]} {row["Descrizione"]}')
        return _has_term(blob, target) and not any(_has_term(blob, lg) for lg in longer)
    return cert[cert.apply(ok, axis=1)].copy()

def rows_for_service(cert, service):
    if cert.empty:
        out = cert.copy(); out["Attribuzione"] = pd.Series(dtype=object); return out
    svc = norm_txt(service)
    others = [norm_txt(s) for s in SERVICE_TREE if norm_txt(s) != svc]
    blob = (cert["Centro di Costo"].astype(str) + " " + cert["Descrizione"].astype(str)).map(norm_txt)
    this = blob.map(lambda t: _has_term(t, svc))
    other = blob.map(lambda t: any(_has_term(t, o) for o in others))
    out = cert[this | ~other].copy()
    out["Attribuzione"] = np.where(this[out.index], "Servizio indicato nel file", "Solo sottoservizio")
    return out

PEOPLE_COLS = ["Certificazione ID", "Operatore", "Matricola", "Contratto", "Livello", "Ore", "Data", "Inizio", "Fine", "Stato Match"]
VEHICLE_COLS = ["Certificazione ID", "Targa", "Attrezzatura", "Tipo", "Ore", "Data", "Stato Match"]

def op_lookup(operators):
    lookup = {}
    for _, r in operators.iterrows():
        for k in (f'{r["Nome"]} {r["Cognome"]}', f'{r["Cognome"]} {r["Nome"]}', r["Matricola"]):
            k = norm_txt(k)
            if k: lookup.setdefault(k, r)
    return lookup

def expand_people(cert, operators):
    lookup, rows = op_lookup(operators), []
    for _, r in cert.iterrows():
        for person in split_list(r["Operatori"]):
            found = lookup.get(norm_txt(person))
            rows.append({
                "Certificazione ID": r["ID"], "Operatore": person, "Matricola": "" if found is None else found["Matricola"],
                "Contratto": "" if found is None else found["Contratto"], "Livello": "" if found is None else found["Livello"],
                "Ore": float(r["Durata"]), "Data": r["Data Analisi"], "Inizio": r["Inizio Svolgimento"], "Fine": r["Fine Svolgimento"],
                "Stato Match": "MATCH ANAGRAFICA" if found is not None else "DA ASSEGNARE",
            })
    return pd.DataFrame(rows, columns=PEOPLE_COLS)

def expand_vehicles(cert, vehicles):
    lookup = {plate_key(r["Targa"]): r for _, r in vehicles.iterrows() if plate_key(r["Targa"])}
    rows = []
    for _, r in cert.iterrows():
        plates = split_list(r["Targa"], r"[;,|/\n]+")
        if not plates and txt(r["Attrezzatura"]): plates = [""]
        for plate in plates:
            found = lookup.get(plate_key(plate)) if plate else None
            rows.append({
                "Certificazione ID": r["ID"], "Targa": plate, "Attrezzatura": r["Attrezzatura"],
                "Tipo": "" if found is None else found["Tipo"], "Ore": float(r["Durata"]), "Data": r["Data Analisi"],
                "Stato Match": "MATCH ANAGRAFICA" if found is not None else "DA ASSEGNARE",
            })
    return pd.DataFrame(rows, columns=VEHICLE_COLS)

def find_overlaps(people):
    p = people.copy()
    p["Data"] = pd.to_datetime(p["Data"], errors="coerce")
    p = p[p["Operatore"].map(txt).ne("") & p["Data"].notna()].copy()
    p["s"] = p["Inizio"].map(time_to_min); p["e"] = p["Fine"].map(time_to_min)
    p = p.dropna(subset=["s", "e"])
    rows = []
    for (op, day), g in p.groupby(["Operatore", p["Data"].dt.date]):
        prev_end, prev_id = None, ""
        for _, r in g.sort_values("s").iterrows():
            end = r["e"] if r["e"] >= r["s"] else r["e"] + 1440
            if prev_end is not None and r["s"] < prev_end:
                rows.append({"Operatore": op, "Data": day, "Servizio A": prev_id, "Servizio B": r["Certificazione ID"],
                             "Inizio B": r["Inizio"], "Fine A": f"{int(prev_end % 1440) // 60:02d}:{int(prev_end % 1440) % 60:02d}"})
            if prev_end is None or end > prev_end: prev_end, prev_id = end, r["Certificazione ID"]
    return pd.DataFrame(rows)

def run_checks(cert, operators, vehicles, max_day_hours=12.0, tol_pct=10.0):
    checks, details = [], {}
    def add(sev, name, ok_msg, ko_msg, frame=None):
        n = 0 if frame is None else len(frame)
        checks.append({"sev": "ok" if n == 0 else sev, "name": name, "msg": ok_msg if n == 0 else ko_msg, "n": n})
        if n: details[name] = frame
    people, vehs = expand_people(cert, operators), expand_vehicles(cert, vehicles)
    cols = ["ID", "Comuni", "Data Analisi", "Durata", "Operatori", "Targa", "Stato"]

    add("bad", "Durata mancante", "Tutte le righe hanno una durata.", "Righe con durata pari a zero.", cert[cert["Durata"] <= 0][cols])
    add("warn", "Data mancante", "Tutte le righe hanno una data.", "Righe senza data di svolgimento.", cert[cert["Data Analisi"].isna()][cols])
    dup = cert[cert["Chiave"].duplicated(keep=False)]
    add("bad", "Righe duplicate", "Nessuna riga duplicata.", "Righe identiche presenti più volte.", dup[cols])
    
    if not people.empty:
        unknown = people[people["Stato Match"] == "DA ASSEGNARE"].groupby("Operatore", as_index=False).agg(Righe=("Ore", "size"), Ore=("Ore", "sum"))
        add("warn", "Operatori fuori anagrafica", "Tutti gli operatori sono in anagrafica.", "Operatori senza contratto.", unknown)
        daily = people[people["Operatore"].map(txt).ne("")].assign(Giorno=pd.to_datetime(people["Data"], errors="coerce").dt.date)
        daily = daily.groupby(["Operatore", "Giorno"], as_index=False)["Ore"].sum()
        add("bad", "Ore giornaliere eccessive", f"Nessun operatore supera {num(max_day_hours, 0)} ore.", f"Operatori sopra {num(max_day_hours, 0)} ore.", daily[daily["Ore"] > max_day_hours].sort_values("Ore", ascending=False))
        add("bad", "Sovrapposizioni orarie", "Nessun operatore sovrapposto.", "Operatori con servizi sovrapposti.", find_overlaps(people))
    if not vehs.empty:
        unknown_v = vehs[(vehs["Stato Match"] == "DA ASSEGNARE")].groupby(["Targa", "Attrezzatura"], as_index=False).agg(Righe=("Ore", "size"), Ore=("Ore", "sum"))
        add("warn", "Mezzi fuori anagrafica", "Tutti i mezzi sono in anagrafica.", "Mezzi senza tipologia.", unknown_v)

    planned = cert[cert["Orario Previsto"] > 0].copy()
    if not planned.empty:
        planned["Scostamento %"] = planned["Scostamento"] / planned["Orario Previsto"] * 100
        out = planned[planned["Scostamento %"].abs() > tol_pct][["ID", "Comuni", "Data Analisi", "Orario Previsto", "Durata", "Scostamento", "Scostamento %"]]
        add("warn", "Scostamento previsto", f"Entro {num(tol_pct, 0)}%.", f"Scostamento oltre il {num(tol_pct, 0)}%.", out.sort_values("Scostamento %", key=abs, ascending=False))
    return checks, details, people, vehs

def price_people(df, tariffs):
    out = df.copy()
    out["Ore"] = out["Ore"].apply(parse_hours)
    out = out[~((out["Ore"] <= 0) & (out["Operatore"].map(txt) == ""))].copy()
    rates, states = [], []
    for _, r in out.iterrows():
        c, lv = txt(r.get("Contratto")), txt(r.get("Livello"))
        if not c and not lv: rates.append(0.0); states.append("Da assegnare")
        elif c in CONTRACTS and lv in CONTRACTS[c]:
            rate = labor_rate(tariffs, c, lv)
            rates.append(rate); states.append("OK" if rate > 0 else "Costo da configurare")
        else: rates.append(0.0); states.append("Livello non valido")
    out["Costo Orario"], out["Validita"] = rates, states
    out["Costo Totale"] = out["Ore"] * out["Costo Orario"]
    return out

def price_vehicles(df, tariffs):
    out = df.copy()
    out["Ore"] = out["Ore"].apply(parse_hours)
    out = out[~((out["Ore"] <= 0) & (out["Targa"].map(txt) == "") & (out["Attrezzatura"].map(txt) == ""))].copy()
    rates, states = [], []
    for _, r in out.iterrows():
        kind = txt(r.get("Tipo"))
        rate = vehicle_rate(tariffs, kind) if kind else 0.0
        rates.append(rate)
        states.append("Da assegnare" if not kind else ("OK" if rate > 0 else "Costo da configurare"))
    out["Costo Orario"], out["Validita"] = rates, states
    out["Costo Totale"] = out["Ore"] * out["Costo Orario"]
    return out

PERIODS = ["Tutto", "Ultimi 30 giorni", "Ultimi 90 giorni", "Anno corrente"]

def apply_period(df, label):
    if label == "Tutto" or df.empty: return df.copy(), df.iloc[0:0].copy()
    today = pd.Timestamp.today().normalize()
    if label == "Anno corrente": start, prev_start, prev_end = pd.Timestamp(today.year, 1, 1), pd.Timestamp(today.year - 1, 1, 1), today - pd.DateOffset(years=1)
    else:
        days = 30 if label == "Ultimi 30 giorni" else 90
        start = today - pd.Timedelta(days=days - 1); prev_start, prev_end = start - pd.Timedelta(days=days), start - pd.Timedelta(days=1)
    cur = df[df["Data"].between(start, today + pd.Timedelta(days=1))].copy()
    prev = df[df["Data"].between(prev_start, prev_end + pd.Timedelta(days=1))].copy()
    return cur, prev

def series_of(df, col, n=30):
    if df.empty or df["Data"].isna().all(): return []
    return df.dropna(subset=["Data"]).groupby("Data")[col].sum().sort_index().tail(n).tolist()

def totals(df):
    if df.empty: return dict(revenue=0.0, costs=0.0, margin=0.0, labor_h=0.0, vehicle_h=0.0, tonnes=0.0)
    return dict(revenue=safe_sum(df["Ricavi"]), costs=safe_sum(df["Costo Totale"]), margin=safe_sum(df["Margine"]),
                labor_h=safe_sum(df["Ore Uomo"]), vehicle_h=safe_sum(df["Ore Mezzi"]), tonnes=safe_sum(df["Tonnellate"]))

def spark(values, color=MOSS, w=120, h=36, stroke=2.0):
    v = [float(x) for x in values if pd.notna(x)]
    if len(v) < 2: return ""
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1.0
    pts = [(i / (len(v) - 1) * w, h - 3 - (x - lo) / rng * (h - 8)) for i, x in enumerate(v)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    gid = "g" + hashlib.md5((color + line).encode()).hexdigest()[:8]
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><defs><linearGradient id="{gid}" x1="0" x2="0" y1="0" y2="1">'
            f'<stop offset="0" stop-color="{color}" stop-opacity=".30"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="0,{h} {line} {w},{h}" fill="url(#{gid})"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')

def delta_badge(cur, prev, good_up=True):
    if not prev: return ""
    change = (cur - prev) / abs(prev) * 100
    good = (change >= 0) == good_up
    arrow = "▲" if change >= 0 else "▼"
    return f'<span class="delta {"ok" if good else "bad"}">{arrow} {abs(change):.1f}%</span>'.replace(".", ",", 1)

def page_head(title, subtitle):
    html(f'<div class="page-head"><div><div class="page-title">{title}</div><div class="page-sub">{subtitle}</div></div>'
         f'<div class="who"><i></i>{st.session_state.nome}</div></div>')

def section(title, note=""):
    html(f'<div class="section-title">{title}</div>' + (f'<div class="section-note">{note}</div>' if note else ""))

def chart_head(title, sub=""):
    html(f'<div class="chart-head"><div class="panel-head">{title}</div>' + (f'<div class="panel-sub">{sub}</div>' if sub else "") + '</div>')

def stat_html(label, value, note="", spark_svg="", tone="", delta=""):
    return (f'<div class="stat {tone}"><div class="stat-label">{label}</div><div class="stat-value">{value}</div>'
            f'<div class="stat-note">{note}{delta}</div><div class="stat-spark">{spark_svg}</div></div>')

def strip_html(cells, cols=None):
    body = "".join(f'<div class="cell"><div class="cell-label">{a}</div><div class="cell-value">{b}</div><div class="cell-note">{c}</div></div>' for a, b, c in cells)
    return f'<div class="strip" style="grid-template-columns:repeat({cols or len(cells)},1fr)">{body}</div>'

def style_chart(chart, height=280):
    return (chart.properties(height=height, background="transparent").configure_view(strokeWidth=0)
            .configure_axis(labelColor=MUTE, titleColor=MUTE, gridColor="#E6ECE8", domainColor=LINE, tickColor=LINE, labelFont="IBM Plex Sans", titleFont="IBM Plex Sans", labelFontSize=12)
            .configure_legend(labelColor=INK, labelFont="IBM Plex Sans", labelFontSize=12, symbolType="circle"))

def show_chart(chart): sx(st.altair_chart, chart)

def trend_chart(df):
    d = df.dropna(subset=["Data"])
    if d.empty: return None
    monthly = (d["Data"].max() - d["Data"].min()).days > 75
    g = d.groupby(pd.Grouper(key="Data", freq="MS" if monthly else "D"))[["Ricavi", "Costo Totale", "Margine"]].sum().reset_index()
    if not monthly: g = g[(g[["Ricavi", "Costo Totale", "Margine"]] != 0).any(axis=1)]
    g = g.rename(columns={"Costo Totale": "Costi"}).melt("Data", var_name="Voce", value_name="Euro")
    chart = alt.Chart(g).mark_line(strokeWidth=2.6, interpolate="monotone", point=alt.OverlayMarkDef(size=44, filled=True)).encode(
        x=alt.X("Data:T", title=None, axis=alt.Axis(format="%b %Y" if monthly else "%d/%m", labelOverlap=True)),
        y=alt.Y("Euro:Q", title=None, axis=alt.Axis(format="~s")),
        color=alt.Color("Voce:N", scale=alt.Scale(domain=["Ricavi", "Costi", "Margine"], range=[MOSS, TIDE, SIGNAL]), legend=alt.Legend(orient="top", title=None)),
        tooltip=[alt.Tooltip("Data:T", format="%d/%m/%Y"), "Voce:N", alt.Tooltip("Euro:Q", format=",.2f")])
    return style_chart(chart, 290)

def donut_chart(mix):
    d = pd.DataFrame({"Voce": list(mix.keys()), "Euro": list(mix.values())})
    d = d[d["Euro"] > 0]
    if d.empty: return None
    chart = alt.Chart(d).mark_arc(innerRadius=64, outerRadius=104, cornerRadius=4, padAngle=0.03).encode(
        theta=alt.Theta("Euro:Q"),
        color=alt.Color("Voce:N", scale=alt.Scale(domain=["Personale", "Mezzi", "Overhead"], range=[MOSS, TIDE, SIGNAL]), legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Voce:N", alt.Tooltip("Euro:Q", format=",.2f")])
    return style_chart(chart, 250)

def hbar_chart(d, label_col, value_col, title=None, signed=False, color=TIDE):
    if d.empty: return None
    enc_color = alt.condition(f"datum['{value_col}'] >= 0", alt.value(MOSS), alt.value(ALERT)) if signed else alt.value(color)
    chart = alt.Chart(d).mark_bar(cornerRadiusEnd=4, size=17).encode(
        y=alt.Y(f"{label_col}:N", sort="-x", title=None), x=alt.X(f"{value_col}:Q", title=title, axis=alt.Axis(format="~s")),
        color=enc_color, tooltip=[label_col, alt.Tooltip(f"{value_col}:Q", format=",.2f")])
    return style_chart(chart, max(120, 34 * len(d) + 30))

for _key, _value in {"logged": False, "username": "", "nome": "", "ruolo": "", "allowed_subservices": [], "default_pwd": False, "cert_df": pd.DataFrame(), "cert_file": "", "cert_import_id": "", "cert_sig": ""}.items():
    if _key not in st.session_state: st.session_state[_key] = _value

if not st.session_state.logged:
    html('<div class="login"><div class="brand-name">Cristoforo<b>.</b></div><p>Controllo di ore, mezzi e costi dei servizi. Accedi per aprire la Control Room.</p></div>')
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if sx(st.button, "Accedi", type="primary"):
            users_df = read_users()
            match = users_df[users_df["username"].eq(username.strip())]
            if match.empty or not check_password(match.iloc[0]["password"], password): st.error("Username o password non corretti.")
            else:
                row = match.iloc[0]
                if not str(row["password"]).startswith("pbkdf2$"):  
                    users_df.loc[match.index[0], "password"] = hash_password(password)
                    save_csv(users_df, FILES["users"])
                st.session_state.update(logged=True, username=str(row["username"]), nome=str(row["nome"]), ruolo=str(row["ruolo"]), allowed_subservices=split_access(row["autorizzazioni"]), default_pwd=DEFAULT_PASSWORDS.get(str(row["username"])) == password)
                st.rerun()
    st.stop()

operators = read_operators()
vehicles = read_vehicles()
tariffs = read_tariffs()
services_df = read_services()
personnel_detail = read_personnel()
vehicle_detail = read_vehicle_detail()

def cert_pool():
    archive, current = read_cert_rows(), st.session_state.cert_df
    if current is None or current.empty: return archive
    current = current[[c for c in current.columns if c in archive.columns]]
    pool = pd.concat([archive, current], ignore_index=True)
    pool["ID Import"] = pool["ID Import"].fillna("")
    return pool.drop_duplicates(subset="Chiave", keep="first").reset_index(drop=True)

def cert_visible(pool):
    if is_admin() or pool.empty: return pool
    parts = [rows_for_subservice(pool, s) for s in st.session_state.allowed_subservices]
    return pd.concat(parts).drop_duplicates(subset="Chiave") if parts else pool.iloc[0:0]

PAGE_LABELS = {"Dashboard": "Dashboard", "Ingombranti": "Importa Ingombranti", "Consuntivazione": "Nuovo consuntivo", "Certificazioni": "Certificazioni Standard", "Economico": "Centro di costo", "Anagrafiche": "Anagrafiche", "Tariffari": "Tariffe e contratti", "Accessi": "Accessi"}
pages = ["Dashboard", "Ingombranti", "Consuntivazione", "Certificazioni", "Economico"] + (["Anagrafiche", "Tariffari", "Accessi"] if is_admin() else [])

with st.sidebar:
    html('<div class="brand"><div class="brand-name">Cristoforo<b>.</b></div><div class="brand-sub">Control Room</div></div><div class="nav-title">Menu</div>')
    selected = st.radio("Menu", [PAGE_LABELS[p] for p in pages], label_visibility="collapsed")
    page = next(p for p in pages if PAGE_LABELS[p] == selected)
    st.markdown("---")
    access = "Accesso a tutti i servizi" if is_admin() else f"Accesso a {len(st.session_state.allowed_subservices)} sottoservizi"
    html(f'<div class="side-user"><b>{st.session_state.nome}</b><span>{st.session_state.ruolo}</span><span>{access}</span></div>')
    st.write("")
    if sx(st.button, "Esci"):
        for _k in ["logged", "username", "nome", "ruolo", "allowed_subservices", "default_pwd", "cert_df", "cert_file", "cert_import_id", "cert_sig"]: st.session_state.pop(_k, None)
        st.rerun()

PAGE_META = {
    "Dashboard": ("Control Room", "Ricavi, costi, ore e margine dei servizi in un colpo d'occhio."),
    "Ingombranti": ("Raccolta Ingombranti", "Importa file Excel per calcolare automaticamente ricavi e costi con livelli personalizzati."),
    "Consuntivazione": ("Nuovo consuntivo", "Collega la certificazione a un servizio, controlla il costo e salva il centro di costo."),
    "Certificazioni": ("Certificazioni Standard", "Importa i file di certificazione ordinari per validare ore e mezzi."),
    "Economico": ("Centro di costo", "Ricavi, costi e margine per servizio, sottoservizio, operatore e mezzo."),
    "Anagrafiche": ("Anagrafiche", "Operatori con contratto e livello, mezzi con tipologia."),
    "Tariffari": ("Tariffe e contratti", "Gestisci costo orario personale, costo orario mezzi e Ricavo a Tonnellata per comune."),
    "Accessi": ("Accessi", "Utenti, password e sottoservizi autorizzati."),
}
page_head(*PAGE_META[page])
if st.session_state.get("flash"): st.success(st.session_state.pop("flash"))

# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":
    base = authorized(services_df)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    service_filter = c1.selectbox("Servizio", ["Tutti"] + list(SERVICE_TREE))
    subs = ALL_SUBSERVICES if service_filter == "Tutti" else SERVICE_TREE[service_filter]
    if not is_admin(): subs = [x for x in subs if x in st.session_state.allowed_subservices]
    sub_filter = c2.selectbox("Sottoservizio", ["Tutti"] + list(subs))
    period = c3.selectbox("Periodo", PERIODS)

    df = base
    if service_filter != "Tutti": df = df[df["Servizio"].eq(service_filter)]
    if sub_filter != "Tutti": df = df[df["Sottoservizio"].eq(sub_filter)]
    cur, prev = apply_period(df, period)
    t, p = totals(cur), totals(prev)
    m_pct = t["margin"] / t["revenue"] * 100 if t["revenue"] else 0.0
    scope_label = sub_filter if sub_filter != "Tutti" else (service_filter if service_filter != "Tutti" else "di tutte le attività")

    if base.empty: st.info("Non ci sono ancora consuntivi salvati nel database.")
    s_label, s_text, s_class = status_for_margin(t["margin"], m_pct, not cur.empty)
    vs_prev = delta_badge(t["margin"], p["margin"]) + (' <span style="opacity:.75">sul periodo precedente</span>' if p["margin"] else "")
    left, right = st.columns([1, 1.55])
    with left:
        html(f'<div class="hero-margin"><div class="hm-top"><span class="hm-label">Margine {scope_label}</span><span class="chip dark">{s_label}</span></div>'
             f'<div class="hm-value {"neg" if t["margin"] < 0 else ""}">{euro(t["margin"])}</div><div class="hm-sub"><span>{pct(m_pct)} del ricavo</span>{vs_prev}</div>'
             f'<div class="hm-spark">{spark(series_of(cur, "Margine"), "#7BE0B0", 400, 92, 2.6)}</div></div>')
    with right:
        html('<div class="stats-grid">' + stat_html("Ricavi", euro(t["revenue"]), "fatturato", spark(series_of(cur, "Ricavi"), MOSS), "moss", delta_badge(t["revenue"], p["revenue"]))
             + stat_html("Costo totale", euro(t["costs"]), "personale, mezzi", spark(series_of(cur, "Costo Totale"), TIDE), "tide", delta_badge(t["costs"], p["costs"], False))
             + stat_html("Ore uomo", f'{num(t["labor_h"])} h', "ore di personale certificate", spark(series_of(cur, "Ore Uomo"), SIGNAL), "signal", delta_badge(t["labor_h"], p["labor_h"]))
             + stat_html("Ore mezzi", f'{num(t["vehicle_h"])} h', "ore di mezzi certificate", spark(series_of(cur, "Ore Mezzi"), "#7C8B85"), "", delta_badge(t["vehicle_h"], p["vehicle_h"])) + '</div>')

    total_h = t["labor_h"] + t["vehicle_h"]
    with_anom = int((cur["Anomalie"] > 0).sum()) if not cur.empty else 0
    html(strip_html([("Costo medio all'ora", euro(t["costs"] / total_h if total_h else 0), "costo totale / ore uomo e mezzi"),
                     ("Costo per tonnellata", euro(t["costs"] / t["tonnes"] if t["tonnes"] else 0), f'{num(t["tonnes"])} t registrate'),
                     ("Ricavo per tonnellata", euro(t["revenue"] / t["tonnes"] if t["tonnes"] else 0), "sul totale delle tonnellate"),
                     ("Consuntivi con anomalie", str(with_anom), f'su {len(cur)} nel periodo')]))

    section("Andamento e composizione dei costi")
    a, b = st.columns([1.75, 1])
    with a:
        chart_head("Ricavi, costi e margine")
        ch = trend_chart(cur)
        show_chart(ch) if ch is not None else st.info("Servono consuntivi con data per mostrare l'andamento.")
    with b:
        chart_head("Da cosa sono fatti i costi")
        mix = {"Personale": safe_sum(cur["Costo Personale"]) if not cur.empty else 0, "Mezzi": safe_sum(cur["Costo Mezzi"]) if not cur.empty else 0, "Overhead": safe_sum(cur["Overhead"]) if not cur.empty else 0}
        ch = donut_chart(mix)
        show_chart(ch) if ch is not None else st.info("Nessun costo nel periodo.")

    section("Ultimi consuntivi")
    if cur.empty: st.info("Nessun consuntivo da mostrare.")
    else:
        last = cur.sort_values("Data", ascending=False).head(12)
        table = pd.DataFrame({"Data": last["Data"].dt.date, "Centro di costo": last["Centro di Costo"], "Ricavi": last["Ricavi"], "Costi": last["Costo Totale"], "Margine": last["Margine"], "Margine %": np.where(last["Ricavi"] != 0, last["Margine"] / last["Ricavi"].replace(0, np.nan) * 100, 0.0)})
        sx(st.dataframe, table, hide_index=True, column_config={"Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "Ricavi": st.column_config.NumberColumn(format="€ %.2f"), "Costi": st.column_config.NumberColumn(format="€ %.2f"), "Margine": st.column_config.NumberColumn(format="€ %.2f"), "Margine %": st.column_config.NumberColumn(format="%.1f%%")})

# ============================================================
# MODULO INGOMBRANTI
# ============================================================
elif page == "Ingombranti":
    st.info("Carica il file Excel mensile della Raccolta Ingombranti. Il sistema individuerà in automatico Provincia, Comune e Kg a prescindere dal loro ordine nel file.")
    col_a, col_b = st.columns([1, 1])
    
    file_ing = col_a.file_uploader("Carica file Ingombranti", type=["xlsx", "xls"])
    selected_ccnl = col_b.selectbox("Scegli il CCNL di Riferimento per questo file", options=list(CONTRACTS.keys()), help="Indica a quale listino appartengono i livelli scritti nel file (es. D1, B2).")

    if file_ing:
        try:
            df_ing = pd.read_excel(file_ing, header=3)
            
            cols_lower = {c: str(c).lower().replace('\n', ' ').strip() for c in df_ing.columns}
            rename_map = {}
            for orig, lower in cols_lower.items():
                if lower == 'data': rename_map[orig] = 'Data'
                elif 'comune' in lower: rename_map[orig] = 'Comune'
                elif 'provincia' in lower: rename_map[orig] = 'Provincia'
                elif lower == 'autista' or ('autista' in lower and 'nr' not in lower): rename_map[orig] = 'Livello_Autista'
                elif 'supporto' in lower: rename_map[orig] = 'Livello_Supporto'
                elif 'tipologia mezzo' in lower: rename_map[orig] = 'Mezzo'
                elif 'h/turno' in lower: rename_map[orig] = 'Ore'
                elif 'quantità' in lower and 'kg' in lower: rename_map[orig] = 'Kg'
                elif 'tipo di servizio' in lower: rename_map[orig] = 'Servizio'

            df_ing.rename(columns=rename_map, inplace=True)
            
            if 'Data' not in df_ing.columns or 'Comune' not in df_ing.columns:
                st.error("Errore: Impossibile trovare le colonne 'Data' e 'Comune' nel file. Controlla il formato.")
                st.stop()
                
            df_ing = df_ing.dropna(subset=['Data', 'Comune'])
            
            if df_ing.empty:
                st.warning("Il file non contiene righe valide con Date e Comuni.")
            else:
                st.success(f"File letto con successo! Elaborazione di {len(df_ing)} servizi ingombranti.")
                
                risultati = []
                overhead_pct = general_rate(tariffs, "Overhead", 15.0)

                for _, row in df_ing.iterrows():
                    comune = str(row.get('Comune', '')).strip()
                    provincia = str(row.get('Provincia', '')).strip() 
                    data = pd.to_datetime(row.get('Data'), errors='coerce')
                    
                    kg = parse_num(row.get('Kg', 0))
                    ton = kg / 1000.0
                    
                    ricavo_ton = rate_lookup(tariffs, "Ricavo Tonnellata", comune, "Ingombranti")
                    if ricavo_ton is None: ricavo_ton = 0.0
                    ricavo_totale = ton * ricavo_ton
                    
                    ore_str = row.get('Ore', 0)
                    ore_dec = parse_hours(ore_str)
                    
                    liv_aut = str(row.get('Livello_Autista', '')).strip()
                    liv_sup = str(row.get('Livello_Supporto', '')).strip()
                    tipo_mezzo = str(row.get('Mezzo', '')).strip()
                    
                    costo_h_aut = labor_rate(tariffs, selected_ccnl, liv_aut)
                    costo_h_sup = labor_rate(tariffs, selected_ccnl, liv_sup) if liv_sup and liv_sup.lower() != 'nan' else 0.0
                    costo_h_mezzo = vehicle_rate(tariffs, tipo_mezzo)
                    
                    costo_h_pers_totale = costo_h_aut + costo_h_sup
                    
                    costo_personale = costo_h_pers_totale * ore_dec
                    costo_mezzo = costo_h_mezzo * ore_dec
                    overhead = (costo_personale + costo_mezzo) * overhead_pct / 100.0
                    costo_totale = costo_personale + costo_mezzo + overhead
                    
                    margine = ricavo_totale - costo_totale
                    
                    anomalia = 0
                    if ricavo_ton == 0.0 or costo_h_aut == 0.0 or (liv_sup and liv_sup.lower() != 'nan' and costo_h_sup == 0.0) or costo_h_mezzo == 0.0:
                        anomalia = 1

                    nota_servizio = f"Provincia: {provincia}" if provincia and provincia != 'nan' else ""

                    risultati.append({
                        "Data": data.date() if pd.notnull(data) else None,
                        "Provincia": provincia,
                        "Comune": comune,
                        "Mezzo": tipo_mezzo,
                        "Costo h Mezzo": costo_h_mezzo,  
                        "Addetti": f"{liv_aut} + {liv_sup}" if liv_sup and liv_sup != 'nan' else liv_aut,
                        "Costo h Pers.": costo_h_pers_totale, 
                        "Ore": ore_dec,
                        "Ton": ton,
                        "Ricavo Tonnellata": ricavo_ton,
                        "Ricavi Totali": ricavo_totale,
                        "Costi Diretti": costo_personale + costo_mezzo,
                        "Margine": margine,
                        "Anomalie": anomalia,
                        "Note": nota_servizio,
                        "raw_costo_pers": costo_personale,
                        "raw_costo_mezzo": costo_mezzo,
                        "raw_overhead": overhead,
                        "raw_costo_tot": costo_totale,
                        "Servizio": "Ingombranti",
                    })

                df_res = pd.DataFrame(risultati)
                
                st.subheader("Anteprima Elaborazione Automatica")
                view_df = df_res.copy()
                view_df.drop(columns=['raw_costo_pers', 'raw_costo_mezzo', 'raw_overhead', 'raw_costo_tot', 'Servizio', 'Note', 'Anomalie'], inplace=True)
                
                sx(st.dataframe, view_df, hide_index=True, column_config={
                    "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "Ore": st.column_config.NumberColumn(format="%.2f"),
                    "Ton": st.column_config.NumberColumn(format="%.2f"),
                    "Costo h Mezzo": st.column_config.NumberColumn(format="€ %.2f"),
                    "Costo h Pers.": st.column_config.NumberColumn(format="€ %.2f"),
                    "Ricavo Tonnellata": st.column_config.NumberColumn(format="€ %.2f"),
                    "Ricavi Totali": st.column_config.NumberColumn(format="€ %.2f"),
                    "Costi Diretti": st.column_config.NumberColumn(format="€ %.2f"),
                    "Margine": st.column_config.NumberColumn(format="€ %.2f")
                })
                
                anomalie_tot = df_res['Anomalie'].sum()
                if anomalie_tot > 0:
                    st.warning(f"ATTENZIONE: {anomalie_tot} righe presentano tariffe a zero (Ricavo a tonnellata o Costi Orari). Per risolvere, copia il nome esatto del mezzo o dell'addetto e inseriscigli un costo nella scheda 'Tariffe e contratti'.")
                
                if sx(st.button, "Salva tutti come Centri di Costo", type="primary"):
                    rows_to_save = []
                    batch_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    
                    for i, r in df_res.iterrows():
                        cid = f"CC-ING-{batch_id}-{i}"
                        rows_to_save.append({
                            "ID": cid, "Data": r["Data"], "Servizio": r["Servizio"], "Sottoservizio": r["Comune"], 
                            "Centro di Costo": centro_costo(r["Servizio"], r["Comune"]),
                            "Tonnellate": r["Ton"], "Ricavi": r["Ricavi Totali"], 
                            "Costo Personale": r["raw_costo_pers"], "Costo Mezzi": r["raw_costo_mezzo"], 
                            "Overhead": r["raw_overhead"], "Costo Totale": r["raw_costo_tot"], 
                            "Margine": r["Margine"], "Ore Uomo": r["Ore"] * (2 if "+" in r["Addetti"] else 1), 
                            "Ore Mezzi": r["Ore"], "Note": r["Note"] + f" | Mezzo: {r['Mezzo']}",
                            "Creato Da": st.session_state.nome, "Periodo Da": r["Data"], "Periodo A": r["Data"], 
                            "Anomalie": r["Anomalie"]
                        })
                        
                    append_rows("services", read_services, pd.DataFrame(rows_to_save))
                    st.session_state.flash = f"Completato! {len(rows_to_save)} centri di costo ingombranti salvati nel sistema."
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Errore durante l'elaborazione del file: {e}")

# ============================================================
# CONSUNTIVAZIONE E CERTIFICAZIONI STANDARD
# ============================================================
elif page == "Consuntivazione":
    pool = cert_visible(cert_pool())
    section("Servizio e periodo")
    c1, c2, c3 = st.columns([1, 1.1, 1.4])
    service = c1.selectbox("Servizio", list(SERVICE_TREE))
    options = [x for x in SERVICE_TREE[service] if is_admin() or x in st.session_state.allowed_subservices]
    if not options: st.error("Non hai sottoservizi autorizzati."); st.stop()
    subservice = c2.selectbox("Sottoservizio", options)
    by_sub = rows_for_subservice(pool, subservice); pre = rows_for_service(by_sub, service)
    dates = pre["Data Analisi"].dropna() if not pre.empty else pd.Series(dtype="datetime64[ns]")
    d_min, d_max = (dates.min().date(), dates.max().date()) if not dates.empty else (date.today(), date.today())
    period = c3.date_input("Periodo da consuntivare", value=(d_min, d_max), format="DD/MM/YYYY", key=f"per_{service}_{subservice}_{len(pool)}_{d_min}_{d_max}")
    if not (isinstance(period, (tuple, list)) and len(period) == 2): st.info("Scegli la data di fine."); st.stop()
    d0, d1 = period

    html(f'<div class="panel"><div class="panel-sub">Centro di costo generato dal servizio e dal sottoservizio</div><div class="panel-head" style="font-size:22px;margin-top:4px">{centro_costo(service, subservice)}</div></div>')
    section("Righe di certificazione collegate")
    in_period = pre[pre["Data Analisi"].between(pd.Timestamp(d0), pd.Timestamp(d1) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))] if not pre.empty else pre
    o1, o2 = st.columns(2)
    has_cert = bool(in_period["Stato"].map(is_certified).any()) if not in_period.empty else True
    only_cert = o1.radio("Righe da includere", ["Solo certificate", "Tutte le righe"], index=0 if has_cert else 1, horizontal=True) == "Solo certificate"
    reuse = o2.checkbox("Includi anche righe già consuntivate", value=False)
    step_status = in_period[in_period["Stato"].map(is_certified)] if only_cert and not in_period.empty else in_period
    used = set(personnel_detail["Certificazione ID"]) | set(vehicle_detail["Certificazione ID"]); used.discard("")
    scope = step_status if reuse or step_status.empty else step_status[~step_status["ID"].isin(used)]

    funnel = [("Nel file", len(pool)), (f"Per {subservice}", len(by_sub)), (f"Per {service}", len(pre)), ("Nel periodo", len(in_period)), ("Con lo stato scelto", len(step_status)), ("Ancora da consuntivare", len(scope))]
    html('<div class="funnel">' + "".join(f"<span>{a}: <b>{b}</b></span>" for a, b in funnel) + "</div>")
    if pool.empty: st.warning("Non c'è nessuna certificazione. Importala da Certificazioni e ore.")
    if not scope.empty and (scope["Attribuzione"] == "Solo sottoservizio").any(): st.caption("Alcune righe collegate solo dal sottoservizio.")

    manual = False
    if scope.empty:
        st.info("Nessuna riga da consuntivare. Cambia periodo o stato.")
        manual = st.checkbox("Inserimento manuale senza certificazione")
        if not manual: st.stop()

    sig = hashlib.md5(("|".join(scope["Chiave"]) + f"{service}{subservice}{d0}{d1}{manual}").encode()).hexdigest()[:10]
    section("Tonnellate e ricavo")
    r1, r2, r3 = st.columns(3)
    tonnage = r1.number_input("Tonnellate", min_value=0.0, step=0.1, value=0.0)
    auto_rev = r3.checkbox("Calcola il ricavo dalla tariffa a tonnellata", value=False)
    ton_rate = general_rate(tariffs, "Tariffa tonnellata", 0.0)
    revenue = tonnage * ton_rate if auto_rev else r2.number_input("Ricavo (€)", min_value=0.0, step=50.0, value=0.0)
    if auto_rev: r2.metric("Ricavo calcolato", euro(revenue))

    section("Personale", "Ore uomo = durata per operatore.")
    people_rows = expand_people(scope, operators) if not scope.empty else pd.DataFrame([{**{c: "" for c in PEOPLE_COLS}, "Ore": 0.0, "Stato Match": "MANUALE"}])
    people_rows["Data"] = pd.to_datetime(people_rows["Data"], errors="coerce").dt.strftime("%Y-%m-%d")
    edited_people = sx(st.data_editor, people_rows, num_rows="dynamic", hide_index=True, key=f"pe_{sig}", disabled=["Certificazione ID", "Stato Match"], column_config={"Contratto": st.column_config.SelectboxColumn("Contratto", options=[""] + list(CONTRACTS)), "Livello": st.column_config.SelectboxColumn("Livello", options=[""] + ALL_LEVELS), "Ore": st.column_config.NumberColumn("Ore", min_value=0.0, step=0.25, format="%.2f"), "Data": None, "Inizio": None, "Fine": None})
    labor = price_people(edited_people, tariffs)

    section("Mezzi")
    vehicle_types = sorted(set(DEFAULT_VEHICLE_TYPES + tariffs.loc[tariffs["Tipo"].str.lower().eq("mezzo"), "Livello_o_Tipo"].astype(str).tolist()))
    veh_rows = expand_vehicles(scope, vehicles) if not scope.empty else pd.DataFrame([{**{c: "" for c in VEHICLE_COLS}, "Ore": 0.0, "Stato Match": "MANUALE"}])
    veh_rows["Data"] = pd.to_datetime(veh_rows["Data"], errors="coerce").dt.strftime("%Y-%m-%d")
    edited_veh = sx(st.data_editor, veh_rows, num_rows="dynamic", hide_index=True, key=f"ve_{sig}", disabled=["Certificazione ID", "Stato Match"], column_config={"Tipo": st.column_config.SelectboxColumn("Tipo mezzo", options=[""] + vehicle_types), "Ore": st.column_config.NumberColumn("Ore", min_value=0.0, step=0.25, format="%.2f"), "Data": None})
    veh = price_vehicles(edited_veh, tariffs)

    labor_cost, vehicle_cost = safe_sum(labor["Costo Totale"]), safe_sum(veh["Costo Totale"])
    labor_h, vehicle_h = safe_sum(labor["Ore"]), safe_sum(veh["Ore"])
    overhead_pct = general_rate(tariffs, "Overhead", 15.0); overhead = (labor_cost + vehicle_cost) * overhead_pct / 100
    total_cost = labor_cost + vehicle_cost + overhead
    margin = revenue - total_cost; margin_pct = margin / revenue * 100 if revenue else 0.0
    bad_level = int((labor["Validita"] == "Livello non valido").sum())
    missing = int(labor["Validita"].isin(["Da assegnare", "Costo da configurare"]).sum() + (veh["Validita"] != "OK").sum())

    section("Risultato del centro di costo")
    html(strip_html([("Personale", euro(labor_cost), f"{num(labor_h)} h"), ("Mezzi", euro(vehicle_cost), f"{num(vehicle_h)} h"), ("Overhead", euro(overhead), f"{num(overhead_pct)}%"), ("Costo totale", euro(total_cost), ""), ("Margine", euro(margin), pct(margin_pct) + " del ricavo")]))
    html(f'<div style="margin:12px 0"><span class="chip {"ok" if margin >= 0 else "bad"}">{"Margine positivo" if margin >= 0 else "Margine negativo"}</span></div>')

    if bad_level: st.error(f"{bad_level} righe hanno livello errato.")
    allow_missing = False
    if missing:
        st.warning(f"{missing} righe hanno costo zero. Il margine risulterebbe più alto del reale.")
        allow_missing = st.checkbox("Salva comunque come anomalia")
    empty = labor.empty and veh.empty
    notes = st.text_area("Note e scostamenti")
    can_save = not bad_level and not empty and (not missing or allow_missing)

    if sx(st.button, "Salva centro di costo", type="primary", disabled=not can_save):
        cid = "CC-" + datetime.now().strftime("%Y%m%d%H%M%S%f"); end = pd.Timestamp(d1)
        append_rows("services", read_services, pd.DataFrame([{"ID": cid, "Data": end, "Servizio": service, "Sottoservizio": subservice, "Centro di Costo": centro_costo(service, subservice), "Tonnellate": tonnage, "Ricavi": revenue, "Costo Personale": labor_cost, "Costo Mezzi": vehicle_cost, "Overhead": overhead, "Costo Totale": total_cost, "Margine": margin, "Ore Uomo": labor_h, "Ore Mezzi": vehicle_h, "Note": notes, "Creato Da": st.session_state.nome, "Periodo Da": pd.Timestamp(d0), "Periodo A": end, "Anomalie": missing}]))
        def row_date(v):
            d = parse_date(v)
            return end if pd.isna(d) else d
        append_rows("personnel", read_personnel, pd.DataFrame([{"ID Consuntivo": cid, "Certificazione ID": txt(r.get("Certificazione ID")), "Data": row_date(r.get("Data")), "Servizio": service, "Sottoservizio": subservice, "Matricola": txt(r.get("Matricola")), "Operatore": txt(r.get("Operatore")), "Contratto": txt(r.get("Contratto")), "Livello": txt(r.get("Livello")), "Ore": float(r["Ore"]), "Costo Orario": float(r["Costo Orario"]), "Costo Totale": float(r["Costo Totale"]), "Stato Match": txt(r.get("Stato Match"))} for _, r in labor.iterrows()]))
        append_rows("vehicle_detail", read_vehicle_detail, pd.DataFrame([{"ID Consuntivo": cid, "Certificazione ID": txt(r.get("Certificazione ID")), "Data": row_date(r.get("Data")), "Servizio": service, "Sottoservizio": subservice, "Targa": txt(r.get("Targa")), "Attrezzatura": txt(r.get("Attrezzatura")), "Tipo": txt(r.get("Tipo")), "Ore": float(r["Ore"]), "Costo Orario": float(r["Costo Orario"]), "Costo Totale": float(r["Costo Totale"]), "Stato Match": txt(r.get("Stato Match"))} for _, r in veh.iterrows()]))
        st.session_state.flash = f"Centro di costo {cid} salvato."; st.rerun()

elif page == "Certificazioni":
    section("Carica il file ufficiale")
    c1, c2 = st.columns([2, 1])
    uploaded = c1.file_uploader("Certificazione", type=["csv", "xlsx", "xls"])
    mode_label = c2.radio("Durate", ["Automatico", "Ore decimali (1,5 = 1h30)", "Frazione di giorno Excel"])
    mode = {"Automatico": "auto", "Ore decimali (1,5 = 1h30)": "decimali", "Frazione di giorno Excel": "frazione"}[mode_label]
    if uploaded is not None:
        sig = f"{uploaded.name}|{uploaded.size}|{mode}"
        if st.session_state.cert_sig != sig:
            try: st.session_state.cert_df = normalize_certification(load_uploaded_raw(uploaded), mode); st.session_state.cert_file, st.session_state.cert_sig = uploaded.name, sig; st.session_state.cert_import_id = "IMP-" + datetime.now().strftime("%Y%m%d%H%M%S")
            except Exception as exc: st.error(f"Errore file: {exc}")

    current = st.session_state.cert_df
    source = cert_visible(current if not current.empty else read_cert_rows())
    if source.empty: st.info("Carica un file."); st.stop()

    t1, t2 = st.columns(2)
    max_day = t1.number_input("Massimo ore operatore", min_value=1.0, max_value=24.0, value=12.0, step=0.5)
    tol = t2.number_input("Tolleranza", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
    checks, details, people, vehs = run_checks(source, operators, vehicles, max_day, tol)

    done, planned = float(source["Durata"].sum()), float(source["Orario Previsto"].sum()); gap = done - planned
    html(strip_html([("Righe", str(len(source)), ""), ("Ore svolte", f"{num(done)} h", ""), ("Ore previste", f"{num(planned)} h", ""), ("Scostamento", f'{"+" if gap >= 0 else ""}{num(gap)} h', "")]))

    bad, warn = sum(c["sev"] == "bad" for c in checks), sum(c["sev"] == "warn" for c in checks)
    tab_check, tab_rows, tab_arch = st.tabs(["Verifica ore", "Righe", "Archivio"])
    with tab_check:
        verdict = ("bad", f"{bad} controlli bloccanti") if bad else (("warn", f"{warn} segnalazioni") if warn else ("ok", "Pronta per il consuntivo"))
        html(f'<div style="margin:10px 0 12px"><span class="chip {verdict[0]}">{verdict[1]}</span></div>')
        for c in checks:
            n = f'<div class="check-n">{c["n"]}</div>' if c["n"] else '<span class="chip ok">OK</span>'
            html(f'<div class="check {c["sev"]}"><div><div class="check-title">{c["name"]}</div><div class="check-msg">{c["msg"]}</div></div><div style="margin-left:auto">{n}</div></div>')
            if c["name"] in details:
                with st.expander(f'Vedi righe'): sx(st.dataframe, details[c["name"]], hide_index=True)
        chart_head("Ore previste e svolte")
        ch = hours_chart(source); show_chart(ch) if ch is not None else st.info("Servono date.")
    with tab_rows:
        view = source[CERT_COLUMNS].copy()
        for col in ["Data Pianificazione", "Data Svolgimento"]: view[col] = pd.to_datetime(view[col], errors="coerce").dt.strftime("%d/%m/%Y")
        sx(st.dataframe, view, hide_index=True)
    with tab_arch:
        imports = read_imports()
        if imports.empty: st.info("Nessun archivio.")
        else: sx(st.dataframe, imports.sort_values("Data Import", ascending=False), hide_index=True)

    if not current.empty:
        section("Archivia")
        if sx(st.button, "Archivia questa certificazione", type="primary"):
            old = read_cert_rows(); new = current.copy(); new["ID Import"] = st.session_state.cert_import_id
            new = new[~new["Chiave"].isin(old["Chiave"])].drop_duplicates("Chiave"); out_cols = CERT_COLUMNS + ["ID Import"]
            save_csv(pd.concat([old[out_cols], new[out_cols]], ignore_index=True), FILES["cert_rows"])
            append_rows("certifications", read_imports, pd.DataFrame([{"ID Import": st.session_state.cert_import_id, "Data Import": datetime.now(), "File": st.session_state.cert_file, "Righe": len(new), "Ore": float(new["Durata"].sum()), "Stato": "DA VERIFICARE" if bad else "OK", "Operatore": st.session_state.nome}]))
            st.session_state.cert_df = pd.DataFrame(); st.session_state.flash = f"Archiviate {len(new)} righe."; st.rerun()

# ============================================================
# PAGINE ANALISI ED IMPOSTAZIONI
# ============================================================
elif page == "Economico":
    df = authorized(services_df)
    if df.empty: st.info("Non ci sono ancora consuntivi."); st.stop()
    a, b = st.columns([1, 1.4])
    service_filter = a.selectbox("Servizio", ["Tutti"] + list(SERVICE_TREE))
    subs = ALL_SUBSERVICES if service_filter == "Tutti" else SERVICE_TREE[service_filter]
    if not is_admin(): subs = [x for x in subs if x in st.session_state.allowed_subservices]
    sub_filter = b.selectbox("Sottoservizio", ["Tutti"] + list(subs))
    if service_filter != "Tutti": df = df[df["Servizio"].eq(service_filter)]
    if sub_filter != "Tutti": df = df[df["Sottoservizio"].eq(sub_filter)]

    def scoped(detail):
        d = authorized(detail)
        if service_filter != "Tutti": d = d[d["Servizio"].eq(service_filter)]
        return d[d["Sottoservizio"].eq(sub_filter)] if sub_filter != "Tutti" else d

    tab_sum, tab_people, tab_veh = st.tabs(["Riepilogo", "Personale", "Mezzi"])
    with tab_sum:
        summary = df.groupby(["Servizio", "Sottoservizio"], as_index=False).agg(Ricavi=("Ricavi", "sum"), Costi=("Costo Totale", "sum"), Margine=("Margine", "sum"), Tonnellate=("Tonnellate", "sum"), Ore_uomo=("Ore Uomo", "sum"), Ore_mezzi=("Ore Mezzi", "sum"))
        summary["Margine %"] = np.where(summary["Ricavi"] != 0, summary["Margine"] / summary["Ricavi"].replace(0, np.nan) * 100, 0.0)
        sx(st.dataframe, summary, hide_index=True, column_config={"Ricavi": st.column_config.NumberColumn(format="€ %.2f"), "Costi": st.column_config.NumberColumn(format="€ %.2f"), "Margine": st.column_config.NumberColumn(format="€ %.2f"), "Margine %": st.column_config.NumberColumn(format="%.1f%%"), "Tonnellate": st.column_config.NumberColumn(format="%.1f"), "Ore_uomo": st.column_config.NumberColumn("Ore uomo", format="%.1f"), "Ore_mezzi": st.column_config.NumberColumn("Ore mezzi", format="%.1f")})
        chart_head("Margine per centro di costo"); g = df.groupby("Centro di Costo", as_index=False)["Margine"].sum().sort_values("Margine", ascending=False)
        show_chart(hbar_chart(g, "Centro di Costo", "Margine", signed=True))
    with tab_people:
        pdx = scoped(personnel_detail)
        if pdx.empty: st.info("Nessun dettaglio del personale.")
        else:
            l, r = st.columns(2)
            with l:
                chart_head("Costo per contratto e livello"); g = pdx.assign(Voce=pdx["Contratto"].replace("", "Non assegnato") + " " + pdx["Livello"]).groupby("Voce", as_index=False)["Costo Totale"].sum(); show_chart(hbar_chart(g.sort_values("Costo Totale", ascending=False).head(12), "Voce", "Costo Totale", color=MOSS))
            with r:
                chart_head("Ore per operatore"); g = pdx.groupby("Operatore", as_index=False)["Ore"].sum().sort_values("Ore", ascending=False).head(12); show_chart(hbar_chart(g, "Operatore", "Ore", color=SIGNAL))
            by_op = pdx.groupby(["Operatore", "Contratto", "Livello"], as_index=False).agg(Ore=("Ore", "sum"), Costo=("Costo Totale", "sum"))
            sx(st.dataframe, by_op.sort_values("Costo", ascending=False), hide_index=True, column_config={"Ore": st.column_config.NumberColumn(format="%.2f"), "Costo": st.column_config.NumberColumn(format="€ %.2f")})
    with tab_veh:
        vdx = scoped(vehicle_detail)
        if vdx.empty: st.info("Nessun dettaglio dei mezzi.")
        else:
            l, r = st.columns(2)
            with l:
                chart_head("Costo per tipologia"); g = vdx.assign(Tipo=vdx["Tipo"].replace("", "Non assegnato")).groupby("Tipo", as_index=False)["Costo Totale"].sum(); show_chart(hbar_chart(g.sort_values("Costo Totale", ascending=False), "Tipo", "Costo Totale", color=TIDE))
            with r:
                chart_head("Ore per targa"); g = vdx.assign(Targa=vdx["Targa"].replace("", "Senza targa")).groupby("Targa", as_index=False)["Ore"].sum().sort_values("Ore", ascending=False).head(12); show_chart(hbar_chart(g, "Targa", "Ore", color="#7C8B85"))

elif page == "Anagrafiche":
    t1, t2 = st.tabs(["Operatori", "Mezzi"])
    with t1:
        edited = sx(st.data_editor, operators, num_rows="dynamic", hide_index=True, key="operators_editor", column_config={"Contratto": st.column_config.SelectboxColumn(options=[""] + list(CONTRACTS)), "Livello": st.column_config.SelectboxColumn(options=[""] + ALL_LEVELS)})
        dup = edited[edited["Matricola"].map(txt).ne("") & edited["Matricola"].duplicated(keep=False)]
        if not dup.empty: st.error("Matricole ripetute!")
        if sx(st.button, "Salva operatori", type="primary", disabled=not dup.empty): save_csv(edited.fillna(""), FILES["operators"]); st.session_state.flash = "Operatori salvati."; st.rerun()
    with t2:
        types = sorted(set(DEFAULT_VEHICLE_TYPES + tariffs.loc[tariffs["Tipo"].str.lower().eq("mezzo"), "Livello_o_Tipo"].astype(str).tolist()))
        edited = sx(st.data_editor, vehicles, num_rows="dynamic", hide_index=True, key="vehicles_editor", column_config={"Tipo": st.column_config.SelectboxColumn(options=[""] + types)})
        keys = edited["Targa"].map(plate_key); dup = edited[keys.ne("") & keys.duplicated(keep=False)]
        if not dup.empty: st.error("Targhe ripetute!")
        if sx(st.button, "Salva mezzi", type="primary", disabled=not dup.empty): save_csv(edited.fillna(""), FILES["vehicles"]); st.session_state.flash = "Mezzi salvati."; st.rerun()

elif page == "Tariffari":
    t1, t2, t3, t4 = st.tabs(["Costi Personale", "Costi Mezzi", "Parametri Generali", "Ricavi a Tonnellata (Comuni)"])
    def save_group(kind, label, edited, force_contract=None):
        edited = edited.copy(); edited["Tipo"] = label
        if force_contract is not None: edited["Contratto"] = force_contract
        edited["Costo_Orario"] = edited["Costo_Orario"].apply(parse_num); edited["Attivo"] = edited["Attivo"].replace("", "SI").fillna("SI")
        current = read_tariffs()
        save_csv(pd.concat([current[~current["Tipo"].str.lower().eq(kind)], edited.fillna("")], ignore_index=True), FILES["tariffs"]); st.session_state.flash = "Tariffe aggiornate."; st.rerun()
    with t1:
        edited = sx(st.data_editor, tariffs[tariffs["Tipo"].str.lower().eq("personale")], num_rows="dynamic", hide_index=True, column_config={"Tipo": None, "Contratto": st.column_config.SelectboxColumn("Contratto", options=list(CONTRACTS)), "Livello_o_Tipo": st.column_config.SelectboxColumn("Livello", options=ALL_LEVELS), "Costo_Orario": st.column_config.NumberColumn("Costo orario aziendale (€)", min_value=0.0, step=0.01, format="%.2f"), "Attivo": st.column_config.SelectboxColumn("Attivo", options=["SI", "NO"])})
        if sx(st.button, "Salva costi personale", type="primary", key="s1"): save_group("personale", "Personale", edited)
    with t2:
        edited = sx(st.data_editor, tariffs[tariffs["Tipo"].str.lower().eq("mezzo")], num_rows="dynamic", hide_index=True, column_config={"Tipo": None, "Contratto": None, "Livello_o_Tipo": st.column_config.TextColumn("Tipo mezzo"), "Costo_Orario": st.column_config.NumberColumn("Costo orario (€)", min_value=0.0, step=0.01, format="%.2f"), "Attivo": st.column_config.SelectboxColumn("Attivo", options=["SI", "NO"])})
        if sx(st.button, "Salva costi mezzi", type="primary", key="s2"): save_group("mezzo", "Mezzo", edited)
    with t3:
        edited = sx(st.data_editor, tariffs[tariffs["Tipo"].str.lower().eq("generale")], num_rows="dynamic", hide_index=True, column_config={"Tipo": None, "Contratto": None, "Livello_o_Tipo": st.column_config.TextColumn("Parametro"), "Costo_Orario": st.column_config.NumberColumn("Valore", step=0.01, format="%.2f"), "Attivo": st.column_config.SelectboxColumn("Attivo", options=["SI", "NO"])})
        if sx(st.button, "Salva parametri", type="primary", key="s3"): save_group("generale", "Generale", edited)
    with t4:
        st.info("Imposta il Ricavo in base al Comune dove viene svolta la raccolta (Es. Prato, Mugello).")
        edited = sx(st.data_editor, tariffs[tariffs["Tipo"].str.lower().eq("ricavo tonnellata")], num_rows="dynamic", hide_index=True, column_config={"Tipo": None, "Contratto": None, "Livello_o_Tipo": st.column_config.TextColumn("Comune / Cantiere"), "Costo_Orario": st.column_config.NumberColumn("Ricavo (€/Ton)", min_value=0.0, step=0.01, format="%.2f"), "Attivo": st.column_config.SelectboxColumn("Attivo", options=["SI", "NO"])})
        if sx(st.button, "Salva Ricavi", type="primary", key="s4"): save_group("ricavo tonnellata", "Ricavo Tonnellata", edited, force_contract="Ingombranti")

elif page == "Accessi":
    section("Utenti e autorizzazioni")
    users_now = read_users()
    edited = sx(st.data_editor, users_now, num_rows="dynamic", hide_index=True, key="users_editor", column_config={"password": None, "ruolo": st.column_config.SelectboxColumn("ruolo", options=["admin", "capocantiere"])})
    if sx(st.button, "Salva utenti", type="primary"):
        names = edited["username"].map(txt)
        if names.eq("").any() or names.duplicated().any(): st.error("Controlla gli username inseriti.")
        else:
            out = edited.fillna(""); no_pw = out["password"].map(txt).eq("")
            out.loc[no_pw, "password"] = [hash_password(secrets.token_urlsafe(12)) for _ in range(int(no_pw.sum()))]
            save_csv(out, FILES["users"]); st.session_state.flash = "Utenti aggiornati."; st.rerun()
    section("Imposta password")
    p1, p2, p3 = st.columns([1, 1, 0.6])
    target = p1.selectbox("Utente", users_now["username"].tolist()); new_pw = p2.text_input("Nuova password", type="password"); p3.write("")
    if sx(p3.button, "Aggiorna password"):
        if len(new_pw) < 6: st.error("Almeno 6 caratteri.")
        else: users_now.loc[users_now["username"] == target, "password"] = hash_password(new_pw); save_csv(users_now, FILES["users"]); st.session_state.flash = f"Password {target} aggiornata."; st.rerun()

html('<div class="foot">Cristoforo Control Room V8.5</div>')
