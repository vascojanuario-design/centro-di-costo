import io
import os
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# ============================================================
# CRISTOFORO | CONTROL ROOM V6
# Flusso: Servizio -> Sottoservizio -> Certificazione ->
# Personale/Contratto -> Mezzi/Tipo -> Centro di costo -> Margine
# ============================================================

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

# ============================================================
# SERVIZI / SOTTOSERVIZI
# ============================================================

SERVICE_TREE = {
    "Spazzamenti": ["Scandicci"],
    "Aree Verdi": ["Piana", "Prato"],
    "Porta a Porta": [
        "Prato", "Vaiano", "Campi", "Noventa", "Costabissara",
        "Cremona", "Mantova", "Lucca",
    ],
    "Trasporti": ["Alia"],
    "Raccolta Cartone Selettivo": ["Firenze", "Piana", "Prato", "Campi"],
    "Ingombranti": ["Prato", "Campi Bisenzio", "Valdisieve", "Mugello"],
}
ALL_SUBSERVICES = sorted({x for values in SERVICE_TREE.values() for x in values})

# Tipi mezzo: archivio centrale. La direzione può aggiungerne/modificarne.
# La struttura evita di legare il calcolo economico alla targa.
DEFAULT_VEHICLE_TYPES = [
    "Leggero",
    "Furgone",
    "Compattatore",
    "Spazzatrice",
    "Scarrabile",
    "Pesante",
    "Speciale",
]

CONTRACTS = {
    "Servizi Ambientali - Utilitalia": [
        "Q", "A1", "A2S", "A2", "B1S", "B1", "B2S", "B2",
        "C1S", "C1", "C2S", "C2", "D1S", "D1", "D2S", "D2",
    ],
    "Cooperative Sociali": [
        "A1", "A2", "B1", "C1", "C2", "C3",
        "D1", "D2", "D3", "E1", "E2", "F1", "F2",
    ],
}

DEFAULT_VEHICLE_COSTS = {
    "Leggero": 15.0,
    "Furgone": 18.0,
    "Compattatore": 25.0,
    "Spazzatrice": 35.0,
    "Scarrabile": 40.0,
    "Pesante": 45.0,
    "Speciale": 65.0,
}

DEFAULT_USERS = pd.DataFrame([
    {
        "username": "direzione",
        "password": "admin",
        "nome": "Direzione",
        "ruolo": "admin",
        "autorizzazioni": "TUTTI",
    },
    {
        "username": "resp_prato",
        "password": "123",
        "nome": "Responsabile Prato",
        "ruolo": "capocantiere",
        "autorizzazioni": "Prato",
    },
    {
        "username": "resp_mantova",
        "password": "456",
        "nome": "Responsabile Mantova",
        "ruolo": "capocantiere",
        "autorizzazioni": "Mantova",
    },
])

# ============================================================
# PALETTE CHIARA / ALTO CONTRASTO
# ============================================================

