# -*- coding: utf-8 -*-
# ============================================================
# CRISTOFORO | CONTROL ROOM V8.15
# Escudo Antierrores Global (Evita la pantalla blanca)
# Fix Lector Universal y Auto-Repair
# ============================================================
import hashlib
import hmac
import io
import os
import re
import secrets
import traceback
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

# --- ESCUDO GLOBAL ANTI-CRASH ---
try:
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
        "11. 3 Assi Scarrabile", "12. 4 Assi Scarrabile", "13. 3 Assi Scar. + Caricatore"
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
        "13. 3 Assi Scar. + Caricatore": 55.0
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
        if isinstance(value, (datetime, pd.Timestamp)): 
            return value.hour + (value.minute / 60.0) + (value.second / 3600.0)
        if isinstance(value, dtime): 
            return value.hour + (value.minute / 60.0) + (value.second / 3600.0)
        if isinstance(value, (timedelta, pd.Timedelta)): 
            return value.total_seconds() / 3600.0
        
        if isinstance(value, (int, float, np.integer, np.floating)):
            if pd.isna(value): return 0.0
            n = float(value)
            return n * 24 if (excel_fraction and 0 < n < 1) else n
            
        text = str(value).strip()
        if not text or text.lower() in ['nan', 'nat', 'none']: return 0.0
        
        if ":" in text:
            parts = text.split(":")
            try: return float(parts[0]) + (float(parts[1]) if len(parts) > 1 else 0.0) / 60.0 + (float(parts[2]) if len(parts) > 2 else 0.0) / 3600.0
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

    # ============================================================
    # INIZIALIZZAZIONE FILE GLOBALI (SAFE)
    # ============================================================
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
            "cert_rows": ["ID", "Codice", "Descrizione", "Comuni", "Centro di Costo", "Data Pianificazione", "Inizio Pianificazione", "Fine Pianificazione", "Orario Previsto", "Data Svolgimento", "Inizio Svolgimento", "Fine Svolgimento", "Durata", "Operatori", "Targa", "Attrezzatura", "Note", "Stato", "ID Import"],
        }
        for key, cols in empties.items():
            if not os.path.exists(FILES[key]): save_csv(pd.DataFrame(columns=cols), FILES[key])
        
        default_tariffs = [{"Tipo": "Personale", "Contratto": c, "Livello_o_Tipo": lv, "Costo_Orario": 0.0, "Attivo": "SI"} for c, levels in CONTRACTS.items() for lv in levels]
        default_tariffs += [{"Tipo": "Mezzo", "Contratto": "", "Livello_o_Tipo": k, "Costo_Orario": v, "Attivo": "SI"} for k, v in DEFAULT_VEHICLE_COSTS.items()]
        default_tariffs += [
            {"Tipo": "Generale", "Contratto": "", "Livello_o_Tipo": "Overhead", "Costo_Orario": 15.0, "Attivo": "SI"},
            {"Tipo": "Generale", "Contratto": "", "Livello_o_Tipo": "Tariffa tonnellata", "Costo_Orario": 130.0, "Attivo": "SI"},
            {"Tipo": "Ricavo Tonnellata", "Contratto": "Ingombranti", "Livello_o_Tipo": "Prato", "Costo_Orario": 140.0, "Attivo": "SI"},
            {"Tipo": "Ricavo Tonnellata", "Contratto": "Ingombranti", "Livello_o_Tipo": "Mugello", "Costo_Orario": 160.0, "Attivo": "SI"}
        ]

        if not os.path.exists(FILES["tariffs"]):
            save_csv(pd.DataFrame(default_tariffs), FILES["tariffs"])
        else:
            try:
                df_t = read_csv_flexible(FILES["tariffs"])
                if len(df_t.columns) > len(set(df_t.columns)): raise ValueError("File corrotto duplicato")
                if df_t.empty: save_csv(pd.DataFrame(default_tariffs), FILES["tariffs"])
                else:
                    missing = []
                    df_t_tipo = df_t.get("tipo", pd.Series(dtype=str)).astype(str).str.lower().str.strip()
                    df_t_liv = df_t.get("livello_o_tipo", pd.Series(dtype=str)).astype(str).str.lower().str.strip()
                    if not df_t_tipo.empty and not df_t_liv.empty:
                        for dt in default_tariffs:
                            match = (df_t_tipo == str(dt["Tipo"]).lower().strip()) & (df_t_liv == str(dt["Livello_o_Tipo"]).lower().strip())
                            if not match.any(): missing.append(dt)
                        if missing: 
                            mapper = {k: clean_col(k) for k in dt.keys()}
                            miss_df = pd.DataFrame(missing).rename(columns=mapper)
                            save_csv(pd.concat([df_t, miss_df], ignore_index=True), FILES["tariffs"])
            except Exception:
                save_csv(pd.DataFrame(default_tariffs), FILES["tariffs"])

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
        
        if contract is not None and str(contract).strip(): 
            m_exact = m & tariffs["Contratto"].astype(str).str.strip().eq(str(contract).strip())
            d_exact = tariffs.loc[m_exact, "Costo_Orario"]
            if not d_exact.empty and float(d_exact.iloc[0]) > 0:
                return float(d_exact.iloc[0])
                
        d_fuzzy = tariffs.loc[m & (tariffs["Costo_Orario"] > 0), "Costo_Orario"]
        if not d_fuzzy.empty:
            return float(d_fuzzy.iloc[0])
            
        d_zero = tariffs.loc[m, "Costo_Orario"]
        return float(d_zero.iloc[0]) if not d_zero.empty else 0.0

    def labor_rate(tariffs, contract, level): return rate_lookup(tariffs, "personale", level, contract) or 0.0
    def vehicle_rate(tariffs, kind): return rate_lookup(tariffs, "mezzo", kind) or 0.0
    def general_rate(tariffs, name, default=0.0):
        v = rate_lookup(tariffs, "generale", name)
        return default if v is None else v

    # ============================================================
    # INTERFACCIA E DASHBOARD
    # ============================================================
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
                if match.empty or not check_password(match.iloc[0]["password"], password): st.error("Usuario o contraseña incorrectos.")
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

    PAGE_LABELS = {"Dashboard": "Dashboard", "Ingombranti": "Importa Ingombranti", "Consuntivazione": "Nuovo consuntivo", "Economico": "Centro di costo", "Anagrafiche": "Anagrafiche", "Tariffari": "Tariffe e contratti", "Accessi": "Accessi"}
    pages = ["Dashboard", "Ingombranti", "Consuntivazione", "Economico"] + (["Anagrafiche", "Tariffari", "Accessi"] if is_admin() else [])

    with st.sidebar:
        html('<div class="brand"><div class="brand-name">Cristoforo<b>.</b></div><div class="brand-sub">Control Room</div></div><div class="nav-title">Menu</div>')
        selected = st.radio("Menu", [PAGE_LABELS[p] for p in pages], label_visibility="collapsed")
        page = next(p for p in pages if PAGE_LABELS[p] == selected)
        st.markdown("---")
        access = "Acceso total" if is_admin() else f"Acceso a {len(st.session_state.allowed_subservices)} subservicios"
        html(f'<div class="side-user"><b>{st.session_state.nome}</b><span>{st.session_state.ruolo}</span><span>{access}</span></div>')
        st.write("")
        if sx(st.button, "Salir"):
            for _k in ["logged", "username", "nome", "ruolo", "allowed_subservices", "default_pwd", "cert_df", "cert_file", "cert_import_id", "cert_sig"]: st.session_state.pop(_k, None)
            st.rerun()

    PAGE_META = {
        "Dashboard": ("Control Room", "Ingresos, costos, horas y margen de los servicios en un solo vistazo."),
        "Ingombranti": ("Raccolta Ingombranti", "Importa el archivo Excel y calcula automáticamente las tarifas de los medios y el personal."),
        "Consuntivazione": ("Nuovo consuntivo", "Conecta la certificación a un servicio, controla el costo y guarda el centro de costos."),
        "Economico": ("Centro di costo", "Ingresos, costos y margen por servicio, subservicio, operador y vehículo."),
        "Anagrafiche": ("Anagrafiche", "Operadores con contrato y nivel, vehículos con tipología."),
        "Tariffari": ("Tariffe e contratti", "Gestiona el costo por hora del personal, vehículos e ingresos por tonelada."),
        "Accessi": ("Accessi", "Usuarios, contraseñas y subservicios autorizados."),
    }
    page_head(*PAGE_META[page])
    if st.session_state.get("flash"): st.success(st.session_state.pop("flash"))

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

        if base.empty: st.info("No hay informes guardados en la base de datos todavía.")
        s_label, s_text, s_class = status_for_margin(t["margin"], m_pct, not cur.empty)
        vs_prev = delta_badge(t["margin"], p["margin"]) + (' <span style="opacity:.75">en el periodo anterior</span>' if p["margin"] else "")
        left, right = st.columns([1, 1.55])
        with left:
            html(f'<div class="hero-margin"><div class="hm-top"><span class="hm-label">Margen {scope_label}</span><span class="chip dark">{s_label}</span></div>'
                 f'<div class="hm-value {"neg" if t["margin"] < 0 else ""}">{euro(t["margin"])}</div><div class="hm-sub"><span>{pct(m_pct)} de ingresos</span>{vs_prev}</div>'
                 f'<div class="hm-spark">{spark(series_of(cur, "Margine"), "#7BE0B0", 400, 92, 2.6)}</div></div>')
        with right:
            html('<div class="stats-grid">' + stat_html("Ingresos", euro(t["revenue"]), "facturación", spark(series_of(cur, "Ricavi"), MOSS), "moss", delta_badge(t["revenue"], p["revenue"]))
                 + stat_html("Costo total", euro(t["costs"]), "personal, vehículos", spark(series_of(cur, "Costo Totale"), TIDE), "tide", delta_badge(t["costs"], p["costs"], False))
                 + stat_html("Horas hombre", f'{num(t["labor_h"])} h', "horas de personal", spark(series_of(cur, "Ore Uomo"), SIGNAL), "signal", delta_badge(t["labor_h"], p["labor_h"]))
                 + stat_html("Horas vehículos", f'{num(t["vehicle_h"])} h', "horas de vehículos", spark(series_of(cur, "Ore Mezzi"), "#7C8B85"), "", delta_badge(t["vehicle_h"], p["vehicle_h"])) + '</div>')

        total_h = t["labor_h"] + t["vehicle_h"]
        with_anom = int((cur["Anomalie"] > 0).sum()) if not cur.empty else 0
        html(strip_html([("Costo medio por hora", euro(t["costs"] / total_h if total_h else 0), "costo total / horas hombre y vehículos"),
                         ("Costo por tonelada", euro(t["costs"] / t["tonnes"] if t["tonnes"] else 0), f'{num(t["tonnes"])} t registradas'),
                         ("Ingreso por tonelada", euro(t["revenue"] / t["tonnes"] if t["tonnes"] else 0), "sobre el total de toneladas"),
                         ("Informes con anomalías", str(with_anom), f'de {len(cur)} en el periodo')]))

        section("Tendencia y composición de los costos")
        a, b = st.columns([1.75, 1])
        with a:
            chart_head("Ingresos, costos y margen")
            ch = trend_chart(cur)
            show_chart(ch) if ch is not None else st.info("Se necesitan informes con fecha para mostrar la tendencia.")
        with b:
            chart_head("De qué están hechos los costos")
            mix = {"Personal": safe_sum(cur["Costo Personale"]) if not cur.empty else 0, "Vehículos": safe_sum(cur["Costo Mezzi"]) if not cur.empty else 0, "Overhead": safe_sum(cur["Overhead"]) if not cur.empty else 0}
            ch = donut_chart(mix)
            show_chart(ch) if ch is not None else st.info("Ningún costo en el periodo.")

    # ============================================================
    # MODULO INGOMBRANTI (CON FILTROS ESTRICTOS Y PREVENCIÓN DE DUPLICADOS)
    # ============================================================
    elif page == "Ingombranti":
        st.info("Carga el archivo Excel mensual. El sistema escaneará todas las columnas con precisión.")
        col_a, col_b = st.columns([1, 1])
        
        file_ing = col_a.file_uploader("Carica file Ingombranti", type=["xlsx", "xls"])
        selected_ccnl = col_b.selectbox("Scegli il CCNL di Riferimento", options=list(CONTRACTS.keys()), help="Indica en qué lista buscar los niveles del personal.")

        if file_ing:
            try:
                excel_file = pd.ExcelFile(file_ing)
                sheet_name = excel_file.sheet_names[0]
                df_temp = pd.read_excel(file_ing, sheet_name=sheet_name, header=None, nrows=20)
                
                header_idx = 0
                for i, row in df_temp.iterrows():
                    row_str = " ".join([str(x).lower() for x in row.values if pd.notnull(x)])
                    if ('comune' in row_str or 'autista' in row_str) and ('kg' in row_str or 'quantit' in row_str):
                        header_idx = i
                        break
                        
                file_ing.seek(0)
                df_ing = pd.read_excel(file_ing, sheet_name=sheet_name, header=header_idx)
                
                # REPARACIÓN EXCLUSIVA PARA EL ERROR DE "TRUTH VALUE AMBIGUOUS"
                cols_originales = df_ing.columns.tolist()
                cols_lower = [str(c).lower().replace('\n', ' ').strip() for c in cols_originales]
                rename_map = {}
                
                for i, lower in enumerate(cols_lower):
                    orig = cols_originales[i]
                    
                    # Usamos comprobaciones exactas en lugar de 'in' para no atrapar palabras compuestas
                    if lower == 'data' or lower == 'giorno': 
                        rename_map[orig] = 'Data'
                    elif lower == 'comune' or lower.startswith('comune '): 
                        rename_map[orig] = 'Comune'
                    elif lower == 'provincia' or lower.startswith('provincia '): 
                        rename_map[orig] = 'Provincia'
                    elif lower == 'autista' or lower == 'liv. operatore' or lower.startswith('autista '): 
                        rename_map[orig] = 'Livello_Autista'
                    elif lower == 'supporto' or lower.startswith('supporto '): 
                        rename_map[orig] = 'Livello_Supporto'
                    elif lower == 'tipologia mezzo' or lower == 'mezzo': 
                        rename_map[orig] = 'Mezzo'
                    elif lower == 'tot. h/turno' or lower == 'ore' or lower.startswith('tot. h'): 
                        rename_map[orig] = 'Ore'
                    elif lower == 'quantità kg' or lower == 'kg': 
                        rename_map[orig] = 'Kg'
                    elif lower == 'tipo di servizio' or lower == 'servizio': 
                        rename_map[orig] = 'Servizio'

                df_ing.rename(columns=rename_map, inplace=True)
                
                # Eliminación contundente de columnas duplicadas por si acaso
                df_ing = df_ing.loc[:, ~df_ing.columns.duplicated()]
                
                missing_cols = [c for c in ['Data', 'Comune'] if c not in df_ing.columns]
                if missing_cols:
                    st.error(f"Error: Imposible encontrar las columnas {missing_cols} en el archivo.")
                    with st.expander("🛠️ Abre para ver el Debug de Columnas"):
                        st.write(f"Encontré estas columnas en el Excel en la fila {header_idx}:")
                        st.write(list(df_ing.columns))
                    st.stop()
                    
                df_ing = df_ing.dropna(subset=['Data', 'Comune'])
                
                if df_ing.empty:
                    st.warning("No se encontraron datos válidos bajo las columnas Data y Comune.")
                else:
                    st.success(f"¡Archivo interpretado perfectamente! (Encabezado encontrado en la fila {header_idx + 1}). Procesando...")
                    
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
                        
                        ore_dec = parse_hours(row.get('Ore', 0))
                        
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
                            "Comune": comune,
                            "Liv. Autista": liv_aut if liv_aut != 'nan' and liv_aut else "-",
                            "€/h Autista": costo_h_aut,
                            "Liv. Supporto": liv_sup if liv_sup and liv_sup.lower() != 'nan' else "-",
                            "€/h Supporto": costo_h_sup,
                            "Mezzo": tipo_mezzo,
                            "€/h Mezzo": costo_h_mezzo,  
                            "Ore": ore_dec,
                            "Tot. Costo Pers.": costo_personale,
                            "Tot. Costo Mezzo": costo_mezzo,
                            "Ricavo/Ton": ricavo_ton,
                            "Ricavo Totale": ricavo_totale,
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
                    
                    st.subheader("Anteprima Elaboración")
                    view_df = df_res.copy()
                    view_df.drop(columns=['raw_costo_pers', 'raw_costo_mezzo', 'raw_overhead', 'raw_costo_tot', 'Servizio', 'Note', 'Anomalie'], inplace=True)
                    
                    sx(st.dataframe, view_df, hide_index=True, column_config={
                        "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "€/h Autista": st.column_config.NumberColumn(format="€ %.2f"),
                        "€/h Supporto": st.column_config.NumberColumn(format="€ %.2f"),
                        "€/h Mezzo": st.column_config.NumberColumn(format="€ %.2f"),
                        "Ore": st.column_config.NumberColumn(format="%.2f"),
                        "Tot. Costo Pers.": st.column_config.NumberColumn(format="€ %.2f"),
                        "Tot. Costo Mezzo": st.column_config.NumberColumn(format="€ %.2f"),
                        "Ricavo/Ton": st.column_config.NumberColumn(format="€ %.2f"),
                        "Ricavo Totale": st.column_config.NumberColumn(format="€ %.2f"),
                        "Margine": st.column_config.NumberColumn(format="€ %.2f")
                    })
                    
                    anomalie_tot = df_res['Anomalie'].sum()
                    if anomalie_tot > 0:
                        st.warning(f"ATENCIÓN: {anomalie_tot} filas presentan costos horarios a 0,00 €. Verifica en el menú 'Tariffe e contratti' haber guardado el importe para el nivel o vehículo mostrado arriba.")
                    
                    if sx(st.button, "Guardar todos como Centros de Costos", type="primary"):
                        rows_to_save = []
                        batch_id = datetime.now().strftime("%Y%m%d%H%M%S")
                        
                        for i, r in df_res.iterrows():
                            cid = f"CC-ING-{batch_id}-{i}"
                            rows_to_save.append({
                                "ID": cid, "Data": r["Data"], "Servizio": r["Servizio"], "Sottoservizio": r["Comune"], 
                                "Centro di Costo": centro_costo(r["Servizio"], r["Comune"]),
                                "Tonnellate": df_ing.iloc[i].get('Kg', 0) / 1000.0, "Ricavi": r["Ricavo Totale"], 
                                "Costo Personale": r["raw_costo_pers"], "Costo Mezzi": r["raw_costo_mezzo"], 
                                "Overhead": r["raw_overhead"], "Costo Totale": r["raw_costo_tot"], 
                                "Margine": r["Margine"], "Ore Uomo": r["Ore"] * (2 if r["Liv. Supporto"] != "-" else 1), 
                                "Ore Mezzi": r["Ore"], "Note": r["Note"] + f" | Vehículo: {r['Mezzo']}",
                                "Creato Da": st.session_state.nome, "Periodo Da": r["Data"], "Periodo A": r["Data"], 
                                "Anomalie": r["Anomalie"]
                            })
                            
                        append_rows("services", read_services, pd.DataFrame(rows_to_save))
                        st.session_state.flash = f"¡Completado! {len(rows_to_save)} centros de costo de voluminosos guardados en el sistema."
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error durante el procesamiento del archivo: {e}")

    # ============================================================
    # PAGINAS DE ANALISIS Y CONFIGURACION (SE CONTINUA)
    # ============================================================
    elif page == "Economico":
        df = authorized(services_df)
        if df.empty: st.info("No hay informes guardados todavía."); st.stop()
        a, b = st.columns([1, 1.4])
        service_filter = a.selectbox("Servicio", ["Tutti"] + list(SERVICE_TREE))
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
            if pdx.empty: st.info("Ningún detalle del personal.")
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
            if vdx.empty: st.info("Ningún detalle de los vehículos.")
            else:
                l, r = st.columns(2)
                with l:
                    chart_head("Costo per tipologia"); g = vdx.assign(Tipo=vdx["Tipo"].replace("", "Non assegnato")).groupby("Tipo", as_index=False)["Costo Totale"].sum(); show_chart(hbar_chart(g.sort_values("Costo Totale", ascending=False), "Tipo", "Costo Totale", color=TIDE))
                with r:
                    chart_head("Ore per targa"); g = vdx.assign(Targa=vdx["Targa"].replace("", "Senza targa")).groupby("Targa", as_index=False)["Ore"].sum().sort_values("Ore", ascending=False).head(12); show_chart(hbar_chart(g, "Targa", "Ore", color="#7C8B85"))

    elif page == "Anagrafiche":
        t1, t2 = st.tabs(["Operadores", "Vehículos"])
        with t1:
            edited = sx(st.data_editor, operators, num_rows="dynamic", hide_index=True, key="operators_editor", column_config={"Contratto": st.column_config.SelectboxColumn(options=[""] + list(CONTRACTS)), "Livello": st.column_config.SelectboxColumn(options=[""] + ALL_LEVELS)})
            dup = edited[edited["Matricola"].map(txt).ne("") & edited["Matricola"].duplicated(keep=False)]
            if not dup.empty: st.error("¡Matrículas repetidas!")
            if sx(st.button, "Guardar operadores", type="primary", disabled=not dup.empty): save_csv(edited.fillna(""), FILES["operators"]); st.session_state.flash = "Operadores guardados."; st.rerun()
        with t2:
            types = sorted(set(DEFAULT_VEHICLE_TYPES + tariffs.loc[tariffs["Tipo"].str.lower().eq("mezzo"), "Livello_o_Tipo"].astype(str).tolist()))
            edited = sx(st.data_editor, vehicles, num_rows="dynamic", hide_index=True, key="vehicles_editor", column_config={"Tipo": st.column_config.SelectboxColumn(options=[""] + types)})
            keys = edited["Targa"].map(plate_key); dup = edited[keys.ne("") & keys.duplicated(keep=False)]
            if not dup.empty: st.error("¡Placas repetidas!")
            if sx(st.button, "Guardar vehículos", type="primary", disabled=not dup.empty): save_csv(edited.fillna(""), FILES["vehicles"]); st.session_state.flash = "Vehículos guardados."; st.rerun()

    elif page == "Tariffari":
        t1, t2, t3, t4 = st.tabs(["Costos de Personal", "Costos de Vehículos", "Parámetros Generales", "Ingresos por Tonelada (Comunas)"])
        def save_group(kind, label, edited, force_contract=None):
            edited = edited.copy(); edited["Tipo"] = label
            if force_contract is not None: edited["Contratto"] = force_contract
            edited["Costo_Orario"] = edited["Costo_Orario"].apply(parse_num); edited["Attivo"] = edited["Attivo"].replace("", "SI").fillna("SI")
            current = read_tariffs()
            save_csv(pd.concat([current[~current["Tipo"].str.lower().eq(kind)], edited.fillna("")], ignore_index=True), FILES["tariffs"]); st.session_state.flash = "Tarifas actualizadas."; st.rerun()
        with t1:
            edited = sx(st.data_editor, tariffs[tariffs["Tipo"].str.lower().eq("personale")], num_rows="dynamic", hide_index=True, column_config={"Tipo": None, "Contratto": st.column_config.SelectboxColumn("Contratto", options=list(CONTRACTS)), "Livello_o_Tipo": st.column_config.SelectboxColumn("Nivel", options=ALL_LEVELS), "Costo_Orario": st.column_config.NumberColumn("Costo horario empresarial (€)", min_value=0.0, step=0.01, format="%.2f"), "Attivo": st.column_config.SelectboxColumn("Activo", options=["SI", "NO"])})
            if sx(st.button, "Guardar costos de personal", type="primary", key="s1"): save_group("personale", "Personale", edited)
        with t2:
            edited = sx(st.data_editor, tariffs[tariffs["Tipo"].str.lower().eq("mezzo")], num_rows="dynamic", hide_index=True, column_config={"Tipo": None, "Contratto": None, "Livello_o_Tipo": st.column_config.TextColumn("Tipo de vehículo"), "Costo_Orario": st.column_config.NumberColumn("Costo horario (€)", min_value=0.0, step=0.01, format="%.2f"), "Attivo": st.column_config.SelectboxColumn("Activo", options=["SI", "NO"])})
            if sx(st.button, "Guardar costos de vehículos", type="primary", key="s2"): save_group("mezzo", "Mezzo", edited)
        with t3:
            edited = sx(st.data_editor, tariffs[tariffs["Tipo"].str.lower().eq("generale")], num_rows="dynamic", hide_index=True, column_config={"Tipo": None, "Contratto": None, "Livello_o_Tipo": st.column_config.TextColumn("Parámetro"), "Costo_Orario": st.column_config.NumberColumn("Valor", step=0.01, format="%.2f"), "Attivo": st.column_config.SelectboxColumn("Activo", options=["SI", "NO"])})
            if sx(st.button, "Guardar parámetros", type="primary", key="s3"): save_group("generale", "Generale", edited)
        with t4:
            st.info("Configura el Ingreso basándote en la Comuna donde se realiza la recolección (Ej. Prato, Mugello).")
            edited = sx(st.data_editor, tariffs[tariffs["Tipo"].str.lower().eq("ricavo tonnellata")], num_rows="dynamic", hide_index=True, column_config={"Tipo": None, "Contratto": None, "Livello_o_Tipo": st.column_config.TextColumn("Comuna / Cantiere"), "Costo_Orario": st.column_config.NumberColumn("Ingreso (€/Ton)", min_value=0.0, step=0.01, format="%.2f"), "Attivo": st.column_config.SelectboxColumn("Activo", options=["SI", "NO"])})
            if sx(st.button, "Guardar Ingresos", type="primary", key="s4"): save_group("ricavo tonnellata", "Ricavo Tonnellata", edited, force_contract="Ingombranti")

    elif page == "Accessi":
        section("Usuarios y autorizaciones")
        users_now = read_users()
        edited = sx(st.data_editor, users_now, num_rows="dynamic", hide_index=True, key="users_editor", column_config={"password": None, "ruolo": st.column_config.SelectboxColumn("Rol", options=["admin", "capocantiere"])})
        if sx(st.button, "Guardar usuarios", type="primary"):
            names = edited["username"].map(txt)
            if names.eq("").any() or names.duplicated().any(): st.error("Comprueba los nombres de usuario introducidos.")
            else:
                out = edited.fillna(""); no_pw = out["password"].map(txt).eq("")
                out.loc[no_pw, "password"] = [hash_password(secrets.token_urlsafe(12)) for _ in range(int(no_pw.sum()))]
                save_csv(out, FILES["users"]); st.session_state.flash = "Usuarios actualizados."; st.rerun()
        section("Cambiar contraseña")
        p1, p2, p3 = st.columns([1, 1, 0.6])
        target = p1.selectbox("Usuario", users_now["username"].tolist()); new_pw = p2.text_input("Nueva contraseña", type="password"); p3.write("")
        if sx(p3.button, "Actualizar contraseña"):
            if len(new_pw) < 6: st.error("Al menos 6 caracteres.")
            else: users_now.loc[users_now["username"] == target, "password"] = hash_password(new_pw); save_csv(users_now, FILES["users"]); st.session_state.flash = f"Contraseña {target} actualizada."; st.rerun()

    html('<div class="foot">Cristoforo Control Room V8.15</div>')

except Exception as global_error:
    st.error("¡ERROR CRÍTICO! La aplicación no pudo iniciar.")
    st.error("Razón técnica: " + str(global_error))
    st.code(traceback.format_exc())
    st.warning("Pásame este bloque de error rojo y lo arreglaremos al instante.")
