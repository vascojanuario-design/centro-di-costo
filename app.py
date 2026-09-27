import io
import os
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# ============================================================
# CRISTOFORO | CONTROL ROOM V4
# Dashboard premium / Servizio -> Sottoservizio -> Certificazione
# Personale -> Contratto -> Livello -> Costo orario
# Mezzi -> Tipo -> Costo orario -> Costo totale
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
    "tariffs": os.path.join(BASE_DIR, "tariffe_cristoforo.csv"),
}

SERVICE_TREE = {
    "Spazzamenti": ["Scandicci"],
    "Aree Verdi": ["Piana", "Prato"],
    "Porta a Porta": [
        "Prato", "Vaiano", "Campi", "Noventa", "Costabissara",
        "Cremona", "Mantova", "Lucca"
    ],
    "Trasporti": ["Alia"],
    "Raccolta Cartone Selettivo": ["Firenze", "Piana", "Prato", "Campi"],
    "Ingombranti": ["Prato", "Campi Bisenzio", "Valdisieve", "Mugello"],
}

ALL_SUBSERVICES = sorted({v for items in SERVICE_TREE.values() for v in items})

CONTRACTS = {
    "Servizi Ambientali - Utilitalia": [
        "Q", "A1", "A2S", "A2", "B1S", "B1", "B2S", "B2",
        "C1S", "C1", "C2S", "C2", "D1S", "D1", "D2S", "D2"
    ],
    "Cooperative Sociali": [
        "A1", "A2", "B1", "C1", "C2", "C3",
        "D1", "D2", "D3", "E1", "E2", "F1", "F2"
    ],
}

VEHICLE_TYPES = [
    "Leggero",
    "Furgone",
    "Compattatore",
    "Spazzatrice",
    "Scarrabile",
    "Pesante",
    "Speciale",
]

# Sono valori iniziali configurabili dalla Direzione.
# I costi del personale partono da 0 perché il costo aziendale reale
# deve essere inserito dall'azienda e non viene inventato dal gestionale.
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
# DESIGN SYSTEM
# ============================================================

