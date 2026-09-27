import io
import os
import re
from datetime import date, datetime

import numpy as np
import pandas as pd
import streamlit as st

# ============================================================
# CRISTOFORO | CONTROL ROOM V3
# Architettura:
#   Servizio -> Sottoservizio -> Risorse certificate
#   Personale: Contratto + Livello + ore + costo orario aziendale
#   Mezzi: Tipo mezzo + ore + costo orario
#   Ricavi -> Costi -> Margine
# ============================================================

st.set_page_config(
    page_title="Cristoforo | Control Room V3",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LEGACY_SERVICES_FILE = os.path.join(BASE_DIR, "storico_servizi_v9.csv")

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

# ------------------------------------------------------------
# SERVIZI / SOTTOSERVIZI
# La struttura segue esattamente l'elenco fornito.
# ------------------------------------------------------------
SERVICE_TREE = {
    "Spazzamenti": ["Scandicci"],
    "Aree Verdi": ["Piana", "Prato"],
    "Porta a Porta": [
        "Prato", "Vaiano", "Campi", "Noventa", "Costabissara",
        "Cremona", "Mantova", "Lucca"
    ],
    "Trasporti": ["Alia"],
    "Raccolta Cartone Selettivo": [
        "Firenze", "Piana", "Prato", "Campi"
    ],
    "Ingombranti": [
        "Prato", "Campi Bisenzio", "Valdisieve", "Mugello"
    ],
}

SUBSERVICES = sorted({x for values in SERVICE_TREE.values() for x in values})

# ------------------------------------------------------------
# CONTRATTI
# Nota: il codice rende configurabile il costo orario aziendale.
# Non viene confuso con il minimo tabellare del CCNL.
# ------------------------------------------------------------
UTILITALIA_LEVELS = [
    "Q", "A1", "A2S", "A2", "B1S", "B1", "B2S", "B2",
    "C1S", "C1", "C2S", "C2", "D1S", "D1", "D2S", "D2"
]

COOPERATIVE_SOCIALI_LEVELS = [
    "A1", "A2", "B1", "C1", "C2", "C3",
    "D1", "D2", "D3", "E1", "E2", "F1", "F2"
]

CONTRACTS = {
    "Servizi Ambientali - Utilitalia": UTILITALIA_LEVELS,
    "Cooperative Sociali": COOPERATIVE_SOCIALI_LEVELS,
}

DEFAULT_VEHICLE_TYPES = [
    "Leggero",
    "Furgone",
    "Compattatore",
    "Spazzatrice",
    "Scarrabile",
    "Pesante",
    "Speciale",
]

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
# CSS
# ============================================================

st.markdown("""
<style>
:root {
    --green:#008b3a;
    --green-dark:#00682d;
    --green-soft:#eaf7ef;
    --ink:#17211c;
    --muted:#6c7770;
    --line:#e4e8e5;
    --bg:#f3f6f4;
    --white:#ffffff;
}

.stApp { background:var(--bg); }
.block-container { max-width:1500px; padding-top:1rem; padding-bottom:3rem; }
section[data-testid="stSidebar"] { background:#0f1713; border-right:1px solid #1d2821; }
section[data-testid="stSidebar"] * { color:#eef5f0; }

.brand { padding:10px 4px 20px 4px; }
.brand-title { font-size:27px; font-weight:900; letter-spacing:-1px; }
.brand-sub { color:#8c9a92 !important; font-size:12px; margin-top:3px; }

.topbar {
    background:#fff; border:1px solid var(--line); border-radius:20px;
    padding:16px 20px; display:flex; justify-content:space-between;
    align-items:center; box-shadow:0 5px 18px rgba(20,40,30,.04);
    margin-bottom:18px;
}
.title { font-size:28px; font-weight:900; letter-spacing:-.8px; color:var(--ink); }
.subtitle { color:var(--muted); font-size:13px; margin-top:4px; }
.user-pill { background:var(--green-soft); color:var(--green-dark); font-weight:800; border-radius:999px; padding:8px 13px; font-size:12px; }

.hero {
    background:linear-gradient(135deg,#ffffff 0%,#edf8f1 100%);
    border:1px solid #dce9e0; border-radius:22px; padding:20px 22px;
    box-shadow:0 8px 26px rgba(0,60,30,.035); margin-bottom:18px;
}
.hero-kicker { color:var(--green-dark); text-transform:uppercase; letter-spacing:1px; font-size:11px; font-weight:900; }
.hero-title { font-size:29px; font-weight:900; margin-top:4px; color:#122018; }
.hero-copy { color:#6a756e; margin-top:4px; }

.step-card {
    background:#fff; border:1px solid var(--line); border-radius:18px;
    padding:15px 17px; min-height:110px; box-shadow:0 4px 17px rgba(20,40,30,.035);
}
.step-number { font-size:11px; font-weight:900; color:var(--green); text-transform:uppercase; }
.step-title { font-size:17px; font-weight:850; margin-top:6px; }
.step-copy { color:var(--muted); font-size:12px; margin-top:3px; }

.kpi {
    background:#fff; border:1px solid var(--line); border-radius:17px;
    padding:17px; min-height:120px; box-shadow:0 4px 18px rgba(20,40,30,.035);
}
.kpi-label { color:#7b857e; font-size:11px; font-weight:850; text-transform:uppercase; letter-spacing:.5px; }
.kpi-value { font-size:28px; line-height:1.15; font-weight:900; margin-top:8px; color:#111a15; }
.kpi-note { color:#8a948d; font-size:11px; margin-top:5px; }

.section-title { font-size:18px; font-weight:900; color:var(--ink); margin:22px 0 10px; }
.info-card { background:#fff; border:1px solid var(--line); border-radius:17px; padding:16px; box-shadow:0 4px 18px rgba(20,40,30,.035); }
.info-title { font-size:12px; font-weight:850; color:#68736c; text-transform:uppercase; letter-spacing:.45px; }
.info-value { font-size:24px; font-weight:900; margin-top:5px; }

.badge-ok { display:inline-block; background:#e5f6eb; color:#08763a; padding:5px 9px; border-radius:999px; font-size:10px; font-weight:900; }
.badge-warn { display:inline-block; background:#fff5dd; color:#976600; padding:5px 9px; border-radius:999px; font-size:10px; font-weight:900; }
.badge-danger { display:inline-block; background:#fdeaea; color:#b42318; padding:5px 9px; border-radius:999px; font-size:10px; font-weight:900; }

.login { max-width:430px; margin:8vh auto 0; background:#fff; border:1px solid var(--line); border-radius:24px; padding:35px; box-shadow:0 20px 60px rgba(20,40,30,.08); }
.login-logo { text-align:center; color:var(--green); font-size:36px; font-weight:950; }
.login-copy { text-align:center; color:var(--muted); margin-bottom:24px; }

div.stButton > button { border-radius:11px; font-weight:800; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CSV HELPERS
# ============================================================

def clean_col(value):
    value = str(value).replace("\ufeff", "").strip().lower()
    trans = str.maketrans({"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u"})
    value = value.translate(trans)
    value = value.replace("€", "euro").replace("/", "_").replace("-", "_").replace(" ", "_")
    return re.sub(r"_+", "_", value).strip("_")


def normalize_columns(df):
    if df is None:
        return pd.DataFrame()
    out = df.copy()
    out.columns = [clean_col(c) for c in out.columns]
    return out


def read_csv_flexible(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    for enc in ["utf-8-sig", "utf-8", "latin1"]:
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
    ren = {}
    for target, aliases in mapping.items():
        for name in [target] + list(aliases):
            key = clean_col(name)
            if key in existing:
                ren[existing[key]] = target
                break
    return df.rename(columns=ren)


def ensure(df, cols):
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = ""
    return out


def parse_num(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
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
        v = float(value)
        return v * 24 if 0 < v < 1 else v
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


def euro(v):
    txt = f"€ {float(v):,.2f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def num(v, dec=1):
    txt = f"{float(v):,.{dec}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")

# ============================================================
# FILE INITIALIZATION
# ============================================================

def init_files():
    if not os.path.exists(FILES["users"]):
        save_csv(DEFAULT_USERS, FILES["users"])
    if not os.path.exists(FILES["operators"]):
        save_csv(pd.DataFrame(columns=["Matricola", "Nome", "Cognome", "Contratto", "Livello", "Commessa"]), FILES["operators"])
    if not os.path.exists(FILES["vehicles"]):
        save_csv(pd.DataFrame(columns=["Targa", "Mezzo", "Tipo", "Commessa"]), FILES["vehicles"])
    if not os.path.exists(FILES["services"]):
        save_csv(pd.DataFrame(columns=[
            "ID", "Data", "Servizio", "Sottoservizio", "Tonnellate", "Ricavi",
            "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine",
            "Note", "Creato Da"
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
        save_csv(pd.DataFrame(columns=[
            "ID Import", "Data Import", "File", "Righe", "Esito", "Operatore"
        ]), FILES["certifications"])
    if not os.path.exists(FILES["tariffs"]):
        # Livelli contrattuali: costo orario volutamente configurabile.
        rows = []
        for contract, levels in CONTRACTS.items():
            for level in levels:
                rows.append({
                    "Tipo": "Personale",
                    "Contratto": contract,
                    "Livello_o_Tipo": level,
                    "Costo_Orario": 0.0,
                    "Attivo": "SI",
                })
        for vehicle, cost in DEFAULT_VEHICLE_COSTS.items():
            rows.append({
                "Tipo": "Mezzo",
                "Contratto": "",
                "Livello_o_Tipo": vehicle,
                "Costo_Orario": cost,
                "Attivo": "SI",
            })
        rows.append({
            "Tipo": "Generale",
            "Contratto": "",
            "Livello_o_Tipo": "Overhead",
            "Costo_Orario": 15.0,
            "Attivo": "SI",
        })
        save_csv(pd.DataFrame(rows), FILES["tariffs"])

init_files()

# ============================================================
# READ DATASETS
# ============================================================

def read_users():
    df = read_csv_flexible(FILES["users"])
    df = aliases_rename(df, {
        "username": ["user", "utente", "login"],
        "password": ["pass", "pwd"],
        "nome": ["name", "nominativo"],
        "ruolo": ["role", "profilo"],
        "autorizzazioni": ["cantieri", "commesse", "cantiere", "accessi"],
    })
    req = ["username", "password", "nome", "ruolo", "autorizzazioni"]
    if df.empty or not all(x in df.columns for x in req):
        df = DEFAULT_USERS.copy()
    df = ensure(df, req)
    for c in req:
        df[c] = df[c].astype(str).str.replace("\ufeff", "", regex=False).str.strip()
    return df[req]


def read_operators():
    df = read_csv_flexible(FILES["operators"])
    df = aliases_rename(df, {
        "Matricola": ["matricola", "id_operatore", "codice"],
        "Nome": ["nome"],
        "Cognome": ["cognome"],
        "Contratto": ["ccnl", "contratto_collettivo"],
        "Livello": ["livello", "qualifica"],
        "Commessa": ["cantiere", "commessa"],
    })
    req = ["Matricola", "Nome", "Cognome", "Contratto", "Livello", "Commessa"]
    df = ensure(df, req)
    for c in req:
        df[c] = df[c].astype(str).str.strip()
    return df[req]


def read_vehicles():
    df = read_csv_flexible(FILES["vehicles"])
    df = aliases_rename(df, {
        "Targa": ["targa", "plate"],
        "Mezzo": ["mezzo", "veicolo", "descrizione"],
        "Tipo": ["tipo", "categoria", "classe"],
        "Commessa": ["cantiere", "commessa"],
    })
    req = ["Targa", "Mezzo", "Tipo", "Commessa"]
    df = ensure(df, req)
    for c in req:
        df[c] = df[c].astype(str).str.strip()
    return df[req]


def read_tariffs():
    df = read_csv_flexible(FILES["tariffs"])
    df = aliases_rename(df, {
        "Tipo": ["categoria"],
        "Contratto": ["ccnl"],
        "Livello_o_Tipo": ["livello", "voce", "tipo_mezzo"],
        "Costo_Orario": ["costo_orario", "costo", "tariffa"],
        "Attivo": ["attiva", "active"],
    })
    req = ["Tipo", "Contratto", "Livello_o_Tipo", "Costo_Orario", "Attivo"]
    df = ensure(df, req)
    df["Costo_Orario"] = df["Costo_Orario"].apply(parse_num)
    return df[req]


def read_services():
    df = read_csv_flexible(FILES["services"])

    # Compatibilità con lo storico precedente: se il nuovo archivio è vuoto,
    # leggiamo in sola lettura storico_servizi_v9.csv senza modificarlo.
    if df.empty and os.path.exists(LEGACY_SERVICES_FILE):
        legacy = read_csv_flexible(LEGACY_SERVICES_FILE)
        if not legacy.empty:
            legacy = aliases_rename(legacy, {
                "ID": ["id", "id_servizio", "codice"],
                "Data": ["data_servizio", "giorno", "date"],
                "CommessaLegacy": ["cantiere", "commessa"],
                "ServizioLegacy": ["categoria", "servizio", "tipo_servizio"],
                "DettaglioLegacy": ["dettaglio", "sottoservizio"],
                "Tonnellate": ["ton", "tonnellaggio"],
                "Ricavi": ["ricavo", "revenue", "fatturato"],
                "Costo Totale": ["costo", "costi", "costo_totale"],
                "Margine": ["margine_netto", "margine_euro"],
                "Ore Personale": ["ore_personale", "ore_operatori"],
                "Ore Mezzi": ["ore_mezzi", "ore_veicoli"],
            })
            legacy = ensure(legacy, ["ID", "Data", "CommessaLegacy", "ServizioLegacy", "DettaglioLegacy", "Tonnellate", "Ricavi", "Costo Totale", "Margine", "Ore Personale", "Ore Mezzi"])
            df = pd.DataFrame({
                "ID": legacy["ID"],
                "Data": legacy["Data"],
                "Servizio": legacy["ServizioLegacy"],
                "Sottoservizio": legacy["DettaglioLegacy"].where(legacy["DettaglioLegacy"].astype(str).str.strip() != "", legacy["CommessaLegacy"]),
                "Tonnellate": legacy["Tonnellate"],
                "Ricavi": legacy["Ricavi"],
                "Costo Personale": 0.0,
                "Costo Mezzi": 0.0,
                "Overhead": 0.0,
                "Costo Totale": legacy["Costo Totale"],
                "Margine": legacy["Margine"],
                "Note": "Storico legacy",
                "Creato Da": "Legacy",
            })

    req = [
        "ID", "Data", "Servizio", "Sottoservizio", "Tonnellate", "Ricavi",
        "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine", "Note", "Creato Da"
    ]
    df = aliases_rename(df, {
        "ID": ["id", "id_consuntivo"],
        "Data": ["giorno", "data_servizio"],
        "Servizio": ["categoria", "tipo_servizio"],
        "Sottoservizio": ["sotto_servizio", "dettaglio", "commessa"],
        "Tonnellate": ["ton", "tonnellaggio"],
        "Ricavi": ["ricavo", "fatturato", "revenue"],
        "Costo Personale": ["costo_personale"],
        "Costo Mezzi": ["costo_mezzi"],
        "Overhead": ["costi_indiretti"],
        "Costo Totale": ["costo", "costi"],
        "Margine": ["margine_netto"],
        "Note": ["note", "commenti"],
        "Creato Da": ["operatore_creazione", "utente"],
    })
    df = ensure(df, req)
    df["Data"] = df["Data"].apply(parse_date)
    for c in ["Tonnellate", "Ricavi", "Costo Personale", "Costo Mezzi", "Overhead", "Costo Totale", "Margine"]:
        df[c] = df[c].apply(parse_num)
    return df[req]


def read_personnel():
    df = read_csv_flexible(FILES["personnel"])
    req = [
        "ID Consuntivo", "Data", "Servizio", "Sottoservizio", "Matricola",
        "Operatore", "Contratto", "Livello", "Ore", "Costo Orario", "Costo Totale"
    ]
    df = aliases_rename(df, {
        "ID Consuntivo": ["id", "id_consuntivo"],
        "Data": ["data_servizio", "giorno"],
        "Servizio": ["categoria"],
        "Sottoservizio": ["sotto_servizio", "dettaglio", "commessa"],
        "Matricola": ["matricola", "id_operatore"],
        "Operatore": ["operatore", "dipendente", "addetto"],
        "Contratto": ["ccnl"],
        "Livello": ["livello"],
        "Ore": ["ore_lavorate", "ore"],
        "Costo Orario": ["costo_orario", "tariffa_oraria"],
        "Costo Totale": ["costo", "costo_totale"],
    })
    df = ensure(df, req)
    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)
    df["Costo Orario"] = df["Costo Orario"].apply(parse_num)
    df["Costo Totale"] = df["Costo Totale"].apply(parse_num)
    return df[req]


def read_vehicle_detail():
    df = read_csv_flexible(FILES["vehicle_detail"])
    req = [
        "ID Consuntivo", "Data", "Servizio", "Sottoservizio", "Targa",
        "Mezzo", "Tipo", "Ore", "Costo Orario", "Costo Totale"
    ]
    df = aliases_rename(df, {
        "ID Consuntivo": ["id", "id_consuntivo"],
        "Data": ["data_servizio", "giorno"],
        "Servizio": ["categoria"],
        "Sottoservizio": ["sotto_servizio", "dettaglio", "commessa"],
        "Targa": ["targa", "plate"],
        "Mezzo": ["mezzo", "veicolo"],
        "Tipo": ["tipo", "categoria_mezzo"],
        "Ore": ["ore_mezzo", "ore"],
        "Costo Orario": ["costo_orario", "tariffa_oraria"],
        "Costo Totale": ["costo", "costo_totale"],
    })
    df = ensure(df, req)
    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)
    df["Costo Orario"] = df["Costo Orario"].apply(parse_num)
    df["Costo Totale"] = df["Costo Totale"].apply(parse_num)
    return df[req]


def current_datasets():
    return (
        read_users(), read_operators(), read_vehicles(), read_tariffs(),
        read_services(), read_personnel(), read_vehicle_detail()
    )

# ============================================================
# AUTHORIZATION
# ============================================================

def split_access(value):
    if str(value).strip().upper() in {"TUTTI", "ALL", "*"}:
        return SUBSERVICES
    vals = re.split(r"[,;|]", str(value))
    return sorted(set([v.strip() for v in vals if v.strip()]))


def is_admin():
    return st.session_state.get("ruolo", "").strip().lower() in {"admin", "direzione"}


def allowed_subservices():
    if is_admin():
        return SUBSERVICES.copy()
    return [x for x in split_access(st.session_state.get("autorizzazioni", "")) if x in SUBSERVICES]


def authorized_services(df, col="Sottoservizio"):
    if df.empty or is_admin():
        return df.copy()
    allowed = allowed_subservices()
    if not allowed:
        return df.iloc[0:0].copy()
    return df[df[col].astype(str).isin(allowed)].copy()

# ============================================================
# COST LOOKUP
# ============================================================

def labor_rate(tariffs, contract, level):
    if tariffs.empty:
        return 0.0
    m = (
        (tariffs["Tipo"].astype(str).str.lower() == "personale")
        & (tariffs["Contratto"].astype(str).str.strip() == str(contract).strip())
        & (tariffs["Livello_o_Tipo"].astype(str).str.strip() == str(level).strip())
        & (tariffs["Attivo"].astype(str).str.upper() == "SI")
    )
    r = tariffs.loc[m, "Costo_Orario"]
    return float(r.iloc[0]) if not r.empty else 0.0


def vehicle_rate(tariffs, vehicle_type):
    if tariffs.empty:
        return 0.0
    m = (
        (tariffs["Tipo"].astype(str).str.lower() == "mezzo")
        & (tariffs["Livello_o_Tipo"].astype(str).str.strip() == str(vehicle_type).strip())
        & (tariffs["Attivo"].astype(str).str.upper() == "SI")
    )
    r = tariffs.loc[m, "Costo_Orario"]
    return float(r.iloc[0]) if not r.empty else 0.0


def overhead_rate(tariffs):
    if tariffs.empty:
        return 15.0
    m = (
        (tariffs["Tipo"].astype(str).str.lower() == "generale")
        & (tariffs["Livello_o_Tipo"].astype(str).str.strip().str.lower() == "overhead")
    )
    r = tariffs.loc[m, "Costo_Orario"]
    return float(r.iloc[0]) if not r.empty else 15.0

# ============================================================
# IMPORT CERTIFICAZIONE
# ============================================================

CERT_ALIASES = {
    "Data": ["giorno", "data_servizio", "date"],
    "Matricola": ["matricola", "id_operatore", "codice_operatore", "employee_id"],
    "Operatore": ["operatore", "dipendente", "addetto", "employee", "nome_operatore"],
    "Ore": ["ore", "ore_lavorate", "hours", "durata", "ore_totali"],
    "Targa": ["targa", "plate", "veicolo_targa"],
    "Mezzo": ["mezzo", "veicolo", "vehicle"],
    "Tipo Mezzo": ["tipo_mezzo", "categoria_mezzo", "classe_mezzo"],
    "Servizio": ["servizio", "categoria", "tipo_servizio"],
    "Sottoservizio": ["sottoservizio", "sotto_servizio", "dettaglio", "commessa", "cantiere"],
    "Risorsa": ["tipo_risorsa", "risorsa", "tipo"],
}


def read_uploaded_file(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        raw = uploaded.getvalue()
        text = None
        for enc in ["utf-8-sig", "utf-8", "latin1"]:
            try:
                text = raw.decode(enc)
                break
            except Exception:
                pass
        if text is None:
            raise ValueError("Codifica CSV non riconosciuta.")
        return pd.read_csv(io.StringIO(text), sep=None, engine="python"), None
    if name.endswith((".xlsx", ".xls")):
        xl = pd.ExcelFile(uploaded)
        return None, xl
    raise ValueError("Formato non supportato.")


def normalize_certification(df):
    df = aliases_rename(df, CERT_ALIASES)
    df = ensure(df, [
        "Data", "Matricola", "Operatore", "Ore", "Targa", "Mezzo",
        "Tipo Mezzo", "Servizio", "Sottoservizio", "Risorsa"
    ])
    for c in ["Matricola", "Operatore", "Targa", "Mezzo", "Tipo Mezzo", "Servizio", "Sottoservizio", "Risorsa"]:
        df[c] = df[c].astype(str).str.strip()
    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)

    # Se il file certificazione non identifica la risorsa, inferiamo:
    # presenza operatore -> personale; presenza targa/mezzo -> mezzo.
    def infer(row):
        r = str(row["Risorsa"]).strip().lower()
        if r in {"personale", "operatore", "dipendente", "operatori"}:
            return "Personale"
        if r in {"mezzo", "mezzi", "veicolo", "veicoli"}:
            return "Mezzo"
        if row["Operatore"].strip() or row["Matricola"].strip():
            return "Personale"
        if row["Targa"].strip() or row["Mezzo"].strip():
            return "Mezzo"
        return ""

    df["Risorsa"] = df.apply(infer, axis=1)
    return df

# ============================================================
# SESSION STATE
# ============================================================

for key, default in {
    "logged": False,
    "username": "",
    "nome": "",
    "ruolo": "",
    "autorizzazioni": "",
    "cert_df": pd.DataFrame(),
    "cert_file_name": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# LOGIN
# ============================================================

if not st.session_state.logged:
    st.markdown("""
    <div class="login">
      <div class="login-logo">♻️ CRISTOFORO</div>
      <div class="login-copy">Control Room · Consuntivazione Economica</div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Accedi alla Control Room", type="primary", use_container_width=True):
            users = read_users()
            m = users[(users["username"] == u.strip()) & (users["password"] == p.strip())]
            if m.empty:
                st.error("Username o password non corretti.")
            else:
                row = m.iloc[0]
                st.session_state.logged = True
                st.session_state.username = row["username"]
                st.session_state.nome = row["nome"]
                st.session_state.ruolo = row["ruolo"]
                st.session_state.autorizzazioni = row["autorizzazioni"]
                st.rerun()
    st.stop()

# ============================================================
# DATASETS
# ============================================================

users, operators, vehicles, tariffs, services, personnel_detail, vehicle_detail = current_datasets()

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("""
    <div class="brand">
      <div class="brand-title">♻️ CRISTOFORO</div>
      <div class="brand-sub">Control Room · Centro di Costo</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    pages = ["Dashboard", "Consuntivazione", "Certificazioni", "Economico"]
    if is_admin():
        pages += ["Anagrafiche", "Tariffari & Contratti", "Accessi"]
    page = st.radio("Menu", pages, label_visibility="collapsed")

    st.markdown("---")
    st.caption(f"👤 {st.session_state.nome}")
    st.caption(f"Ruolo: {st.session_state.ruolo}")
    allowed = allowed_subservices()
    st.caption(f"Accesso: {len(allowed)} sottoservizi")
    if st.button("Esci", use_container_width=True):
        for key in ["logged", "username", "nome", "ruolo", "autorizzazioni"]:
            st.session_state.pop(key, None)
        st.rerun()

# ============================================================
# TOPBAR
# ============================================================

page_meta = {
    "Dashboard": ("Control Room", "Panoramica operativa ed economica"),
    "Consuntivazione": ("Nuovo consuntivo", "Servizio, sottoservizio, personale, mezzi e margine"),
    "Certificazioni": ("Certificazioni ore", "Carica e controlla il file certificato di operatori e mezzi"),
    "Economico": ("Centro di Costo", "Analisi dei costi per servizio e sottoservizio"),
    "Anagrafiche": ("Anagrafiche", "Operatori e mezzi"),
    "Tariffari & Contratti": ("Tariffari & Contratti", "Contratti, livelli e costi orari aziendali"),
    "Accessi": ("Accessi", "Utenti e autorizzazioni"),
}
title, subtitle = page_meta[page]
st.markdown(f"""
<div class="topbar">
  <div>
    <div class="title">{title}</div>
    <div class="subtitle">{subtitle}</div>
  </div>
  <div class="user-pill">● {st.session_state.nome}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":
    allowed_df = authorized_services(services)
    st.markdown(f"""
    <div class="hero">
      <div class="hero-kicker">Centro di costo operativo</div>
      <div class="hero-title">Servizi → Sottoservizi → Risorse certificate</div>
      <div class="hero-copy">Una sola vista per leggere ricavi, costi, ore uomo, ore mezzi e margine.</div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    metrics = [
        ("Ricavi", allowed_df["Ricavi"].sum(), "fatturato consuntivato"),
        ("Costo totale", allowed_df["Costo Totale"].sum(), "personale + mezzi + indiretti"),
        ("Margine", allowed_df["Margine"].sum(), "ricavi - costo totale"),
        ("Ore uomo", personnel_detail["Ore"].sum(), "da certificazione"),
    ]
    for col, (label, value, note) in zip(cols, metrics):
        with col:
            value_txt = euro(value) if label != "Ore uomo" else f"{num(value)} h"
            st.markdown(f"""
            <div class="kpi">
              <div class="kpi-label">{label}</div>
              <div class="kpi-value">{value_txt}</div>
              <div class="kpi-note">{note}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Navigazione operativa</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    cards = [
        (c1, "01", "Servizio", "Seleziona il servizio principale e passa ai sottoservizi disponibili."),
        (c2, "02", "Certificazione", "Carica il file ore e fai riconoscere automaticamente operatori e mezzi."),
        (c3, "03", "Costo & margine", "Applica contratto, livello, tariffa oraria e costo mezzi."),
    ]
    for col, n, t, d in cards:
        with col:
            st.markdown(f"""
            <div class="step-card">
              <div class="step-number">Passo {n}</div>
              <div class="step-title">{t}</div>
              <div class="step-copy">{d}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Andamento economico</div>', unsafe_allow_html=True)
    if not allowed_df.empty:
        trend = allowed_df.copy()
        trend["Data"] = pd.to_datetime(trend["Data"], errors="coerce")
        trend = trend.dropna(subset=["Data"])
        if not trend.empty:
            trend = trend.groupby("Data")[["Ricavi", "Costo Totale", "Margine"]].sum().sort_index()
            st.line_chart(trend)

    st.markdown('<div class="section-title">Mix servizi</div>', unsafe_allow_html=True)
    if not allowed_df.empty:
        mix = allowed_df.groupby("Servizio")["Costo Totale"].sum().sort_values(ascending=False)
        st.bar_chart(mix)

# ============================================================
# CERTIFICAZIONI
# ============================================================

elif page == "Certificazioni":
    st.markdown('<div class="section-title">1 · Carica certificazione ore</div>', unsafe_allow_html=True)
    st.info("Il caricamento accetta CSV/XLSX. L'app prova a riconoscere automaticamente data, operatore, ore, targa, mezzo e sottoservizio.")

    uploaded = st.file_uploader("File certificazione", type=["csv", "xlsx", "xls"])

    if uploaded:
        try:
            csv_df, excel_file = read_uploaded_file(uploaded)
            if excel_file is not None:
                sheet = st.selectbox("Foglio Excel", excel_file.sheet_names)
                raw_df = pd.read_excel(excel_file, sheet_name=sheet)
            else:
                raw_df = csv_df

            cert = normalize_certification(raw_df)
            st.session_state.cert_df = cert
            st.session_state.cert_file_name = uploaded.name

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Righe", len(cert))
            with c2: st.metric("Ore", f"{num(cert['Ore'].sum())} h")
            with c3: st.metric("Personale", int((cert["Risorsa"] == "Personale").sum()))

            st.markdown('<div class="section-title">Anteprima normalizzata</div>', unsafe_allow_html=True)
            st.dataframe(cert.head(200), use_container_width=True, hide_index=True)

            if st.button("Usa questa certificazione nella consuntivazione", type="primary", use_container_width=True):
                st.success("Certificazione caricata nella sessione. Vai su 'Consuntivazione'.")
        except Exception as exc:
            st.error(f"Errore nel caricamento: {exc}")

    if not st.session_state.cert_df.empty:
        st.markdown('<div class="section-title">Controlli qualità</div>', unsafe_allow_html=True)
        cert = st.session_state.cert_df
        missing_hours = int((cert["Ore"] <= 0).sum())
        missing_resource = int((cert["Risorsa"].astype(str).str.strip() == "").sum())
        missing_sub = int((cert["Sottoservizio"].astype(str).str.strip() == "").sum())
        q1, q2, q3 = st.columns(3)
        with q1:
            st.markdown(f'<div class="info-card"><div class="info-title">Righe senza ore</div><div class="info-value">{missing_hours}</div></div>', unsafe_allow_html=True)
        with q2:
            st.markdown(f'<div class="info-card"><div class="info-title">Risorsa non riconosciuta</div><div class="info-value">{missing_resource}</div></div>', unsafe_allow_html=True)
        with q3:
            st.markdown(f'<div class="info-card"><div class="info-title">Sottoservizio mancante</div><div class="info-value">{missing_sub}</div></div>', unsafe_allow_html=True)

        if st.button("Registra log importazione", use_container_width=True):
            log = pd.DataFrame([{
                "ID Import": "IMP-" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "Data Import": datetime.now(),
                "File": st.session_state.cert_file_name,
                "Righe": len(cert),
                "Esito": "Caricato",
                "Operatore": st.session_state.nome,
            }])
            old = read_csv_flexible(FILES["certifications"])
            save_csv(pd.concat([old, normalize_columns(log)], ignore_index=True), FILES["certifications"])
            st.success("Importazione registrata.")

# ============================================================
# CONSUNTIVAZIONE
# ============================================================

elif page == "Consuntivazione":
    st.markdown('<div class="section-title">1 · Identifica il servizio</div>', unsafe_allow_html=True)
    services_available = list(SERVICE_TREE.keys())
    selected_service = st.selectbox("Servizio principale", services_available)

    allowed_ss = [x for x in SERVICE_TREE[selected_service] if is_admin() or x in allowed_subservices()]
    if not allowed_ss:
        st.error("Nessun sottoservizio autorizzato per questo servizio.")
        st.stop()
    selected_subservice = st.selectbox("Sottoservizio", allowed_ss)

    st.markdown(f"""
    <div class="hero">
      <div class="hero-kicker">Cost center selezionato</div>
      <div class="hero-title">{selected_service} · {selected_subservice}</div>
      <div class="hero-copy">Ora associamo la certificazione alle risorse e calcoliamo automaticamente i costi.</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📥 Carica qui la certificazione ore (opzionale)", expanded=st.session_state.cert_df.empty):
        inline_upload = st.file_uploader("Certificazione CSV/XLSX", type=["csv", "xlsx", "xls"], key="inline_cert")
        if inline_upload is not None:
            try:
                csv_df, excel_file = read_uploaded_file(inline_upload)
                if excel_file is not None:
                    sheet_inline = st.selectbox("Foglio", excel_file.sheet_names, key="inline_sheet")
                    raw_inline = pd.read_excel(excel_file, sheet_name=sheet_inline)
                else:
                    raw_inline = csv_df
                st.session_state.cert_df = normalize_certification(raw_inline)
                st.session_state.cert_file_name = inline_upload.name
                st.success(f"Certificazione pronta: {len(st.session_state.cert_df)} righe.")
            except Exception as exc:
                st.error(f"Errore certificazione: {exc}")

    c1, c2, c3 = st.columns(3)
    with c1:
        service_date = st.date_input("Data servizio", value=date.today())
    with c2:
        tonnage = st.number_input("Tonnellate", min_value=0.0, value=0.0, step=0.1)
    with c3:
        revenue = st.number_input("Ricavo / fatturato", min_value=0.0, value=0.0, step=50.0)

    cert = st.session_state.cert_df.copy()
    if not cert.empty:
        cert = cert.copy()
        # La certificazione può contenere più sottoservizi; filtriamo quando disponibile.
        if cert["Sottoservizio"].astype(str).str.strip().eq("").all():
            cert["Sottoservizio"] = selected_subservice
        cert = cert[cert["Sottoservizio"].astype(str).str.strip().isin(["", selected_subservice])].copy()

    # ---------------- PERSONALE ----------------
    st.markdown('<div class="section-title">2 · Ore personale certificate</div>', unsafe_allow_html=True)
    pc1, pc2 = st.columns(2)
    with pc1:
        default_contract = st.selectbox("Contratto predefinito", list(CONTRACTS.keys()), key="default_contract")
    with pc2:
        default_level = st.selectbox("Livello predefinito", CONTRACTS[default_contract], key="default_level")

    if cert.empty or not (cert["Risorsa"] == "Personale").any():
        st.warning("Nessuna riga personale disponibile. Puoi comunque inserire le righe manualmente.")
        personnel_rows = pd.DataFrame([{
            "Matricola": "", "Operatore": "", "Contratto": "Servizi Ambientali - Utilitalia",
            "Livello": UTILITALIA_LEVELS[0], "Ore": 0.0,
        }])
    else:
        personnel_rows = cert[cert["Risorsa"] == "Personale"][["Matricola", "Operatore", "Ore"]].copy()
        personnel_rows["Contratto"] = ""
        personnel_rows["Livello"] = ""
        # join anagrafica per compilare contratto/livello
        for idx, row in personnel_rows.iterrows():
            m = operators[operators["Matricola"].astype(str) == str(row["Matricola"]).strip()]
            if not m.empty:
                personnel_rows.loc[idx, "Contratto"] = m.iloc[0]["Contratto"]
                personnel_rows.loc[idx, "Livello"] = m.iloc[0]["Livello"]
        personnel_rows = personnel_rows[["Matricola", "Operatore", "Contratto", "Livello", "Ore"]]

    # Default contract/level per righe vuote.
    for idx in personnel_rows.index:
        if not str(personnel_rows.loc[idx, "Contratto"]).strip():
            personnel_rows.loc[idx, "Contratto"] = "Servizi Ambientali - Utilitalia"
        if not str(personnel_rows.loc[idx, "Livello"]).strip():
            personnel_rows.loc[idx, "Livello"] = UTILITALIA_LEVELS[0]

    edited_personnel = st.data_editor(
        personnel_rows.reset_index(drop=True),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Contratto": st.column_config.SelectboxColumn("Contratto", options=list(CONTRACTS.keys())),
            "Livello": st.column_config.TextColumn("Livello"),
            "Ore": st.column_config.NumberColumn("Ore", min_value=0.0, step=0.25, format="%.2f"),
        },
        key="personnel_editor",
    )

    # Controllo livelli consentiti e tariffa.
    personnel_calc = edited_personnel.copy()
    personnel_calc["Costo Orario"] = 0.0
    personnel_calc["Costo Totale"] = 0.0
    warnings = []
    for idx, row in personnel_calc.iterrows():
        contract = str(row.get("Contratto", "")).strip()
        level = str(row.get("Livello", "")).strip()
        if contract not in CONTRACTS:
            warnings.append(f"Riga {idx+1}: contratto non riconosciuto.")
            continue
        if level not in CONTRACTS[contract]:
            warnings.append(f"Riga {idx+1}: livello {level} non valido per {contract}.")
            continue
        rate = labor_rate(tariffs, contract, level)
        personnel_calc.loc[idx, "Costo Orario"] = rate
        personnel_calc.loc[idx, "Costo Totale"] = parse_hours(row.get("Ore", 0)) * rate

    if warnings:
        st.warning("\n".join(warnings))

    labor_cost = float(personnel_calc["Costo Totale"].sum())
    labor_hours = float(personnel_calc["Ore"].apply(parse_hours).sum())

    # ---------------- MEZZI ----------------
    st.markdown('<div class="section-title">3 · Ore mezzi certificate</div>', unsafe_allow_html=True)
    if cert.empty or not (cert["Risorsa"] == "Mezzo").any():
        st.warning("Nessuna riga mezzi disponibile. Puoi aggiungerla manualmente.")
        vehicle_rows = pd.DataFrame([{
            "Targa": "", "Mezzo": "", "Tipo": DEFAULT_VEHICLE_TYPES[0], "Ore": 0.0,
        }])
    else:
        vehicle_rows = cert[cert["Risorsa"] == "Mezzo"][["Targa", "Mezzo", "Tipo Mezzo", "Ore"]].copy()
        vehicle_rows = vehicle_rows.rename(columns={"Tipo Mezzo": "Tipo"})
        vehicle_rows = vehicle_rows[["Targa", "Mezzo", "Tipo", "Ore"]]
        for idx, row in vehicle_rows.iterrows():
            if not str(row["Tipo"]).strip():
                m = vehicles[vehicles["Targa"].astype(str) == str(row["Targa"]).strip()]
                if not m.empty:
                    vehicle_rows.loc[idx, "Tipo"] = m.iloc[0]["Tipo"]
            if not str(vehicle_rows.loc[idx, "Tipo"]).strip():
                vehicle_rows.loc[idx, "Tipo"] = DEFAULT_VEHICLE_TYPES[0]

    edited_vehicles = st.data_editor(
        vehicle_rows.reset_index(drop=True),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tipo": st.column_config.SelectboxColumn("Tipo mezzo", options=DEFAULT_VEHICLE_TYPES),
            "Ore": st.column_config.NumberColumn("Ore", min_value=0.0, step=0.25, format="%.2f"),
        },
        key="vehicle_editor",
    )

    vehicle_calc = edited_vehicles.copy()
    vehicle_calc["Costo Orario"] = 0.0
    vehicle_calc["Costo Totale"] = 0.0
    for idx, row in vehicle_calc.iterrows():
        vtype = str(row.get("Tipo", "")).strip()
        rate = vehicle_rate(tariffs, vtype)
        vehicle_calc.loc[idx, "Costo Orario"] = rate
        vehicle_calc.loc[idx, "Costo Totale"] = parse_hours(row.get("Ore", 0)) * rate

    vehicle_cost = float(vehicle_calc["Costo Totale"].sum())
    vehicle_hours = float(vehicle_calc["Ore"].apply(parse_hours).sum())

    # ---------------- ECONOMIA ----------------
    st.markdown('<div class="section-title">4 · Risultato economico</div>', unsafe_allow_html=True)
    overhead = (labor_cost + vehicle_cost) * overhead_rate(tariffs) / 100
    total_cost = labor_cost + vehicle_cost + overhead
    margin = revenue - total_cost
    margin_pct = (margin / revenue * 100) if revenue else 0

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "Personale", euro(labor_cost)),
        (c2, "Mezzi", euro(vehicle_cost)),
        (c3, "Overhead", euro(overhead)),
        (c4, "Margine", euro(margin)),
    ]:
        with col:
            st.markdown(f'<div class="info-card"><div class="info-title">{label}</div><div class="info-value">{value}</div></div>', unsafe_allow_html=True)

    if margin > 0:
        st.markdown('<span class="badge-ok">MARGINE POSITIVO</span>', unsafe_allow_html=True)
    elif margin < 0:
        st.markdown('<span class="badge-danger">MARGINE NEGATIVO</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-warn">PAREGGIO</span>', unsafe_allow_html=True)

    notes = st.text_area("Note", placeholder="Annotazioni operative, anomalie, scostamenti...")

    st.markdown('<div class="section-title">5 · Salva consuntivo</div>', unsafe_allow_html=True)
    if st.button("Salva consuntivo", type="primary", use_container_width=True):
        if not selected_subservice:
            st.error("Sottoservizio obbligatorio.")
            st.stop()

        cid = "CC-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        service_row = pd.DataFrame([{
            "ID": cid,
            "Data": pd.Timestamp(service_date),
            "Servizio": selected_service,
            "Sottoservizio": selected_subservice,
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
        save_csv(pd.concat([services, service_row], ignore_index=True), FILES["services"])

        pdetail = personnel_calc.copy()
        pdetail["ID Consuntivo"] = cid
        pdetail["Data"] = pd.Timestamp(service_date)
        pdetail["Servizio"] = selected_service
        pdetail["Sottoservizio"] = selected_subservice
        pdetail = pdetail.rename(columns={"Operatore":"Operatore"})
        pdetail = pdetail[["ID Consuntivo","Data","Servizio","Sottoservizio","Matricola","Operatore","Contratto","Livello","Ore","Costo Orario","Costo Totale"]]
        old_p = read_personnel()
        save_csv(pd.concat([old_p, pdetail], ignore_index=True), FILES["personnel"])

        vdetail = vehicle_calc.copy()
        vdetail["ID Consuntivo"] = cid
        vdetail["Data"] = pd.Timestamp(service_date)
        vdetail["Servizio"] = selected_service
        vdetail["Sottoservizio"] = selected_subservice
        vdetail = vdetail[["ID Consuntivo","Data","Servizio","Sottoservizio","Targa","Mezzo","Tipo","Ore","Costo Orario","Costo Totale"]]
        old_v = read_vehicle_detail()
        save_csv(pd.concat([old_v, vdetail], ignore_index=True), FILES["vehicle_detail"])

        st.success(f"Consuntivo {cid} salvato.")

# ============================================================
# ECONOMICO
# ============================================================

elif page == "Economico":
    df = authorized_services(services)
    st.markdown('<div class="section-title">Analisi per servizio e sottoservizio</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("Non ci sono consuntivi disponibili.")
    else:
        summary = df.groupby(["Servizio", "Sottoservizio"]).agg(
            Ricavi=("Ricavi", "sum"),
            Costi=("Costo Totale", "sum"),
            Margine=("Margine", "sum"),
            Tonnellate=("Tonnellate", "sum"),
        ).reset_index()
        summary["Margine %"] = np.where(summary["Ricavi"] != 0, summary["Margine"] / summary["Ricavi"] * 100, 0)
        st.dataframe(summary, use_container_width=True, hide_index=True)
        st.markdown('<div class="section-title">Costo del personale</div>', unsafe_allow_html=True)
        p = authorized_services(personnel_detail, "Sottoservizio")
        if not p.empty:
            by_contract = p.groupby(["Contratto", "Livello"])["Costo Totale"].sum().sort_values(ascending=False)
            st.bar_chart(by_contract)
        st.markdown('<div class="section-title">Costo mezzi</div>', unsafe_allow_html=True)
        v = authorized_services(vehicle_detail, "Sottoservizio")
        if not v.empty:
            by_vehicle = v.groupby("Tipo")["Costo Totale"].sum().sort_values(ascending=False)
            st.bar_chart(by_vehicle)

# ============================================================
# ANAGRAFICHE
# ============================================================

elif page == "Anagrafiche":
    if not is_admin():
        st.error("Sezione riservata alla Direzione.")
        st.stop()
    tab1, tab2 = st.tabs(["Operatori", "Mezzi"])
    with tab1:
        st.markdown('<div class="section-title">Operatori</div>', unsafe_allow_html=True)
        edited = st.data_editor(operators, num_rows="dynamic", use_container_width=True, hide_index=True)
        st.info("Per ogni operatore imposta Contratto e Livello. Il costo orario verrà poi letto dal tariffario.")
        if st.button("Salva operatori", type="primary"):
            save_csv(edited, FILES["operators"])
            st.success("Operatori salvati.")
            st.rerun()
    with tab2:
        st.markdown('<div class="section-title">Mezzi</div>', unsafe_allow_html=True)
        edited = st.data_editor(vehicles, num_rows="dynamic", use_container_width=True, hide_index=True)
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

    st.markdown("""<div class=\"hero\"><div class=\"hero-kicker\">Regola contabile</div><div class=\"hero-title\">Livello contrattuale ≠ costo aziendale</div><div class=\"hero-copy\">Il contratto determina l'inquadramento. Il costo orario usato dal centro di costo viene impostato dall'azienda.</div></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Personale", "Mezzi", "Struttura"])
    with tab1:
        ptab = tariffs[tariffs["Tipo"].astype(str).str.lower() == "personale"].copy()
        edit_p = st.data_editor(ptab, num_rows="dynamic", use_container_width=True, hide_index=True, key="tariff_personale")
        if st.button("Salva costi personale", type="primary"):
            other = tariffs[tariffs["Tipo"].astype(str).str.lower() != "personale"]
            save_csv(pd.concat([other, edit_p], ignore_index=True), FILES["tariffs"])
            st.success("Tariffe personale salvate.")
            st.rerun()
    with tab2:
        vtab = tariffs[tariffs["Tipo"].astype(str).str.lower() == "mezzo"].copy()
        edit_v = st.data_editor(vtab, num_rows="dynamic", use_container_width=True, hide_index=True, key="tariff_mezzi")
        if st.button("Salva costi mezzi", type="primary"):
            other = tariffs[tariffs["Tipo"].astype(str).str.lower() != "mezzo"]
            save_csv(pd.concat([other, edit_v], ignore_index=True), FILES["tariffs"])
            st.success("Tariffe mezzi salvate.")
            st.rerun()
    with tab3:
        gtab = tariffs[tariffs["Tipo"].astype(str).str.lower() == "generale"].copy()
        edit_g = st.data_editor(gtab, num_rows="dynamic", use_container_width=True, hide_index=True, key="tariff_generale")
        if st.button("Salva struttura costi", type="primary"):
            other = tariffs[tariffs["Tipo"].astype(str).str.lower() != "generale"]
            save_csv(pd.concat([other, edit_g], ignore_index=True), FILES["tariffs"])
            st.success("Struttura costi salvata.")
            st.rerun()

    st.markdown('<div class="section-title">Livelli disponibili</div>', unsafe_allow_html=True)
    st.write("**Servizi Ambientali - Utilitalia:** " + ", ".join(UTILITALIA_LEVELS))
    st.write("**Cooperative Sociali:** " + ", ".join(COOPERATIVE_SOCIALI_LEVELS))

# ============================================================
# ACCESSI
# ============================================================

elif page == "Accessi":
    if not is_admin():
        st.error("Sezione riservata alla Direzione.")
        st.stop()
    st.markdown('<div class="section-title">Utenti e autorizzazioni</div>', unsafe_allow_html=True)
    edit_users = st.data_editor(users, num_rows="dynamic", use_container_width=True, hide_index=True)
    st.caption("Le autorizzazioni sono i sottoservizi operativi: separali con virgola. Usa TUTTI per la Direzione.")
    if st.button("Salva accessi", type="primary"):
        save_csv(edit_users, FILES["users"])
        st.success("Accessi salvati.")
        st.rerun()

# ============================================================
# FOOTER
# ============================================================

st.markdown("""
<div style="text-align:center;color:#8a938d;font-size:11px;padding:35px 0 5px;">
Cristoforo · Control Room V3 · Servizi · Sottoservizi · Certificazione Ore · Centro di Costo
</div>
""", unsafe_allow_html=True)