st.markdown(
    """
<style>
:root {
    --bg: #F1F4F2;
    --surface: #FFFFFF;
    --surface-soft: #F8FAF9;
    --surface-green: #EAF5EE;
    --text: #16231D;
    --text-2: #34423B;
    --muted: #607068;
    --muted-2: #7A8780;
    --border: #D7E1DB;
    --border-strong: #C1D0C7;

    --green: #087A3D;
    --green-dark: #055A2D;
    --green-soft: #E4F3E9;
    --green-line: #BBDCC7;

    --blue: #1F5FAF;
    --blue-soft: #E8F1FC;
    --blue-line: #C6DAF2;

    --teal: #08777C;
    --teal-soft: #E5F4F5;
    --teal-line: #C5E2E4;

    --amber: #8A5A00;
    --amber-soft: #FFF5DE;
    --amber-line: #EED49C;

    --red: #B42318;
    --red-soft: #FDECEA;
    --red-line: #EDC8C4;

    --purple: #6744B4;
    --purple-soft: #F1ECFF;
    --purple-line: #DCD0FA;

    --shadow: 0 5px 20px rgba(24, 48, 34, 0.055);
}

html, body, [class*="css"] {
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.stApp { background: var(--bg); color: var(--text); }
.block-container { max-width: 1520px; padding-top: 1rem; padding-bottom: 4rem; }

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: #F7FAF8 !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] hr { border-color: var(--border) !important; }

.brand-box {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 14px;
    margin-bottom: 14px;
    box-shadow: var(--shadow);
}
.brand-main { color: var(--green) !important; font-size: 24px; font-weight: 950; letter-spacing: -1px; }
.brand-sub { color: var(--muted) !important; font-size: 9px; font-weight: 850; letter-spacing: 1px; margin-top: 3px; }
.nav-label { color: var(--muted) !important; font-size: 10px; text-transform: uppercase; letter-spacing: .9px; font-weight: 900; margin: 4px 4px 9px; }

section[data-testid="stSidebar"] [role="radiogroup"] { gap: 5px !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label {
    position: relative;
    min-height: 40px;
    border-radius: 12px !important;
    padding: 5px 11px !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    transition: all .15s ease;
}
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label p { color: var(--text-2) !important; font-size: 12px !important; font-weight: 800 !important; }
section[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #ECF5EF !important; border-color: #D6E8DC !important; transform: translateX(2px); }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background: var(--green-soft) !important; border-color: var(--green-line) !important; box-shadow: 0 4px 12px rgba(8, 122, 61, .07); }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::before {
    content: ""; position: absolute; left: -1px; top: 50%; transform: translateY(-50%); width: 4px; height: 22px; border-radius: 999px; background: var(--green);
}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color: var(--green-dark) !important; font-weight: 900 !important; }

.sidebar-user {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 11px 12px;
    box-shadow: var(--shadow);
}
.sidebar-user-name { color: var(--text) !important; font-weight: 900; font-size: 12px; }
.sidebar-user-meta { color: var(--muted) !important; font-size: 10px; margin-top: 3px; }

/* TOP */
.topbar {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 17px;
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: var(--shadow);
    margin-bottom: 15px;
}
.title { color: var(--text) !important; font-size: 27px; font-weight: 950; letter-spacing: -.8px; }
.subtitle { color: var(--muted) !important; font-size: 12px; margin-top: 3px; }
.user-pill { color: var(--green-dark) !important; background: var(--green-soft); border: 1px solid var(--green-line); border-radius: 999px; padding: 7px 11px; font-size: 10px; font-weight: 900; }

/* HERO */
.hero {
    position: relative;
    background: linear-gradient(135deg, #FFFFFF 0%, #F4FAF6 100%);
    border: 1px solid var(--green-line);
    border-left: 5px solid var(--green);
    border-radius: 18px;
    padding: 19px 22px;
    box-shadow: var(--shadow);
    margin-bottom: 15px;
    overflow: hidden;
}
.hero-kicker { color: var(--green-dark) !important; font-size: 10px; text-transform: uppercase; letter-spacing: 1.3px; font-weight: 950; }
.hero-title { color: var(--text) !important; font-size: 28px; font-weight: 950; letter-spacing: -1px; margin-top: 3px; }
.hero-copy { color: var(--muted) !important; max-width: 920px; font-size: 12px; margin-top: 4px; line-height: 1.5; }
.hero-stat { color: var(--green-dark) !important; font-size: 10px; font-weight: 800; margin-top: 12px; }

/* SECTION */
.section-title {
    color: var(--text) !important;
    font-size: 17px;
    font-weight: 950;
    margin: 19px 0 9px;
    padding-left: 9px;
    border-left: 4px solid var(--green);
}

/* KPI */
.kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 15px;
    min-height: 118px;
    padding: 14px 15px 13px 18px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
}
.kpi-strip { position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--green); }
.kpi.blue .kpi-strip { background: var(--blue); }
.kpi.teal .kpi-strip { background: var(--teal); }
.kpi.amber .kpi-strip { background: #C28600; }
.kpi.purple .kpi-strip { background: var(--purple); }
.kpi.red .kpi-strip { background: var(--red); }
.kpi-label { color: var(--muted) !important; font-size: 10px; text-transform: uppercase; letter-spacing: .65px; font-weight: 950; }
.kpi-value { color: var(--text) !important; font-size: 26px; line-height: 1.05; font-weight: 950; margin-top: 7px; }
.kpi-note { color: var(--muted-2) !important; font-size: 10px; margin-top: 5px; }

/* PANEL */
.panel { background: #FFFFFF; border: 1px solid var(--border); border-radius: 16px; padding: 15px; box-shadow: var(--shadow); margin-bottom: 13px; }
.panel-title { display:flex; align-items:center; background: var(--surface-soft); border:1px solid var(--border); border-radius: 10px; color: var(--text) !important; padding: 8px 10px; font-size: 13px; font-weight: 900; }
.panel-sub { color: var(--muted) !important; font-size: 10px; margin-top: 6px; }

/* STATUS */
.status { display:inline-block; border-radius: 999px; padding: 6px 9px; font-size: 10px; font-weight: 950; }
.status.ok { color: var(--green-dark) !important; background: var(--green-soft); border:1px solid var(--green-line); }
.status.warn { color: var(--amber) !important; background: var(--amber-soft); border:1px solid var(--amber-line); }
.status.bad { color: var(--red) !important; background: var(--red-soft); border:1px solid var(--red-line); }
.status.info { color: var(--blue) !important; background: var(--blue-soft); border:1px solid var(--blue-line); }

/* PILLS */
.pill { display:inline-block; border-radius:999px; padding:5px 8px; margin:2px 4px 2px 0; font-size:10px; font-weight:850; background:#F3F6F4; color:#405048 !important; border:1px solid var(--border); }
.pill.ok { background: var(--green-soft); color: var(--green-dark) !important; border-color: var(--green-line); }
.pill.warn { background: var(--amber-soft); color: var(--amber) !important; border-color: var(--amber-line); }
.pill.bad { background: var(--red-soft); color: var(--red) !important; border-color: var(--red-line); }

/* PROCESS */
.step { background:#FFFFFF; border:1px solid var(--border); border-radius:15px; padding:14px; min-height:120px; box-shadow:var(--shadow); }
.step-num { color:var(--green-dark) !important; font-size:9px; font-weight:950; text-transform:uppercase; letter-spacing:.8px; }
.step-title { color:var(--text) !important; font-size:15px; font-weight:900; margin-top:4px; }
.step-text { color:var(--muted) !important; font-size:10px; line-height:1.45; margin-top:4px; }

/* WIDGETS */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] span { color: var(--text) !important; font-weight: 800 !important; }
.stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 { color: var(--text) !important; }
.stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: var(--muted) !important; }

div[data-baseweb="select"] > div,
div[data-baseweb="input"],
div[data-baseweb="textarea"],
input, textarea {
    background:#FFFFFF !important;
    color:var(--text) !important;
    border-color:var(--border-strong) !important;
}
input::placeholder, textarea::placeholder { color:#8A968F !important; }
div[data-baseweb="select"] *, div[data-baseweb="input"] *, div[data-baseweb="textarea"] * { color:var(--text) !important; }
[data-baseweb="menu"], [data-baseweb="popover"] { background:#FFFFFF !important; }
[data-baseweb="menu"] li { color:var(--text) !important; }
[data-baseweb="menu"] li:hover { background:#EDF5F0 !important; }

div.stButton > button { min-height:40px; border-radius:11px; font-weight:900; }
div.stButton > button[kind="primary"] { background:var(--green) !important; color:#FFFFFF !important; border-color:var(--green) !important; }
div.stButton > button:not([kind="primary"]) { background:#FFFFFF !important; color:var(--text) !important; border-color:var(--border-strong) !important; }
div.stButton > button:hover { transform:translateY(-1px); }

[data-testid="stMetric"] { background:#FFFFFF !important; border:1px solid var(--border) !important; border-radius:13px !important; }
[data-testid="stMetricLabel"] { color:var(--muted) !important; }
[data-testid="stMetricValue"] { color:var(--text) !important; }

[data-testid="stDataFrame"], [data-testid="stDataEditor"] { border:1px solid var(--border); border-radius:12px; overflow:hidden; }
[data-testid="stFileUploader"] section { background:#FFFFFF !important; border:1px dashed var(--border-strong) !important; border-radius:14px !important; }
[data-testid="stFileUploader"] section * { color:var(--text-2) !important; }
[data-testid="stExpander"] { background:#FFFFFF !important; border:1px solid var(--border) !important; border-radius:14px !important; }
[data-testid="stExpander"] summary * { color:var(--text) !important; font-weight:850 !important; }

.footer { text-align:center; color:var(--muted-2) !important; font-size:10px; padding:30px 0 5px; }
footer { visibility:hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# UTILITY DATA
# ============================================================

def clean_col(value):
    text = str(value).replace("\ufeff", "").strip().lower()
    trans = str.maketrans({"à": "a", "è": "e", "é": "e", "ì": "i", "ò": "o", "ù": "u"})
    text = text.translate(trans)
    text = text.replace("€", "euro").replace("/", "_").replace("-", "_").replace(" ", "_")
    return re.sub(r"_+", "_", text).strip("_")


def normalize_columns(df):
    if df is None:
        return pd.DataFrame()
    out = df.copy()
    out.columns = [clean_col(c) for c in out.columns]
    return out


def aliases_rename(df, aliases):
    df = normalize_columns(df)
    reverse = {clean_col(k): k for k in aliases}
    mapping = {}
    for target, names in aliases.items():
        candidates = [target] + list(names)
        found = None
        for candidate in candidates:
            c = clean_col(candidate)
            if c in df.columns:
                found = c
                break
        if found and found != clean_col(target):
            mapping[found] = target
        elif found == clean_col(target):
            mapping[found] = target
    if mapping:
        df = df.rename(columns=mapping)
    return df


def ensure(df, columns):
    out = df.copy() if df is not None else pd.DataFrame()
    for col in columns:
        if col not in out.columns:
            out[col] = ""
    return out


def read_csv_flexible(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        try:
            df = pd.read_csv(path, sep=None, engine="python", dtype=str, keep_default_na=False, encoding=enc)
            if len(df.columns) > 1:
                return normalize_columns(df)
        except Exception:
            pass
    return pd.DataFrame()


def save_csv(df, path):
    out = df.copy()
    out.to_csv(path, index=False, encoding="utf-8-sig")


def parse_num(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        if pd.isna(value):
            return 0.0
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "nat"}:
        return 0.0
    text = text.replace("€", "").replace("EUR", "").replace("eur", "").replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif text.count(".") == 1:
        a, b = text.split(".")
        if len(b) == 3:
            text = a + b
    try:
        return float(text)
    except Exception:
        return 0.0


def parse_hours(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        n = float(value)
        if 0 < n < 1:
            return n * 24
        return n
    text = str(value).strip()
    if not text:
        return 0.0
    if ":" in text:
        parts = text.split(":")
        try:
            h = float(parts[0])
            m = float(parts[1]) if len(parts) > 1 else 0.0
            s = float(parts[2]) if len(parts) > 2 else 0.0
            return h + m / 60 + s / 3600
        except Exception:
            pass
    return parse_num(text)


def parse_date(value):
    if value is None or str(value).strip() == "":
        return pd.NaT
    try:
        return pd.to_datetime(value, dayfirst=True, errors="coerce")
    except Exception:
        return pd.NaT


def safe_value(value):
    return parse_num(value)


def safe_sum(series):
    if series is None:
        return 0.0
    try:
        return float(pd.Series(series).apply(parse_num).sum())
    except Exception:
        return 0.0


def euro(value):
    x = parse_num(value)
    return f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(value, decimals=1):
    x = parse_num(value)
    return f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value):
    return f"{parse_num(value):.1f}%".replace(".", ",")


def is_admin():
    return str(st.session_state.get("ruolo", "")).lower() in {"admin", "direzione"}


def split_people(value):
    if value is None:
        return []
    text = str(value).replace("\n", ";")
    parts = re.split(r"[;,|]+", text)
    return [p.strip() for p in parts if p.strip()]


def status_for_margin(margin, margin_pct, has_data):
    m = safe_value(margin)
    p = safe_value(margin_pct)
    if not has_data:
        return "ATTENZIONE", "Nessun dato consuntivato", "warn"
    if m < 0:
        return "CRITICO", "Margine negativo", "bad"
    if p < 5:
        return "ATTENZIONE", "Margine molto contenuto", "warn"
    return "OK", "Margine sotto controllo", "ok"


def centro_costo(service, subservice):
    return f"{service} · {subservice}"

# ============================================================
# CERTIFICATION SCHEMA: exactly the table supplied by the user
# ============================================================

CERT_ALIASES = {
    "ID": ["id_servizio", "id_record", "id_certificazione"],
    "Codice": ["codice_servizio", "codice_mezzo", "code"],
    "Descrizione": ["descrizione_servizio", "descrizione_mezzo", "description"],
    "Comuni": ["comune", "comuni", "territorio", "citta"],
    "Centro di Costo": ["centro_di_costo", "centro_costo", "cost_center"],
    "Data Pianificazione": ["data_pianificazione", "planning_date"],
    "Inizio Pianificazione": ["inizio_pianificazione", "planning_start"],
    "Fine Pianificazione": ["fine_pianificazione", "planning_end"],
    "Orario Previsto": ["orario_previsto", "durata_prevista", "planned_duration"],
    "Data Svolgimento": ["data_svolgimento", "data_esecuzione", "execution_date"],
    "Inizio Svolgimento": ["inizio_svolgimento", "inizio_esecuzione", "execution_start"],
    "Fine Svolgimento": ["fine_svolgimento", "fine_esecuzione", "execution_end"],
    "Durata": ["durata_svolgimento", "ore", "ore_lavorate", "duration"],
    "Operatori": ["operatore", "dipendente", "addetto", "operatori", "personale"],
    "Targa": ["targa", "plate"],
    "Attrezzatura": ["attrezzatura", "equipment", "mezzo", "veicolo"],
    "Note": ["note", "commenti"],
    "Stato": ["stato", "status", "stato_servizio"],
}

CERT_COLUMNS = list(CERT_ALIASES.keys())


def score_cert_header(df):
    if df is None or df.empty:
        return 0
    cols = {clean_col(c) for c in df.columns}
    aliases = set()
    for target, names in CERT_ALIASES.items():
        aliases.add(clean_col(target))
        aliases.update(clean_col(x) for x in names)
    return len(cols.intersection(aliases))


def load_uploaded_raw(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        raw = uploaded.getvalue()
        text = None
        for enc in ("utf-8-sig", "utf-8", "latin1"):
            try:
                text = raw.decode(enc)
                break
            except Exception:
                continue
        if text is None:
            raise ValueError("Codifica CSV non riconosciuta.")
        return pd.read_csv(io.StringIO(text), sep=None, engine="python")
    if name.endswith((".xlsx", ".xls")):
        excel = pd.ExcelFile(uploaded)
        best_df = None
        best_score = -1
        for sheet in excel.sheet_names:
            for header in range(0, 4):
                try:
                    sample = pd.read_excel(excel, sheet_name=sheet, header=header, nrows=30)
                    score = score_cert_header(sample)
                    if score > best_score:
                        best_df = pd.read_excel(excel, sheet_name=sheet, header=header)
                        best_score = score
                except Exception:
                    continue
        if best_df is None:
            raise ValueError("Nessun foglio Excel leggibile.")
        return best_df
    raise ValueError("Formato non supportato.")


def normalize_certification(df):
    df = aliases_rename(df, CERT_ALIASES)
    df = ensure(df, CERT_COLUMNS)[CERT_COLUMNS].copy()

    for col in ["ID", "Codice", "Descrizione", "Comuni", "Centro di Costo", "Operatori", "Targa", "Attrezzatura", "Note", "Stato"]:
        df[col] = df[col].astype(str).str.replace("\ufeff", "", regex=False).str.strip()

    for col in ["Data Pianificazione", "Data Svolgimento"]:
        df[col] = df[col].apply(parse_date)

    for col in ["Inizio Pianificazione", "Fine Pianificazione", "Inizio Svolgimento", "Fine Svolgimento"]:
        df[col] = df[col].astype(str).str.strip()

    df["Orario Previsto"] = df["Orario Previsto"].apply(parse_hours)
    df["Durata"] = df["Durata"].apply(parse_hours)

    # Fallback: se manca la data svolgimento ma c'è la pianificazione, usiamo la pianificazione solo per analisi.
    df["Data Analisi"] = df["Data Svolgimento"]
    df.loc[df["Data Analisi"].isna(), "Data Analisi"] = df.loc[df["Data Analisi"].isna(), "Data Pianificazione"]

    # Se la durata è assente ma ci sono inizio/fine, prova a ricavarla.
    def duration_from_times(row):
        current = parse_hours(row["Durata"])
        if current > 0:
            return current
        try:
            start = pd.to_datetime(str(row["Inizio Svolgimento"]), format="%H:%M", errors="coerce")
            end = pd.to_datetime(str(row["Fine Svolgimento"]), format="%H:%M", errors="coerce")
            if pd.notna(start) and pd.notna(end):
                delta = (end - start).total_seconds() / 3600
                if delta < 0:
                    delta += 24
                return max(delta, 0)
        except Exception:
            pass
        return 0.0

    df["Durata"] = df.apply(duration_from_times, axis=1)
    df["Stato"] = df["Stato"].replace("", "Da verificare")

    return df

# ============================================================
# INIT FILES
# ============================================================

def init_files():
    if not os.path.exists(FILES["users"]):
        save_csv(DEFAULT_USERS, FILES["users"])
    if not os.path.exists(FILES["operators"]):
        save_csv(pd.DataFrame(columns=["Matricola", "Nome", "Cognome", "Contratto", "Livello", "Sottoservizio"]), FILES["operators"])
    if not os.path.exists(FILES["vehicles"]):
        save_csv(pd.DataFrame(columns=["Targa", "Mezzo", "Tipo", "Sottoservizio"]), FILES["vehicles"])
    if not os.path.exists(FILES["services"]):
        save_csv(pd.DataFrame(columns=[
            "ID", "Data", "Servizio", "Sottoservizio", "Centro di Costo", "Tonnellate", "Ricavi",
            "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Ore Uomo", "Ore Mezzi", "Note", "Creato Da",
        ]), FILES["services"])
    if not os.path.exists(FILES["personnel"]):
        save_csv(pd.DataFrame(columns=[
            "ID Consuntivo", "Certificazione ID", "Data", "Servizio", "Sottoservizio", "Matricola", "Operatore",
            "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale", "Stato Match",
        ]), FILES["personnel"])
    if not os.path.exists(FILES["vehicle_detail"]):
        save_csv(pd.DataFrame(columns=[
            "ID Consuntivo", "Certificazione ID", "Data", "Servizio", "Sottoservizio", "Targa", "Attrezzatura",
            "Tipo", "Ore", "Costo Orario", "Costo Totale", "Stato Match",
        ]), FILES["vehicle_detail"])
    if not os.path.exists(FILES["certifications"]):
        save_csv(pd.DataFrame(columns=["ID Import", "Data Import", "File", "Righe", "Ore", "Stato", "Operatore"]), FILES["certifications"])
    if not os.path.exists(FILES["cert_rows"]):
        save_csv(pd.DataFrame(columns=CERT_COLUMNS + ["ID Import"]), FILES["cert_rows"])
    if not os.path.exists(FILES["tariffs"]):
        rows = []
        for contract, levels in CONTRACTS.items():
            for level in levels:
                rows.append({"Tipo": "Personale", "Contratto": contract, "Livello_o_Tipo": level, "Costo_Orario": 0.0, "Attivo": "SI"})
        for kind, cost in DEFAULT_VEHICLE_COSTS.items():
            rows.append({"Tipo": "Mezzo", "Contratto": "", "Livello_o_Tipo": kind, "Costo_Orario": cost, "Attivo": "SI"})
        rows.extend([
            {"Tipo": "Generale", "Contratto": "", "Livello_o_Tipo": "Overhead", "Costo_Orario": 15.0, "Attivo": "SI"},
            {"Tipo": "Generale", "Contratto": "", "Livello_o_Tipo": "Tariffa tonnellata", "Costo_Orario": 130.0, "Attivo": "SI"},
        ])
        save_csv(pd.DataFrame(rows), FILES["tariffs"])

init_files()

# ============================================================
# READERS
# ============================================================

def read_users():
    df = aliases_rename(read_csv_flexible(FILES["users"]), {
        "username": ["user", "utente", "login"],
        "password": ["pass", "pwd"],
        "nome": ["name", "nominativo"],
        "ruolo": ["role", "profilo"],
        "autorizzazioni": ["cantieri", "commesse", "cantiere", "accessi"],
    })
    cols = ["username", "password", "nome", "ruolo", "autorizzazioni"]
    if df.empty or not all(c in df.columns for c in cols):
        return DEFAULT_USERS.copy()
    df = ensure(df, cols)[cols].copy()
    for c in cols:
        df[c] = df[c].astype(str).str.strip()
    return df


def read_operators():
    df = aliases_rename(read_csv_flexible(FILES["operators"]), {
        "Matricola": ["matricola", "id_operatore", "codice_operatore", "employee_id"],
        "Nome": ["nome", "first_name"],
        "Cognome": ["cognome", "last_name"],
        "Contratto": ["contratto", "ccnl"],
        "Livello": ["livello", "level", "inquadramento"],
        "Sottoservizio": ["cantiere", "commessa", "subservice"],
    })
    cols = ["Matricola", "Nome", "Cognome", "Contratto", "Livello", "Sottoservizio"]
    df = ensure(df, cols)[cols].copy()
    for c in cols:
        df[c] = df[c].astype(str).str.strip()
    return df


def read_vehicles():
    df = aliases_rename(read_csv_flexible(FILES["vehicles"]), {
        "Targa": ["targa", "plate"],
        "Mezzo": ["mezzo", "veicolo", "vehicle"],
        "Tipo": ["tipo", "tipo_mezzo", "categoria_mezzo"],
        "Sottoservizio": ["cantiere", "commessa", "subservice"],
    })
    cols = ["Targa", "Mezzo", "Tipo", "Sottoservizio"]
    df = ensure(df, cols)[cols].copy()
    for c in cols:
        df[c] = df[c].astype(str).str.strip()
    return df


def read_tariffs():
    df = aliases_rename(read_csv_flexible(FILES["tariffs"]), {
        "Tipo": ["tipo_costo", "categoria"],
        "Contratto": ["ccnl"],
        "Livello_o_Tipo": ["livello", "livello_o_tipo", "voce", "tipo_mezzo"],
        "Costo_Orario": ["costo_orario", "costo", "tariffa", "prezzo"],
        "Attivo": ["attiva", "active"],
    })
    cols = ["Tipo", "Contratto", "Livello_o_Tipo", "Costo_Orario", "Attivo"]
    df = ensure(df, cols)[cols].copy()
    df["Costo_Orario"] = df["Costo_Orario"].apply(parse_num)
    return df


def read_services():
    # Compatibilità con lo storico precedente:
    # Categoria -> Servizio, Cantiere/Dettaglio -> Sottoservizio.
    df = aliases_rename(read_csv_flexible(FILES["services"]), {
        "ID": ["id_consuntivo", "id"],
        "Data": ["data_servizio", "giorno", "date"],
        "Servizio": ["categoria", "servizio_principale", "tipo_servizio"],
        "Sottoservizio": ["sotto_servizio", "dettaglio", "cantiere", "commessa"],
        "Centro di Costo": ["centro_di_costo", "centro_costo"],
        "Tonnellate": ["ton", "tonnellaggio"],
        "Ricavi": ["ricavo", "ricavi_euro", "revenue", "fatturato"],
        "Costo Personale": ["costo_personale"],
        "Costo Mezzi": ["costo_mezzi"],
        "Overhead": ["overhead", "costi_indiretti"],
        "Costo Totale": ["costo", "costi", "costo_totale"],
        "Margine": ["margine_netto", "profitto"],
        "Ore Uomo": ["ore_uomo", "ore_personale", "ore_operatori"],
        "Ore Mezzi": ["ore_mezzi", "ore_veicoli"],
        "Note": ["note", "commenti"],
        "Creato Da": ["operatore", "utente", "created_by"],
    })
    cols = ["ID", "Data", "Servizio", "Sottoservizio", "Centro di Costo", "Tonnellate", "Ricavi",
            "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Ore Uomo", "Ore Mezzi", "Note", "Creato Da"]
    df = ensure(df, cols)[cols].copy()
    df["Data"] = df["Data"].apply(parse_date)
    for c in ["Tonnellate", "Ricavi", "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Ore Uomo", "Ore Mezzi"]:
        if c in ["Ore Uomo", "Ore Mezzi"]:
            df[c] = df[c].apply(parse_hours)
        else:
            df[c] = df[c].apply(parse_num)
    for c in ["ID", "Servizio", "Sottoservizio", "Centro di Costo", "Note", "Creato Da"]:
        df[c] = df[c].astype(str).str.strip()
    if not df.empty:
        missing = df["Margine"].eq(0) & (df["Ricavi"].ne(0) | df["Costo Totale"].ne(0))
        df.loc[missing, "Margine"] = df.loc[missing, "Ricavi"] - df.loc[missing, "Costo Totale"]
        missing_cc = df["Centro di Costo"].eq("")
        df.loc[missing_cc, "Centro di Costo"] = df.loc[missing_cc].apply(lambda r: centro_costo(r["Servizio"], r["Sottoservizio"]), axis=1)
    return df


def read_personnel():
    df = aliases_rename(read_csv_flexible(FILES["personnel"]), {
        "ID Consuntivo": ["id_consuntivo", "id"],
        "Certificazione ID": ["certificazione_id", "id_certificazione", "id_import"],
        "Data": ["data"],
        "Servizio": ["categoria", "servizio"],
        "Sottoservizio": ["cantiere", "commessa", "dettaglio"],
        "Matricola": ["matricola", "id_operatore"],
        "Operatore": ["operatore", "dipendente", "addetto"],
        "Contratto": ["ccnl"],
        "Livello": ["level", "inquadramento"],
        "Ore": ["ore_lavorate", "hours"],
        "Costo Orario": ["costo_orario", "tariffa"],
        "Costo Totale": ["costo", "costo_totale"],
        "Stato Match": ["stato_match", "match"],
    })
    cols = ["ID Consuntivo", "Certificazione ID", "Data", "Servizio", "Sottoservizio", "Matricola", "Operatore", "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale", "Stato Match"]
    df = ensure(df, cols)[cols].copy()
    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)
    df["Costo Orario"] = df["Costo Orario"].apply(parse_num)
    df["Costo Totale"] = df["Costo Totale"].apply(parse_num)
    return df


def read_vehicle_detail():
    df = aliases_rename(read_csv_flexible(FILES["vehicle_detail"]), {
        "ID Consuntivo": ["id_consuntivo", "id"],
        "Certificazione ID": ["certificazione_id", "id_certificazione", "id_import"],
        "Data": ["data"],
        "Servizio": ["categoria", "servizio"],
        "Sottoservizio": ["cantiere", "commessa", "dettaglio"],
        "Targa": ["targa", "plate"],
        "Attrezzatura": ["attrezzatura", "equipment"],
        "Tipo": ["tipo", "tipo_mezzo"],
        "Ore": ["ore_lavorate", "hours"],
        "Costo Orario": ["costo_orario", "tariffa"],
        "Costo Totale": ["costo", "costo_totale"],
        "Stato Match": ["stato_match", "match"],
    })
    cols = ["ID Consuntivo", "Certificazione ID", "Data", "Servizio", "Sottoservizio", "Targa", "Attrezzatura", "Tipo", "Ore", "Costo Orario", "Costo Totale", "Stato Match"]
    df = ensure(df, cols)[cols].copy()
    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)
    df["Costo Orario"] = df["Costo Orario"].apply(parse_num)
    df["Costo Totale"] = df["Costo Totale"].apply(parse_num)
    return df


def read_cert_rows():
    df = aliases_rename(read_csv_flexible(FILES["cert_rows"]), {
        **CERT_ALIASES,
        "ID Import": ["id_import", "import_id"],
    })
    cols = CERT_COLUMNS + ["ID Import"]
    df = ensure(df, cols)[cols].copy()
    for c in ["Data Pianificazione", "Data Svolgimento"]:
        df[c] = df[c].apply(parse_date)
    df["Orario Previsto"] = df["Orario Previsto"].apply(parse_hours)
    df["Durata"] = df["Durata"].apply(parse_hours)
    return df


def split_access(value):
    raw = str(value).strip()
    if raw.upper() in {"TUTTI", "ALL", "*"}:
        return ALL_SUBSERVICES.copy()
    values = re.split(r"[,;|]", raw)
    return sorted({x.strip() for x in values if x.strip() in ALL_SUBSERVICES})


def authorized(df, column="Sottoservizio"):
    if df is None or df.empty or is_admin():
        return df.copy() if df is not None else pd.DataFrame()
    allowed = st.session_state.get("allowed_subservices", [])
    if not allowed or column not in df.columns:
        return df.iloc[0:0].copy()
    return df[df[column].astype(str).str.strip().isin(allowed)].copy()


def labor_rate(tariffs, contract, level):
    m = (
        tariffs["Tipo"].astype(str).str.lower().eq("personale")
        & tariffs["Contratto"].astype(str).str.strip().eq(str(contract).strip())
        & tariffs["Livello_o_Tipo"].astype(str).str.strip().eq(str(level).strip())
        & tariffs["Attivo"].astype(str).str.upper().eq("SI")
    )
    data = tariffs.loc[m, "Costo_Orario"]
    return float(data.iloc[0]) if not data.empty else 0.0


def certification_scope(cert, subservice):
    """Filtra la certificazione sul sottoservizio/comune selezionato."""
    if cert is None or cert.empty:
        return pd.DataFrame(columns=CERT_COLUMNS + ["Data Analisi"])
    target = str(subservice).strip().lower()
    comune = cert["Comuni"].astype(str).str.strip().str.lower()
    centro = cert["Centro di Costo"].astype(str).str.strip().str.lower()
    descrizione = cert["Descrizione"].astype(str).str.strip().str.lower()
    mask = comune.eq(target) | centro.str.contains(re.escape(target), regex=True, na=False) | descrizione.str.contains(re.escape(target), regex=True, na=False)
    return cert[mask].copy()


def vehicle_rate(tariffs, kind):
    m = (
        tariffs["Tipo"].astype(str).str.lower().eq("mezzo")
        & tariffs["Livello_o_Tipo"].astype(str).str.strip().eq(str(kind).strip())
        & tariffs["Attivo"].astype(str).str.upper().eq("SI")
    )
    data = tariffs.loc[m, "Costo_Orario"]
    return float(data.iloc[0]) if not data.empty else 0.0


def general_rate(tariffs, name, default=0.0):
    m = (
        tariffs["Tipo"].astype(str).str.lower().eq("generale")
        & tariffs["Livello_o_Tipo"].astype(str).str.strip().eq(name)
        & tariffs["Attivo"].astype(str).str.upper().eq("SI")
    )
    data = tariffs.loc[m, "Costo_Orario"]
    return float(data.iloc[0]) if not data.empty else default


def find_operator(operators, matricola, name):
    if not operators.empty and matricola:
        found = operators[operators["Matricola"].astype(str).str.strip().eq(str(matricola).strip())]
        if not found.empty:
            return found.iloc[0]
    if not operators.empty and name:
        target = re.sub(r"\s+", " ", str(name).strip().lower())
        full = (operators["Nome"].astype(str) + " " + operators["Cognome"].astype(str)).str.replace(r"\s+", " ", regex=True).str.strip().str.lower()
        found = operators[full.eq(target)]
        if not found.empty:
            return found.iloc[0]
    return None


def find_vehicle(vehicles, targa):
    if vehicles.empty or not targa:
        return None
    found = vehicles[vehicles["Targa"].astype(str).str.upper().str.strip().eq(str(targa).strip().upper())]
    return found.iloc[0] if not found.empty else None

# ============================================================
# SESSION / LOGIN
# ============================================================

for key, value in {
    "logged": False,
    "username": "",
    "nome": "",
    "ruolo": "",
    "allowed_subservices": [],
    "cert_df": pd.DataFrame(),
    "cert_file": "",
    "cert_import_id": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

if not st.session_state.logged:
    st.markdown(
        '<div class="hero" style="max-width:470px;margin:8vh auto 18px;text-align:center;border-left:0;border-top:5px solid #087A3D"><div class="hero-kicker">CRISTOFORO</div><div class="hero-title">Control Room</div><div class="hero-copy">Controllo operativo, certificazione ore e centro di costo.</div></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1.35, 1])
    with c2:
        username = st.text_input("Username", placeholder="Inserisci username")
        password = st.text_input("Password", type="password", placeholder="Inserisci password")
        if st.button("Entra nella Control Room", type="primary", use_container_width=True):
            users = read_users()
            mask = users["username"].astype(str).str.strip().eq(username.strip()) & users["password"].astype(str).str.strip().eq(password.strip())
            match = users[mask]
            if match.empty:
                st.error("Username o password non corretti.")
            else:
                row = match.iloc[0]
                st.session_state.logged = True
                st.session_state.username = str(row["username"])
                st.session_state.nome = str(row["nome"])
                st.session_state.ruolo = str(row["ruolo"])
                st.session_state.allowed_subservices = split_access(row["autorizzazioni"])
                st.rerun()
    st.stop()

# ============================================================
# GLOBAL DATA
# ============================================================

users = read_users()
operators = read_operators()
vehicles = read_vehicles()
tariffs = read_tariffs()
services_df = read_services()
personnel_detail = read_personnel()
vehicle_detail = read_vehicle_detail()
cert_rows = read_cert_rows()

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        '<div class="brand-box"><div class="brand-main">♻️ CRISTOFORO</div><div class="brand-sub">CONTROL ROOM · CENTRO DI COSTO</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="nav-label">Navigazione</div>', unsafe_allow_html=True)
    page_labels = {
        "Dashboard": "◈  Dashboard",
        "Consuntivazione": "＋  Nuovo consuntivo",
        "Certificazioni": "✓  Certificazioni",
        "Economico": "€  Centro di costo",
    }
    pages = ["Dashboard", "Consuntivazione", "Certificazioni", "Economico"]
    if is_admin():
        pages += ["Anagrafiche", "Tariffari & Contratti", "Accessi"]
    selected = st.radio("Menu", [page_labels.get(p, p) for p in pages], label_visibility="collapsed")
    page = next(p for p in pages if page_labels.get(p, p) == selected)

    st.markdown("---")
    access_text = "Direzione" if is_admin() else f"Accesso a {len(st.session_state.allowed_subservices)} sottoservizi"
    st.markdown(
        f'<div class="sidebar-user"><div class="sidebar-user-name">● {st.session_state.nome}</div><div class="sidebar-user-meta">Ruolo · {st.session_state.ruolo}</div><div class="sidebar-user-meta">{access_text}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    if st.button("↪  Esci", use_container_width=True):
        for key in ["logged", "username", "nome", "ruolo", "allowed_subservices", "cert_df", "cert_file", "cert_import_id"]:
            st.session_state.pop(key, None)
        st.rerun()

# ============================================================
# TOPBAR
# ============================================================

meta = {
    "Dashboard": ("Control Room", "La cabina di regia operativa ed economica"),
    "Consuntivazione": ("Nuovo consuntivo", "Servizio → sottoservizio → certificazione → costo"),
    "Certificazioni": ("Certificazioni", "Importa la certificazione reale e verifica operatori e mezzi"),
    "Economico": ("Centro di costo", "Ricavi, costi, ore e margine per servizio e sottoservizio"),
    "Anagrafiche": ("Anagrafiche", "Operatori e mezzi"),
    "Tariffari & Contratti": ("Tariffari & Contratti", "Livelli contrattuali, costi del personale e costi mezzi"),
    "Accessi": ("Accessi", "Utenti e autorizzazioni"),
}
title, subtitle = meta[page]
st.markdown(
    f'<div class="topbar"><div><div class="title">{title}</div><div class="subtitle">{subtitle}</div></div><div class="user-pill">● {st.session_state.nome}</div></div>',
    unsafe_allow_html=True,
)

# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":
    df = authorized(services_df)
    st.markdown(
        '<div class="section-title">1. Cosa vuoi controllare?</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1.3, 1])
    with c1:
        service_filter = st.selectbox("Servizio", ["Tutti"] + list(SERVICE_TREE.keys()))
    with c2:
        if service_filter == "Tutti":
            subs = ALL_SUBSERVICES.copy()
        else:
            subs = SERVICE_TREE[service_filter].copy()
        if not is_admin():
            subs = [x for x in subs if x in st.session_state.allowed_subservices]
        sub_filter = st.selectbox("Sottoservizio", ["Tutti"] + subs)
    with c3:
        period = st.selectbox("Periodo", ["Tutto", "Ultimi 30 giorni", "Ultimi 90 giorni", "Anno corrente"])

    if service_filter != "Tutti":
        df = df[df["Servizio"].astype(str).eq(service_filter)].copy()
    if sub_filter != "Tutti":
        df = df[df["Sottoservizio"].astype(str).eq(sub_filter)].copy()
    if period != "Tutto":
        today = pd.Timestamp.today().normalize()
        start = today - pd.Timedelta(days=30 if period == "Ultimi 30 giorni" else 90) if period != "Anno corrente" else pd.Timestamp(today.year, 1, 1)
        df = df[df["Data"].isna() | (df["Data"] >= start)].copy()

    label = sub_filter if sub_filter != "Tutti" else (service_filter if service_filter != "Tutti" else "Tutte le attività")
    st.markdown(
        f'<div class="hero"><div class="hero-kicker">Dashboard operativa</div><div class="hero-title">{label}</div><div class="hero-copy">La selezione guida tutti i KPI, le ore certificate e il centro di costo. Nessun dato viene mescolato tra servizi differenti.</div><div class="hero-stat">● {len(df)} consuntivi · filtri applicati in tempo reale</div></div>',
        unsafe_allow_html=True,
    )

    revenue = safe_sum(df["Ricavi"] if "Ricavi" in df.columns else None)
    costs = safe_sum(df["Costo Totale"] if "Costo Totale" in df.columns else None)
    margin = safe_sum(df["Margine"] if "Margine" in df.columns else None)
    margin_pct = margin / revenue * 100 if revenue else 0
    labor_hours = safe_sum(df["Ore Uomo"] if "Ore Uomo" in df.columns else None)
    vehicle_hours = safe_sum(df["Ore Mezzi"] if "Ore Mezzi" in df.columns else None)
    tonnes = safe_sum(df["Tonnellate"] if "Tonnellate" in df.columns else None)

    cards = [
        ("Ricavi", euro(revenue), "fatturato", ""),
        ("Costo totale", euro(costs), "personale + mezzi + indiretti", "blue"),
        ("Margine", euro(margin), pct(margin_pct), "teal" if margin >= 0 else "red"),
        ("Margine %", pct(margin_pct), "sul ricavo", "purple"),
        ("Ore uomo", f"{num(labor_hours)} h", "certificazione", "amber"),
        ("Ore mezzi", f"{num(vehicle_hours)} h", "certificazione", ""),
    ]
    cols = st.columns(6)
    for col, (label_kpi, value, note, cls) in zip(cols, cards):
        with col:
            st.markdown(f'<div class="kpi {cls}"><div class="kpi-strip"></div><div class="kpi-label">{label_kpi}</div><div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">2. Control Tower</div>', unsafe_allow_html=True)
    s_label, s_text, s_class = status_for_margin(margin, margin_pct, not df.empty)
    total_hours = labor_hours + vehicle_hours
    cost_hour = costs / total_hours if total_hours else 0
    cost_ton = costs / tonnes if tonnes else 0
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.markdown(f'<div class="panel"><div class="panel-title">Stato economico</div><div style="margin-top:13px"><span class="status {s_class}">{s_label}</span></div><div class="panel-sub">{s_text}</div></div>', unsafe_allow_html=True)
    with t2:
        st.markdown(f'<div class="panel"><div class="panel-title">Ore certificate</div><div class="kpi-value" style="font-size:25px;margin-top:10px">{num(total_hours)} h</div><div class="panel-sub">Uomo {num(labor_hours)} h · Mezzi {num(vehicle_hours)} h</div></div>', unsafe_allow_html=True)
    with t3:
        st.markdown(f'<div class="panel"><div class="panel-title">Costo medio / ora</div><div class="kpi-value" style="font-size:25px;margin-top:10px">{euro(cost_hour)}</div><div class="panel-sub">costo totale / ore certificate</div></div>', unsafe_allow_html=True)
    with t4:
        st.markdown(f'<div class="panel"><div class="panel-title">Costo / tonnellata</div><div class="kpi-value" style="font-size:25px;margin-top:10px">{euro(cost_ton)}</div><div class="panel-sub">{num(tonnes)} tonnellate registrate</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">3. Andamento e composizione</div>', unsafe_allow_html=True)
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown('<div class="panel"><div class="panel-title">Ricavi / Costi / Margine</div><div class="panel-sub">Solo i dati della selezione corrente</div></div>', unsafe_allow_html=True)
        if not df.empty and df["Data"].notna().any():
            trend = df.dropna(subset=["Data"]).groupby("Data")[["Ricavi", "Costo Totale", "Margine"]].sum().sort_index()
            st.line_chart(trend)
        else:
            st.info("Servono consuntivi con data per mostrare il trend.")
    with right:
        st.markdown('<div class="panel"><div class="panel-title">Composizione costi</div><div class="panel-sub">Personale, mezzi e costi indiretti</div></div>', unsafe_allow_html=True)
        mix = pd.Series({
            "Personale": safe_sum(df["Costo Personale"] if "Costo Personale" in df.columns else None),
            "Mezzi": safe_sum(df["Costo Mezzi"] if "Costo Mezzi" in df.columns else None),
            "Overhead": safe_sum(df["Overhead"] if "Overhead" in df.columns else None),
        })
        st.bar_chart(mix)

    st.markdown('<div class="section-title">4. Semaforo servizi</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    for service_name, subs in SERVICE_TREE.items():
        visible = subs if is_admin() else [x for x in subs if x in st.session_state.allowed_subservices]
        if not visible:
            continue
        html = f'<div style="padding:7px 0"><strong style="color:#16231D">{service_name}</strong><div style="margin-top:4px">'
        for sub in visible:
            d = df[df["Sottoservizio"].eq(sub)]
            m = safe_sum(d["Margine"] if not d.empty else None)
            r = safe_sum(d["Ricavi"] if not d.empty else None)
            p = m / r * 100 if r else 0
            _, _, klass = status_for_margin(m, p, not d.empty)
            label = "NESSUN DATO" if d.empty else f"{euro(m)} · {pct(p)}"
            html += f'<span class="pill {klass}">{sub} · {label}</span>'
        html += '</div></div>'
        st.markdown(html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# CERTIFICATIONS
# ============================================================

elif page == "Certificazioni":
    st.markdown('<div class="section-title">1. Importa il file ufficiale</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="panel-title">Struttura riconosciuta</div><div class="panel-sub">ID · Codice · Descrizione · Comuni · Centro di Costo · Pianificazione · Svolgimento · Durata · Operatori · Targa · Attrezzatura · Note · Stato</div></div>', unsafe_allow_html=True)

    uploaded = st.file_uploader("Certificazione ore mezzi / operatori", type=["csv", "xlsx", "xls"])
    if uploaded:
        try:
            raw = load_uploaded_raw(uploaded)
            cert = normalize_certification(raw)
            st.session_state.cert_df = cert
            st.session_state.cert_file = uploaded.name
            st.session_state.cert_import_id = "IMP-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
            st.success(f"File letto correttamente: {len(cert)} righe.")
        except Exception as exc:
            st.error(f"Errore nella lettura del file: {exc}")

    cert = st.session_state.cert_df.copy()
    if not cert.empty:
        total = safe_sum(cert["Durata"])
        rows_with_operator = int(cert["Operatori"].astype(str).str.strip().ne("").sum())
        rows_with_plate = int(cert["Targa"].astype(str).str.strip().ne("").sum())
        certified = int(cert["Stato"].astype(str).str.lower().eq("certificato").sum())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Righe", len(cert))
        c2.metric("Durata totale", f"{num(total)} h")
        c3.metric("Righe con operatori", rows_with_operator)
        c4.metric("Righe con targa", rows_with_plate)

        st.markdown('<div class="section-title">2. Verifica della certificazione</div>', unsafe_allow_html=True)
        # Mostra esattamente la struttura operativa fornita dall'utente.
        view = cert.copy()
        view["Data Pianificazione"] = pd.to_datetime(view["Data Pianificazione"], errors="coerce").dt.strftime("%d/%m/%Y")
        view["Data Svolgimento"] = pd.to_datetime(view["Data Svolgimento"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(view[CERT_COLUMNS], use_container_width=True, hide_index=True)

        # Controlli automatici
        missing_state = int(cert["Stato"].astype(str).str.lower().isin(["", "da verificare", "nan"]).sum())
        missing_duration = int(cert["Durata"].apply(parse_hours).le(0).sum())
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="panel"><div class="panel-title">Stato certificazione</div><div style="margin-top:10px"><span class="status {"ok" if missing_state == 0 else "warn"}">{"OK" if missing_state == 0 else f"{missing_state} da verificare"}</span></div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="panel"><div class="panel-title">Durate</div><div style="margin-top:10px"><span class="status {"ok" if missing_duration == 0 else "warn"}">{"OK" if missing_duration == 0 else f"{missing_duration} senza durata"}</span></div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="panel"><div class="panel-title">Righe certificate</div><div class="kpi-value" style="font-size:23px;margin-top:10px">{certified}/{len(cert)}</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">3. Salvataggio importazione</div>', unsafe_allow_html=True)
        if st.button("Registra e archivia certificazione", type="primary", use_container_width=True):
            import_row = pd.DataFrame([{
                "ID Import": st.session_state.cert_import_id,
                "Data Import": datetime.now(),
                "File": st.session_state.cert_file,
                "Righe": len(cert),
                "Ore": total,
                "Stato": "OK" if missing_state == 0 and missing_duration == 0 else "DA VERIFICARE",
                "Operatore": st.session_state.nome,
            }])
            imports = read_csv_flexible(FILES["certifications"])
            save_csv(pd.concat([imports, import_row], ignore_index=True), FILES["certifications"])
            rows = cert.copy()
            rows["ID Import"] = st.session_state.cert_import_id
            old = read_cert_rows()
            save_csv(pd.concat([old, rows], ignore_index=True), FILES["cert_rows"])
            st.success("Certificazione archiviata. Ora puoi aprire Nuovo Consuntivo.")

        st.download_button(
            "Scarica copia normalizzata",
            data=view[CERT_COLUMNS].to_csv(index=False, encoding="utf-8-sig"),
            file_name="certificazione_normalizzata.csv",
            mime="text/csv",
            use_container_width=True,
        )

# ============================================================
# CONSUNTIVAZIONE
# ============================================================

elif page == "Consuntivazione":
    st.markdown('<div class="section-title">1. Definisci il servizio</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c1:
        service = st.selectbox("Servizio", list(SERVICE_TREE.keys()))
    with c2:
        options = SERVICE_TREE[service].copy()
        if not is_admin():
            options = [x for x in options if x in st.session_state.allowed_subservices]
        if not options:
            st.error("Nessun sottoservizio autorizzato.")
            st.stop()
        subservice = st.selectbox("Sottoservizio", options)
    with c3:
        service_date = st.date_input("Data centro di costo", value=datetime.today().date())

    st.markdown(
        f'<div class="panel"><div class="panel-title">Centro di Costo</div><div class="kpi-value" style="font-size:22px;margin-top:10px">{centro_costo(service, subservice)}</div><div class="panel-sub">Il centro di costo viene generato automaticamente dalla coppia Servizio + Sottoservizio.</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">2. Collega la certificazione</div>', unsafe_allow_html=True)
    raw_cert = st.session_state.cert_df.copy()
    cert = certification_scope(raw_cert, subservice)
    if raw_cert.empty:
        st.warning("Non c'è una certificazione attiva. Vai in Certificazioni per caricare il file ufficiale.")
    elif cert.empty:
        st.error(f"La certificazione {st.session_state.cert_file} non contiene righe riconducibili al sottoservizio **{subservice}**. Controlla la colonna Comuni/Centro di Costo.")
    else:
        st.success(f"Certificazione attiva: {st.session_state.cert_file} · {len(cert)} righe riferite a {subservice}")
        with st.expander("Vedi righe certificate associate al sottoservizio"):
            st.dataframe(cert[CERT_COLUMNS], use_container_width=True, hide_index=True)

    tonnage = st.number_input("Tonnellate", min_value=0.0, step=0.1, value=0.0)
    revenue = st.number_input("Ricavo", min_value=0.0, step=50.0, value=0.0)
    if revenue == 0 and tonnage > 0:
        revenue = tonnage * general_rate(tariffs, "Tariffa tonnellata", 0.0)
        st.caption(f"Ricavo automatico dalla tariffa tonnellata: {euro(revenue)}")

    # --------------------------------------------------------
    # ESPANSIONE CERTIFICAZIONE -> PERSONALE
    # --------------------------------------------------------
    st.markdown('<div class="section-title">3. Personale certificato</div>', unsafe_allow_html=True)
    if not cert.empty:
        p_rows = []
        for _, row in cert.iterrows():
            people = split_people(row["Operatori"])
            if not people:
                continue
            for person in people:
                found = find_operator(operators, "", person)
                matricola = "" if found is None else str(found["Matricola"])
                contract = "" if found is None else str(found["Contratto"])
                level = "" if found is None else str(found["Livello"])
                status = "MATCH ANAGRAFICA" if found is not None else "DA ASSEGNARE"
                p_rows.append({
                    "Certificazione ID": row["ID"],
                    "Operatore": person,
                    "Matricola": matricola,
                    "Contratto": contract,
                    "Livello": level,
                    "Ore": parse_hours(row["Durata"]),
                    "Data": row["Data Analisi"],
                    "Stato": status,
                })
        personnel_rows = pd.DataFrame(p_rows)
    else:
        personnel_rows = pd.DataFrame([{
            "Certificazione ID": "",
            "Operatore": "",
            "Matricola": "",
            "Contratto": list(CONTRACTS.keys())[0],
            "Livello": CONTRACTS[list(CONTRACTS.keys())[0]][0],
            "Ore": 0.0,
            "Data": pd.Timestamp(service_date),
            "Stato": "MANUALE",
        }])

    if personnel_rows.empty:
        personnel_rows = pd.DataFrame([{
            "Certificazione ID": "",
            "Operatore": "",
            "Matricola": "",
            "Contratto": list(CONTRACTS.keys())[0],
            "Livello": CONTRACTS[list(CONTRACTS.keys())[0]][0],
            "Ore": 0.0,
            "Data": pd.Timestamp(service_date),
            "Stato": "MANUALE",
        }])

    # Only fields required to edit contracts/levels/hours.
    personnel_editor = personnel_rows.copy()
    personnel_editor["Data"] = pd.to_datetime(personnel_editor["Data"], errors="coerce").dt.strftime("%d/%m/%Y")
    edited_personnel = st.data_editor(
        personnel_editor,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Contratto": st.column_config.SelectboxColumn("Contratto", options=list(CONTRACTS.keys()), required=True),
            "Livello": st.column_config.TextColumn("Livello"),
            "Ore": st.column_config.NumberColumn("Ore certificate", min_value=0.0, step=0.25),
            "Stato": st.column_config.TextColumn("Stato", disabled=True),
        },
        key="v6_personnel_editor",
    )

    # Il livello deve essere coerente con il contratto.
    contract_options = list(CONTRACTS.keys())
    labor_rows = []
    for _, row in edited_personnel.iterrows():
        contract = str(row.get("Contratto", "")).strip()
        level = str(row.get("Livello", "")).strip()
        hours = parse_hours(row.get("Ore", 0))
        rate = labor_rate(tariffs, contract, level)
        valid = contract in contract_options and level in CONTRACTS.get(contract, [])
        labor_rows.append({**row.to_dict(), "Costo Orario": rate, "Costo Totale": hours * rate, "Validita": "OK" if valid and rate > 0 else ("COSTO DA CONFIGURARE" if valid else "LIVELLO NON VALIDO")})
    labor_calc = pd.DataFrame(labor_rows)

    invalid_levels = labor_calc[labor_calc["Validita"] == "LIVELLO NON VALIDO"] if not labor_calc.empty else pd.DataFrame()
    zero_rates = labor_calc[labor_calc["Validita"] == "COSTO DA CONFIGURARE"] if not labor_calc.empty else pd.DataFrame()
    if not invalid_levels.empty:
        st.error("Ci sono livelli non validi per il contratto scelto.")
    if not zero_rates.empty:
        st.warning("Alcuni livelli validi non hanno ancora un costo orario aziendale nel tariffario.")

    labor_hours = safe_sum(labor_calc["Ore"] if not labor_calc.empty else None)
    labor_cost = safe_sum(labor_calc["Costo Totale"] if not labor_calc.empty else None)

    # --------------------------------------------------------
    # ESPANSIONE CERTIFICAZIONE -> MEZZI
    # --------------------------------------------------------
    st.markdown('<div class="section-title">4. Mezzi certificati</div>', unsafe_allow_html=True)
    v_rows = []
    if not cert.empty:
        for _, row in cert.iterrows():
            plates = split_people(row["Targa"])
            if not plates and str(row["Attrezzatura"]).strip():
                plates = [""]
            for plate in plates:
                found = find_vehicle(vehicles, plate)
                kind = "" if found is None else str(found["Tipo"])
                v_rows.append({
                    "Certificazione ID": row["ID"],
                    "Targa": plate,
                    "Attrezzatura": row["Attrezzatura"],
                    "Tipo": kind,
                    "Ore": parse_hours(row["Durata"]),
                    "Data": row["Data Analisi"],
                    "Stato": "MATCH ANAGRAFICA" if found is not None else "DA ASSEGNARE",
                })
    if not v_rows:
        v_rows = [{
            "Certificazione ID": "",
            "Targa": "",
            "Attrezzatura": "",
            "Tipo": DEFAULT_VEHICLE_TYPES[0],
            "Ore": 0.0,
            "Data": pd.Timestamp(service_date),
            "Stato": "MANUALE",
        }]
    vehicle_editor = pd.DataFrame(v_rows)
    vehicle_editor["Data"] = pd.to_datetime(vehicle_editor["Data"], errors="coerce").dt.strftime("%d/%m/%Y")

    # Tipo mezzo dinamico: lista di default + tipi presenti in tariffario/anagrafica.
    tariff_types = tariffs.loc[tariffs["Tipo"].astype(str).str.lower().eq("mezzo"), "Livello_o_Tipo"].astype(str).tolist()
    vehicle_types = sorted(set(DEFAULT_VEHICLE_TYPES + [x for x in tariff_types if x.strip()]))

    edited_vehicles = st.data_editor(
        vehicle_editor,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tipo": st.column_config.SelectboxColumn("Tipo mezzo", options=vehicle_types),
            "Ore": st.column_config.NumberColumn("Ore certificate", min_value=0.0, step=0.25),
            "Stato": st.column_config.TextColumn("Stato", disabled=True),
        },
        key="v6_vehicle_editor",
    )

    vehicle_calc_rows = []
    for _, row in edited_vehicles.iterrows():
        kind = str(row.get("Tipo", "")).strip()
        hours = parse_hours(row.get("Ore", 0))
        rate = vehicle_rate(tariffs, kind)
        vehicle_calc_rows.append({**row.to_dict(), "Costo Orario": rate, "Costo Totale": hours * rate, "Validita": "OK" if rate > 0 else "COSTO DA CONFIGURARE"})
    vehicle_calc = pd.DataFrame(vehicle_calc_rows)
    zero_vehicle_rates = vehicle_calc[vehicle_calc["Costo Orario"].le(0)] if not vehicle_calc.empty else pd.DataFrame()
    if not zero_vehicle_rates.empty:
        st.warning("Alcune tipologie di mezzo non hanno ancora un costo orario.")

    vehicle_hours = safe_sum(vehicle_calc["Ore"] if not vehicle_calc.empty else None)
    vehicle_cost = safe_sum(vehicle_calc["Costo Totale"] if not vehicle_calc.empty else None)

    # --------------------------------------------------------
    # RISULTATO ECONOMICO
    # --------------------------------------------------------
    st.markdown('<div class="section-title">5. Centro di costo</div>', unsafe_allow_html=True)
    overhead_pct = general_rate(tariffs, "Overhead", 15.0)
    overhead = (labor_cost + vehicle_cost) * overhead_pct / 100
    total_cost = labor_cost + vehicle_cost + overhead
    margin = revenue - total_cost
    margin_pct = margin / revenue * 100 if revenue else 0

    result = st.columns(5)
    cards = [
        (result[0], "Personale", euro(labor_cost), "teal"),
        (result[1], "Mezzi", euro(vehicle_cost), "blue"),
        (result[2], "Overhead", euro(overhead), "amber"),
        (result[3], "Costo totale", euro(total_cost), "purple"),
        (result[4], "Margine", euro(margin), "" if margin >= 0 else "red"),
    ]
    for col, name, value, cls in cards:
        with col:
            note = pct(margin_pct) if name == "Margine" else ""
            st.markdown(f'<div class="kpi {cls}"><div class="kpi-strip"></div><div class="kpi-label">{name}</div><div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>', unsafe_allow_html=True)

    st.markdown('<div style="margin:10px 0"><span class="status ' + ("ok" if margin >= 0 else "bad") + '">' + ("● MARGINE POSITIVO" if margin >= 0 else "■ MARGINE NEGATIVO") + '</span></div>', unsafe_allow_html=True)
    notes = st.text_area("Note / scostamenti", placeholder="Spiegazioni, anomalie, riferimenti alla certificazione...")

    if st.button("Salva centro di costo", type="primary", use_container_width=True):
        if not raw_cert.empty and cert.empty:
            st.error("Impossibile salvare: la certificazione attiva non corrisponde al sottoservizio selezionato.")
            st.stop()
        if not invalid_levels.empty:
            st.error("Impossibile salvare: correggi i livelli contrattuali non validi.")
            st.stop()
        cid = "CC-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        base = pd.DataFrame([{
            "ID": cid,
            "Data": pd.Timestamp(service_date),
            "Servizio": service,
            "Sottoservizio": subservice,
            "Centro di Costo": centro_costo(service, subservice),
            "Tonnellate": tonnage,
            "Ricavi": revenue,
            "Costo Personale": labor_cost,
            "Costo Mezzi": vehicle_cost,
            "Overhead": overhead,
            "Costo Totale": total_cost,
            "Margine": margin,
            "Ore Uomo": labor_hours,
            "Ore Mezzi": vehicle_hours,
            "Note": notes,
            "Creato Da": st.session_state.nome,
        }])
        save_csv(pd.concat([services_df, base], ignore_index=True), FILES["services"])

        p_rows = []
        for _, row in labor_calc.iterrows():
            p_rows.append({
                "ID Consuntivo": cid,
                "Certificazione ID": row.get("Certificazione ID", ""),
                "Data": pd.Timestamp(service_date),
                "Servizio": service,
                "Sottoservizio": subservice,
                "Matricola": row.get("Matricola", ""),
                "Operatore": row.get("Operatore", ""),
                "Contratto": row.get("Contratto", ""),
                "Livello": row.get("Livello", ""),
                "Ore": parse_hours(row.get("Ore", 0)),
                "Costo Orario": safe_value(row.get("Costo Orario", 0)),
                "Costo Totale": safe_value(row.get("Costo Totale", 0)),
                "Stato Match": row.get("Stato", ""),
            })
        save_csv(pd.concat([personnel_detail, pd.DataFrame(p_rows)], ignore_index=True), FILES["personnel"])

        v_rows_save = []
        for _, row in vehicle_calc.iterrows():
            v_rows_save.append({
                "ID Consuntivo": cid,
                "Certificazione ID": row.get("Certificazione ID", ""),
                "Data": pd.Timestamp(service_date),
                "Servizio": service,
                "Sottoservizio": subservice,
                "Targa": row.get("Targa", ""),
                "Attrezzatura": row.get("Attrezzatura", ""),
                "Tipo": row.get("Tipo", ""),
                "Ore": parse_hours(row.get("Ore", 0)),
                "Costo Orario": safe_value(row.get("Costo Orario", 0)),
                "Costo Totale": safe_value(row.get("Costo Totale", 0)),
                "Stato Match": row.get("Stato", ""),
            })
        save_csv(pd.concat([vehicle_detail, pd.DataFrame(v_rows_save)], ignore_index=True), FILES["vehicle_detail"])
        st.success(f"Centro di costo {cid} salvato.")
        st.rerun()

# ============================================================
# ECONOMICO
# ============================================================

elif page == "Economico":
    df = authorized(services_df)
    st.markdown('<div class="section-title">Centro di costo per servizio e sottoservizio</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("Non ci sono consuntivi disponibili.")
    else:
        a, b = st.columns([1, 1.4])
        with a:
            service_filter = st.selectbox("Servizio", ["Tutti"] + list(SERVICE_TREE.keys()))
        with b:
            subs = ALL_SUBSERVICES if service_filter == "Tutti" else SERVICE_TREE[service_filter]
            if not is_admin():
                subs = [x for x in subs if x in st.session_state.allowed_subservices]
            sub_filter = st.selectbox("Sottoservizio", ["Tutti"] + list(subs))
        if service_filter != "Tutti":
            df = df[df["Servizio"].eq(service_filter)]
        if sub_filter != "Tutti":
            df = df[df["Sottoservizio"].eq(sub_filter)]

        summary = df.groupby(["Servizio", "Sottoservizio"]).agg(
            Ricavi=("Ricavi", "sum"), Costi=("Costo Totale", "sum"), Margine=("Margine", "sum"),
            Tonnellate=("Tonnellate", "sum"), Ore_Uomo=("Ore Uomo", "sum"), Ore_Mezzi=("Ore Mezzi", "sum"),
        ).reset_index()
        summary["Margine %"] = np.where(summary["Ricavi"] != 0, summary["Margine"] / summary["Ricavi"] * 100, 0)
        display = summary.copy()
        for c in ["Ricavi", "Costi", "Margine"]:
            display[c] = display[c].apply(euro)
        for c in ["Tonnellate", "Ore_Uomo", "Ore_Mezzi"]:
            display[c] = display[c].apply(num)
        display["Margine %"] = display["Margine %"].apply(pct)
        st.dataframe(display, use_container_width=True, hide_index=True)

        l, r = st.columns(2)
        with l:
            st.markdown('<div class="panel"><div class="panel-title">Costo personale per contratto / livello</div></div>', unsafe_allow_html=True)
            p = authorized(personnel_detail)
            if not p.empty:
                st.bar_chart(p.groupby(["Contratto", "Livello"])["Costo Totale"].sum().sort_values(ascending=False))
        with r:
            st.markdown('<div class="panel"><div class="panel-title">Costo mezzi per tipologia</div></div>', unsafe_allow_html=True)
            v = authorized(vehicle_detail)
            if not v.empty:
                st.bar_chart(v.groupby("Tipo")["Costo Totale"].sum().sort_values(ascending=False))

# ============================================================
# ANAGRAFICHE
# ============================================================

elif page == "Anagrafiche":
    if not is_admin():
        st.error("Sezione riservata alla Direzione.")
        st.stop()
    t1, t2 = st.tabs(["👷 Operatori", "🚛 Mezzi"])
    with t1:
        st.markdown('<div class="section-title">Operatori</div>', unsafe_allow_html=True)
        edited = st.data_editor(operators, num_rows="dynamic", use_container_width=True, hide_index=True, key="operators_editor")
        st.caption("Contratto e livello alimentano il costo orario del personale.")
        if st.button("Salva operatori", type="primary"):
            save_csv(edited, FILES["operators"])
            st.success("Operatori salvati.")
            st.rerun()
    with t2:
        st.markdown('<div class="section-title">Mezzi</div>', unsafe_allow_html=True)
        current_types = sorted(set(DEFAULT_VEHICLE_TYPES + tariffs.loc[tariffs["Tipo"].astype(str).str.lower().eq("mezzo"), "Livello_o_Tipo"].astype(str).tolist()))
        edited = st.data_editor(vehicles, num_rows="dynamic", use_container_width=True, hide_index=True, column_config={"Tipo": st.column_config.SelectboxColumn("Tipo", options=current_types)}, key="vehicles_editor")
        if st.button("Salva mezzi", type="primary"):
            save_csv(edited, FILES["vehicles"])
            st.success("Mezzi salvati.")
            st.rerun()

# ============================================================
# TARIFFARI / CONTRATTI
# ============================================================

elif page == "Tariffari & Contratti":
    if not is_admin():
        st.error("Sezione riservata alla Direzione.")
        st.stop()

    st.markdown("<div class='hero'><div class='hero-kicker'>Tariffario</div><div class='hero-title'>Contratto ≠ costo orario</div><div class='hero-copy'>Il contratto identifica l'inquadramento. Il costo orario usato nel centro di costo è quello aziendale configurato dalla Direzione.</div></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["👷 Personale", "🚛 Mezzi", "⚙️ Parametri"])

    with t1:
        st.markdown('<div class="section-title">Livelli contrattuali</div>', unsafe_allow_html=True)
        labor = tariffs[tariffs["Tipo"].astype(str).str.lower().eq("personale")].copy()
        edited = st.data_editor(labor, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "Contratto": st.column_config.SelectboxColumn("Contratto", options=list(CONTRACTS.keys())),
                "Livello_o_Tipo": st.column_config.TextColumn("Livello"),
                "Costo_Orario": st.column_config.NumberColumn("Costo orario aziendale", min_value=0.0, step=0.01),
                "Attivo": st.column_config.SelectboxColumn("Attivo", options=["SI", "NO"]),
            }, key="tariff_labor")
        st.info("Imposta qui il costo orario aziendale effettivo per ogni livello. I valori 0 restano volutamente non valorizzati.")
        if st.button("Salva costi personale", type="primary"):
            others = tariffs[~tariffs["Tipo"].astype(str).str.lower().eq("personale")]
            save_csv(pd.concat([others, edited], ignore_index=True), FILES["tariffs"])
            st.success("Tariffario personale aggiornato.")
            st.rerun()

    with t2:
        st.markdown('<div class="section-title">Costi orari mezzi</div>', unsafe_allow_html=True)
        mech = tariffs[tariffs["Tipo"].astype(str).str.lower().eq("mezzo")].copy()
        edited = st.data_editor(mech, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "Livello_o_Tipo": st.column_config.TextColumn("Tipo mezzo"),
                "Costo_Orario": st.column_config.NumberColumn("Costo orario", min_value=0.0, step=0.01),
                "Attivo": st.column_config.SelectboxColumn("Attivo", options=["SI", "NO"]),
            }, key="tariff_vehicle")
        if st.button("Salva costi mezzi", type="primary"):
            others = tariffs[~tariffs["Tipo"].astype(str).str.lower().eq("mezzo")]
            save_csv(pd.concat([others, edited], ignore_index=True), FILES["tariffs"])
            st.success("Tariffario mezzi aggiornato.")
            st.rerun()

    with t3:
        st.markdown('<div class="section-title">Parametri generali</div>', unsafe_allow_html=True)
        general = tariffs[tariffs["Tipo"].astype(str).str.lower().eq("generale")].copy()
        edited = st.data_editor(general, num_rows="dynamic", use_container_width=True, hide_index=True, key="tariff_general")
        if st.button("Salva parametri", type="primary"):
            others = tariffs[~tariffs["Tipo"].astype(str).str.lower().eq("generale")]
            save_csv(pd.concat([others, edited], ignore_index=True), FILES["tariffs"])
            st.success("Parametri aggiornati.")
            st.rerun()

    zero = int(((tariffs["Tipo"].astype(str).str.lower() == "personale") & (tariffs["Costo_Orario"] <= 0)).sum())
    if zero:
        st.warning(f"Attenzione: {zero} livelli personale hanno ancora costo orario 0.")

# ============================================================
# ACCESSI
# ============================================================

elif page == "Accessi":
    if not is_admin():
        st.error("Sezione riservata alla Direzione.")
        st.stop()
    st.markdown('<div class="section-title">Utenti e autorizzazioni</div>', unsafe_allow_html=True)
    st.info("Le autorizzazioni si impostano sui sottoservizi: Prato, Piana, Mantova, ecc. La Direzione può usare TUTTI.")
    edited = st.data_editor(users, num_rows="dynamic", use_container_width=True, hide_index=True, key="users_editor")
    if st.button("Salva accessi", type="primary"):
        save_csv(edited, FILES["users"])
        st.success("Accessi aggiornati.")
        st.rerun()

    st.markdown('<div class="section-title">Albero servizi</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    for service, subs in SERVICE_TREE.items():
        pills = "".join([f'<span class="pill ok">{x}</span>' for x in subs])
        st.markdown(f'<div style="padding:7px 0"><strong style="color:#16231D">{service}</strong><div style="margin-top:3px">{pills}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================

st.markdown('<div class="footer">Cristoforo · Control Room V6.1 · Centro di Costo</div>', unsafe_allow_html=True)