st.markdown(
    """
<style>
:root {
    --bg: #f3f6f4;
    --panel: #ffffff;
    --panel-2: #f8faf9;
    --ink: #152019;
    --muted: #6c7770;
    --line: #e2e8e4;
    --green: #009447;
    --green-dark: #006b33;
    --green-soft: #e7f6ed;
    --teal: #087f8c;
    --teal-soft: #e6f6f7;
    --blue: #2e6fdb;
    --blue-soft: #eaf1ff;
    --amber: #a16a00;
    --amber-soft: #fff5db;
    --red: #b42318;
    --red-soft: #fdecea;
    --purple: #7653c5;
    --purple-soft: #f1ecff;
    --shadow: 0 8px 28px rgba(20, 44, 31, 0.055);
}

.stApp { background: var(--bg); }
.block-container { max-width: 1520px; padding-top: 1.0rem; padding-bottom: 4rem; }
section[data-testid="stSidebar"] { background: #111916; border-right: 1px solid #1e2a23; }
section[data-testid="stSidebar"] * { color: #eef4f0; }

/* Sidebar */
.brand-box { padding: 9px 4px 18px; }
.brand-main { font-size: 27px; font-weight: 950; letter-spacing: -1.2px; }
.brand-sub { color: #91a098 !important; font-size: 11px; margin-top: 4px; }
.nav-note { color:#809087 !important; font-size:10px; margin: 3px 4px 8px; text-transform:uppercase; letter-spacing:.8px; font-weight:800; }

/* Topbar */
.topbar {
    background: rgba(255,255,255,.94);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 14px 18px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    box-shadow: var(--shadow);
    margin-bottom: 16px;
}
.title { font-size: 28px; font-weight: 950; letter-spacing:-.9px; color:var(--ink); }
.subtitle { color:var(--muted); font-size:12px; margin-top:3px; }
.user-pill { background: var(--green-soft); color:var(--green-dark); border-radius:999px; padding:8px 12px; font-size:11px; font-weight:850; }

/* Hero */
.hero {
    position:relative;
    overflow:hidden;
    background: linear-gradient(135deg, #0d2418 0%, #104d30 58%, #0e6c3b 100%);
    color:#fff;
    border-radius:24px;
    padding:24px 25px;
    margin-bottom:16px;
    box-shadow: 0 12px 35px rgba(0, 92, 47, .16);
}
.hero::after {
    content:"";
    position:absolute;
    width:280px;
    height:280px;
    right:-90px;
    top:-150px;
    border-radius:50%;
    background:rgba(255,255,255,.07);
}
.hero-kicker { color:#a9e3bf; font-size:10px; text-transform:uppercase; letter-spacing:1.4px; font-weight:900; }
.hero-title { color:#fff; font-size:30px; font-weight:950; letter-spacing:-1px; margin-top:4px; }
.hero-copy { color:#d1eadb; font-size:12px; margin-top:5px; max-width:820px; }
.hero-stat { margin-top:18px; font-size:11px; color:#bce7cd; }

/* KPI */
.kpi {
    background:var(--panel);
    border:1px solid var(--line);
    border-radius:18px;
    padding:16px;
    min-height:122px;
    box-shadow:var(--shadow);
    position:relative;
    overflow:hidden;
}
.kpi-strip { position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--green); }
.kpi.blue .kpi-strip { background:var(--blue); }
.kpi.teal .kpi-strip { background:var(--teal); }
.kpi.amber .kpi-strip { background:#d89b13; }
.kpi.purple .kpi-strip { background:var(--purple); }
.kpi.red .kpi-strip { background:var(--red); }
.kpi-label { color:#7a857e; font-size:10px; text-transform:uppercase; letter-spacing:.65px; font-weight:900; }
.kpi-value { color:#121a15; font-size:27px; font-weight:950; line-height:1.08; margin-top:8px; }
.kpi-note { color:#8b958f; font-size:10px; margin-top:5px; }

/* Dashboard panels */
.panel {
    background:var(--panel);
    border:1px solid var(--line);
    border-radius:19px;
    padding:17px;
    box-shadow:var(--shadow);
    margin-bottom:14px;
}
.panel-title { font-size:14px; font-weight:900; color:var(--ink); }
.panel-sub { font-size:10px; color:#8a948e; margin-top:2px; }
.section-title { font-size:17px; font-weight:950; color:var(--ink); margin:20px 0 9px; }

/* Service matrix */
.matrix-row {
    display:flex;
    gap:8px;
    flex-wrap:wrap;
    padding:9px 0;
    border-bottom:1px solid #edf0ee;
}
.matrix-name { width:185px; font-weight:850; font-size:12px; color:#29352e; padding-top:5px; }
.pill { border-radius:999px; padding:5px 9px; font-size:10px; font-weight:800; background:#f1f4f2; color:#435149; border:1px solid #e4e9e6; }
.pill.on { background:var(--green-soft); color:var(--green-dark); border-color:#cfe8d7; }
.pill.warn { background:var(--amber-soft); color:var(--amber); border-color:#f0d89d; }
.pill.bad { background:var(--red-soft); color:var(--red); border-color:#efc8c4; }

/* Status */
.status { border-radius:13px; padding:9px 11px; font-size:10px; font-weight:900; display:inline-block; }
.status.ok { background:var(--green-soft); color:var(--green-dark); }
.status.warn { background:var(--amber-soft); color:var(--amber); }
.status.bad { background:var(--red-soft); color:var(--red); }
.status.info { background:var(--blue-soft); color:#275cae; }

/* Process */
.step {
    background:#fff;
    border:1px solid var(--line);
    border-radius:17px;
    padding:15px;
    box-shadow:var(--shadow);
    min-height:125px;
}
.step-num { color:var(--green); font-size:10px; font-weight:950; text-transform:uppercase; letter-spacing:.7px; }
.step-title { font-size:16px; font-weight:900; color:var(--ink); margin-top:5px; }
.step-text { color:var(--muted); font-size:10px; line-height:1.5; margin-top:4px; }

/* Login */
.login-card { max-width:430px; margin:8vh auto 0; background:#fff; border:1px solid var(--line); border-radius:25px; padding:35px; box-shadow:0 20px 60px rgba(20,40,30,.09); }
.login-logo { text-align:center; color:var(--green); font-size:36px; font-weight:950; letter-spacing:-1px; }
.login-sub { text-align:center; color:var(--muted); font-size:12px; margin:5px 0 23px; }

/* Forms */
div.stButton > button { border-radius:11px; font-weight:850; min-height:40px; }
div[data-testid="stDataEditor"] { border-radius:14px; overflow:hidden; }

/* Footer */
.footer { text-align:center; color:#87918b; font-size:10px; padding:30px 0 5px; }
footer { visibility:hidden; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# UTILITA' DATI
# ============================================================

def clean_col(value):
    s = str(value).replace("\ufeff", "").strip().lower()
    trans = str.maketrans({"à":"a", "è":"e", "é":"e", "ì":"i", "ò":"o", "ù":"u"})
    s = s.translate(trans)
    s = s.replace("€", "euro").replace("/", "_").replace("-", "_").replace(" ", "_")
    return re.sub(r"_+", "_", s).strip("_")


def normalize_columns(df):
    out = df.copy() if df is not None else pd.DataFrame()
    if not out.empty or len(out.columns) > 0:
        out.columns = [clean_col(c) for c in out.columns]
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
    df.to_csv(path, index=False, encoding="utf-8-sig")


def aliases_rename(df, mapping):
    df = normalize_columns(df)
    existing = {clean_col(c): c for c in df.columns}
    rename = {}
    for target, aliases in mapping.items():
        for name in [target] + list(aliases):
            key = clean_col(name)
            if key in existing:
                rename[existing[key]] = target
                break
    return df.rename(columns=rename)


def ensure(df, columns):
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = ""
    return out


def parse_num(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return 0.0 if pd.isna(value) else float(value)
    s = str(value).strip().replace("€", "").replace("EUR", "").replace("eur", "").replace(" ", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") == 1 and len(s.split(".")[-1]) == 3:
        s = s.replace(".", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def parse_hours(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        x = float(value)
        return x * 24 if 0 < x < 1 else x
    s = str(value).strip()
    if not s:
        return 0.0
    if ":" in s:
        try:
            p = s.split(":")
            return float(p[0]) + float(p[1]) / 60
        except Exception:
            pass
    return parse_num(s)


def parse_date(value):
    if value is None or str(value).strip() == "":
        return pd.NaT
    return pd.to_datetime(value, dayfirst=True, errors="coerce")


def euro(value):
    x = parse_num(value)
    return f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(value, dec=1):
    x = parse_num(value)
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value):
    return f"{parse_num(value):.1f}%".replace(".", ",")


def safe_sum(series):
    """Somma robusta: gestisce numeri, stringhe, celle vuote e NaN."""
    if series is None:
        return 0.0
    try:
        return float(pd.Series(series).apply(parse_num).sum())
    except Exception:
        return 0.0


def safe_value(value):
    """Converte qualsiasi valore economico in float senza propagare errori."""
    return parse_num(value)


def margin_status(margin, margin_pct, has_data=True):
    """Semaforo gestionale: OK / ATTENZIONE / CRITICO."""
    m = safe_value(margin)
    p = safe_value(margin_pct)
    if not has_data:
        return ("ATTENZIONE", "Nessun dato consuntivato", "warn")
    if m < 0:
        return ("CRITICO", "Margine negativo", "bad")
    if p < 5:
        return ("ATTENZIONE", "Margine molto contenuto", "warn")
    return ("OK", "Margine sotto controllo", "ok")


# ============================================================
# INIT FILE
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
            "ID", "Data", "Servizio", "Sottoservizio", "Tonnellate", "Ricavi",
            "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Note", "Creato Da"
        ]), FILES["services"])
    if not os.path.exists(FILES["personnel"]):
        save_csv(pd.DataFrame(columns=[
            "ID Consuntivo", "Data", "Servizio", "Sottoservizio", "Matricola",
            "Operatore", "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale"
        ]), FILES["personnel"])
    if not os.path.exists(FILES["vehicle_detail"]):
        save_csv(pd.DataFrame(columns=[
            "ID Consuntivo", "Data", "Servizio", "Sottoservizio", "Targa",
            "Mezzo", "Tipo", "Ore", "Costo Orario", "Costo Totale"
        ]), FILES["vehicle_detail"])
    if not os.path.exists(FILES["certifications"]):
        save_csv(pd.DataFrame(columns=["ID Import", "Data Import", "File", "Righe", "Esito", "Operatore"]), FILES["certifications"])
    if not os.path.exists(FILES["tariffs"]):
        rows = []
        for contract, levels in CONTRACTS.items():
            for level in levels:
                rows.append({"Tipo": "Personale", "Contratto": contract, "Livello_o_Tipo": level, "Costo_Orario": 0.0, "Attivo": "SI"})
        for kind, cost in DEFAULT_VEHICLE_COSTS.items():
            rows.append({"Tipo": "Mezzo", "Contratto": "", "Livello_o_Tipo": kind, "Costo_Orario": cost, "Attivo": "SI"})
        rows.append({"Tipo": "Generale", "Contratto": "", "Livello_o_Tipo": "Overhead", "Costo_Orario": 15.0, "Attivo": "SI"})
        rows.append({"Tipo": "Generale", "Contratto": "", "Livello_o_Tipo": "Tariffa tonnellata", "Costo_Orario": 130.0, "Attivo": "SI"})
        save_csv(pd.DataFrame(rows), FILES["tariffs"])


init_files()


# ============================================================
# READ DATA
# ============================================================

def read_users():
    df = aliases_rename(read_csv_flexible(FILES["users"]), {
        "username": ["user", "utente", "login"],
        "password": ["pass", "pwd"],
        "nome": ["name", "nominativo"],
        "ruolo": ["role", "profilo"],
        "autorizzazioni": ["cantieri", "commesse", "cantiere", "accessi"],
    })
    required = ["username", "password", "nome", "ruolo", "autorizzazioni"]
    if df.empty or not all(c in df.columns for c in required):
        return DEFAULT_USERS.copy()
    df = ensure(df, required)
    for c in required:
        df[c] = df[c].astype(str).str.strip()
    return df[required].copy()


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
    return ensure(df, cols)[cols].copy()


def read_vehicles():
    df = aliases_rename(read_csv_flexible(FILES["vehicles"]), {
        "Targa": ["targa", "plate"],
        "Mezzo": ["mezzo", "veicolo", "vehicle"],
        "Tipo": ["tipo", "tipo_mezzo", "categoria_mezzo"],
        "Sottoservizio": ["cantiere", "commessa", "subservice"],
    })
    cols = ["Targa", "Mezzo", "Tipo", "Sottoservizio"]
    return ensure(df, cols)[cols].copy()


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
    df = aliases_rename(read_csv_flexible(FILES["services"]), {
        "ID": ["id_consuntivo", "id"],
        "Data": ["data_servizio", "giorno", "date"],
        "Servizio": ["categoria", "servizio_principale", "tipo_servizio"],
        "Sottoservizio": ["sotto_servizio", "dettaglio", "cantiere", "commessa"],
        "Tonnellate": ["ton", "tonnellaggio", "quantita_tonnellate"],
        "Ricavi": ["ricavo", "ricavi_euro", "revenue", "fatturato"],
        "Costo Personale": ["costo_personale", "personale_costo"],
        "Costo Mezzi": ["costo_mezzi", "mezzi_costo"],
        "Overhead": ["overhead", "costi_indiretti"],
        "Costo Totale": ["costo", "costi", "costo_totale"],
        "Margine": ["margine_netto", "profitto"],
        "Note": ["note", "commenti"],
        "Creato Da": ["operatore", "utente", "created_by"],
    })
    cols = ["ID", "Data", "Servizio", "Sottoservizio", "Tonnellate", "Ricavi",
            "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Note", "Creato Da"]
    df = ensure(df, cols)[cols].copy()
    df["Data"] = df["Data"].apply(parse_date)
    for c in ["Tonnellate", "Ricavi", "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine"]:
        df[c] = df[c].apply(parse_num)
    for c in ["ID", "Servizio", "Sottoservizio", "Note", "Creato Da"]:
        df[c] = df[c].astype(str).str.strip()
    if not df.empty:
        missing = df["Margine"].eq(0) & (df["Ricavi"].ne(0) | df["Costo Totale"].ne(0))
        df.loc[missing, "Margine"] = df.loc[missing, "Ricavi"] - df.loc[missing, "Costo Totale"]
    return df


def read_personnel():
    df = aliases_rename(read_csv_flexible(FILES["personnel"]), {
        "ID Consuntivo": ["id_consuntivo", "id"],
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
    })
    cols = ["ID Consuntivo", "Data", "Servizio", "Sottoservizio", "Matricola", "Operatore", "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale"]
    df = ensure(df, cols)[cols].copy()
    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)
    df["Costo Orario"] = df["Costo Orario"].apply(parse_num)
    df["Costo Totale"] = df["Costo Totale"].apply(parse_num)
    return df


def read_vehicle_detail():
    df = aliases_rename(read_csv_flexible(FILES["vehicle_detail"]), {
        "ID Consuntivo": ["id_consuntivo", "id"],
        "Data": ["data"],
        "Servizio": ["categoria", "servizio"],
        "Sottoservizio": ["cantiere", "commessa", "dettaglio"],
        "Targa": ["targa", "plate"],
        "Mezzo": ["mezzo", "veicolo"],
        "Tipo": ["tipo", "tipo_mezzo"],
        "Ore": ["ore_lavorate", "hours"],
        "Costo Orario": ["costo_orario", "tariffa"],
        "Costo Totale": ["costo", "costo_totale"],
    })
    cols = ["ID Consuntivo", "Data", "Servizio", "Sottoservizio", "Targa", "Mezzo", "Tipo", "Ore", "Costo Orario", "Costo Totale"]
    df = ensure(df, cols)[cols].copy()
    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)
    df["Costo Orario"] = df["Costo Orario"].apply(parse_num)
    df["Costo Totale"] = df["Costo Totale"].apply(parse_num)
    return df


# ============================================================
# ACCESSI + TARIFFE
# ============================================================

def is_admin():
    return str(st.session_state.get("ruolo", "")).lower() in {"admin", "direzione"}


def split_access(value):
    if str(value).strip().upper() in {"TUTTI", "ALL", "*"}:
        return ALL_SUBSERVICES.copy()
    values = re.split(r"[,;|]", str(value))
    return sorted([x.strip() for x in values if x.strip() in ALL_SUBSERVICES])


def authorized_services(df, column="Sottoservizio"):
    if df is None or df.empty or is_admin():
        return df.copy() if df is not None else pd.DataFrame()
    allowed = st.session_state.get("allowed_subservices", [])
    if not allowed:
        return df.iloc[0:0].copy()
    out = df.copy()
    return out[out[column].astype(str).str.strip().isin(allowed)].copy()


def labor_rate(tariffs, contract, level):
    m = (
        tariffs["Tipo"].astype(str).str.lower().eq("personale")
        & tariffs["Contratto"].astype(str).str.strip().eq(str(contract).strip())
        & tariffs["Livello_o_Tipo"].astype(str).str.strip().eq(str(level).strip())
        & tariffs["Attivo"].astype(str).str.upper().eq("SI")
    )
    r = tariffs.loc[m, "Costo_Orario"]
    return float(r.iloc[0]) if not r.empty else 0.0


def vehicle_rate(tariffs, kind):
    m = (
        tariffs["Tipo"].astype(str).str.lower().eq("mezzo")
        & tariffs["Livello_o_Tipo"].astype(str).str.strip().eq(str(kind).strip())
        & tariffs["Attivo"].astype(str).str.upper().eq("SI")
    )
    r = tariffs.loc[m, "Costo_Orario"]
    return float(r.iloc[0]) if not r.empty else 0.0


def general_rate(tariffs, label, default=0.0):
    m = (
        tariffs["Tipo"].astype(str).str.lower().eq("generale")
        & tariffs["Livello_o_Tipo"].astype(str).str.strip().eq(label)
        & tariffs["Attivo"].astype(str).str.upper().eq("SI")
    )
    r = tariffs.loc[m, "Costo_Orario"]
    return float(r.iloc[0]) if not r.empty else default


def current_datasets():
    return (
        read_users(),
        read_operators(),
        read_vehicles(),
        read_tariffs(),
        read_services(),
        read_personnel(),
        read_vehicle_detail(),
    )


# ============================================================
# CERTIFICAZIONE
# ============================================================

CERT_ALIASES = {
    "Data": ["data_turno", "giorno", "date", "data_servizio"],
    "Matricola": ["matricola", "id_operatore", "codice_operatore", "employee_id"],
    "Operatore": ["operatore", "dipendente", "addetto", "employee", "nome_operatore"],
    "Ore": ["ore", "ore_lavorate", "hours", "durata", "ore_totali"],
    "Targa": ["targa", "plate", "veicolo_targa"],
    "Mezzo": ["mezzo", "veicolo", "vehicle"],
    "Tipo Mezzo": ["tipo_mezzo", "categoria_mezzo", "classe_mezzo", "tipo_veicolo"],
    "Risorsa": ["tipo_risorsa", "risorsa", "tipo"],
    "Servizio": ["servizio", "categoria", "tipo_servizio"],
    "Sottoservizio": ["sottoservizio", "sotto_servizio", "dettaglio", "commessa", "cantiere"],
}


def read_uploaded_file(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        raw = uploaded.getvalue()
        text = None
        for enc in ("utf-8-sig", "utf-8", "latin1"):
            try:
                text = raw.decode(enc)
                break
            except Exception:
                pass
        if text is None:
            raise ValueError("Codifica CSV non riconosciuta.")
        return pd.read_csv(io.StringIO(text), sep=None, engine="python"), None
    if name.endswith((".xlsx", ".xls")):
        return None, pd.ExcelFile(uploaded)
    raise ValueError("Formato non supportato.")


def score_headers(df):
    norm = {clean_col(c) for c in df.columns}
    candidates = set()
    for target, aliases in CERT_ALIASES.items():
        candidates.add(clean_col(target))
        candidates.update(clean_col(a) for a in aliases)
    return len(norm.intersection(candidates))


def normalize_certification(df):
    df = aliases_rename(df, CERT_ALIASES)
    cols = ["Data", "Matricola", "Operatore", "Ore", "Targa", "Mezzo", "Tipo Mezzo", "Risorsa", "Servizio", "Sottoservizio"]
    df = ensure(df, cols)[cols].copy()
    for c in ["Matricola", "Operatore", "Targa", "Mezzo", "Tipo Mezzo", "Risorsa", "Servizio", "Sottoservizio"]:
        df[c] = df[c].astype(str).str.strip()
    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)

    def infer(row):
        r = row["Risorsa"].lower()
        if r in {"personale", "operatore", "dipendente", "operatori"}:
            return "Personale"
        if r in {"mezzo", "mezzi", "veicolo", "veicoli"}:
            return "Mezzo"
        if row["Operatore"] or row["Matricola"]:
            return "Personale"
        if row["Targa"] or row["Mezzo"] or row["Tipo Mezzo"]:
            return "Mezzo"
        return ""

    df["Risorsa"] = df.apply(infer, axis=1)
    return df


def load_certification(uploaded):
    csv_df, excel = read_uploaded_file(uploaded)
    if excel is None:
        return normalize_certification(csv_df)

    best = None
    best_score = -1
    for sheet in excel.sheet_names:
        for header in [0, 1, 2]:
            try:
                sample = pd.read_excel(excel, sheet_name=sheet, header=header, nrows=30)
                score = score_headers(sample)
                if score > best_score:
                    best = pd.read_excel(excel, sheet_name=sheet, header=header)
                    best_score = score
            except Exception:
                pass
    if best is None:
        raise ValueError("Nessun foglio Excel leggibile.")
    return normalize_certification(best)


# ============================================================
# SESSIONE
# ============================================================

SESSION_DEFAULTS = {
    "logged": False,
    "username": "",
    "nome": "",
    "ruolo": "",
    "autorizzazioni": "",
    "allowed_subservices": [],
    "cert_df": pd.DataFrame(),
    "cert_file": "",
}
for key, default in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ============================================================
# LOGIN
# ============================================================

if not st.session_state.logged:
    st.markdown(
        """
        <div class="login-card">
            <div class="login-logo">♻️ CRISTOFORO</div>
            <div class="login-sub">Control Room · Centro di Costo</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        username = st.text_input("Username", placeholder="Inserisci username")
        password = st.text_input("Password", type="password", placeholder="Inserisci password")
        if st.button("Entra nella Control Room", type="primary", use_container_width=True):
            users = read_users()
            match = users[
                users["username"].astype(str).str.strip().eq(username.strip())
                & users["password"].astype(str).str.strip().eq(password.strip())
            ]
            if match.empty:
                st.error("Username o password non corretti.")
            else:
                row = match.iloc[0]
                st.session_state.logged = True
                st.session_state.username = row["username"]
                st.session_state.nome = row["nome"]
                st.session_state.ruolo = row["ruolo"]
                st.session_state.autorizzazioni = row["autorizzazioni"]
                st.session_state.allowed_subservices = split_access(row["autorizzazioni"])
                st.rerun()
    st.stop()


# ============================================================
# DATASET GLOBALI
# ============================================================

users, operators, vehicles, tariffs, services, personnel_detail, vehicle_detail = current_datasets()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div class="brand-box">
            <div class="brand-main">♻️ CRISTOFORO</div>
            <div class="brand-sub">CONTROL ROOM · CENTRO DI COSTO</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="nav-note">Navigazione</div>', unsafe_allow_html=True)

    pages = ["Dashboard", "Consuntivazione", "Certificazioni", "Economico"]
    if is_admin():
        pages += ["Anagrafiche", "Tariffari & Contratti", "Accessi"]
    page = st.radio("Menu", pages, label_visibility="collapsed")

    st.markdown("---")
    st.caption(f"● {st.session_state.nome}")
    st.caption(f"Ruolo · {st.session_state.ruolo}")
    if is_admin():
        st.caption("Accesso · Direzione")
    else:
        st.caption(f"Sottoservizi · {len(st.session_state.allowed_subservices)}")

    if st.button("Esci", use_container_width=True):
        for key in ["logged", "username", "nome", "ruolo", "autorizzazioni", "allowed_subservices"]:
            st.session_state.pop(key, None)
        st.rerun()


# ============================================================
# TOPBAR
# ============================================================

META = {
    "Dashboard": ("Control Room", "La cabina di regia operativa ed economica"),
    "Consuntivazione": ("Nuovo consuntivo", "Servizio → sottoservizio → certificazione → costo"),
    "Certificazioni": ("Certificazioni", "Importa il file ore ufficiale e controlla i dati riconosciuti"),
    "Economico": ("Centro di costo", "Leggi margine, personale, mezzi e costo per sottoservizio"),
    "Anagrafiche": ("Anagrafiche", "Operatori e mezzi"),
    "Tariffari & Contratti": ("Tariffari & Contratti", "Livelli contrattuali, costi orari e mezzi"),
    "Accessi": ("Accessi", "Utenti e autorizzazioni"),
}

title, subtitle = META[page]
st.markdown(
    f"""
    <div class="topbar">
        <div>
            <div class="title">{title}</div>
            <div class="subtitle">{subtitle}</div>
        </div>
        <div class="user-pill">● {st.session_state.nome}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":
    df = authorized_services(services)

    # Filtri dashboard: prima servizio principale, poi sottoservizio.
    f1, f2, f3 = st.columns([1.2, 1.4, 1])
    with f1:
        service_filter = st.selectbox("Servizio principale", ["Tutti"] + list(SERVICE_TREE.keys()))
    with f2:
        if service_filter == "Tutti":
            sub_options = ["Tutti"] + sorted(st.session_state.allowed_subservices if not is_admin() else ALL_SUBSERVICES)
        else:
            values = SERVICE_TREE[service_filter]
            if not is_admin():
                values = [x for x in values if x in st.session_state.allowed_subservices]
            sub_options = ["Tutti"] + values
        sub_filter = st.selectbox("Sottoservizio", sub_options)
    with f3:
        period = st.selectbox("Periodo", ["Tutto", "Ultimi 30 giorni", "Ultimi 90 giorni", "Anno corrente"])

    if service_filter != "Tutti":
        df = df[df["Servizio"].astype(str).eq(service_filter)].copy()
    if sub_filter != "Tutti":
        df = df[df["Sottoservizio"].astype(str).eq(sub_filter)].copy()
    if period != "Tutto":
        today = pd.Timestamp.today().normalize()
        if period == "Ultimi 30 giorni":
            start = today - pd.Timedelta(days=30)
        elif period == "Ultimi 90 giorni":
            start = today - pd.Timedelta(days=90)
        else:
            start = pd.Timestamp(today.year, 1, 1)
        df = df[df["Data"].isna() | (df["Data"] >= start)].copy()

    current_label = sub_filter if sub_filter != "Tutti" else (service_filter if service_filter != "Tutti" else "Tutte le attività")

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-kicker">Dashboard operativa</div>
            <div class="hero-title">{current_label}</div>
            <div class="hero-copy">Ricavi, costi, ore certificate e margine in una sola vista. Il verde indica performance positiva, l'ambra attenzione e il rosso criticità.</div>
            <div class="hero-stat">● Dati consuntivati: {len(df)} record · Ultimo aggiornamento alla lettura dei CSV</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    revenue = safe_sum(df["Ricavi"] if "Ricavi" in df.columns else None)
    cost = safe_sum(df["Costo Totale"] if "Costo Totale" in df.columns else None)
    margin = safe_sum(df["Margine"] if "Margine" in df.columns else None)
    margin_pct = (margin / revenue * 100) if revenue else 0.0

    # Le ore nella Control Tower seguono gli stessi filtri della dashboard.
    dashboard_personnel = authorized_services(personnel_detail)
    dashboard_vehicles = authorized_services(vehicle_detail)
    if service_filter != "Tutti":
        dashboard_personnel = dashboard_personnel[dashboard_personnel["Servizio"].astype(str).eq(service_filter)].copy() if not dashboard_personnel.empty else dashboard_personnel
        dashboard_vehicles = dashboard_vehicles[dashboard_vehicles["Servizio"].astype(str).eq(service_filter)].copy() if not dashboard_vehicles.empty else dashboard_vehicles
    if sub_filter != "Tutti":
        dashboard_personnel = dashboard_personnel[dashboard_personnel["Sottoservizio"].astype(str).eq(sub_filter)].copy() if not dashboard_personnel.empty else dashboard_personnel
        dashboard_vehicles = dashboard_vehicles[dashboard_vehicles["Sottoservizio"].astype(str).eq(sub_filter)].copy() if not dashboard_vehicles.empty else dashboard_vehicles
    if period != "Tutto":
        date_start = start
        if not dashboard_personnel.empty:
            dashboard_personnel = dashboard_personnel[dashboard_personnel["Data"].isna() | (dashboard_personnel["Data"] >= date_start)].copy()
        if not dashboard_vehicles.empty:
            dashboard_vehicles = dashboard_vehicles[dashboard_vehicles["Data"].isna() | (dashboard_vehicles["Data"] >= date_start)].copy()

    labor_hours = safe_sum(dashboard_personnel["Ore"] if not dashboard_personnel.empty and "Ore" in dashboard_personnel.columns else None)
    vehicle_hours = safe_sum(dashboard_vehicles["Ore"] if not dashboard_vehicles.empty and "Ore" in dashboard_vehicles.columns else None)
    margin = safe_value(margin)
    margin_pct = safe_value(margin_pct)

    kcols = st.columns(6)
    margin_card_class = "teal" if safe_value(margin) >= 0 else "red"
    cards = [
        (kcols[0], "Ricavi", euro(revenue), "fatturato", ""),
        (kcols[1], "Costo totale", euro(cost), "personale + mezzi + indiretti", "blue"),
        (kcols[2], "Margine", euro(margin), percent(margin_pct), margin_card_class),
        (kcols[3], "Margine %", percent(margin_pct), "sul ricavo", "purple"),
        (kcols[4], "Ore uomo", f"{num(labor_hours)} h", "da certificazione", "amber"),
        (kcols[5], "Ore mezzi", f"{num(vehicle_hours)} h", "da certificazione", ""),
    ]
    for col, label, value, note, cls in cards:
        with col:
            st.markdown(
                f"""
                <div class="kpi {cls}">
                    <div class="kpi-strip"></div>
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-title">Lettura della giornata economica</div>', unsafe_allow_html=True)
    left, right = st.columns([1.55, 1])

    with left:
        st.markdown('<div class="panel"><div class="panel-title">Andamento Ricavi / Costi / Margine</div><div class="panel-sub">Il grafico segue il periodo selezionato</div></div>', unsafe_allow_html=True)
        if not df.empty and df["Data"].notna().any():
            trend = df.dropna(subset=["Data"]).groupby("Data")[["Ricavi", "Costo Totale", "Margine"]].sum().sort_index()
            st.area_chart(trend)
        else:
            st.info("Inserisci almeno un consuntivo con data per visualizzare l'andamento.")

    with right:
        st.markdown('<div class="panel"><div class="panel-title">Composizione costi</div><div class="panel-sub">Peso delle principali componenti</div></div>', unsafe_allow_html=True)
        cost_mix = pd.Series({
            "Personale": safe_sum(df["Costo Personale"] if "Costo Personale" in df.columns else None),
            "Mezzi": safe_sum(df["Costo Mezzi"] if "Costo Mezzi" in df.columns else None),
            "Overhead": safe_sum(df["Overhead"] if "Overhead" in df.columns else None),
        })
        st.bar_chart(cost_mix)

    st.markdown('<div class="section-title">Semaforo operativo</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    for service_name, subs in SERVICE_TREE.items():
        visible = subs if is_admin() else [x for x in subs if x in st.session_state.allowed_subservices]
        if not visible:
            continue
        pills = []
        for sub in visible:
            d = df[df["Sottoservizio"].eq(sub)].copy()
            m = safe_sum(d["Margine"] if not d.empty else None)
            r = safe_sum(d["Ricavi"] if not d.empty else None)
            p = (m / r * 100) if r else 0.0
            status_label, status_text, status_class = margin_status(m, p, not d.empty)
            icon = {"ok": "●", "warn": "▲", "bad": "■"}.get(status_class, "●")
            if d.empty:
                label = f"{icon} {sub} · nessun dato"
            else:
                label = f"{icon} {sub} · {euro(m)} · {percent(p)}"
            pill_class = "on" if status_class == "ok" else status_class
            pills.append(f'<span class="pill {pill_class}">{label}</span>')
        st.markdown(
            f'<div class="matrix-row"><div class="matrix-name">{service_name}</div>{"".join(pills)}</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Control Tower</div>', unsafe_allow_html=True)
    total_hours = safe_value(labor_hours) + safe_value(vehicle_hours)
    cost_per_hour = cost / total_hours if total_hours else 0.0
    tonnes = safe_sum(df["Tonnellate"] if "Tonnellate" in df.columns else None)
    cost_per_ton = cost / tonnes if tonnes else 0.0
    status_label, status_text, status_class = margin_status(margin, margin_pct, not df.empty)

    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.markdown(
            f'<div class="panel"><div class="panel-title">Stato economico</div><div class="panel-sub">Indicatore automatico</div><div style="margin-top:14px"><span class="status {status_class}">{status_label}</span></div><div style="font-size:12px;color:#67736c;margin-top:10px">{status_text}</div></div>',
            unsafe_allow_html=True,
        )
    with t2:
        st.markdown(
            f'<div class="panel"><div class="panel-title">Ore certificate</div><div class="panel-sub">Personale + mezzi</div><div class="kpi-value" style="font-size:25px;margin-top:12px">{num(total_hours)} h</div><div class="kpi-note">Uomo {num(labor_hours)} h · Mezzi {num(vehicle_hours)} h</div></div>',
            unsafe_allow_html=True,
        )
    with t3:
        st.markdown(
            f'<div class="panel"><div class="panel-title">Costo / ora</div><div class="panel-sub">Totale / ore certificate</div><div class="kpi-value" style="font-size:25px;margin-top:12px">{euro(cost_per_hour)}</div><div class="kpi-note">Indicatore operativo</div></div>',
            unsafe_allow_html=True,
        )
    with t4:
        st.markdown(
            f'<div class="panel"><div class="panel-title">Costo / tonnellata</div><div class="panel-sub">Quando è presente il tonnellaggio</div><div class="kpi-value" style="font-size:25px;margin-top:12px">{euro(cost_per_ton)}</div><div class="kpi-note">Tonnellate: {num(tonnes, 1)}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">Flusso operativo</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    steps = [
        (c1, "01", "Servizio", "Seleziona il servizio principale."),
        (c2, "02", "Sottoservizio", "Il sistema mostra solo i sottoservizi compatibili."),
        (c3, "03", "Certificazione", "Importa ore operatori e mezzi."),
        (c4, "04", "Costo / Margine", "Applica contratti, livelli, mezzi e tariffe."),
    ]
    for col, n, title_step, text_step in steps:
        with col:
            st.markdown(f'<div class="step"><div class="step-num">Passo {n}</div><div class="step-title">{title_step}</div><div class="step-text">{text_step}</div></div>', unsafe_allow_html=True)


# ============================================================
# CERTIFICAZIONI
# ============================================================

elif page == "Certificazioni":
    st.markdown('<div class="section-title">Import certificazione ore</div>', unsafe_allow_html=True)
    st.info("Carica il file ufficiale della certificazione. L'app prova a riconoscere automaticamente operatori, matricole, ore, targhe, mezzi e tipo risorsa.")

    uploaded = st.file_uploader("File certificazione", type=["csv", "xlsx", "xls"])
    if uploaded:
        try:
            cert = load_certification(uploaded)
            st.session_state.cert_df = cert
            st.session_state.cert_file = uploaded.name
            st.success(f"Certificazione letta: {len(cert)} righe · {cert['Risorsa'].value_counts().to_dict()}")
        except Exception as exc:
            st.error(f"Errore nella lettura della certificazione: {exc}")

    cert = st.session_state.cert_df.copy()
    if not cert.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("File", st.session_state.cert_file or "-")
        with c2: st.metric("Righe", len(cert))
        with c3: st.metric("Ore", f"{num(safe_sum(cert['Ore']))} h")
        with c4: st.metric("Righe mezzi", int((cert["Risorsa"] == "Mezzo").sum()))

        st.markdown('<div class="section-title">Anteprima riconoscimento</div>', unsafe_allow_html=True)
        st.dataframe(cert, use_container_width=True, hide_index=True)

        st.download_button(
            "Scarica certificazione normalizzata",
            data=cert.to_csv(index=False, encoding="utf-8-sig"),
            file_name="certificazione_normalizzata.csv",
            mime="text/csv",
            use_container_width=True,
        )

        if st.button("Registra importazione", type="primary"):
            imports = read_csv_flexible(FILES["certifications"])
            row = pd.DataFrame([{
                "ID Import": "IMP-" + datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "Data Import": datetime.now(),
                "File": st.session_state.cert_file,
                "Righe": len(cert),
                "Esito": "OK",
                "Operatore": st.session_state.nome,
            }])
            save_csv(pd.concat([imports, row], ignore_index=True), FILES["certifications"])
            st.success("Importazione registrata.")


# ============================================================
# CONSUNTIVAZIONE
# ============================================================

elif page == "Consuntivazione":
    st.markdown('<div class="section-title">Step 1 · Dove stiamo consuntivando?</div>', unsafe_allow_html=True)
    a, b, c = st.columns([1, 1.2, 1])
    with a:
        service = st.selectbox("Servizio principale", list(SERVICE_TREE.keys()))
    with b:
        choices = SERVICE_TREE[service]
        if not is_admin():
            choices = [x for x in choices if x in st.session_state.allowed_subservices]
        if not choices:
            st.error("Nessun sottoservizio autorizzato per questo servizio.")
            st.stop()
        subservice = st.selectbox("Sottoservizio", choices)
    with c:
        service_date = st.date_input("Data servizio", value=datetime.today().date())

    d1, d2 = st.columns([1, 2])
    with d1:
        tonnage = st.number_input("Tonnellate", min_value=0.0, step=0.1, value=0.0)
    with d2:
        revenue = st.number_input("Ricavo", min_value=0.0, step=50.0, value=0.0)
        if revenue == 0 and tonnage > 0:
            revenue = tonnage * general_rate(tariffs, "Tariffa tonnellata", 0.0)
            st.caption(f"Ricavo calcolato a tariffa tonnellata: {euro(revenue)}")

    st.markdown('<div class="section-title">Step 2 · Certificazione</div>', unsafe_allow_html=True)
    if st.session_state.cert_df.empty:
        st.warning("Nessuna certificazione caricata. Puoi caricarla nella sezione Certificazioni oppure inserire manualmente le risorse qui sotto.")
        cert = pd.DataFrame()
    else:
        cert = st.session_state.cert_df.copy()
        st.success(f"Certificazione attiva: {st.session_state.cert_file} · {len(cert)} righe")

    # --------------------------------------------------------
    # PERSONALE
    # --------------------------------------------------------
    st.markdown('<div class="section-title">Step 3 · Ore operatori</div>', unsafe_allow_html=True)

    if not cert.empty and (cert["Risorsa"] == "Personale").any():
        personnel_rows = cert[cert["Risorsa"] == "Personale"][
            ["Matricola", "Operatore", "Ore"]
        ].copy()
        personnel_rows["Contratto"] = ""
        personnel_rows["Livello"] = ""

        # Recupero automatico dal registro operatori.
        for idx, row in personnel_rows.iterrows():
            found = pd.DataFrame()
            if row["Matricola"]:
                found = operators[operators["Matricola"].astype(str).eq(str(row["Matricola"]))]
            if found.empty and row["Operatore"]:
                full = found
                name = str(row["Operatore"]).strip().lower()
                full_name = (operators["Nome"].astype(str) + " " + operators["Cognome"].astype(str)).str.strip().str.lower()
                found = operators[full_name.eq(name)]
            if not found.empty:
                personnel_rows.loc[idx, "Contratto"] = found.iloc[0]["Contratto"]
                personnel_rows.loc[idx, "Livello"] = found.iloc[0]["Livello"]
    else:
        default_contract = list(CONTRACTS.keys())[0]
        personnel_rows = pd.DataFrame([{
            "Matricola": "",
            "Operatore": "",
            "Contratto": default_contract,
            "Livello": CONTRACTS[default_contract][0],
            "Ore": 0.0,
        }])

    edited_personnel = st.data_editor(
        personnel_rows.reset_index(drop=True),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Contratto": st.column_config.SelectboxColumn("Contratto", options=list(CONTRACTS.keys()), required=True),
            "Livello": st.column_config.SelectboxColumn("Livello", options=sorted({x for y in CONTRACTS.values() for x in y})),
            "Ore": st.column_config.NumberColumn("Ore", min_value=0.0, step=0.25, format="%.2f"),
        },
        key="personnel_v4",
    )

    person_calc = edited_personnel.copy()
    person_calc["Costo Orario"] = 0.0
    person_calc["Costo Totale"] = 0.0
    invalid_contracts = []
    zero_rates = []
    for idx, row in person_calc.iterrows():
        contract = str(row.get("Contratto", "")).strip()
        level = str(row.get("Livello", "")).strip()
        rate = labor_rate(tariffs, contract, level)
        if contract not in CONTRACTS:
            invalid_contracts.append(idx + 1)
        elif level not in CONTRACTS[contract]:
            invalid_contracts.append(idx + 1)
        if rate <= 0 and contract in CONTRACTS and level in CONTRACTS[contract]:
            zero_rates.append(f"{contract} / {level}")
        person_calc.loc[idx, "Costo Orario"] = rate
        person_calc.loc[idx, "Costo Totale"] = parse_hours(row.get("Ore", 0)) * rate

    if invalid_contracts:
        st.error("Controlla il contratto/livello nelle righe: " + ", ".join(map(str, invalid_contracts)))
    if zero_rates:
        st.warning("Costo orario non configurato per: " + ", ".join(sorted(set(zero_rates))) + ". Configuralo in Tariffari & Contratti.")

    labor_hours = safe_sum(person_calc["Ore"].apply(parse_hours))
    labor_cost = safe_sum(person_calc["Costo Totale"])

    # --------------------------------------------------------
    # MEZZI
    # --------------------------------------------------------
    st.markdown('<div class="section-title">Step 4 · Ore mezzi</div>', unsafe_allow_html=True)

    if not cert.empty and (cert["Risorsa"] == "Mezzo").any():
        vehicle_rows = cert[cert["Risorsa"] == "Mezzo"][
            ["Targa", "Mezzo", "Tipo Mezzo", "Ore"]
        ].copy().rename(columns={"Tipo Mezzo": "Tipo"})
    else:
        vehicle_rows = pd.DataFrame([{
            "Targa": "",
            "Mezzo": "",
            "Tipo": VEHICLE_TYPES[0],
            "Ore": 0.0,
        }])

    vehicle_rows["Tipo"] = vehicle_rows["Tipo"].astype(str).str.strip()
    vehicle_rows.loc[~vehicle_rows["Tipo"].isin(VEHICLE_TYPES), "Tipo"] = VEHICLE_TYPES[0]

    edited_vehicles = st.data_editor(
        vehicle_rows.reset_index(drop=True),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tipo": st.column_config.SelectboxColumn("Tipo mezzo", options=VEHICLE_TYPES),
            "Ore": st.column_config.NumberColumn("Ore", min_value=0.0, step=0.25, format="%.2f"),
        },
        key="vehicles_v4",
    )

    vehicle_calc = edited_vehicles.copy()
    vehicle_calc["Costo Orario"] = 0.0
    vehicle_calc["Costo Totale"] = 0.0
    vehicle_zero_rates = []
    for idx, row in vehicle_calc.iterrows():
        kind = str(row.get("Tipo", "")).strip()
        rate = vehicle_rate(tariffs, kind)
        if rate <= 0:
            vehicle_zero_rates.append(kind)
        vehicle_calc.loc[idx, "Costo Orario"] = rate
        vehicle_calc.loc[idx, "Costo Totale"] = parse_hours(row.get("Ore", 0)) * rate

    if vehicle_zero_rates:
        st.warning("Costo mezzo non configurato per: " + ", ".join(sorted(set(vehicle_zero_rates))))

    vehicle_hours = safe_sum(vehicle_calc["Ore"].apply(parse_hours))
    vehicle_cost = safe_sum(vehicle_calc["Costo Totale"])

    # --------------------------------------------------------
    # ECONOMIA
    # --------------------------------------------------------
    st.markdown('<div class="section-title">Step 5 · Risultato economico</div>', unsafe_allow_html=True)

    overhead_pct = safe_value(general_rate(tariffs, "Overhead", 15.0))
    labor_cost = safe_value(labor_cost)
    vehicle_cost = safe_value(vehicle_cost)
    revenue = safe_value(revenue)
    overhead = (labor_cost + vehicle_cost) * overhead_pct / 100
    total_cost = labor_cost + vehicle_cost + overhead
    margin = revenue - total_cost
    margin_pct = (margin / revenue * 100) if revenue else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)
    result_cards = [
        (k1, "Personale", euro(labor_cost), "teal"),
        (k2, "Mezzi", euro(vehicle_cost), "blue"),
        (k3, "Overhead", euro(overhead), "amber"),
        (k4, "Costo totale", euro(total_cost), "purple"),
        (k5, "Margine", euro(margin), "" if safe_value(margin) >= 0 else "red"),
    ]
    for col, label, value, cls in result_cards:
        with col:
            st.markdown(f'<div class="kpi {cls}"><div class="kpi-strip"></div><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-note">{percent(margin_pct) if label == "Margine" else ""}</div></div>', unsafe_allow_html=True)

    if margin > 0:
        st.markdown('<span class="status ok">● MARGINE POSITIVO</span>', unsafe_allow_html=True)
    elif margin < 0:
        st.markdown('<span class="status bad">● MARGINE NEGATIVO</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status warn">● PAREGGIO</span>', unsafe_allow_html=True)

    notes = st.text_area("Note operative", placeholder="Anomalie, scostamenti, spiegazioni, riferimenti alla certificazione...")

    if st.button("Salva consuntivo completo", type="primary", use_container_width=True):
        if invalid_contracts:
            st.error("Correggere prima contratto/livello delle righe personale.")
            st.stop()
        cid = "CC-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        base = pd.DataFrame([{
            "ID": cid,
            "Data": pd.Timestamp(service_date),
            "Servizio": service,
            "Sottoservizio": subservice,
            "Tonnellate": tonnage,
            "Ricavi": revenue,
            "Costo Personale": labor_cost,
            "Costo Mezzi": vehicle_cost,
            "Overhead": overhead,
            "Costo Totale": total_cost,
            "Margine": margin,
            "Note": notes,
            "Creato Da": st.session_state.nome,
        }])
        services_new = pd.concat([services, base], ignore_index=True)
        save_csv(services_new, FILES["services"])

        p = person_calc.copy()
        p["ID Consuntivo"] = cid
        p["Data"] = pd.Timestamp(service_date)
        p["Servizio"] = service
        p["Sottoservizio"] = subservice
        p = ensure(p, ["Matricola", "Operatore", "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale"])
        p = p[["ID Consuntivo", "Data", "Servizio", "Sottoservizio", "Matricola", "Operatore", "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale"]]
        save_csv(pd.concat([personnel_detail, p], ignore_index=True), FILES["personnel"])

        v = vehicle_calc.copy()
        v["ID Consuntivo"] = cid
        v["Data"] = pd.Timestamp(service_date)
        v["Servizio"] = service
        v["Sottoservizio"] = subservice
        v = ensure(v, ["Targa", "Mezzo", "Tipo", "Ore", "Costo Orario", "Costo Totale"])
        v = v[["ID Consuntivo", "Data", "Servizio", "Sottoservizio", "Targa", "Mezzo", "Tipo", "Ore", "Costo Orario", "Costo Totale"]]
        save_csv(pd.concat([vehicle_detail, v], ignore_index=True), FILES["vehicle_detail"])

        st.success(f"Consuntivo {cid} salvato correttamente.")
        st.rerun()


