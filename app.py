import streamlit as st
import pandas as pd
import numpy as np
import os
import re
from datetime import datetime, date


# ============================================================
# CONFIGURAZIONE
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
# UTENTI DEFAULT
# ============================================================

DEFAULT_USERS = pd.DataFrame([
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
])


# ============================================================
# TARIFFE DEFAULT
# ============================================================

DEFAULT_TARIFFE = pd.DataFrame([
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
])


# ============================================================
# STRUTTURA SERVIZI
# ============================================================
#
# Categoria = tipo di servizio
# Dettaglio = territorio / commessa
#
# ============================================================

STRUTTURA_SERVIZI = {
    "Spazzamenti": [
        "Scandicci",
    ],

    "Aree Verdi": [
        "Piana",
        "Prato",
    ],

    "Porta a Porta": [
        "Prato",
        "Vaiano",
        "Campi",
        "Noventa",
        "Costabissara",
        "Cremona",
        "Mantova",
        "Lucca",
    ],

    "Trasporti": [
        "Alia",
    ],

    "Raccolta Cartone Selettivo": [
        "Firenze",
        "Piana",
        "Prato",
        "Campi",
    ],

    "Ingombranti": [
        "Prato",
        "Campi Bisenzio",
        "Valdisieve",
        "Mugello",
    ],
}


# ============================================================
# LISTA COMMESSE DERIVATA DALLA STRUTTURA SERVIZI
# ============================================================

COMMESSE_STANDARD = sorted(
    set(
        dettaglio
        for dettagli in STRUTTURA_SERVIZI.values()
        for dettaglio in dettagli
    )
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

:root {
    --green: #008b3a;
    --green-dark: #006d2e;
    --green-light: #e9f7ef;
    --bg: #f4f6f8;
    --card: #ffffff;
    --text: #17202a;
    --muted: #6b7280;
    --border: #e5e7eb;
    --sidebar: #101714;
}

html, body, [class*="css"] {
    font-family: Inter, -apple-system, BlinkMacSystemFont,
                 "Segoe UI", sans-serif;
}

.stApp {
    background: var(--bg);
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

section[data-testid="stSidebar"] {
    background: var(--sidebar);
}

section[data-testid="stSidebar"] * {
    color: #eef5f0;
}

section[data-testid="stSidebar"] .stRadio label {
    padding: 9px 10px;
    border-radius: 9px;
}

section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.07);
}

h1, h2, h3 {
    letter-spacing: -0.03em;
    color: var(--text);
}

.page-title {
    font-size: 31px;
    font-weight: 750;
    margin-bottom: 3px;
}

.page-subtitle {
    color: var(--muted);
    font-size: 14px;
    margin-bottom: 20px;
}

.top-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.brand-mark {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: var(--green);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    font-weight: 700;
}

.brand-name {
    font-weight: 750;
    font-size: 18px;
}

.brand-role {
    color: var(--muted);
    font-size: 12px;
}

.kpi-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 20px;
    min-height: 125px;
    box-shadow: 0 3px 12px rgba(15, 23, 42, 0.035);
}

.kpi-label {
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 650;
}

.kpi-value {
    font-size: 29px;
    line-height: 1.15;
    font-weight: 780;
    margin-top: 8px;
    color: var(--text);
}

.kpi-caption {
    font-size: 12px;
    color: var(--muted);
    margin-top: 7px;
}

.commessa-hero {
    background: linear-gradient(
        135deg,
        #ffffff 0%,
        #f0faf4 100%
    );
    border: 1px solid #dcefe4;
    border-radius: 18px;
    padding: 22px 24px;
    margin: 5px 0 22px 0;
}

.commessa-kicker {
    color: var(--green);
    text-transform: uppercase;
    font-size: 11px;
    font-weight: 750;
    letter-spacing: 0.08em;
}

.commessa-name {
    color: var(--text);
    font-size: 25px;
    font-weight: 780;
    margin-top: 4px;
}

.commessa-meta {
    color: var(--muted);
    font-size: 13px;
    margin-top: 4px;
}

.panel {
    background: white;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 18px;
    box-shadow: 0 3px 12px rgba(15, 23, 42, 0.03);
}

.panel-title {
    font-size: 16px;
    font-weight: 730;
    margin-bottom: 12px;
}

.badge {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
}

.badge-ok {
    background: #e8f7ee;
    color: #087a38;
}

.badge-warning {
    background: #fff5df;
    color: #9a6500;
}

.badge-critical {
    background: #fdecec;
    color: #b42318;
}

.badge-neutral {
    background: #eef1f4;
    color: #59636e;
}

.login-box {
    max-width: 480px;
    margin: 70px auto;
    background: white;
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 35px;
    box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
}

.login-title {
    font-size: 28px;
    font-weight: 800;
    color: var(--text);
}

.login-subtitle {
    color: var(--muted);
    margin-bottom: 25px;
}

.stButton > button {
    border-radius: 10px;
    font-weight: 650;
    border: 1px solid var(--border);
}

.stButton > button[kind="primary"] {
    background: var(--green);
    border-color: var(--green);
}

div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

hr {
    border-color: var(--border);
}

.footer {
    color: #8a929b;
    text-align: center;
    font-size: 11px;
    margin-top: 35px;
}

.service-box {
    background: #f8faf9;
    border: 1px solid #e1e9e4;
    border-radius: 14px;
    padding: 15px;
    margin: 10px 0;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FUNZIONI CSV
# ============================================================

def clean_col_name(value):
    if value is None:
        return ""

    value = str(value)
    value = value.replace("\ufeff", "")
    value = value.strip().lower()

    value = (
        value.replace("à", "a")
        .replace("è", "e")
        .replace("é", "e")
        .replace("ì", "i")
        .replace("ò", "o")
        .replace("ù", "u")
    )

    value = re.sub(r"\s+", " ", value)
    value = value.replace("_", " ")
    value = value.replace("-", " ")

    return value.strip()


def normalize_columns(df):
    if df is None:
        return pd.DataFrame()

    df = df.copy()

    df.columns = [
        clean_col_name(col)
        for col in df.columns
    ]

    return df


def flexible_read_csv(path, **kwargs):

    if not os.path.exists(path):
        return pd.DataFrame()

    attempts = [
        {
            "sep": None,
            "engine": "python",
            "encoding": "utf-8-sig",
        },
        {
            "sep": ";",
            "encoding": "utf-8-sig",
        },
        {
            "sep": ",",
            "encoding": "utf-8-sig",
        },
        {
            "sep": "\t",
            "encoding": "utf-8-sig",
        },
        {
            "sep": ";",
            "encoding": "latin1",
        },
        {
            "sep": ",",
            "encoding": "latin1",
        },
    ]

    for options in attempts:

        try:

            final_options = options.copy()
            final_options.update(kwargs)

            df = pd.read_csv(
                path,
                **final_options,
            )

            return normalize_columns(df)

        except Exception:
            continue

    return pd.DataFrame()


def flexible_read_uploaded_csv(uploaded_file):

    attempts = [
        {
            "sep": None,
            "engine": "python",
            "encoding": "utf-8-sig",
        },
        {
            "sep": ";",
            "encoding": "utf-8-sig",
        },
        {
            "sep": ",",
            "encoding": "utf-8-sig",
        },
        {
            "sep": "\t",
            "encoding": "utf-8-sig",
        },
        {
            "sep": ";",
            "encoding": "latin1",
        },
        {
            "sep": ",",
            "encoding": "latin1",
        },
    ]

    for options in attempts:

        try:

            uploaded_file.seek(0)

            df = pd.read_csv(
                uploaded_file,
                **options,
            )

            return normalize_columns(df)

        except Exception:
            continue

    return pd.DataFrame()


def safe_to_csv(df, path):

    try:

        df.to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
        )

        return True

    except Exception:

        return False


