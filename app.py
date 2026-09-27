import os
import io
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURAZIONE PAGINA
# ============================================================

st.set_page_config(
    page_title="Control Room | Cristoforo",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# FILE
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UTENTI_FILE = os.path.join(BASE_DIR, "utenti_cristoforo.csv")
ORE_FILE = os.path.join(BASE_DIR, "storico_ore_cristoforo.csv")
OPERATORI_FILE = os.path.join(BASE_DIR, "anagrafica_operatori.csv")
MEZZI_FILE = os.path.join(BASE_DIR, "anagrafica_mezzi.csv")
SERVIZI_FILE = os.path.join(BASE_DIR, "storico_servizi_v9.csv")
TARIFFE_FILE = os.path.join(BASE_DIR, "tariffe_cristoforo.csv")


# ============================================================
# COMMESSE E SERVIZI
# ============================================================

# La seconda colonna della struttura fornita viene trattata
# come COMMESSA.
COMMESSE_STANDARD = [
    "Scandicci",
    "Piana",
    "Prato",
    "Vaiano",
    "Campi",
    "Noventa",
    "Costabissara",
    "Cremona",
    "Mantova",
    "Lucca",
    "Alia",
    "Firenze",
    "Campi Bisenzio",
    "Valdisieve",
    "Mugello",
]

# La prima colonna viene trattata come SERVIZIO.
SERVIZI_PER_COMMESSA = {
    "Scandicci": [
        "Spazzamenti",
    ],
    "Piana": [
        "Aree Verdi",
        "Raccolta Cartone Selettivo",
    ],
    "Prato": [
        "Aree Verdi",
        "Porta a Porta",
        "Raccolta Cartone Selettivo",
        "Ingombranti",
    ],
    "Vaiano": [
        "Porta a Porta",
    ],
    "Campi": [
        "Porta a Porta",
        "Raccolta Cartone Selettivo",
    ],
    "Noventa": [
        "Porta a Porta",
    ],
    "Costabissara": [
        "Porta a Porta",
    ],
    "Cremona": [
        "Porta a Porta",
    ],
    "Mantova": [
        "Porta a Porta",
    ],
    "Lucca": [
        "Porta a Porta",
    ],
    "Alia": [
        "Trasporti",
    ],
    "Firenze": [
        "Raccolta Cartone Selettivo",
    ],
    "Campi Bisenzio": [
        "Ingombranti",
    ],
    "Valdisieve": [
        "Ingombranti",
    ],
    "Mugello": [
        "Ingombranti",
    ],
}


# ============================================================
# ALIAS LEGACY
# ============================================================

# Permette di continuare a leggere i vecchi CSV.
COMMESSA_LEGACY_MAP = {
    "RACCOLTA PAP PRATO": "Prato",
    "RACCOLTA PAP MANTOVA": "Mantova",
    "RACCOLTA PAP CAMPI": "Campi",
    "RACCOLTA PAP VAIANO": "Vaiano",
    "RACCOLTA PAP NOVENTA": "Noventa",
    "RACCOLTA PAP COSTABISSARA": "Costabissara",
    "RACCOLTA PAP CREMONA": "Cremona",
    "RACCOLTA PAP LUCCA": "Lucca",
}

SERVIZIO_LEGACY_MAP = {
    "Raccolta Porta a Porta": "Porta a Porta",
    "Raccolta PAP": "Porta a Porta",
    "Spazzamento Stradale": "Spazzamenti",
    "Spazzamento": "Spazzamenti",
    "Aree verdi": "Aree Verdi",
    "Ritiro Ingombranti": "Ingombranti",
    "Movimentazione Scarrabili": "Trasporti",
    "Raccolta Cartone": "Raccolta Cartone Selettivo",
}


# ============================================================
# UTENTI DEFAULT
# ============================================================

DEFAULT_USERS = pd.DataFrame(
    [
        {
            "username": "direzione",
            "password": "admin",
            "nome": "Direzione",
            "ruolo": "admin",
            "cantieri": "TUTTI",
        },
        {
            "username": "resp_prato",
            "password": "123",
            "nome": "Responsabile Prato",
            "ruolo": "capocantiere",
            "cantieri": "Prato",
        },
        {
            "username": "resp_mantova",
            "password": "456",
            "nome": "Responsabile Mantova",
            "ruolo": "capocantiere",
            "cantieri": "Mantova",
        },
    ]
)


DEFAULT_TARIFFE = pd.DataFrame(
    [
        {"Categoria": "Personale", "Voce": "L1", "Costo": 22.0},
        {"Categoria": "Personale", "Voce": "L2", "Costo": 25.0},
        {"Categoria": "Personale", "Voce": "L3", "Costo": 28.0},
        {"Categoria": "Personale", "Voce": "L4", "Costo": 32.0},
        {"Categoria": "Mezzi", "Voce": "Leggero", "Costo": 15.0},
        {"Categoria": "Mezzi", "Voce": "Compattatore", "Costo": 25.0},
        {"Categoria": "Mezzi", "Voce": "Pesante", "Costo": 45.0},
        {"Categoria": "Mezzi", "Voce": "Speciale", "Costo": 65.0},
        {"Categoria": "Generale", "Voce": "Overhead", "Costo": 15.0},
        {"Categoria": "Generale", "Voce": "Tariffa tonnellata", "Costo": 130.0},
    ]
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

:root {
    --green: #008b3a;
    --green-dark: #006f2f;
    --green-light: #e9f7ef;
    --bg: #f4f6f8;
    --card: #ffffff;
    --text: #17202a;
    --muted: #6b7280;
    --border: #e5e7eb;
}

html, body, [class*="css"] {
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI",
                 Roboto, Helvetica, Arial, sans-serif;
}

.stApp {
    background: var(--bg);
}

.block-container {
    padding-top: 1.3rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

section[data-testid="stSidebar"] {
    background: #101714;
    border-right: 1px solid #1f2924;
}

section[data-testid="stSidebar"] * {
    color: #e9f2ed;
}

.sidebar-brand {
    padding: 12px 8px 25px 8px;
}

.sidebar-logo {
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -1px;
}

.sidebar-subtitle {
    color: #91a39a !important;
    font-size: 12px;
    margin-top: 2px;
}

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 15px 20px;
    margin-bottom: 18px;
    box-shadow: 0 3px 15px rgba(15, 23, 42, 0.04);
}

.page-title {
    font-size: 27px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.7px;
}

.page-subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-top: 3px;
}

.user-pill {
    background: #eef7f1;
    color: var(--green-dark);
    padding: 8px 13px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
}

.hero {
    background: linear-gradient(135deg, #ffffff 0%, #eef8f2 100%);
    border: 1px solid #dcebe1;
    border-radius: 22px;
    padding: 23px 26px;
    margin-bottom: 20px;
}

.hero-label {
    color: var(--green-dark);
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.hero-title {
    color: #132019;
    font-size: 30px;
    font-weight: 850;
    margin-top: 5px;
}

.hero-detail {
    color: #68756e;
    margin-top: 5px;
}

.kpi {
    background: white;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 18px;
    min-height: 125px;
    box-shadow: 0 3px 14px rgba(15, 23, 42, 0.035);
}

.kpi-label {
    color: #7b8490;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .5px;
}

.kpi-value {
    color: #111827;
    font-size: 29px;
    font-weight: 850;
    margin-top: 8px;
}

.kpi-note {
    color: #8a929d;
    font-size: 12px;
    margin-top: 5px;
}

.section-title {
    font-size: 18px;
    font-weight: 800;
    color: #18221d;
    margin: 24px 0 10px 0;
}

.status-ok {
    display: inline-block;
    background: #e7f7ed;
    color: #087a36;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
}

.status-warning {
    display: inline-block;
    background: #fff6df;
    color: #9a6a00;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
}

.status-critical {
    display: inline-block;
    background: #fdeaea;
    color: #b42318;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
}

.info-card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 12px;
}

.info-title {
    font-size: 14px;
    font-weight: 800;
    color: #202b25;
}

.info-value {
    font-size: 24px;
    font-weight: 850;
    margin-top: 6px;
}

.login-box {
    max-width: 430px;
    margin: 8vh auto;
    background: white;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 35px;
    box-shadow: 0 15px 50px rgba(15, 23, 42, .08);
}

.login-logo {
    text-align: center;
    font-size: 38px;
    font-weight: 900;
    color: var(--green);
}

.login-sub {
    text-align: center;
    color: var(--muted);
    margin-bottom: 25px;
}

div.stButton > button {
    border-radius: 11px;
    font-weight: 700;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid var(--border);
    padding: 12px;
    border-radius: 14px;
}

footer {
    visibility: hidden;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FUNZIONI GENERALI CSV
# ============================================================

def clean_col_name(value):
    """Normalizza il nome di una colonna."""

    if value is None:
        return ""

    value = str(value)
    value = value.replace("\ufeff", "")
    value = value.strip().lower()

    replacements = {
        "à": "a",
        "è": "e",
        "é": "e",
        "ì": "i",
        "ò": "o",
        "ù": "u",
        "€": "euro",
        "/": "_",
        "-": "_",
        " ": "_",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"_+", "_", value)

    return value.strip("_")


def normalize_columns(df):
    """Normalizza tutte le colonne."""

    if df is None:
        return pd.DataFrame()

    df = df.copy()

    new_columns = []
    for col in df.columns:
        new_columns.append(clean_col_name(col))

    df.columns = new_columns

    return df


def flexible_read_csv(path):
    """
    Legge CSV con:
    - ;
    - ,
    - tab
    - utf-8
    - utf-8-sig
    - latin1
    """

    if not os.path.exists(path):
        return pd.DataFrame()

    encodings = ["utf-8-sig", "utf-8", "latin1"]

    for encoding in encodings:
        try:
            df = pd.read_csv(
                path,
                sep=None,
                engine="python",
                encoding=encoding,
                dtype=str,
                keep_default_na=False,
            )

            if len(df.columns) > 1:
                return normalize_columns(df)

        except Exception:
            pass

    # Ultimo tentativo con ;
    try:
        df = pd.read_csv(
            path,
            sep=";",
            encoding="latin1",
            dtype=str,
            keep_default_na=False,
        )
        return normalize_columns(df)
    except Exception:
        return pd.DataFrame()


def safe_to_csv(df, path):
    try:
        df.to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
        )
        return True
    except Exception as exc:
        st.error(f"Impossibile salvare {os.path.basename(path)}: {exc}")
        return False


def first_existing_column(df, candidates):
    if df is None or df.empty:
        return None

    normalized = {
        clean_col_name(c): c
        for c in df.columns
    }

    for candidate in candidates:
        key = clean_col_name(candidate)

        if key in normalized:
            return normalized[key]

    return None


def rename_using_aliases(df, aliases):
    """
    aliases:
        {"colonna_standard": ["alias1", "alias2"]}
    """

    df = normalize_columns(df)

    rename_map = {}

    for standard, possible_names in aliases.items():

        candidates = [standard] + possible_names

        found = first_existing_column(df, candidates)

        if found and found != standard:
            rename_map[found] = standard

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def ensure_columns(df, columns):
    df = df.copy()

    for col in columns:
        if col not in df.columns:
            df[col] = ""

    return df


# ============================================================
# CONVERSIONI
# ============================================================

def parse_number(value):
    if value is None:
        return 0.0

    if isinstance(value, (int, float, np.integer, np.floating)):
        if pd.isna(value):
            return 0.0
        return float(value)

    text = str(value).strip()

    if text == "":
        return 0.0

    text = (
        text.replace("€", "")
        .replace("EUR", "")
        .replace("eur", "")
        .replace(" ", "")
    )

    # 1.234,56
    if "." in text and "," in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")

    # 1234,56
    elif "," in text:
        text = text.replace(",", ".")

    # 1.234 -> può essere mille duecentotrentaquattro
    elif text.count(".") == 1:
        parts = text.split(".")

        if len(parts[-1]) == 3:
            text = text.replace(".", "")

    try:
        return float(text)
    except Exception:
        return 0.0


def parse_hours(value):
    if value is None:
        return 0.0

    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)

        # Excel time fraction
        if 0 < number < 1:
            return number * 24

        return number

    text = str(value).strip()

    if not text:
        return 0.0

    # HH:MM
    if ":" in text:
        try:
            parts = text.split(":")

            hours = float(parts[0])
            minutes = float(parts[1])

            return hours + minutes / 60
        except Exception:
            pass

    return parse_number(text)


def parse_date(value):
    if value is None or str(value).strip() == "":
        return pd.NaT

    try:
        return pd.to_datetime(
            value,
            dayfirst=True,
            errors="coerce",
        )
    except Exception:
        return pd.NaT


def euro(value):
    return f"€ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def number_it(value, decimals=1):
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def hours_text(value):
    return f"{float(value):.1f} h".replace(".", ",")


def pct(value):
    return f"{float(value):.1f}%".replace(".", ",")


# ============================================================
# CANONICALIZZAZIONE COMMESSE
# ============================================================

def canonical_commessa(value):
    if value is None:
        return ""

    text = str(value).strip()

    if text in COMMESSE_STANDARD:
        return text

    upper = text.upper()

    if upper in COMMESSA_LEGACY_MAP:
        return COMMESSA_LEGACY_MAP[upper]

    return text


def canonical_servizio(value):
    if value is None:
        return ""

    text = str(value).strip()

    if text in {
        "Spazzamenti",
        "Aree Verdi",
        "Porta a Porta",
        "Trasporti",
        "Raccolta Cartone Selettivo",
        "Ingombranti",
    }:
        return text

    if text in SERVIZIO_LEGACY_MAP:
        return SERVIZIO_LEGACY_MAP[text]

    return text


# ============================================================
# FILE INIZIALI
# ============================================================

def ensure_files():

    if not os.path.exists(UTENTI_FILE):
        safe_to_csv(DEFAULT_USERS, UTENTI_FILE)

    if not os.path.exists(TARIFFE_FILE):
        safe_to_csv(DEFAULT_TARIFFE, TARIFFE_FILE)

    if not os.path.exists(SERVIZI_FILE):
        empty = pd.DataFrame(
            columns=[
                "ID",
                "Data",
                "Commessa",
                "Servizio",
                "Dettaglio",
                "Tonnellate",
                "Ricavo",
                "Costo",
                "Margine",
                "Ore Personale",
                "Ore Mezzi",
                "Operatore",
                "Note",
            ]
        )
        safe_to_csv(empty, SERVIZI_FILE)

    if not os.path.exists(ORE_FILE):
        empty = pd.DataFrame()
        safe_to_csv(empty, ORE_FILE)

    if not os.path.exists(OPERATORI_FILE):
        empty = pd.DataFrame()
        safe_to_csv(empty, OPERATORI_FILE)

    if not os.path.exists(MEZZI_FILE):
        empty = pd.DataFrame()
        safe_to_csv(empty, MEZZI_FILE)


ensure_files()


# ============================================================
# LETTURA UTENTI
# ============================================================

def read_users():

    df = flexible_read_csv(UTENTI_FILE)

    aliases = {
        "username": [
            "user",
            "utente",
            "login",
            "nome_utente",
        ],
        "password": [
            "pass",
            "pwd",
        ],
        "nome": [
            "name",
            "nominativo",
            "nome_completo",
        ],
        "ruolo": [
            "role",
            "profilo",
        ],
        "cantieri": [
            "commesse",
            "cantiere",
            "cantiere_assegnato",
            "autorizzazioni",
        ],
    }

    df = rename_using_aliases(df, aliases)

    required = [
        "username",
        "password",
        "nome",
        "ruolo",
        "cantieri",
    ]

    # Se il CSV è completamente inutilizzabile,
    # usiamo i default senza distruggere il file originale.
    if df.empty or not all(col in df.columns for col in required):

        st.warning(
            "Il file utenti_cristoforo.csv non ha una struttura riconoscibile. "
            "Sono stati caricati temporaneamente gli utenti di default."
        )

        df = DEFAULT_USERS.copy()

    df = ensure_columns(df, required)

    for col in required:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("\ufeff", "", regex=False)
            .str.strip()
        )

    return df[required].copy()