# ============================================================
# ECONOMICO
# ============================================================

elif page == "Economico":
    df = authorized_services(services)
    st.markdown('<div class="section-title">Centro di costo per servizio</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("Non ci sono consuntivi disponibili.")
    else:
        service_filter = st.selectbox("Servizio", ["Tutti"] + list(SERVICE_TREE.keys()))
        sub_filter = st.selectbox("Sottoservizio", ["Tutti"] + sorted(st.session_state.allowed_subservices if not is_admin() else ALL_SUBSERVICES))
        if service_filter != "Tutti":
            df = df[df["Servizio"].eq(service_filter)]
        if sub_filter != "Tutti":
            df = df[df["Sottoservizio"].eq(sub_filter)]

        summary = df.groupby(["Servizio", "Sottoservizio"]).agg(
            Ricavi=("Ricavi", "sum"),
            Costi=("Costo Totale", "sum"),
            Margine=("Margine", "sum"),
            Tonnellate=("Tonnellate", "sum"),
        ).reset_index()
        for c in ["Ricavi", "Costi", "Margine", "Tonnellate"]:
            summary[c] = summary[c].apply(parse_num)
        summary["Margine %"] = np.where(summary["Ricavi"] != 0, summary["Margine"] / summary["Ricavi"] * 100, 0)

        display = summary.copy()
        for c in ["Ricavi", "Costi", "Margine"]:
            display[c] = display[c].apply(euro)
        display["Tonnellate"] = display["Tonnellate"].apply(lambda x: num(x, 1))
        display["Margine %"] = display["Margine %"].apply(percent)
        st.dataframe(display, use_container_width=True, hide_index=True)

        l, r = st.columns(2)
        with l:
            st.markdown('<div class="panel"><div class="panel-title">Costo personale per contratto / livello</div></div>', unsafe_allow_html=True)
            p = authorized_services(personnel_detail)
            if not p.empty:
                data = p.groupby(["Contratto", "Livello"])["Costo Totale"].sum().sort_values(ascending=False)
                st.bar_chart(data)
        with r:
            st.markdown('<div class="panel"><div class="panel-title">Costo mezzi per tipologia</div></div>', unsafe_allow_html=True)
            v = authorized_services(vehicle_detail)
            if not v.empty:
                data = v.groupby("Tipo")["Costo Totale"].sum().sort_values(ascending=False)
                st.bar_chart(data)


# ============================================================
# ANAGRAFICHE
# ============================================================

elif page == "Anagrafiche":
    if not is_admin():
        st.error("Sezione riservata alla Direzione.")
        st.stop()

    t1, t2 = st.tabs(["Operatori", "Mezzi"])
    with t1:
        st.markdown('<div class="section-title">Operatori</div>', unsafe_allow_html=True)
        edited = st.data_editor(operators, num_rows="dynamic", use_container_width=True, hide_index=True)
        st.caption("Il contratto e il livello dell'operatore alimentano automaticamente il calcolo del costo orario nei consuntivi.")
        if st.button("Salva operatori", type="primary"):
            save_csv(edited, FILES["operators"])
            st.success("Operatori salvati.")
            st.rerun()

    with t2:
        st.markdown('<div class="section-title">Mezzi</div>', unsafe_allow_html=True)
        edited = st.data_editor(
            vehicles,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={"Tipo": st.column_config.SelectboxColumn("Tipo", options=VEHICLE_TYPES)},
        )
        if st.button("Salva mezzi", type="primary"):
            save_csv(edited, FILES["vehicles"])
            st.success("Mezzi salvati.")
            st.rerun()


# ============================================================
# TARIFFARI & CONTRATTI
# ============================================================

elif page == "Tariffari & Contratti":
    if not is_admin():
        st.error("Sezione riservata alla Direzione.")
        st.stop()

    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Regola economica</div>
            <div class="hero-title">Contratto e costo orario sono due cose diverse</div>
            <div class="hero-copy">Il contratto definisce l'inquadramento dell'operatore. Il costo orario utilizzato dal Centro di Costo viene configurato dalla Direzione e può includere il costo aziendale effettivo.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    t1, t2, t3 = st.tabs(["👷 Personale", "🚛 Mezzi", "⚙️ Generale"])

    with t1:
        labor = tariffs[tariffs["Tipo"].astype(str).str.lower().eq("personale")].copy()
        edited = st.data_editor(
            labor,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Contratto": st.column_config.SelectboxColumn("Contratto", options=list(CONTRACTS.keys())),
                "Costo_Orario": st.column_config.NumberColumn("Costo orario aziendale", min_value=0.0, step=0.01, format="%.2f"),
                "Attivo": st.column_config.SelectboxColumn("Attivo", options=["SI", "NO"]),
            },
        )
        if st.button("Salva costi orari personale", type="primary"):
            others = tariffs[~tariffs["Tipo"].astype(str).str.lower().eq("personale")].copy()
            save_csv(pd.concat([others, edited], ignore_index=True), FILES["tariffs"])
            st.success("Costi orari del personale aggiornati.")
            st.rerun()

    with t2:
        mech = tariffs[tariffs["Tipo"].astype(str).str.lower().eq("mezzo")].copy()
        edited = st.data_editor(
            mech,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Livello_o_Tipo": st.column_config.SelectboxColumn("Tipo mezzo", options=VEHICLE_TYPES),
                "Costo_Orario": st.column_config.NumberColumn("Costo orario", min_value=0.0, step=0.01, format="%.2f"),
                "Attivo": st.column_config.SelectboxColumn("Attivo", options=["SI", "NO"]),
            },
        )
        if st.button("Salva costi mezzi", type="primary"):
            others = tariffs[~tariffs["Tipo"].astype(str).str.lower().eq("mezzo")].copy()
            save_csv(pd.concat([others, edited], ignore_index=True), FILES["tariffs"])
            st.success("Costi mezzi aggiornati.")
            st.rerun()

    with t3:
        general = tariffs[tariffs["Tipo"].astype(str).str.lower().eq("generale")].copy()
        edited = st.data_editor(general, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("Salva parametri generali", type="primary"):
            others = tariffs[~tariffs["Tipo"].astype(str).str.lower().eq("generale")].copy()
            save_csv(pd.concat([others, edited], ignore_index=True), FILES["tariffs"])
            st.success("Parametri generali aggiornati.")
            st.rerun()

    zero_labor = int(((tariffs["Tipo"].astype(str).str.lower() == "personale") & (tariffs["Costo_Orario"] <= 0)).sum())
    if zero_labor:
        st.warning(f"Ci sono {zero_labor} livelli del personale senza costo orario configurato. Prima di usare il consuntivo definitivo, valorizza il tariffario.")


# ============================================================
# ACCESSI
# ============================================================

elif page == "Accessi":
    if not is_admin():
        st.error("Sezione riservata alla Direzione.")
        st.stop()

    st.markdown('<div class="section-title">Utenti e autorizzazioni</div>', unsafe_allow_html=True)
    st.info("Nel campo autorizzazioni puoi usare più sottoservizi separati da virgola oppure TUTTI per la Direzione.")
    edited = st.data_editor(users, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("Salva accessi", type="primary"):
        save_csv(edited, FILES["users"])
        st.success("Accessi aggiornati.")
        st.rerun()

    st.markdown('<div class="section-title">Albero servizi</div>', unsafe_allow_html=True)
    for service_name, subs in SERVICE_TREE.items():
        st.markdown(f'<div class="matrix-row"><div class="matrix-name">{service_name}</div>{"".join([f"<span class=\"pill on\">{x}</span>" for x in subs])}</div>', unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================

st.markdown('<div class="footer">Cristoforo · Control Room · Centro di Costo · V4</div>', unsafe_allow_html=True)