def first_existing_column(df, aliases):

    if df is None:
        return None

    aliases = [
        clean_col_name(x)
        for x in aliases
    ]

    for alias in aliases:

        if alias in df.columns:
            return alias

    return None


def rename_using_aliases(df, alias_map):

    if df is None:
        return pd.DataFrame()

    df = normalize_columns(df)

    rename_map = {}

    for standard, aliases in alias_map.items():

        found = first_existing_column(
            df,
            [standard] + list(aliases),
        )

        if found and found != standard:
            rename_map[found] = standard

    if rename_map:
        df = df.rename(
            columns=rename_map
        )

    return df


def ensure_columns(
    df,
    columns,
    defaults=None,
):

    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    defaults = defaults or {}

    for col in columns:

        if col not in df.columns:
            df[col] = defaults.get(
                col,
                "",
            )

    return df


# ============================================================
# CONVERSIONI
# ============================================================

def parse_number(value, default=0.0):

    if value is None:
        return default

    if isinstance(
        value,
        (
            int,
            float,
            np.integer,
            np.floating,
        ),
    ):

        if pd.isna(value):
            return default

        return float(value)

    text = str(value).strip()

    if not text:
        return default

    text = (
        text
        .replace("€", "")
        .replace("EUR", "")
        .replace("eur", "")
        .replace(" ", "")
        .strip()
    )

    try:

        if "," in text and "." in text:

            if text.rfind(",") > text.rfind("."):

                text = text.replace(
                    ".",
                    "",
                )

                text = text.replace(
                    ",",
                    ".",
                )

            else:

                text = text.replace(
                    ",",
                    "",
                )

        elif "," in text:

            text = text.replace(
                ",",
                ".",
            )

        return float(text)

    except Exception:

        return default


def parse_hours(value, default=0.0):

    if value is None:
        return default

    if isinstance(
        value,
        (
            int,
            float,
            np.integer,
            np.floating,
        ),
    ):

        if pd.isna(value):
            return default

        value = float(value)

        if 0 <= value < 1:
            return value * 24

        return value

    text = str(value).strip()

    if not text:
        return default

    if ":" in text:

        try:

            parts = text.split(":")

            h = parse_number(
                parts[0]
            )

            m = (
                parse_number(parts[1])
                if len(parts) > 1
                else 0
            )

            s = (
                parse_number(parts[2])
                if len(parts) > 2
                else 0
            )

            return (
                h
                + m / 60
                + s / 3600
            )

        except Exception:

            return default

    return parse_number(
        text,
        default,
    )


def euro(value):

    value = parse_number(value)

    return (
        f"€ {value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def number_it(
    value,
    decimals=1,
):

    value = parse_number(value)

    return (
        f"{value:,.{decimals}f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def percent(value):

    value = parse_number(value)

    return (
        f"{value:.1f}%"
        .replace(".", ",")
    )


def make_id():

    return datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )


# ============================================================
# USERS
# ============================================================

USER_ALIASES = {

    "username": [
        "user",
        "utente",
        "login",
        "nome utente",
        "userid",
    ],

    "password": [
        "pass",
        "pwd",
        "password utente",
    ],

    "nome": [
        "name",
        "nominativo",
        "nome completo",
        "operatore",
        "responsabile",
    ],

    "ruolo": [
        "role",
        "profilo",
        "tipo utente",
    ],

    "cantieri": [
        "cantiere",
        "commesse",
        "commessa",
        "autorizzazioni",
        "autorizzazione",
        "cantieri autorizzati",
        "commesse autorizzate",
    ],
}


def read_users():

    df = flexible_read_csv(
        UTENTI_FILE
    )

    if df.empty:

        if not os.path.exists(
            UTENTI_FILE
        ):

            safe_to_csv(
                DEFAULT_USERS,
                UTENTI_FILE,
            )

        return DEFAULT_USERS.copy()

    df = rename_using_aliases(
        df,
        USER_ALIASES,
    )

    required = [
        "username",
        "password",
        "nome",
        "ruolo",
        "cantieri",
    ]

    if not all(
        col in df.columns
        for col in required
    ):

        st.warning(
            "Il file utenti esistente "
            "non presenta intestazioni riconoscibili. "
            "Controlla utenti_cristoforo.csv."
        )

        return DEFAULT_USERS.copy()

    for col in required:

        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.replace(
                "\ufeff",
                "",
                regex=False,
            )
            .str.strip()
        )

    return df[required].copy()


def authorized_commesse(row):

    if row is None:
        return []

    raw = str(
        row.get(
            "cantieri",
            "",
        )
    ).strip()

    if not raw:
        return []

    if raw.upper() in [
        "TUTTI",
        "ALL",
        "*",
    ]:
        return ["TUTTI"]

    raw = raw.replace(
        ";",
        ",",
    )

    return [
        x.strip()
        for x in raw.split(",")
        if x.strip()
    ]


def is_admin():

    return (
        st.session_state
        .get("ruolo", "")
        .lower()
        in [
            "admin",
            "direzione",
            "amministratore",
        ]
    )


# ============================================================
# SERVIZI CSV
# ============================================================

SERVICE_ALIASES = {

    "ID": [
        "id servizio",
        "id",
        "codice",
        "codice servizio",
    ],

    "Data": [
        "data servizio",
        "giorno",
        "data",
    ],

    "Cantiere": [
        "commessa",
        "commessa/cantiere",
        "cantiere",
        "cliente",
        "sede",
        "territorio",
    ],

    "Categoria": [
        "categoria servizio",
        "tipologia",
        "tipo servizio",
        "servizio",
    ],

    "Dettaglio": [
        "dettaglio servizio",
        "sottocategoria",
        "descrizione",
        "attivita",
        "attività",
        "territorio servizio",
    ],

    "Tonnellate": [
        "ton",
        "tons",
        "tonnellata",
        "tonnellate raccolte",
        "peso",
        "quantita ton",
        "quantità ton",
    ],

    "Ricavo": [
        "ricavi",
        "revenue",
        "fatturato",
        "ricavo netto",
        "ricavo €",
        "ricavi €",
        "ricavo (€)",
    ],

    "Costo": [
        "costi",
        "costo totale",
        "costo totale €",
        "costo €",
        "costo (€)",
    ],

    "Margine": [
        "margine netto",
        "margine netto €",
        "margine netto (€)",
        "margine €",
        "utile",
        "profitto",
    ],

    "Ore Personale": [
        "ore personale",
        "ore uomo",
        "ore operatori",
        "ore lavoro",
        "ore",
    ],

    "Ore Mezzi": [
        "ore mezzi",
        "ore veicoli",
        "ore mezzo",
    ],
}