# ============================================================
# LETTURA TARIFFE
# ============================================================

def read_tariffe():

    df = flexible_read_csv(TARIFFE_FILE)

    aliases = {
        "Categoria": [
            "categoria_costo",
            "tipo",
        ],
        "Voce": [
            "voce_costo",
            "livello",
            "tipo_mezzo",
        ],
        "Costo": [
            "costo_orario",
            "valore",
            "prezzo",
            "tariffa",
        ],
    }

    df = rename_using_aliases(df, aliases)

    required = [
        "Categoria",
        "Voce",
        "Costo",
    ]

    if df.empty or not all(col in df.columns for col in required):
        df = DEFAULT_TARIFFE.copy()

    df = ensure_columns(df, required)

    df["Categoria"] = df["Categoria"].astype(str).str.strip()
    df["Voce"] = df["Voce"].astype(str).str.strip()
    df["Costo"] = df["Costo"].apply(parse_number)

    return df[required].copy()


def tariff(tariffe, categoria, voce, default=0):

    if tariffe is None or tariffe.empty:
        return default

    mask = (
        tariffe["Categoria"].astype(str).str.strip().str.lower()
        == str(categoria).strip().lower()
    ) & (
        tariffe["Voce"].astype(str).str.strip().str.lower()
        == str(voce).strip().lower()
    )

    result = tariffe.loc[mask, "Costo"]

    if result.empty:
        return default

    return float(result.iloc[0])


# ============================================================
# LETTURA SERVIZI
# ============================================================

def read_services():

    df = flexible_read_csv(SERVIZI_FILE)

    aliases = {
        "ID": [
            "id_servizio",
            "id_record",
            "codice",
        ],
        "Data": [
            "data_servizio",
            "giorno",
            "date",
        ],
        "Commessa": [
            "Cantiere",
            "cantiere",
            "commessa",
            "commessa_operativa",
            "worksite",
        ],
        "Servizio": [
            "Categoria",
            "categoria",
            "tipo_servizio",
            "servizio",
        ],
        "Dettaglio": [
            "dettaglio_operativo",
            "descrizione",
            "note_servizio",
        ],
        "Tonnellate": [
            "ton",
            "tonnellaggio",
            "quantita_tonnellate",
        ],
        "Ricavo": [
            "ricavi",
            "revenue",
            "fatturato",
            "ricavo_euro",
        ],
        "Costo": [
            "costi",
            "costo_totale",
            "costo_euro",
        ],
        "Margine": [
            "margine_netto",
            "margine_euro",
            "profitto",
        ],
        "Ore Personale": [
            "ore_personale",
            "ore_lavorate",
            "ore_operatori",
        ],
        "Ore Mezzi": [
            "ore_mezzi",
            "ore_veicoli",
            "ore_macchine",
        ],
        "Operatore": [
            "operatore",
            "addetto",
            "responsabile",
        ],
        "Note": [
            "note",
            "commenti",
        ],
    }

    df = rename_using_aliases(df, aliases)

    required = [
        "ID",
        "Data",
        "Commessa",
        "Servizio",
        "Dettaglio",
        "Tonnellate",
        "Ricavo",
        "Costo",
        "Margine",
        "Ore Personale",
        "Ore Mezzi",
        "Operatore",
        "Note",
    ]

    df = ensure_columns(df, required)

    if df.empty:
        return pd.DataFrame(columns=required)

    # Pulizia stringhe
    for col in [
        "ID",
        "Commessa",
        "Servizio",
        "Dettaglio",
        "Operatore",
        "Note",
    ]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("\ufeff", "", regex=False)
            .str.strip()
        )

    # Compatibilità con dati vecchi
    df["Commessa"] = df["Commessa"].apply(canonical_commessa)
    df["Servizio"] = df["Servizio"].apply(canonical_servizio)

    # Numeri
    for col in [
        "Tonnellate",
        "Ricavo",
        "Costo",
        "Margine",
    ]:
        df[col] = df[col].apply(parse_number)

    # Ore
    df["Ore Personale"] = df["Ore Personale"].apply(parse_hours)
    df["Ore Mezzi"] = df["Ore Mezzi"].apply(parse_hours)

    # Date
    df["Data"] = df["Data"].apply(parse_date)

    # Se il margine non esiste o è zero, lo ricostruiamo.
    mask_margin = (
        (df["Margine"] == 0)
        & ((df["Ricavo"] != 0) | (df["Costo"] != 0))
    )

    df.loc[mask_margin, "Margine"] = (
        df.loc[mask_margin, "Ricavo"]
        - df.loc[mask_margin, "Costo"]
    )

    # ID automatico per record privi di ID
    missing_id = df["ID"].astype(str).str.strip().isin(["", "nan", "None"])

    if missing_id.any():
        for idx in df.index[missing_id]:
            df.loc[idx, "ID"] = (
                f"S-{idx}-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
            )

    return df[required].copy()