def read_services():

    df = flexible_read_csv(
        SERVIZI_FILE
    )

    required = [
        "ID",
        "Data",
        "Cantiere",
        "Categoria",
        "Dettaglio",
        "Tonnellate",
        "Ricavo",
        "Costo",
        "Margine",
        "Ore Personale",
        "Ore Mezzi",
    ]

    if df.empty:

        return pd.DataFrame(
            columns=required
        )

    df = rename_using_aliases(
        df,
        SERVICE_ALIASES,
    )

    df = ensure_columns(
        df,
        required,
    )

    df["ID"] = (
        df["ID"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    for col in [
        "Cantiere",
        "Categoria",
        "Dettaglio",
    ]:

        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    df["Data"] = pd.to_datetime(
        df["Data"],
        dayfirst=True,
        errors="coerce",
    )

    for col in [
        "Tonnellate",
        "Ricavo",
        "Costo",
        "Margine",
        "Ore Personale",
        "Ore Mezzi",
    ]:

        df[col] = df[col].apply(
            parse_number
        )

    # Calcolo automatico margine
    if "Margine" in df.columns:

        mask = (
            (df["Margine"] == 0)
            &
            (
                (df["Ricavo"] != 0)
                |
                (df["Costo"] != 0)
            )
        )

        df.loc[
            mask,
            "Margine"
        ] = (
            df.loc[
                mask,
                "Ricavo"
            ]
            -
            df.loc[
                mask,
                "Costo"
            ]
        )

    return df


# ============================================================
# ORE
# ============================================================

ORE_ALIASES = {

    "ID": [
        "id",
        "id turno",
        "codice",
    ],

    "Data": [
        "data turno",
        "giorno",
        "data",
    ],

    "Operatore": [
        "nome operatore",
        "dipendente",
        "addetto",
        "nome",
    ],

    "Cantiere": [
        "commessa",
        "cantiere",
        "commessa/cantiere",
    ],

    "Ore": [
        "ore lavorate",
        "ore lavoro",
        "ore totali",
        "ore",
        "durata",
    ],

    "Ore Extra": [
        "extra",
        "ore straordinarie",
        "straordinario",
        "ore extra",
    ],

    "Tipo": [
        "tipologia",
        "tipo turno",
        "servizio",
    ],
}


def read_hours():

    df = flexible_read_csv(
        ORE_FILE
    )

    required = [
        "ID",
        "Data",
        "Operatore",
        "Cantiere",
        "Ore",
        "Ore Extra",
        "Tipo",
    ]

    if df.empty:

        return pd.DataFrame(
            columns=required
        )

    df = rename_using_aliases(
        df,
        ORE_ALIASES,
    )

    df = ensure_columns(
        df,
        required,
    )

    for col in [
        "ID",
        "Operatore",
        "Cantiere",
        "Tipo",
    ]:

        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    df["Data"] = pd.to_datetime(
        df["Data"],
        dayfirst=True,
        errors="coerce",
    )

    df["Ore"] = df["Ore"].apply(
        parse_hours
    )

    df["Ore Extra"] = df[
        "Ore Extra"
    ].apply(
        parse_hours
    )

    return df


# ============================================================
# OPERATORI
# ============================================================

OPERATORI_ALIASES = {

    "Matricola": [
        "matricola",
        "id",
        "codice",
        "codice operatore",
    ],

    "Nome": [
        "nome operatore",
        "nominativo",
        "dipendente",
        "operatore",
    ],

    "Cognome": [
        "cognome",
    ],

    "Livello": [
        "livello",
        "livello contrattuale",
        "qualifica",
        "ccnl",
    ],

    "Cantiere": [
        "commessa",
        "cantiere",
        "sede",
    ],

    "Costo Orario": [
        "costo orario",
        "costo ora",
        "costo/h",
        "costo orario €",
    ],
}


def read_operators():

    df = flexible_read_csv(
        OPERATORI_FILE
    )

    required = [
        "Matricola",
        "Nome",
        "Cognome",
        "Livello",
        "Cantiere",
        "Costo Orario",
    ]

    if df.empty:

        return pd.DataFrame(
            columns=required
        )

    df = rename_using_aliases(
        df,
        OPERATORI_ALIASES,
    )

    df = ensure_columns(
        df,
        required,
    )

    for col in [
        "Matricola",
        "Nome",
        "Cognome",
        "Livello",
        "Cantiere",
    ]:

        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    df["Costo Orario"] = (
        df["Costo Orario"]
        .apply(parse_number)
    )

    return df


# ============================================================
# MEZZI
# ============================================================

MEZZI_ALIASES = {

    "Targa": [
        "targa mezzo",
        "targa",
        "matricola mezzo",
        "id mezzo",
    ],

    "Mezzo": [
        "descrizione mezzo",
        "nome mezzo",
        "veicolo",
        "mezzo",
    ],

    "Categoria": [
        "categoria mezzo",
        "tipologia",
        "tipo",
        "classe",
    ],

    "Cantiere": [
        "commessa",
        "cantiere",
        "sede",
    ],

    "Costo Orario": [
        "costo orario",
        "costo ora",
        "costo/h",
        "costo orario €",
    ],
}


def read_vehicles():

    df = flexible_read_csv(
        MEZZI_FILE
    )

    required = [
        "Targa",
        "Mezzo",
        "Categoria",
        "Cantiere",
        "Costo Orario",
    ]

    if df.empty:

        return pd.DataFrame(
            columns=required
        )

    df = rename_using_aliases(
        df,
        MEZZI_ALIASES,
    )

    df = ensure_columns(
        df,
        required,
    )

    for col in [
        "Targa",
        "Mezzo",
        "Categoria",
        "Cantiere",
    ]:

        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    df["Costo Orario"] = (
        df["Costo Orario"]
        .apply(parse_number)
    )

    return df


# ============================================================
# TARIFFE
# ============================================================

TARIFFE_ALIASES = {

    "Categoria": [
        "categoria",
        "gruppo",
        "tipo",
    ],

    "Voce": [
        "voce",
        "livello",
        "descrizione",
        "tipo mezzo",
    ],

    "Costo": [
        "costo",
        "tariffa",
        "valore",
        "costo orario",
        "importo",
    ],
}


def read_tariffe():

    df = flexible_read_csv(
        TARIFFE_FILE
    )

    if df.empty:

        if not os.path.exists(
            TARIFFE_FILE
        ):

            safe_to_csv(
                DEFAULT_TARIFFE,
                TARIFFE_FILE,
            )

        return DEFAULT_TARIFFE.copy()

    df = rename_using_aliases(
        df,
        TARIFFE_ALIASES,
    )

    required = [
        "Categoria",
        "Voce",
        "Costo",
    ]

    if not all(
        x in df.columns
        for x in required
    ):

        st.warning(
            "Il tariffario esistente non è "
            "riconoscibile. Viene usato il "
            "tariffario standard."
        )

        return DEFAULT_TARIFFE.copy()

    df["Categoria"] = (
        df["Categoria"]
        .astype(str)
        .str.strip()
    )

    df["Voce"] = (
        df["Voce"]
        .astype(str)
        .str.strip()
    )

    df["Costo"] = (
        df["Costo"]
        .apply(parse_number)
    )

    return df[required].copy()


def tariff(
    tariffe,
    categoria,
    voce,
    default=0,
):

    if tariffe.empty:
        return default

    mask = (
        tariffe["Categoria"]
        .astype(str)
        .str.lower()
        .str.strip()
        ==
        categoria.lower().strip()
    ) & (
        tariffe["Voce"]
        .astype(str)
        .str.lower()
        .str.strip()
        ==
        voce.lower().strip()
    )

    result = tariffe.loc[
        mask,
        "Costo",
    ]

    if result.empty:
        return default

    return parse_number(
        result.iloc[0],
        default,
    )


# ============================================================
# AUTORIZZAZIONI
# ============================================================

def filter_authorized(
    df,
    column="Cantiere",
):

    if df is None or df.empty:
        return df

    if is_admin():
        return df.copy()

    authorized = (
        st.session_state
        .get("cantieri", [])
    )

    if "TUTTI" in authorized:
        return df.copy()

    if column not in df.columns:
        return df.iloc[0:0].copy()

    authorized_clean = {
        str(x)
        .strip()
        .lower()
        for x in authorized
    }

    return df[
        df[column]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(authorized_clean)
    ].copy()


def available_commesse(df):

    # Partiamo dalle commesse definite
    # nella struttura dei servizi.
    standard = set(
        COMMESSE_STANDARD
    )

    # Aggiungiamo eventuali commesse
    # già presenti nello storico.
    if (
        df is not None
        and not df.empty
        and "Cantiere" in df.columns
    ):

        standard.update(
            [
                str(x).strip()
                for x in df["Cantiere"]
                .dropna()
                .unique()
                if str(x).strip()
            ]
        )

    values = sorted(
        standard
    )

    if is_admin():
        return values

    authorized = (
        st.session_state
        .get("cantieri", [])
    )

    if "TUTTI" in authorized:
        return values

    authorized_lower = {
        str(x).lower().strip()
        for x in authorized
    }

    return [
        x
        for x in values
        if x.lower().strip()
        in authorized_lower
    ]


# ============================================================
# STORICO
# ============================================================

def aggiorna_storico(
    df_nuovo,
    path,
    id_column="ID",
):

    if (
        df_nuovo is None
        or df_nuovo.empty
    ):
        return False

    storico = flexible_read_csv(
        path
    )

    if storico.empty:

        return safe_to_csv(
            df_nuovo,
            path,
        )

    storico = normalize_columns(
        storico
    )

    df_nuovo = normalize_columns(
        df_nuovo
    )

    if (
        id_column in storico.columns
        and
        id_column in df_nuovo.columns
    ):

        storico[id_column] = (
            storico[id_column]
            .astype(str)
        )

        df_nuovo[id_column] = (
            df_nuovo[id_column]
            .astype(str)
        )

        combinato = pd.concat(
            [
                storico,
                df_nuovo,
            ],
            ignore_index=True,
        )

        combinato = (
            combinato
            .drop_duplicates(
                subset=[id_column],
                keep="last",
            )
        )

    else:

        combinato = pd.concat(
            [
                storico,
                df_nuovo,
            ],
            ignore_index=True,
        )

    return safe_to_csv(
        combinato,
        path,
    )


# ============================================================
# CREA FILE MINIMI
# ============================================================

if not os.path.exists(
    UTENTI_FILE
):

    safe_to_csv(
        DEFAULT_USERS,
        UTENTI_FILE,
    )


if not os.path.exists(
    TARIFFE_FILE
):

    safe_to_csv(
        DEFAULT_TARIFFE,
        TARIFFE_FILE,
    )


# ============================================================
# SESSION STATE
# ============================================================

if "loggato" not in st.session_state:
    st.session_state.loggato = False

if "utente" not in st.session_state:
    st.session_state.utente = ""

if "nome_utente" not in st.session_state:
    st.session_state.nome_utente = ""

if "ruolo" not in st.session_state:
    st.session_state.ruolo = ""

if "cantieri" not in st.session_state:
    st.session_state.cantieri = []


# ============================================================
# LOGIN
# ============================================================

if not st.session_state.loggato:

    st.markdown(
        """
        <div class="login-box">

            <div class="brand">

                <div class="brand-mark">
                    ♻
                </div>

                <div>
                    <div class="brand-name">
                        Cristoforo
                    </div>

                    <div class="brand-role">
                        Control Room
                    </div>
                </div>

            </div>

            <br>

            <div class="login-title">
                Accesso operativo
            </div>

            <div class="login-subtitle">
                Ore, commesse e controllo economico.
            </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(
        "login_form"
    ):

        username = st.text_input(
            "Username",
            placeholder="Inserisci username",
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Inserisci password",
        )

        login = st.form_submit_button(
            "Accedi alla Control Room",
            use_container_width=True,
            type="primary",
        )

        if login:

            users = read_users()

            username_clean = (
                str(username)
                .strip()
            )

            password_clean = (
                str(password)
                .strip()
            )

            match = users[
                (
                    users["username"]
                    .astype(str)
                    .str.strip()
                    ==
                    username_clean
                )
                &
                (
                    users["password"]
                    .astype(str)
                    .str.strip()
                    ==
                    password_clean
                )
            ]

            if not match.empty:

                row = match.iloc[0]

                st.session_state.loggato = True

                st.session_state.utente = (
                    username_clean
                )

                st.session_state.nome_utente = (
                    str(
                        row.get(
                            "nome",
                            username_clean,
                        )
                    ).strip()
                )

                st.session_state.ruolo = (
                    str(
                        row.get(
                            "ruolo",
                            "capocantiere",
                        )
                    ).strip()
                )

                st.session_state.cantieri = (
                    authorized_commesse(
                        row
                    )
                )

                st.rerun()

            else:

                st.error(
                    "Username o password non corretti."
                )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    st.stop()


# ============================================================
# CARICAMENTO DATI
# ============================================================

users = read_users()
servizi = read_services()
ore = read_hours()
operatori = read_operators()
mezzi = read_vehicles()
tariffe = read_tariffe()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            padding:8px 4px 20px 4px;
            font-size:18px;
            font-weight:800;
        ">
            ♻️ Cristoforo
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        f"{st.session_state.nome_utente} · "
        f"{st.session_state.ruolo}"
    )

    st.divider()

    menu_options = [
        "Overview",
        "Commesse",
        "Validazione Turni",
        "Ore",
        "Centro di Costo",
        "Mezzi",
        "Report",
    ]

    if is_admin():

        menu_options += [
            "Anagrafiche",
            "Gestione Accessi",
        ]

    pagina = st.radio(
        "Navigazione",
        menu_options,
        label_visibility="collapsed",
    )

    st.divider()

    st.caption(
        "COMMESSE AUTORIZZATE"
    )

    if "TUTTI" in st.session_state.cantieri:

        st.success(
            "Accesso completo"
        )

    else:

        for c in st.session_state.cantieri:

            st.caption(
                f"• {c}"
            )

    st.divider()

    if st.button(
        "Esci",
        use_container_width=True,
    ):

        for key in [
            "loggato",
            "utente",
            "nome_utente",
            "ruolo",
            "cantieri",
        ]:

            if key in st.session_state:
                del st.session_state[key]

        st.rerun()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    f"""
    <div class="top-header">

        <div class="brand">

            <div class="brand-mark">
                ♻
            </div>

            <div>

                <div class="brand-name">
                    Control Room
                </div>

                <div class="brand-role">
                    Hub operativo · gestione economica
                </div>

            </div>

        </div>

        <div style="
            text-align:right;
            font-size:13px;
            color:#6b7280;
        ">

            <strong>
                {st.session_state.nome_utente}
            </strong>

            <br>

            {st.session_state.ruolo}

        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FILTRI GLOBALI
# ============================================================

commesse_disponibili = (
    available_commesse(servizi)
)

if commesse_disponibili:

    c1, c2 = st.columns(
        [2.2, 1]
    )

    with c1:

        commessa_filter = st.selectbox(
            "Commessa / Territorio",
            [
                "Tutte le commesse"
            ]
            +
            commesse_disponibili,
        )

    with c2:

        periodo = st.selectbox(
            "Periodo",
            [
                "Tutto lo storico",
                "Ultimi 7 giorni",
                "Ultimi 30 giorni",
                "Ultimi 90 giorni",
                "Anno corrente",
            ],
        )

else:

    commessa_filter = (
        "Tutte le commesse"
    )

    periodo = (
        "Tutto lo storico"
    )


# ============================================================
# FILTRO SERVIZI
# ============================================================

servizi_view = filter_authorized(
    servizi
)

if (
    commessa_filter
    != "Tutte le commesse"
):

    servizi_view = servizi_view[
        servizi_view["Cantiere"]
        .astype(str)
        .str.strip()
        .str.lower()
        ==
        commessa_filter
        .strip()
        .lower()
    ]


if (
    not servizi_view.empty
    and
    "Data" in servizi_view.columns
):

    oggi = pd.Timestamp.today().normalize()

    if periodo == "Ultimi 7 giorni":

        servizi_view = servizi_view[
            servizi_view["Data"]
            >=
            oggi
            -
            pd.Timedelta(days=7)
        ]

    elif periodo == "Ultimi 30 giorni":

        servizi_view = servizi_view[
            servizi_view["Data"]
            >=
            oggi
            -
            pd.Timedelta(days=30)
        ]

    elif periodo == "Ultimi 90 giorni":

        servizi_view = servizi_view[
            servizi_view["Data"]
            >=
            oggi
            -
            pd.Timedelta(days=90)
        ]

    elif periodo == "Anno corrente":

        servizi_view = servizi_view[
            servizi_view["Data"].dt.year
            ==
            oggi.year
        ]


# ============================================================
# HERO
# ============================================================

hero_name = (
    commessa_filter
    if commessa_filter
    != "Tutte le commesse"
    else "Portafoglio commesse"
)

st.markdown(
    f"""
    <div class="commessa-hero">

        <div class="commessa-kicker">
            Area operativa
        </div>

        <div class="commessa-name">
            {hero_name}
        </div>

        <div class="commessa-meta">
            Periodo: {periodo}
            ·
            {len(servizi_view)}
            registrazioni economiche
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# OVERVIEW
# ============================================================

if pagina == "Overview":

    st.markdown(
        '<div class="page-title">'
        'Sintesi direzionale'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Quadro sintetico di ricavi, costi, '
        'marginalità e attività operative.'
        '</div>',
        unsafe_allow_html=True,
    )

    ricavi = servizi_view[
        "Ricavo"
    ].sum()

    costi = servizi_view[
        "Costo"
    ].sum()

    margine = servizi_view[
        "Margine"
    ].sum()

    ton = servizi_view[
        "Tonnellate"
    ].sum()

    ore_personale = servizi_view[
        "Ore Personale"
    ].sum()

    ore_mezzi = servizi_view[
        "Ore Mezzi"
    ].sum()

    margine_pct = (
        margine / ricavi * 100
        if ricavi != 0
        else 0
    )

    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Ricavi
                </div>

                <div class="kpi-value">
                    {euro(ricavi)}
                </div>

                <div class="kpi-caption">
                    fatturato del periodo
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Costi
                </div>

                <div class="kpi-value">
                    {euro(costi)}
                </div>

                <div class="kpi-caption">
                    costi operativi
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Margine
                </div>

                <div class="kpi-value">
                    {euro(margine)}
                </div>

                <div class="kpi-caption">
                    marginalità {percent(margine_pct)}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Tonnellate
                </div>

                <div class="kpi-value">
                    {number_it(ton)}
                </div>

                <div class="kpi-caption">
                    materiale gestito
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    c1, c2 = st.columns(
        [1.7, 1]
    )

    with c1:

        st.markdown(
            """
            <div class="panel">

                <div class="panel-title">
                    Andamento economico
                </div>
            """,
            unsafe_allow_html=True,
        )

        if not servizi_view.empty:

            trend = (
                servizi_view
                .dropna(subset=["Data"])
                .groupby(
                    "Data",
                    as_index=False,
                )
                .agg({
                    "Ricavo": "sum",
                    "Costo": "sum",
                    "Margine": "sum",
                })
                .sort_values("Data")
            )

            if not trend.empty:

                trend = trend.set_index(
                    "Data"
                )

                st.line_chart(
                    trend[
                        [
                            "Ricavo",
                            "Costo",
                            "Margine",
                        ]
                    ],
                    height=280,
                )

            else:

                st.info(
                    "Nessun dato temporale disponibile."
                )

        else:

            st.info(
                "Nessun dato disponibile."
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    with c2:

        st.markdown(
            """
            <div class="panel">

                <div class="panel-title">
                    Stato economico
                </div>
            """,
            unsafe_allow_html=True,
        )

        if margine_pct >= 20:

            st.markdown(
                '<span class="badge badge-ok">'
                'OK'
                '</span>',
                unsafe_allow_html=True,
            )

        elif margine_pct >= 0:

            st.markdown(
                '<span class="badge badge-warning">'
                'ATTENZIONE'
                '</span>',
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                '<span class="badge badge-critical">'
                'CRITICO'
                '</span>',
                unsafe_allow_html=True,
            )

        st.write("")

        st.metric(
            "Margine %",
            percent(margine_pct),
        )

        st.metric(
            "Ore personale",
            number_it(ore_personale),
        )

        st.metric(
            "Ore mezzi",
            number_it(ore_mezzi),
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # CENTRO COSTI
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="panel">

            <div class="panel-title">
                Composizione del costo
            </div>
        """,
        unsafe_allow_html=True,
    )

    if (
        not operatori.empty
        and
        ore_personale > 0
    ):

        media_personale = (
            operatori["Costo Orario"]
            .replace(0, np.nan)
            .mean()
        )

        if pd.isna(media_personale):
            media_personale = 28

        personale_cost = (
            ore_personale
            * media_personale
        )

    else:

        personale_cost = (
            costi * 0.55
        )

    if ore_mezzi > 0:

        mezzi_cost = (
            ore_mezzi * 25
        )

    else:

        mezzi_cost = (
            costi * 0.30
        )

    overhead_cost = max(
        costi
        -
        personale_cost
        -
        mezzi_cost,
        0,
    )

    cc1, cc2, cc3 = st.columns(3)

    with cc1:

        st.metric(
            "Personale",
            euro(personale_cost),
        )

    with cc2:

        st.metric(
            "Mezzi",
            euro(mezzi_cost),
        )

    with cc3:

        st.metric(
            "Generali / Overhead",
            euro(overhead_cost),
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # COMMESSE
    # --------------------------------------------------------

    if (
        is_admin()
        and
        not servizi_view.empty
    ):

        st.markdown(
            """
            <div class="panel">

                <div class="panel-title">
                    Performance per commessa
                </div>
            """,
            unsafe_allow_html=True,
        )

        commesse = (
            servizi_view
            .groupby(
                "Cantiere",
                as_index=False,
            )
            .agg(
                Ricavi=("Ricavo", "sum"),
                Costi=("Costo", "sum"),
                Margine=("Margine", "sum"),
                Tonnellate=(
                    "Tonnellate",
                    "sum",
                ),
            )
        )

        commesse["Margine %"] = np.where(
            commesse["Ricavi"] != 0,
            (
                commesse["Margine"]
                /
                commesse["Ricavi"]
                * 100
            ),
            0,
        )

        commesse = commesse.sort_values(
            "Margine",
            ascending=False,
        )

        st.dataframe(
            commesse,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )


# ============================================================
# COMMESSE
# ============================================================

elif pagina == "Commesse":

    st.markdown(
        '<div class="page-title">'
        'Commesse'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Vista economica aggregata delle commesse autorizzate.'
        '</div>',
        unsafe_allow_html=True,
    )

    df = filter_authorized(
        servizi
    )

    if df.empty:

        st.info(
            "Non sono presenti dati economici."
        )

    else:

        summary = (
            df.groupby(
                "Cantiere",
                as_index=False,
            )
            .agg(
                Ricavi=("Ricavo", "sum"),
                Costi=("Costo", "sum"),
                Margine=("Margine", "sum"),
                Tonnellate=(
                    "Tonnellate",
                    "sum",
                ),
                Registrazioni=(
                    "ID",
                    "count",
                ),
            )
        )

        summary["Margine %"] = np.where(
            summary["Ricavi"] != 0,
            summary["Margine"]
            /
            summary["Ricavi"]
            * 100,
            0,
        )

        summary["Costo / Ton"] = np.where(
            summary["Tonnellate"] != 0,
            summary["Costi"]
            /
            summary["Tonnellate"],
            0,
        )

        st.dataframe(
            summary.sort_values(
                "Margine",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
            column_config={

                "Ricavi":
                    st.column_config.NumberColumn(
                        "Ricavi",
                        format="€ %.2f",
                    ),

                "Costi":
                    st.column_config.NumberColumn(
                        "Costi",
                        format="€ %.2f",
                    ),

                "Margine":
                    st.column_config.NumberColumn(
                        "Margine",
                        format="€ %.2f",
                    ),

                "Margine %":
                    st.column_config.NumberColumn(
                        "Margine %",
                        format="%.1f%%",
                    ),

                "Tonnellate":
                    st.column_config.NumberColumn(
                        "Tonnellate",
                        format="%.1f",
                    ),

                "Costo / Ton":
                    st.column_config.NumberColumn(
                        "Costo / Ton",
                        format="€ %.2f",
                    ),
            },
        )


# ============================================================
# VALIDAZIONE TURNI
# ============================================================

elif pagina == "Validazione Turni":

    st.markdown(
        '<div class="page-title">'
        'Validazione turni'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Importazione e controllo dei dati operativi.'
        '</div>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Carica file turni",
        type=[
            "csv",
            "xlsx",
        ],
    )

    if uploaded_file:

        df_upload = pd.DataFrame()

        if uploaded_file.name.lower().endswith(
            ".csv"
        ):

            df_upload = (
                flexible_read_uploaded_csv(
                    uploaded_file
                )
            )

        elif uploaded_file.name.lower().endswith(
            ".xlsx"
        ):

            try:

                uploaded_file.seek(0)

                df_upload = pd.read_excel(
                    uploaded_file,
                    header=1,
                )

                df_upload = (
                    normalize_columns(
                        df_upload
                    )
                )

            except ImportError:

                st.error(
                    "Per importare file Excel "
                    "è necessario installare "
                    "openpyxl."
                )

                st.code(
                    "pip install openpyxl"
                )

            except Exception as exc:

                st.error(
                    f"Errore nella lettura del file Excel: "
                    f"{exc}"
                )

        if not df_upload.empty:

            st.success(
                f"File letto correttamente: "
                f"{len(df_upload)} righe."
            )

            st.dataframe(
                df_upload.head(100),
                use_container_width=True,
                hide_index=True,
            )

            if st.button(
                "Salva nello storico ore",
                type="primary",
            ):

                df_upload = (
                    rename_using_aliases(
                        df_upload,
                        ORE_ALIASES,
                    )
                )

                df_upload = ensure_columns(
                    df_upload,
                    [
                        "ID",
                        "Data",
                        "Operatore",
                        "Cantiere",
                        "Ore",
                        "Ore Extra",
                        "Tipo",
                    ],
                )

                df_upload["ID"] = (
                    df_upload["ID"]
                    .fillna("")
                    .astype(str)
                )

                mask_empty = (
                    df_upload["ID"]
                    .str.strip()
                    == ""
                )

                for idx in df_upload[
                    mask_empty
                ].index:

                    df_upload.loc[
                        idx,
                        "ID",
                    ] = make_id()

                ok = aggiorna_storico(
                    df_upload,
                    ORE_FILE,
                    "ID",
                )

                if ok:

                    st.success(
                        "Storico ore aggiornato."
                    )

                    st.rerun()

                else:

                    st.error(
                        "Errore nel salvataggio."
                    )

    st.markdown(
        "### Storico attuale"
    )

    storico_ore = filter_authorized(
        ore
    )

    if storico_ore.empty:

        st.info(
            "Nessun turno presente."
        )

    else:

        st.dataframe(
            storico_ore.tail(200),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# ORE
# ============================================================

elif pagina == "Ore":

    st.markdown(
        '<div class="page-title">'
        'Cruscotto ore'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Monitoraggio delle ore lavorate e delle anomalie.'
        '</div>',
        unsafe_allow_html=True,
    )

    df = filter_authorized(
        ore
    )

    if (
        commessa_filter
        != "Tutte le commesse"
        and
        not df.empty
    ):

        df = df[
            df["Cantiere"]
            .astype(str)
            .str.lower()
            .str.strip()
            ==
            commessa_filter
            .lower()
            .strip()
        ]

    if df.empty:

        st.info(
            "Nessun dato ore disponibile."
        )

    else:

        h1, h2, h3, h4 = st.columns(4)

        with h1:

            st.metric(
                "Ore lavorate",
                number_it(
                    df["Ore"].sum()
                ),
            )

        with h2:

            st.metric(
                "Ore extra",
                number_it(
                    df["Ore Extra"].sum()
                ),
            )

        with h3:

            st.metric(
                "Operatori",
                df["Operatore"].nunique(),
            )

        with h4:

            st.metric(
                "Turni",
                len(df),
            )

        st.write("")

        c1, c2 = st.columns(2)

        with c1:

            st.markdown(
                """
                <div class="panel">

                    <div class="panel-title">
                        Ore extra per operatore
                    </div>
                """,
                unsafe_allow_html=True,
            )

            by_operator = (
                df.groupby(
                    "Operatore"
                )["Ore Extra"]
                .sum()
                .sort_values(
                    ascending=False
                )
                .head(10)
            )

            if not by_operator.empty:

                st.bar_chart(
                    by_operator,
                    height=300,
                )

            else:

                st.info(
                    "Nessun dato."
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        with c2:

            st.markdown(
                """
                <div class="panel">

                    <div class="panel-title">
                        Ore per commessa
                    </div>
                """,
                unsafe_allow_html=True,
            )

            by_commessa = (
                df.groupby(
                    "Cantiere"
                )["Ore"]
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            st.bar_chart(
                by_commessa,
                height=300,
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div class="panel">

                <div class="panel-title">
                    Dettaglio turni
                </div>
            """,
            unsafe_allow_html=True,
        )

        st.dataframe(
            df.sort_values(
                "Data",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )


# ============================================================
# CENTRO DI COSTO
# ============================================================

elif pagina == "Centro di Costo":

    st.markdown(
        '<div class="page-title">'
        'Centro di costo'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Registrazione del servizio e calcolo della marginalità.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # TARIFFARIO
    # --------------------------------------------------------

    if is_admin():

        with st.expander(
            "⚙️ Configurazione tariffario",
            expanded=False,
        ):

            tariffe_edit = st.data_editor(
                tariffe,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
            )

            if st.button(
                "Salva tariffario",
                type="primary",
            ):

                ok = safe_to_csv(
                    tariffe_edit,
                    TARIFFE_FILE,
                )

                if ok:

                    st.success(
                        "Tariffario salvato."
                    )

                    st.rerun()

                else:

                    st.error(
                        "Errore nel salvataggio."
                    )

    # --------------------------------------------------------
    # NUOVO SERVIZIO
    # --------------------------------------------------------

    st.markdown(
        "### Nuovo servizio"
    )

    if commesse_disponibili:

        if is_admin():

            cantiere_options = (
                commesse_disponibili
            )

        else:

            cantiere_options = (
                commesse_disponibili
            )

        with st.form(
            "nuovo_servizio"
        ):

            # -----------------------------------------------
            # SERVIZIO
            # -----------------------------------------------

            st.markdown(
                "#### Servizio"
            )

            c1, c2 = st.columns(2)

            with c1:

                data_servizio = (
                    st.date_input(
                        "Data servizio",
                        value=date.today(),
                    )
                )

                categoria = st.selectbox(
                    "Tipo di servizio",
                    list(
                        STRUTTURA_SERVIZI.keys()
                    ),
                )

            with c2:

                dettagli = (
                    STRUTTURA_SERVIZI.get(
                        categoria,
                        [],
                    )
                )

                dettaglio = st.selectbox(
                    "Territorio / Commessa",
                    dettagli
                    if dettagli
                    else [""],
                )

                cantiere = st.selectbox(
                    "Commessa gestionale",
                    cantiere_options,
                )

            # -----------------------------------------------
            # PRODUZIONE
            # -----------------------------------------------

            st.markdown(
                "#### Produzione"
            )

            p1, p2 = st.columns(2)

            with p1:

                tonnellate = (
                    st.number_input(
                        "Tonnellate",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                    )
                )

            with p2:

                ricavo_fisso = (
                    st.number_input(
                        "Ricavo fisso (€)",
                        min_value=0.0,
                        value=0.0,
                        step=10.0,
                    )
                )

            # -----------------------------------------------
            # PERSONALE
            # -----------------------------------------------

            st.markdown(
                "#### Personale"
            )

            r1, r2 = st.columns(2)

            with r1:

                livello = st.selectbox(
                    "Livello",
                    [
                        "L1",
                        "L2",
                        "L3",
                        "L4",
                    ],
                )

            with r2:

                ore_personale_input = (
                    st.number_input(
                        "Ore personale",
                        min_value=0.0,
                        value=0.0,
                        step=0.5,
                    )
                )

            # -----------------------------------------------
            # MEZZI
            # -----------------------------------------------

            st.markdown(
                "#### Mezzi"
            )

            m1, m2 = st.columns(2)

            with m1:

                tipo_mezzo = st.selectbox(
                    "Tipo mezzo",
                    [
                        "Nessuno",
                        "Leggero",
                        "Compattatore",
                        "Pesante",
                        "Speciale",
                    ],
                )

            with m2:

                ore_mezzo_input = (
                    st.number_input(
                        "Ore mezzo",
                        min_value=0.0,
                        value=0.0,
                        step=0.5,
                    )
                )

            submit_service = (
                st.form_submit_button(
                    "Calcola e registra servizio",
                    type="primary",
                    use_container_width=True,
                )
            )

            # -----------------------------------------------
            # CALCOLO
            # -----------------------------------------------

            if submit_service:

                costo_personale = (
                    ore_personale_input
                    *
                    tariff(
                        tariffe,
                        "Personale",
                        livello,
                        28,
                    )
                )

                costo_mezzi = 0.0

                if (
                    tipo_mezzo
                    != "Nessuno"
                ):

                    costo_mezzi = (
                        ore_mezzo_input
                        *
                        tariff(
                            tariffe,
                            "Mezzi",
                            tipo_mezzo,
                            25,
                        )
                    )

                base_costi = (
                    costo_personale
                    +
                    costo_mezzi
                )

                overhead_pct = tariff(
                    tariffe,
                    "Generale",
                    "Overhead",
                    15,
                )

                costo_overhead = (
                    base_costi
                    *
                    overhead_pct
                    /
                    100
                )

                costo_totale = (
                    base_costi
                    +
                    costo_overhead
                )

                tariffa_ton = tariff(
                    tariffe,
                    "Generale",
                    "Tariffa tonnellata",
                    130,
                )

                ricavo_tonnellate = (
                    tonnellate
                    *
                    tariffa_ton
                )

                if ricavo_fisso > 0:

                    ricavo = (
                        ricavo_fisso
                    )

                else:

                    ricavo = (
                        ricavo_tonnellate
                    )

                margine = (
                    ricavo
                    -
                    costo_totale
                )

                nuovo = pd.DataFrame([
                    {
                        "ID": make_id(),

                        "Data":
                            pd.Timestamp(
                                data_servizio
                            ),

                        "Cantiere":
                            cantiere,

                        "Categoria":
                            categoria,

                        "Dettaglio":
                            dettaglio,

                        "Tonnellate":
                            tonnellate,

                        "Ricavo":
                            ricavo,

                        "Costo":
                            costo_totale,

                        "Margine":
                            margine,

                        "Ore Personale":
                            ore_personale_input,

                        "Ore Mezzi":
                            ore_mezzo_input,
                    }
                ])

                ok = aggiorna_storico(
                    nuovo,
                    SERVIZI_FILE,
                    "ID",
                )

                if ok:

                    st.success(
                        "Servizio registrato correttamente."
                    )

                    rc1, rc2, rc3 = st.columns(3)

                    with rc1:

                        st.metric(
                            "Ricavo",
                            euro(ricavo),
                        )

                    with rc2:

                        st.metric(
                            "Costo",
                            euro(costo_totale),
                        )

                    with rc3:

                        st.metric(
                            "Margine",
                            euro(margine),
                        )

                    st.rerun()

                else:

                    st.error(
                        "Impossibile salvare il servizio."
                    )

    else:

        st.warning(
            "Non risultano commesse disponibili."
        )

    # --------------------------------------------------------
    # STORICO
    # --------------------------------------------------------

    st.markdown(
        "### Analisi storica"
    )

    df_cc = filter_authorized(
        servizi
    )

    if not df_cc.empty:

        summary_cc = (
            df_cc
            .groupby(
                [
                    "Categoria",
                    "Dettaglio",
                ],
                as_index=False,
            )
            .agg(
                Costi=("Costo", "sum"),
                Ricavi=("Ricavo", "sum"),
                Margine=("Margine", "sum"),
                Tonnellate=(
                    "Tonnellate",
                    "sum",
                ),
            )
        )

        summary_cc["Costo / Ton"] = np.where(
            summary_cc["Tonnellate"] != 0,
            summary_cc["Costi"]
            /
            summary_cc["Tonnellate"],
            0,
        )

        summary_cc["Margine / Ton"] = np.where(
            summary_cc["Tonnellate"] != 0,
            summary_cc["Margine"]
            /
            summary_cc["Tonnellate"],
            0,
        )

        st.dataframe(
            summary_cc.sort_values(
                "Margine",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
            column_config={

                "Costi":
                    st.column_config.NumberColumn(
                        "Costi",
                        format="€ %.2f",
                    ),

                "Ricavi":
                    st.column_config.NumberColumn(
                        "Ricavi",
                        format="€ %.2f",
                    ),

                "Margine":
                    st.column_config.NumberColumn(
                        "Margine",
                        format="€ %.2f",
                    ),

                "Tonnellate":
                    st.column_config.NumberColumn(
                        "Tonnellate",
                        format="%.1f",
                    ),

                "Costo / Ton":
                    st.column_config.NumberColumn(
                        "Costo / Ton",
                        format="€ %.2f",
                    ),

                "Margine / Ton":
                    st.column_config.NumberColumn(
                        "Margine / Ton",
                        format="€ %.2f",
                    ),
            },
        )

    else:

        st.info(
            "Nessun servizio registrato."
        )


# ============================================================
# MEZZI
# ============================================================

elif pagina == "Mezzi":

    st.markdown(
        '<div class="page-title">'
        'Mezzi'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Monitoraggio mezzi e relativo impatto economico.'
        '</div>',
        unsafe_allow_html=True,
    )

    df_mezzi = filter_authorized(
        mezzi
    )

    if df_mezzi.empty:

        st.info(
            "Nessun mezzo presente."
        )

    else:

        m1, m2, m3 = st.columns(3)

        with m1:

            st.metric(
                "Mezzi censiti",
                len(df_mezzi),
            )

        with m2:

            categorie = (
                df_mezzi["Categoria"]
                .replace(
                    "",
                    np.nan,
                )
                .dropna()
                .nunique()
            )

            st.metric(
                "Categorie",
                categorie,
            )

        with m3:

            costo_medio = (
                df_mezzi[
                    "Costo Orario"
                ].replace(
                    0,
                    np.nan,
                ).mean()
            )

            if pd.isna(
                costo_medio
            ):
                costo_medio = 0

            st.metric(
                "Costo orario medio",
                euro(costo_medio),
            )

        st.write("")

        st.dataframe(
            df_mezzi,
            use_container_width=True,
            hide_index=True,
        )

        if (
            "Categoria"
            in df_mezzi.columns
        ):

            st.markdown(
                "### Mezzi per categoria"
            )

            by_category = (
                df_mezzi[
                    "Categoria"
                ].value_counts()
            )

            st.bar_chart(
                by_category,
                height=280,
            )


# ============================================================
# REPORT
# ============================================================

elif pagina == "Report":

    st.markdown(
        '<div class="page-title">'
        'Report & Export'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Esporta i dati economici e operativi filtrati.'
        '</div>',
        unsafe_allow_html=True,
    )

    df_report = filter_authorized(
        servizi
    )

    if (
        commessa_filter
        != "Tutte le commesse"
        and
        not df_report.empty
    ):

        df_report = df_report[
            df_report["Cantiere"]
            .astype(str)
            .str.lower()
            .str.strip()
            ==
            commessa_filter
            .lower()
            .strip()
        ]

    if not df_report.empty:

        csv_data = (
            df_report.to_csv(
                index=False,
                encoding="utf-8-sig",
            )
        )

        st.download_button(
            "⬇️ Scarica report economico CSV",
            data=csv_data,
            file_name="report_cristoforo.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown(
            "### Anteprima"
        )

        st.dataframe(
            df_report,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            "### Riepilogo"
        )

        r1, r2, r3, r4 = st.columns(4)

        with r1:

            st.metric(
                "Ricavi",
                euro(
                    df_report[
                        "Ricavo"
                    ].sum()
                ),
            )

        with r2:

            st.metric(
                "Costi",
                euro(
                    df_report[
                        "Costo"
                    ].sum()
                ),
            )

        with r3:

            st.metric(
                "Margine",
                euro(
                    df_report[
                        "Margine"
                    ].sum()
                ),
            )

        with r4:

            st.metric(
                "Tonnellate",
                number_it(
                    df_report[
                        "Tonnellate"
                    ].sum()
                ),
            )

    else:

        st.info(
            "Nessun dato disponibile."
        )


# ============================================================
# ANAGRAFICHE
# ============================================================

elif pagina == "Anagrafiche":

    if not is_admin():

        st.error(
            "Accesso riservato alla Direzione."
        )

        st.stop()

    st.markdown(
        '<div class="page-title">'
        'Anagrafiche'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Gestione operatori e mezzi.'
        '</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(
        [
            "Operatori",
            "Mezzi",
        ]
    )

    with tab1:

        st.markdown(
            "### Anagrafica operatori"
        )

        edited_operatori = (
            st.data_editor(
                operatori,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
            )
        )

        if st.button(
            "Salva operatori",
            type="primary",
        ):

            ok = safe_to_csv(
                edited_operatori,
                OPERATORI_FILE,
            )

            if ok:

                st.success(
                    "Anagrafica operatori aggiornata."
                )

                st.rerun()

            else:

                st.error(
                    "Errore nel salvataggio."
                )

        st.download_button(
            "Esporta operatori CSV",
            edited_operatori.to_csv(
                index=False,
                encoding="utf-8-sig",
            ),
            "anagrafica_operatori.csv",
            "text/csv",
        )

    with tab2:

        st.markdown(
            "### Anagrafica mezzi"
        )

        edited_mezzi = (
            st.data_editor(
                mezzi,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
            )
        )

        if st.button(
            "Salva mezzi",
            type="primary",
        ):

            ok = safe_to_csv(
                edited_mezzi,
                MEZZI_FILE,
            )

            if ok:

                st.success(
                    "Anagrafica mezzi aggiornata."
                )

                st.rerun()

            else:

                st.error(
                    "Errore nel salvataggio."
                )

        st.download_button(
            "Esporta mezzi CSV",
            edited_mezzi.to_csv(
                index=False,
                encoding="utf-8-sig",
            ),
            "anagrafica_mezzi.csv",
            "text/csv",
        )


# ============================================================
# GESTIONE ACCESSI
# ============================================================

elif pagina == "Gestione Accessi":

    if not is_admin():

        st.error(
            "Accesso riservato alla Direzione."
        )

        st.stop()

    st.markdown(
        '<div class="page-title">'
        'Gestione accessi'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Utenti, ruoli e commesse autorizzate.'
        '</div>',
        unsafe_allow_html=True,
    )

    users_current = read_users()

    st.info(
        "Nel campo 'cantieri' puoi indicare "
        "più commesse separate da virgola. "
        "Per l'accesso completo usa TUTTI."
    )

    edited_users = st.data_editor(
        users_current,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
    )

    if st.button(
        "Salva utenti",
        type="primary",
        use_container_width=True,
    ):

        edited_users = ensure_columns(
            edited_users,
            [
                "username",
                "password",
                "nome",
                "ruolo",
                "cantieri",
            ],
        )

        edited_users = edited_users[
            [
                "username",
                "password",
                "nome",
                "ruolo",
                "cantieri",
            ]
        ]

        ok = safe_to_csv(
            edited_users,
            UTENTI_FILE,
        )

        if ok:

            st.success(
                "Utenti salvati correttamente."
            )

            st.rerun()

        else:

            st.error(
                "Errore nel salvataggio utenti."
            )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        Cristoforo · Control Room ·
        Gestione operativa ed economica
    </div>
    """,
    unsafe_allow_html=True,
)