# ============================================================
# LETTURA ORE
# ============================================================

def read_hours():

    df = flexible_read_csv(ORE_FILE)

    if df.empty:
        return pd.DataFrame()

    aliases = {
        "Data": ["data_turno", "giorno", "date"],
        "Operatore": ["operatore", "dipendente", "addetto"],
        "Commessa": ["Cantiere", "cantiere", "commessa"],
        "Ore": ["ore_lavorate", "ore_totali", "hours"],
        "Straordinario": ["ore_extra", "extra", "straordinari"],
    }

    df = rename_using_aliases(df, aliases)

    for col in [
        "Data",
        "Operatore",
        "Commessa",
        "Ore",
        "Straordinario",
    ]:
        if col not in df.columns:
            df[col] = ""

    df["Data"] = df["Data"].apply(parse_date)
    df["Ore"] = df["Ore"].apply(parse_hours)
    df["Straordinario"] = df["Straordinario"].apply(parse_hours)

    df["Commessa"] = df["Commessa"].apply(canonical_commessa)

    return df


# ============================================================
# ANAGRAFICA OPERATORI
# ============================================================

def read_operators():

    df = flexible_read_csv(OPERATORI_FILE)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Matricola",
                "Nome",
                "Cognome",
                "Livello",
                "Commessa",
            ]
        )

    aliases = {
        "Matricola": ["matricola", "id_operatore", "codice"],
        "Nome": ["nome", "first_name"],
        "Cognome": ["cognome", "last_name"],
        "Livello": ["livello", "qualifica", "level"],
        "Commessa": ["cantiere", "commessa"],
    }

    df = rename_using_aliases(df, aliases)

    required = [
        "Matricola",
        "Nome",
        "Cognome",
        "Livello",
        "Commessa",
    ]

    df = ensure_columns(df, required)

    df["Commessa"] = df["Commessa"].apply(canonical_commessa)

    return df[required].copy()


# ============================================================
# ANAGRAFICA MEZZI
# ============================================================

def read_vehicles():

    df = flexible_read_csv(MEZZI_FILE)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Targa",
                "Mezzo",
                "Categoria",
                "Commessa",
            ]
        )

    aliases = {
        "Targa": ["targa", "plate"],
        "Mezzo": ["mezzo", "descrizione", "veicolo"],
        "Categoria": ["categoria", "tipo", "classe"],
        "Commessa": ["cantiere", "commessa"],
    }

    df = rename_using_aliases(df, aliases)

    required = [
        "Targa",
        "Mezzo",
        "Categoria",
        "Commessa",
    ]

    df = ensure_columns(df, required)

    df["Commessa"] = df["Commessa"].apply(canonical_commessa)

    return df[required].copy()


# ============================================================
# AUTORIZZAZIONI
# ============================================================

def authorized_commesse(user_row):

    if user_row.empty:
        return []

    raw = str(user_row.iloc[0]["cantieri"]).strip()

    if raw.upper() in [
        "TUTTI",
        "ALL",
        "*",
    ]:
        return COMMESSE_STANDARD.copy()

    values = re.split(r"[,;|]", raw)

    result = []

    for value in values:
        value = value.strip()

        if not value:
            continue

        canonical = canonical_commessa(value)

        if canonical in COMMESSE_STANDARD:
            result.append(canonical)

    return sorted(
        list(set(result)),
        key=lambda x: COMMESSE_STANDARD.index(x),
    )


def is_admin():
    return (
        st.session_state.get("ruolo", "").lower()
        in ["admin", "direzione"]
    )


def filter_authorized(df, column="Commessa"):

    if df is None or df.empty:
        return df

    if is_admin():
        return df.copy()

    allowed = st.session_state.get(
        "commesse_autorizzate",
        [],
    )

    if not allowed:
        return df.iloc[0:0].copy()

    result = df.copy()

    result["_commessa_check"] = (
        result[column]
        .astype(str)
        .apply(canonical_commessa)
    )

    result = result[
        result["_commessa_check"].isin(allowed)
    ].copy()

    result.drop(
        columns=["_commessa_check"],
        inplace=True,
        errors="ignore",
    )

    return result


# ============================================================
# SALVATAGGIO SERVIZI
# ============================================================

def save_services(df):

    # Manteniamo sempre le colonne principali.
    required = [
        "ID",
        "Data",
        "Commessa",
        "Servizio",
        "Dettaglio",
        "Tonnellate",
        "Ricavo",
        "Costo",
        "Margine",
        "Ore Personale",
        "Ore Mezzi",
        "Operatore",
        "Note",
    ]

    df = ensure_columns(df, required)

    # Date in formato leggibile
    save_df = df.copy()

    save_df["Data"] = pd.to_datetime(
        save_df["Data"],
        errors="coerce",
    ).dt.strftime("%d/%m/%Y")

    safe_to_csv(
        save_df[required],
        SERVIZI_FILE,
    )


def append_service(record):

    current = read_services()

    new_row = pd.DataFrame([record])

    combined = pd.concat(
        [current, new_row],
        ignore_index=True,
    )

    # ID unico
    combined["ID"] = combined["ID"].astype(str)

    combined = combined.drop_duplicates(
        subset=["ID"],
        keep="last",
    )

    save_services(combined)


# ============================================================
# SESSION STATE
# ============================================================

if "loggato" not in st.session_state:
    st.session_state.loggato = False

if "utente" not in st.session_state:
    st.session_state.utente = ""

if "nome" not in st.session_state:
    st.session_state.nome = ""

if "ruolo" not in st.session_state:
    st.session_state.ruolo = ""

if "commesse_autorizzate" not in st.session_state:
    st.session_state.commesse_autorizzate = []


# ============================================================
# LOGIN
# ============================================================

if not st.session_state.loggato:

    st.markdown(
        """
        <div class="login-box">
            <div class="login-logo">CRISTOFORO</div>
            <div class="login-sub">
                Control Room · Centro di Costo
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        username = st.text_input(
            "Username",
            placeholder="Inserisci username",
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Inserisci password",
        )

        if st.button(
            "Accedi alla Control Room",
            use_container_width=True,
            type="primary",
        ):

            users = read_users()

            username_clean = str(username).strip()
            password_clean = str(password).strip()

            match = users[
                (
                    users["username"]
                    .astype(str)
                    .str.strip()
                    == username_clean
                )
                &
                (
                    users["password"]
                    .astype(str)
                    .str.strip()
                    == password_clean
                )
            ]

            if not match.empty:

                row = match.iloc[0]

                st.session_state.loggato = True
                st.session_state.utente = username_clean
                st.session_state.nome = str(row["nome"]).strip()
                st.session_state.ruolo = str(row["ruolo"]).strip()
                st.session_state.commesse_autorizzate = authorized_commesse(
                    match
                )

                st.rerun()

            else:
                st.error("Username o password non corretti.")

    st.stop()


# ============================================================
# DATI GLOBALI
# ============================================================

users = read_users()
services = read_services()
hours = read_hours()
operators = read_operators()
vehicles = read_vehicles()
tariffe = read_tariffe()

services_auth = filter_authorized(services)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-logo">♻️ CRISTOFORO</div>
            <div class="sidebar-subtitle">
                Control Room · Centro di Costo
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    menu_items = [
        "Overview",
        "Commesse",
        "Validazione Turni",
        "Ore",
        "Centro di Costo",
        "Mezzi",
        "Report",
    ]

    if is_admin():
        menu_items += [
            "Anagrafiche",
            "Gestione Accessi",
        ]

    menu = st.radio(
        "Navigazione",
        menu_items,
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.caption(
        f"👤 {st.session_state.nome}"
    )

    st.caption(
        f"Ruolo: {st.session_state.ruolo}"
    )

    st.caption(
        f"Commesse: {len(st.session_state.commesse_autorizzate)}"
    )

    if st.button(
        "Esci",
        use_container_width=True,
    ):
        for key in [
            "loggato",
            "utente",
            "nome",
            "ruolo",
            "commesse_autorizzate",
        ]:
            st.session_state.pop(key, None)

        st.rerun()


# ============================================================
# HEADER
# ============================================================

titles = {
    "Overview": (
        "Control Room",
        "Vista direzionale delle performance operative ed economiche",
    ),
    "Commesse": (
        "Commesse",
        "Controllo economico per singola commessa",
    ),
    "Validazione Turni": (
        "Validazione Turni",
        "Importazione e controllo delle ore operative",
    ),
    "Ore": (
        "Ore",
        "Analisi delle ore lavorate e delle anomalie",
    ),
    "Centro di Costo": (
        "Centro di Costo",
        "Registrazione e analisi dei costi per servizio",
    ),
    "Mezzi": (
        "Mezzi",
        "Controllo economico e operativo del parco mezzi",
    ),
    "Report": (
        "Report",
        "Esportazione dei dati per analisi e amministrazione",
    ),
    "Anagrafiche": (
        "Anagrafiche",
        "Operatori e mezzi",
    ),
    "Gestione Accessi": (
        "Gestione Accessi",
        "Utenti, ruoli e commesse autorizzate",
    ),
}

title, subtitle = titles[menu]

st.markdown(
    f"""
    <div class="topbar">
        <div>
            <div class="page-title">{title}</div>
            <div class="page-subtitle">{subtitle}</div>
        </div>
        <div class="user-pill">
            ● {st.session_state.nome}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FILTRI GLOBALI
# ============================================================

if menu in [
    "Overview",
    "Commesse",
    "Ore",
    "Mezzi",
    "Report",
]:

    col1, col2 = st.columns([2, 1])

    available_commesse = st.session_state.commesse_autorizzate

    if is_admin():
        available_commesse = COMMESSE_STANDARD.copy()

    with col1:

        selected_commessa = st.selectbox(
            "Commessa",
            ["Tutte"] + available_commesse,
        )

    with col2:

        period_options = [
            "Tutto",
            "Ultimi 7 giorni",
            "Ultimi 30 giorni",
            "Ultimi 90 giorni",
        ]

        selected_period = st.selectbox(
            "Periodo",
            period_options,
        )

else:
    selected_commessa = "Tutte"
    selected_period = "Tutto"


# ============================================================
# FUNZIONE FILTRO PERIODO
# ============================================================

def apply_period_filter(df, date_column="Data"):

    if df is None or df.empty:
        return df

    if date_column not in df.columns:
        return df

    result = df.copy()

    result[date_column] = pd.to_datetime(
        result[date_column],
        errors="coerce",
    )

    if selected_period == "Tutto":
        return result

    today = pd.Timestamp.today().normalize()

    days = {
        "Ultimi 7 giorni": 7,
        "Ultimi 30 giorni": 30,
        "Ultimi 90 giorni": 90,
    }.get(selected_period, 99999)

    start = today - pd.Timedelta(days=days)

    return result[
        result[date_column].isna()
        | (result[date_column] >= start)
    ].copy()


# ============================================================
# DATASET FILTRATO
# ============================================================

filtered_services = services_auth.copy()

if selected_commessa != "Tutte":
    filtered_services = filtered_services[
        filtered_services["Commessa"].apply(
            canonical_commessa
        )
        == selected_commessa
    ].copy()

filtered_services = apply_period_filter(
    filtered_services
)


# ============================================================
# OVERVIEW
# ============================================================

if menu == "Overview":

    if selected_commessa == "Tutte":

        hero_name = "Tutte le commesse"
        hero_detail = (
            "Vista aggregata sulle commesse a cui hai accesso"
        )

    else:

        hero_name = selected_commessa
        hero_detail = (
            f"Servizi disponibili: "
            f"{', '.join(SERVIZI_PER_COMMESSA.get(selected_commessa, []))}"
        )

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-label">Commessa selezionata</div>
            <div class="hero-title">{hero_name}</div>
            <div class="hero-detail">{hero_detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ricavi = filtered_services["Ricavo"].sum()
    costi = filtered_services["Costo"].sum()
    margine = filtered_services["Margine"].sum()
    tonnellate = filtered_services["Tonnellate"].sum()
    ore_personale = filtered_services["Ore Personale"].sum()
    ore_mezzi = filtered_services["Ore Mezzi"].sum()

    margine_pct = (
        margine / ricavi * 100
        if ricavi
        else 0
    )

    cols = st.columns(6)

    kpis = [
        ("Ricavi", euro(ricavi), "Fatturato registrato"),
        ("Costi", euro(costi), "Costi complessivi"),
        ("Margine", euro(margine), pct(margine_pct)),
        ("Tonnellate", number_it(tonnellate), "Quantità gestita"),
        ("Ore personale", hours_text(ore_personale), "Ore operative"),
        ("Ore mezzi", hours_text(ore_mezzi), "Utilizzo mezzi"),
    ]

    for col, (label, value, note) in zip(cols, kpis):

        with col:

            st.markdown(
                f"""
                <div class="kpi">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="section-title">Andamento economico</div>',
        unsafe_allow_html=True,
    )

    if not filtered_services.empty:

        trend = (
            filtered_services
            .dropna(subset=["Data"])
            .groupby("Data")[
                ["Ricavo", "Costo", "Margine"]
            ]
            .sum()
            .sort_index()
        )

        if not trend.empty:
            st.line_chart(trend)

        else:
            st.info(
                "Non ci sono date sufficienti per visualizzare il trend."
            )

    else:
        st.info("Nessun dato disponibile per i filtri selezionati.")

    st.markdown(
        '<div class="section-title">Stato economico</div>',
        unsafe_allow_html=True,
    )

    if margine > 0:
        status_html = (
            '<span class="status-ok">● MARGINE POSITIVO</span>'
        )
    elif margine == 0:
        status_html = (
            '<span class="status-warning">● PAREGGIO</span>'
        )
    else:
        status_html = (
            '<span class="status-critical">● MARGINE NEGATIVO</span>'
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f"""
            <div class="info-card">
                <div class="info-title">Margine</div>
                <div class="info-value">{euro(margine)}</div>
                {status_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:

        costo_ton = (
            costi / tonnellate
            if tonnellate
            else 0
        )

        st.markdown(
            f"""
            <div class="info-card">
                <div class="info-title">Costo / tonnellata</div>
                <div class="info-value">{euro(costo_ton)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:

        ricavo_ton = (
            ricavi / tonnellate
            if tonnellate
            else 0
        )

        st.markdown(
            f"""
            <div class="info-card">
                <div class="info-title">Ricavo / tonnellata</div>
                <div class="info-value">{euro(ricavo_ton)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# COMMESSE
# ============================================================

elif menu == "Commesse":

    st.markdown(
        '<div class="section-title">Performance per commessa</div>',
        unsafe_allow_html=True,
    )

    if services_auth.empty:

        st.info("Non ci sono dati disponibili.")

    else:

        summary = (
            services_auth
            .groupby("Commessa")
            .agg(
                Ricavi=("Ricavo", "sum"),
                Costi=("Costo", "sum"),
                Margine=("Margine", "sum"),
                Tonnellate=("Tonnellate", "sum"),
                Ore=("Ore Personale", "sum"),
            )
            .reset_index()
        )

        summary["Margine %"] = np.where(
            summary["Ricavi"] != 0,
            summary["Margine"]
            / summary["Ricavi"]
            * 100,
            0,
        )

        summary = summary[
            summary["Commessa"].isin(
                st.session_state.commesse_autorizzate
            )
            | is_admin()
        ]

        display = summary.copy()

        display["Ricavi"] = display["Ricavi"].apply(euro)
        display["Costi"] = display["Costi"].apply(euro)
        display["Margine"] = display["Margine"].apply(euro)
        display["Tonnellate"] = display["Tonnellate"].apply(
            lambda x: number_it(x)
        )
        display["Ore"] = display["Ore"].apply(
            lambda x: number_it(x)
        )
        display["Margine %"] = display["Margine %"].apply(
            lambda x: pct(x)
        )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# VALIDAZIONE TURNI
# ============================================================

elif menu == "Validazione Turni":

    st.markdown(
        '<div class="section-title">Importazione turni</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Puoi importare file CSV oppure Excel. "
        "Il sistema tenta automaticamente di riconoscere "
        "separatori e nomi delle colonne."
    )

    uploaded = st.file_uploader(
        "Carica il file dei turni",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded:

        try:

            if uploaded.name.lower().endswith(".csv"):

                raw = uploaded.getvalue()

                decoded = None

                for encoding in [
                    "utf-8-sig",
                    "utf-8",
                    "latin1",
                ]:
                    try:
                        decoded = raw.decode(encoding)
                        break
                    except Exception:
                        continue

                if decoded is None:
                    raise ValueError(
                        "Codifica CSV non riconosciuta."
                    )

                temp = io.StringIO(decoded)

                imported = pd.read_csv(
                    temp,
                    sep=None,
                    engine="python",
                )

            else:

                try:
                    imported = pd.read_excel(
                        uploaded,
                        header=0,
                    )
                except ImportError:
                    st.error(
                        "Per importare Excel devi aggiungere "
                        "`openpyxl` al requirements.txt."
                    )
                    st.stop()

            imported = normalize_columns(imported)

            st.success(
                f"File caricato: {len(imported)} righe."
            )

            st.dataframe(
                imported.head(100),
                use_container_width=True,
            )

            csv_export = imported.to_csv(
                index=False,
                encoding="utf-8-sig",
            )

            st.download_button(
                "Scarica CSV normalizzato",
                data=csv_export,
                file_name="turni_normalizzati.csv",
                mime="text/csv",
            )

        except Exception as exc:

            st.error(
                f"Errore durante l'importazione: {exc}"
            )


# ============================================================
# ORE
# ============================================================

elif menu == "Ore":

    st.markdown(
        '<div class="section-title">Cruscotto ore</div>',
        unsafe_allow_html=True,
    )

    filtered_hours = filter_authorized(hours)

    if selected_commessa != "Tutte" and not filtered_hours.empty:
        filtered_hours = filtered_hours[
            filtered_hours["Commessa"]
            .apply(canonical_commessa)
            == selected_commessa
        ]

    filtered_hours = apply_period_filter(
        filtered_hours
    )

    if filtered_hours.empty:

        st.info(
            "Non sono presenti dati sulle ore."
        )

    else:

        total_hours = filtered_hours["Ore"].sum()
        overtime = filtered_hours["Straordinario"].sum()

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Ore totali",
                hours_text(total_hours),
            )

        with c2:
            st.metric(
                "Straordinario",
                hours_text(overtime),
            )

        with c3:

            perc_extra = (
                overtime / total_hours * 100
                if total_hours
                else 0
            )

            st.metric(
                "% straordinario",
                pct(perc_extra),
            )

        if "Operatore" in filtered_hours.columns:

            by_operator = (
                filtered_hours
                .groupby("Operatore")["Ore"]
                .sum()
                .sort_values(ascending=False)
                .head(15)
            )

            st.markdown(
                '<div class="section-title">Ore per operatore</div>',
                unsafe_allow_html=True,
            )

            st.bar_chart(by_operator)

        st.dataframe(
            filtered_hours,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# CENTRO DI COSTO
# ============================================================

elif menu == "Centro di Costo":

    st.markdown(
        '<div class="section-title">Nuovo centro di costo</div>',
        unsafe_allow_html=True,
    )

    if is_admin():

        with st.expander(
            "⚙️ Configurazione tariffario",
            expanded=False,
        ):

            edited_tariffe = st.data_editor(
                tariffe,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
            )

            if st.button(
                "Salva tariffario",
                type="primary",
            ):

                edited_tariffe["Costo"] = edited_tariffe[
                    "Costo"
                ].apply(parse_number)

                safe_to_csv(
                    edited_tariffe,
                    TARIFFE_FILE,
                )

                st.success(
                    "Tariffario salvato."
                )

                st.rerun()

    st.markdown(
        '<div class="section-title">Registrazione servizio</div>',
        unsafe_allow_html=True,
    )

    allowed_commesse = st.session_state.commesse_autorizzate

    if is_admin():
        allowed_commesse = COMMESSE_STANDARD.copy()

    if not allowed_commesse:

        st.error(
            "Nessuna commessa autorizzata per questo utente."
        )
        st.stop()

    with st.form("form_centro_costo"):

        c1, c2 = st.columns(2)

        with c1:

            data_servizio = st.date_input(
                "Data servizio",
                value=datetime.today().date(),
            )

        with c2:

            commessa = st.selectbox(
                "Commessa",
                allowed_commesse,
            )

        servizi_disponibili = SERVIZI_PER_COMMESSA.get(
            commessa,
            [],
        )

        servizio = st.selectbox(
            "Servizio",
            servizi_disponibili,
        )

        dettaglio = st.text_input(
            "Dettaglio operativo",
            placeholder=(
                "Es. turno mattina, squadra 2, zona specifica..."
            ),
        )

        st.markdown(
            "### Risorse"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            livello = st.selectbox(
                "Livello personale",
                ["L1", "L2", "L3", "L4"],
            )

            ore_personale = st.number_input(
                "Ore personale",
                min_value=0.0,
                step=0.5,
                value=0.0,
            )

        with c2:

            tipo_mezzo = st.selectbox(
                "Tipologia mezzo",
                [
                    "Leggero",
                    "Compattatore",
                    "Pesante",
                    "Speciale",
                ],
            )

            ore_mezzo = st.number_input(
                "Ore mezzo",
                min_value=0.0,
                step=0.5,
                value=0.0,
            )

        with c3:

            tonnellate = st.number_input(
                "Tonnellate",
                min_value=0.0,
                step=0.1,
                value=0.0,
            )

            ricavo = st.number_input(
                "Ricavo",
                min_value=0.0,
                step=50.0,
                value=0.0,
            )

        st.markdown(
            "### Calcolo economico"
        )

        submitted = st.form_submit_button(
            "Registra centro di costo",
            type="primary",
            use_container_width=True,
        )

        if submitted:

            costo_personale = (
                ore_personale
                * tariff(
                    tariffe,
                    "Personale",
                    livello,
                    0,
                )
            )

            costo_mezzo = (
                ore_mezzo
                * tariff(
                    tariffe,
                    "Mezzi",
                    tipo_mezzo,
                    0,
                )
            )

            overhead_pct = tariff(
                tariffe,
                "Generale",
                "Overhead",
                15,
            )

            costo_diretto = (
                costo_personale
                + costo_mezzo
            )

            overhead = (
                costo_diretto
                * overhead_pct
                / 100
            )

            costo_totale = (
                costo_diretto
                + overhead
            )

            # Se il ricavo non è valorizzato manualmente,
            # utilizziamo la tariffa a tonnellata.
            if ricavo == 0 and tonnellate > 0:

                tariffa_ton = tariff(
                    tariffe,
                    "Generale",
                    "Tariffa tonnellata",
                    130,
                )

                ricavo = (
                    tonnellate
                    * tariffa_ton
                )

            margine = (
                ricavo
                - costo_totale
            )

            record_id = (
                "CC-"
                + datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )
            )

            record = {
                "ID": record_id,
                "Data": pd.Timestamp(data_servizio),
                "Commessa": commessa,
                "Servizio": servizio,
                "Dettaglio": dettaglio,
                "Tonnellate": tonnellate,
                "Ricavo": ricavo,
                "Costo": costo_totale,
                "Margine": margine,
                "Ore Personale": ore_personale,
                "Ore Mezzi": ore_mezzo,
                "Operatore": st.session_state.nome,
                "Note": "",
            }

            append_service(record)

            st.success(
                "Centro di costo registrato correttamente."
            )

            st.markdown(
                f"""
                <div class="info-card">
                    <div class="info-title">
                        Risultato economico
                    </div>
                    <div class="info-value">
                        {euro(margine)}
                    </div>
                    <div>
                        Ricavi: {euro(ricavo)}
                        · Costi: {euro(costo_totale)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ========================================================
    # STORICO
    # ========================================================

    st.markdown(
        '<div class="section-title">Storico centri di costo</div>',
        unsafe_allow_html=True,
    )

    storico = services_auth.copy()

    if not storico.empty:

        storico_summary = (
            storico
            .groupby(
                [
                    "Commessa",
                    "Servizio",
                ]
            )
            .agg(
                Ricavi=("Ricavo", "sum"),
                Costi=("Costo", "sum"),
                Margine=("Margine", "sum"),
                Tonnellate=("Tonnellate", "sum"),
                Ore=("Ore Personale", "sum"),
            )
            .reset_index()
        )

        storico_summary["Costo / Ton"] = np.where(
            storico_summary["Tonnellate"] != 0,
            storico_summary["Costi"]
            / storico_summary["Tonnellate"],
            0,
        )

        storico_display = storico_summary.copy()

        for col in [
            "Ricavi",
            "Costi",
            "Margine",
            "Costo / Ton",
        ]:
            storico_display[col] = storico_display[
                col
            ].apply(euro)

        storico_display["Tonnellate"] = (
            storico_display["Tonnellate"]
            .apply(lambda x: number_it(x))
        )

        storico_display["Ore"] = (
            storico_display["Ore"]
            .apply(lambda x: number_it(x))
        )

        st.dataframe(
            storico_display,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Nessun centro di costo registrato."
        )


# ============================================================
# MEZZI
# ============================================================

elif menu == "Mezzi":

    st.markdown(
        '<div class="section-title">Analisi mezzi</div>',
        unsafe_allow_html=True,
    )

    if filtered_services.empty:

        st.info(
            "Non ci sono dati economici disponibili."
        )

    else:

        ore_mezzi = filtered_services[
            "Ore Mezzi"
        ].sum()

        costo_totale = filtered_services[
            "Costo"
        ].sum()

        tonnellate = filtered_services[
            "Tonnellate"
        ].sum()

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Ore mezzi",
                hours_text(ore_mezzi),
            )

        with c2:
            st.metric(
                "Costo complessivo",
                euro(costo_totale),
            )

        with c3:
            costo_ora = (
                costo_totale / ore_mezzi
                if ore_mezzi
                else 0
            )

            st.metric(
                "Costo medio / ora",
                euro(costo_ora),
            )

        if not vehicles.empty:

            vehicles_auth = filter_authorized(
                vehicles
            )

            st.markdown(
                '<div class="section-title">Parco mezzi</div>',
                unsafe_allow_html=True,
            )

            st.dataframe(
                vehicles_auth,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# REPORT
# ============================================================

elif menu == "Report":

    st.markdown(
        '<div class="section-title">Esportazione dati</div>',
        unsafe_allow_html=True,
    )

    report = filtered_services.copy()

    if report.empty:

        st.info(
            "Nessun dato disponibile per il report."
        )

    else:

        st.write(
            f"Record disponibili: **{len(report)}**"
        )

        display = report.copy()

        display["Data"] = pd.to_datetime(
            display["Data"],
            errors="coerce",
        ).dt.strftime("%d/%m/%Y")

        csv_data = display.to_csv(
            index=False,
            encoding="utf-8-sig",
        )

        st.download_button(
            "⬇️ Scarica report CSV",
            data=csv_data,
            file_name=(
                "report_centro_costo_"
                + datetime.now().strftime("%Y%m%d")
                + ".csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# ANAGRAFICHE
# ============================================================

elif menu == "Anagrafiche":

    if not is_admin():

        st.error(
            "Sezione riservata alla Direzione."
        )
        st.stop()

    tab1, tab2 = st.tabs(
        [
            "👷 Operatori",
            "🚛 Mezzi",
        ]
    )

    with tab1:

        st.markdown(
            '<div class="section-title">Anagrafica operatori</div>',
            unsafe_allow_html=True,
        )

        edited_operators = st.data_editor(
            operators,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
        )

        if st.button(
            "Salva operatori",
            key="save_operators",
            type="primary",
        ):

            safe_to_csv(
                edited_operators,
                OPERATORI_FILE,
            )

            st.success(
                "Anagrafica operatori salvata."
            )

            st.rerun()

    with tab2:

        st.markdown(
            '<div class="section-title">Anagrafica mezzi</div>',
            unsafe_allow_html=True,
        )

        edited_vehicles = st.data_editor(
            vehicles,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
        )

        if st.button(
            "Salva mezzi",
            key="save_vehicles",
            type="primary",
        ):

            safe_to_csv(
                edited_vehicles,
                MEZZI_FILE,
            )

            st.success(
                "Anagrafica mezzi salvata."
            )

            st.rerun()


# ============================================================
# GESTIONE ACCESSI
# ============================================================

elif menu == "Gestione Accessi":

    if not is_admin():

        st.error(
            "Sezione riservata alla Direzione."
        )
        st.stop()

    st.markdown(
        '<div class="section-title">Utenti autorizzati</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Nel campo Commesse puoi indicare più commesse "
        "separate da virgola."
    )

    edited_users = st.data_editor(
        users,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
    )

    if st.button(
        "Salva utenti",
        type="primary",
    ):

        required = [
            "username",
            "password",
            "nome",
            "ruolo",
            "cantieri",
        ]

        edited_users = ensure_columns(
            edited_users,
            required,
        )

        safe_to_csv(
            edited_users[required],
            UTENTI_FILE,
        )

        st.success(
            "Gestione accessi aggiornata."
        )

        st.rerun()

    st.markdown(
        '<div class="section-title">Commesse disponibili</div>',
        unsafe_allow_html=True,
    )

    commesse_table = []

    for commessa in COMMESSE_STANDARD:

        commesse_table.append(
            {
                "Commessa": commessa,
                "Servizi disponibili": ", ".join(
                    SERVIZI_PER_COMMESSA.get(
                        commessa,
                        [],
                    )
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(commesse_table),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div style="
        text-align:center;
        color:#8a9290;
        font-size:11px;
        padding:35px 0 10px 0;
    ">
        Cristoforo · Control Room · Centro di Costo
    </div>
    """,
    unsafe_allow_html=True,
)
