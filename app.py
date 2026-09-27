import streamlit as st
import pandas as pd
import numpy as np
import os
import io
from datetime import datetime, date

# ============================================================
# CONFIGURAZIONE
# ============================================================

st.set_page_config(
    page_title="Cristoforo | Control Room",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
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
# CSS - CONTROL ROOM / SAAS PREMIUM
# ============================================================

st.markdown("""
<style>

    /* ------------------------------
       BASE
    ------------------------------ */

    .stApp {
        background: #f4f6f8;
    }

    .main .block-container {
        max-width: 1500px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    /* ------------------------------
       SIDEBAR
    ------------------------------ */

    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1f2937;
    }

    section[data-testid="stSidebar"] > div {
        background: #111827;
    }

    section[data-testid="stSidebar"] * {
        color: #e5e7eb;
    }

    .sidebar-logo {
        padding: 10px 8px 24px 8px;
    }

    .sidebar-logo img {
        max-width: 180px;
        max-height: 58px;
        object-fit: contain;
    }

    .sidebar-title {
        font-size: 12px;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 8px;
        margin-bottom: 18px;
    }

    .sidebar-user {
        background: #1f2937;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 18px;
    }

    .sidebar-user-name {
        font-weight: 700;
        color: white;
        font-size: 14px;
    }

    .sidebar-user-role {
        color: #9ca3af;
        font-size: 12px;
        margin-top: 3px;
    }

    /* ------------------------------
       HEADER
    ------------------------------ */

    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }

    .eyebrow {
        color: #6b7280;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.4px;
    }

    .page-title {
        color: #111827;
        font-size: 32px;
        font-weight: 800;
        line-height: 1.1;
        margin-top: 5px;
    }

    .page-subtitle {
        color: #6b7280;
        font-size: 14px;
        margin-top: 7px;
        margin-bottom: 25px;
    }

    .user-pill {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 30px;
        padding: 9px 15px;
        font-size: 13px;
        color: #374151;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }

    /* ------------------------------
       KPI CARDS
    ------------------------------ */

    .kpi-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 19px 20px;
        min-height: 145px;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.045);
    }

    .kpi-label {
        color: #6b7280;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.7px;
    }

    .kpi-value {
        color: #111827;
        font-size: 30px;
        font-weight: 800;
        margin-top: 12px;
        line-height: 1;
    }

    .kpi-value.green {
        color: #008b3a;
    }

    .kpi-value.red {
        color: #dc2626;
    }

    .kpi-value.orange {
        color: #d97706;
    }

    .kpi-meta {
        margin-top: 13px;
        font-size: 12px;
        color: #6b7280;
    }

    /* ------------------------------
       SECTION
    ------------------------------ */

    .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 28px;
        margin-bottom: 13px;
    }

    .section-title {
        color: #111827;
        font-size: 18px;
        font-weight: 800;
    }

    .section-description {
        color: #6b7280;
        font-size: 12px;
    }

    /* ------------------------------
       PANELS
    ------------------------------ */

    .panel {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.035);
    }

    /* ------------------------------
       BADGES
    ------------------------------ */

    .badge {
        display: inline-block;
        padding: 5px 9px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .3px;
    }

    .badge-ok {
        background: #dcfce7;
        color: #166534;
    }

    .badge-warning {
        background: #fef3c7;
        color: #92400e;
    }

    .badge-critical {
        background: #fee2e2;
        color: #991b1b;
    }

    .badge-neutral {
        background: #f3f4f6;
        color: #4b5563;
    }

    /* ------------------------------
       COMMESSA HERO
    ------------------------------ */

    .commessa-box {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dfe5e9;
        border-left: 5px solid #008b3a;
        border-radius: 16px;
        padding: 19px 22px;
        margin-bottom: 20px;
        box-shadow: 0 5px 20px rgba(15, 23, 42, 0.04);
    }

    .commessa-label {
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 10px;
        font-weight: 800;
    }

    .commessa-name {
        color: #111827;
        font-size: 23px;
        font-weight: 800;
        margin-top: 4px;
    }

    /* ------------------------------
       LOGIN
    ------------------------------ */

    .login-wrapper {
        max-width: 460px;
        margin: 70px auto;
    }

    .login-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 34px;
        box-shadow: 0 15px 50px rgba(15,23,42,0.08);
    }

    .login-title {
        font-size: 28px;
        font-weight: 800;
        color: #111827;
        margin-top: 15px;
    }

    .login-subtitle {
        color: #6b7280;
        font-size: 14px;
        margin-bottom: 25px;
    }

    /* ------------------------------
       STREAMLIT ELEMENTS
    ------------------------------ */

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 12px;
    }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid #d1d5db;
        font-weight: 700;
    }

    .stButton > button[kind="primary"] {
        background: #008b3a;
        border-color: #008b3a;
        color: white;
    }

    .stDownloadButton > button {
        border-radius: 10px;
        font-weight: 700;
    }

    div[data-baseweb="select"] > div {
        border-radius: 10px;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    /* ------------------------------
       TABLE HEADER
    ------------------------------ */

    .table-caption {
        color: #6b7280;
        font-size: 12px;
        margin-bottom: 8px;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATI DI DEFAULT
# ============================================================

DEFAULT_USERS = pd.DataFrame([
    {
        "username": "direzione",
        "password": "admin",
        "nome": "Direzione",
        "ruolo": "admin",
        "cantieri": "TUTTI"
    },
    {
        "username": "mario",
        "password": "123",
        "nome": "Mario Rossi",
        "ruolo": "capocantiere",
        "cantieri": "RACCOLTA PAP PRATO, RACCOLTA CARTONE SELETTIVO"
    },
    {
        "username": "luca",
        "password": "456",
        "nome": "Luca Bianchi",
        "ruolo": "capocantiere",
        "cantieri": "RACCOLTA PAP MANTOVA, Movimentazione Scarrabili"
    }
])

DEFAULT_TARIFFE = pd.DataFrame([
    {"categoria": "Personale", "voce": "L1", "costo": 22.0},
    {"categoria": "Personale", "voce": "L2", "costo": 25.0},
    {"categoria": "Personale", "voce": "L3", "costo": 28.0},
    {"categoria": "Personale", "voce": "L4", "costo": 32.0},
    {"categoria": "Mezzi", "voce": "Leggero", "costo": 15.0},
    {"categoria": "Mezzi", "voce": "Compattatore", "costo": 25.0},
    {"categoria": "Mezzi", "voce": "Pesante", "costo": 45.0},
    {"categoria": "Mezzi", "voce": "Speciale", "costo": 65.0},
    {"categoria": "Generale", "voce": "Overhead", "costo": 15.0},
    {"categoria": "Generale", "voce": "Tariffa tonnellata", "costo": 130.0},
])


# ============================================================
# FUNZIONI FILE
# ============================================================

def ensure_files():

    if not os.path.exists(UTENTI_FILE):
        DEFAULT_USERS.to_csv(UTENTI_FILE, index=False)

    if not os.path.exists(TARIFFE_FILE):
        DEFAULT_TARIFFE.to_csv(TARIFFE_FILE, index=False)

    if not os.path.exists(SERVIZI_FILE):
        pd.DataFrame(columns=[
            "ID",
            "Data",
            "Cantiere",
            "Categoria",
            "Dettaglio",
            "Tonnellate",
            "Ore Personale",
            "Ore Mezzi",
            "Ricavi",
            "Costo Personale",
            "Costo Mezzi",
            "Overhead",
            "Costo Totale",
            "Margine Netto",
            "Utente"
        ]).to_csv(SERVIZI_FILE, index=False)

    if not os.path.exists(ORE_FILE):
        pd.DataFrame().to_csv(ORE_FILE, index=False)


def load_csv(path):
    try:
        if os.path.exists(path):
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame()


def save_csv(df, path):
    df.to_csv(path, index=False)


def read_services():
    df = load_csv(SERVIZI_FILE)

    if df.empty:
        return df

    numeric_cols = [
        "Tonnellate",
        "Ore Personale",
        "Ore Mezzi",
        "Ricavi",
        "Costo Personale",
        "Costo Mezzi",
        "Overhead",
        "Costo Totale",
        "Margine Netto"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ".", regex=False),
                errors="coerce"
            ).fillna(0)

    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

    return df


def read_users():
    df = load_csv(UTENTI_FILE)

    if df.empty:
        df = DEFAULT_USERS.copy()

    return df


def read_tariffe():
    df = load_csv(TARIFFE_FILE)

    if df.empty:
        return DEFAULT_TARIFFE.copy()

    return df


# ============================================================
# UTILITY
# ============================================================

def euro(value):
    try:
        return f"€ {float(value):,.0f}".replace(",", ".")
    except Exception:
        return "€ 0"


def euro_decimal(value):
    try:
        return f"€ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "€ 0,00"


def number(value):
    try:
        return f"{float(value):,.0f}".replace(",", ".")
    except Exception:
        return "0"


def hours(value):
    try:
        return f"{float(value):,.1f}".replace(",", ".")
    except Exception:
        return "0,0"


def percent(value):
    try:
        return f"{float(value):.1f}%".replace(".", ",")
    except Exception:
        return "0,0%"


def badge_status(margin, revenue):

    if revenue <= 0:
        return '<span class="badge badge-neutral">NESSUN DATO</span>'

    pct = (margin / revenue) * 100

    if pct >= 15:
        return '<span class="badge badge-ok">OK</span>'

    if pct >= 5:
        return '<span class="badge badge-warning">ATTENZIONE</span>'

    return '<span class="badge badge-critical">CRITICO</span>'


def get_authorized_commesse():

    if st.session_state.get("ruolo") == "admin":
        return None

    cantieri = st.session_state.get("cantieri", "")

    if not cantieri:
        return []

    return [
        x.strip()
        for x in str(cantieri).split(",")
        if x.strip()
    ]


def filter_authorized(df, column="Cantiere"):

    if df.empty or column not in df.columns:
        return df

    authorized = get_authorized_commesse()

    if authorized is None:
        return df

    return df[df[column].isin(authorized)].copy()


def make_id():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


# ============================================================
# SESSIONE
# ============================================================

ensure_files()

if "loggato" not in st.session_state:
    st.session_state.loggato = False

if "utente" not in st.session_state:
    st.session_state.utente = ""

if "nome_utente" not in st.session_state:
    st.session_state.nome_utente = ""

if "ruolo" not in st.session_state:
    st.session_state.ruolo = ""

if "cantieri" not in st.session_state:
    st.session_state.cantieri = ""


# ============================================================
# LOGIN
# ============================================================

if not st.session_state.loggato:

    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)

    st.markdown("""
    <div class="login-card">
        <div style="font-size:38px;">♻️</div>
        <div class="login-title">Cristoforo Control Room</div>
        <div class="login-subtitle">
            Accesso al sistema operativo ed economico
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        submitted = st.form_submit_button(
            "Accedi alla Control Room",
            use_container_width=True,
            type="primary"
        )

        if submitted:

            users = read_users()

            match = users[
                (users["username"].astype(str) == username) &
                (users["password"].astype(str) == password)
            ]

            if not match.empty:

                row = match.iloc[0]

                st.session_state.loggato = True
                st.session_state.utente = row["username"]
                st.session_state.nome_utente = row.get("nome", row["username"])
                st.session_state.ruolo = row.get("ruolo", "capocantiere")
                st.session_state.cantieri = row.get("cantieri", "")

                st.rerun()

            else:
                st.error("Username o password non corretti.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# ============================================================
# DATI
# ============================================================

servizi = read_services()
servizi = filter_authorized(servizi)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    logo_path = os.path.join(BASE_DIR, "Cristoforo_2025_no-ONLUS.png")

    if os.path.exists(logo_path):
        st.image(logo_path, width=170)

    st.markdown(
        '<div class="sidebar-title">Control Room</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="sidebar-user">
            <div class="sidebar-user-name">
                ● {st.session_state.nome_utente}
            </div>
            <div class="sidebar-user-role">
                {st.session_state.ruolo.upper()}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.ruolo == "admin":

        menu_options = [
            "Overview",
            "Commesse",
            "Validazione Turni",
            "Ore",
            "Centro di Costo",
            "Anagrafiche",
            "Mezzi",
            "Report",
            "Gestione Accessi"
        ]

    else:

        menu_options = [
            "Overview",
            "Commesse",
            "Validazione Turni",
            "Ore",
            "Centro di Costo",
            "Mezzi",
            "Report"
        ]

    if "pagina" not in st.session_state:
        st.session_state.pagina = "Overview"

    for item in menu_options:

        if st.button(
            item,
            key=f"menu_{item}",
            use_container_width=True,
            type="primary" if st.session_state.pagina == item else "secondary"
        ):
            st.session_state.pagina = item
            st.rerun()

    st.markdown("---")

    if st.button(
        "Esci",
        use_container_width=True
    ):
        for key in [
            "loggato",
            "utente",
            "nome_utente",
            "ruolo",
            "cantieri"
        ]:
            st.session_state[key] = False if key == "loggato" else ""

        st.rerun()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    f"""
    <div class="top-header">
        <div>
            <div class="eyebrow">CRISTOFORO · OPERATIONS</div>
            <div class="page-title">{st.session_state.pagina}</div>
            <div class="page-subtitle">
                Controllo operativo, ore e gestione economica delle commesse
            </div>
        </div>
        <div class="user-pill">
            ● {st.session_state.nome_utente}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FILTRO GLOBALE
# ============================================================

if not servizi.empty and "Cantiere" in servizi.columns:

    available_commesse = sorted(
        servizi["Cantiere"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

else:
    available_commesse = []

authorized = get_authorized_commesse()

if authorized is not None:
    available_commesse = [
        x for x in available_commesse
        if x in authorized
    ]

filter_col1, filter_col2, filter_col3 = st.columns([2.2, 1.4, 1.4])

with filter_col1:

    if available_commesse:

        selected_commessa = st.selectbox(
            "COMMESSA",
            ["Tutte le commesse"] + available_commesse,
            key="global_commessa"
        )

    else:
        selected_commessa = "Tutte le commesse"

with filter_col2:

    periodo = st.selectbox(
        "PERIODO",
        [
            "Tutto",
            "Ultimi 7 giorni",
            "Ultimi 30 giorni",
            "Ultimi 90 giorni"
        ],
        key="global_periodo"
    )

with filter_col3:

    oggi = datetime.now().strftime("%d/%m/%Y")

    st.markdown(
        f"""
        <div style="padding-top:28px;color:#6b7280;font-size:12px;">
            AGGIORNATO<br>
            <strong style="color:#111827">{oggi}</strong>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# APPLICA FILTRI
# ============================================================

df = servizi.copy()

if selected_commessa != "Tutte le commesse" and "Cantiere" in df.columns:
    df = df[df["Cantiere"] == selected_commessa].copy()

if "Data" in df.columns:

    oggi_dt = pd.Timestamp.today()

    if periodo == "Ultimi 7 giorni":
        df = df[df["Data"] >= oggi_dt - pd.Timedelta(days=7)]

    elif periodo == "Ultimi 30 giorni":
        df = df[df["Data"] >= oggi_dt - pd.Timedelta(days=30)]

    elif periodo == "Ultimi 90 giorni":
        df = df[df["Data"] >= oggi_dt - pd.Timedelta(days=90)]


# ============================================================
# PAGE: OVERVIEW
# ============================================================

if st.session_state.pagina == "Overview":

    if selected_commessa == "Tutte le commesse":

        commessa_display = "Tutte le commesse autorizzate"

    else:

        commessa_display = selected_commessa

    st.markdown(
        f"""
        <div class="commessa-box">
            <div class="commessa-label">Vista operativa</div>
            <div class="commessa-name">{commessa_display}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # KPI

    ricavi = df["Ricavi"].sum() if "Ricavi" in df.columns else 0
    costi = df["Costo Totale"].sum() if "Costo Totale" in df.columns else 0
    margine = df["Margine Netto"].sum() if "Margine Netto" in df.columns else ricavi - costi
    tonnellate = df["Tonnellate"].sum() if "Tonnellate" in df.columns else 0
    ore_personale = df["Ore Personale"].sum() if "Ore Personale" in df.columns else 0
    ore_mezzi = df["Ore Mezzi"].sum() if "Ore Mezzi" in df.columns else 0

    margine_pct = (margine / ricavi * 100) if ricavi else 0

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Ricavi</div>
                <div class="kpi-value green">{euro(ricavi)}</div>
                <div class="kpi-meta">Valore servizi registrati</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Costi</div>
                <div class="kpi-value">{euro(costi)}</div>
                <div class="kpi-meta">Costo operativo complessivo</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k3:

        margin_class = "green" if margine >= 0 else "red"

        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Margine netto</div>
                <div class="kpi-value {margin_class}">
                    {euro(margine)}
                </div>
                <div class="kpi-meta">
                    Margine operativo · {percent(margine_pct)}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k4:

        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Tonnellate</div>
                <div class="kpi-value">{number(tonnellate)}</div>
                <div class="kpi-meta">
                    Ore personale: {hours(ore_personale)}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Stato

    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">Stato economico</div>
                <div class="section-description">
                    Lettura sintetica della redditività della selezione corrente
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2 = st.columns([1.4, 1])

    with c1:

        if not df.empty and "Data" in df.columns:

            trend = (
                df.dropna(subset=["Data"])
                .groupby(df["Data"].dt.date)
                .agg(
                    Ricavi=("Ricavi", "sum"),
                    Costi=("Costo Totale", "sum"),
                    Margine=("Margine Netto", "sum")
                )
                .reset_index()
                .rename(columns={"Data": "Giorno"})
            )

            if not trend.empty:

                st.markdown('<div class="panel">', unsafe_allow_html=True)

                st.markdown(
                    "**Andamento economico**"
                )

                chart_df = trend.set_index("Data" if "Data" in trend.columns else trend.columns[0])

                st.line_chart(
                    chart_df[["Ricavi", "Costi", "Margine"]],
                    use_container_width=True
                )

                st.markdown('</div>', unsafe_allow_html=True)

        else:

            st.info("Non ci sono ancora dati economici da visualizzare.")

    with c2:

        st.markdown('<div class="panel">', unsafe_allow_html=True)

        st.markdown("**Stato operativo**")

        st.markdown(
            badge_status(margine, ricavi),
            unsafe_allow_html=True
        )

        st.markdown("")

        st.metric(
            "Margine %",
            percent(margine_pct)
        )

        st.metric(
            "Ore mezzi",
            hours(ore_mezzi)
        )

        if tonnellate:
            st.metric(
                "Costo / ton",
                euro_decimal(costi / tonnellate)
            )

        st.markdown('</div>', unsafe_allow_html=True)

    # Centro di costo

    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">Centro di Costo</div>
                <div class="section-description">
                    Composizione dei costi operativi
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    cc1, cc2, cc3 = st.columns(3)

    costo_personale = (
        df["Costo Personale"].sum()
        if "Costo Personale" in df.columns
        else 0
    )

    costo_mezzi = (
        df["Costo Mezzi"].sum()
        if "Costo Mezzi" in df.columns
        else 0
    )

    overhead = (
        df["Overhead"].sum()
        if "Overhead" in df.columns
        else 0
    )

    with cc1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Personale</div>
                <div class="kpi-value">{euro(costo_personale)}</div>
                <div class="kpi-meta">
                    {hours(ore_personale)} ore
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with cc2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Mezzi</div>
                <div class="kpi-value">{euro(costo_mezzi)}</div>
                <div class="kpi-meta">
                    {hours(ore_mezzi)} ore mezzo
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with cc3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Overhead</div>
                <div class="kpi-value">{euro(overhead)}</div>
                <div class="kpi-meta">
                    Costi indiretti
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# PAGE: COMMESSE
# ============================================================

elif st.session_state.pagina == "Commesse":

    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">Performance commesse</div>
                <div class="section-description">
                    Confronto economico delle commesse autorizzate
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if df.empty:

        st.info("Non sono presenti dati per il periodo selezionato.")

    elif "Cantiere" not in df.columns:

        st.warning("La colonna Cantiere non è presente nei dati.")

    else:

        summary = (
            df.groupby("Cantiere")
            .agg(
                Ricavi=("Ricavi", "sum"),
                Costi=("Costo Totale", "sum"),
                Margine=("Margine Netto", "sum"),
                Tonnellate=("Tonnellate", "sum"),
                Ore=("Ore Personale", "sum")
            )
            .reset_index()
        )

        summary["Margine %"] = np.where(
            summary["Ricavi"] != 0,
            summary["Margine"] / summary["Ricavi"] * 100,
            0
        )

        summary["Stato"] = summary.apply(
            lambda r: "OK"
            if r["Margine %"] >= 15
            else "ATTENZIONE"
            if r["Margine %"] >= 5
            else "CRITICO",
            axis=1
        )

        display = summary.copy()

        display["Ricavi"] = display["Ricavi"].map(euro)
        display["Costi"] = display["Costi"].map(euro)
        display["Margine"] = display["Margine"].map(euro)
        display["Margine %"] = display["Margine %"].map(percent)
        display["Tonnellate"] = display["Tonnellate"].map(number)
        display["Ore"] = display["Ore"].map(hours)

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# PAGE: VALIDAZIONE TURNI
# ============================================================

elif st.session_state.pagina == "Validazione Turni":

    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">Validazione turni</div>
                <div class="section-description">
                    Importazione e controllo delle ore provenienti dai sistemi operativi
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Carica file turni",
        type=["csv", "xlsx"],
        help="CSV o Excel con intestazioni sulla seconda riga."
    )

    if uploaded_file:

        try:

            if uploaded_file.name.lower().endswith(".csv"):

                uploaded_df = pd.read_csv(
                    uploaded_file,
                    header=1
                )

            else:

                try:

                    uploaded_df = pd.read_excel(
                        uploaded_file,
                        header=1,
                        engine="openpyxl"
                    )

                except ImportError:

                    st.error(
                        "Per leggere file Excel devi aggiungere "
                        "`openpyxl` al requirements.txt."
                    )
                    st.stop()

            st.success(
                f"File caricato: {len(uploaded_df)} righe"
            )

            st.dataframe(
                uploaded_df.head(100),
                use_container_width=True,
                hide_index=True
            )

            if st.button(
                "Salva nello storico",
                type="primary"
            ):

                storico = load_csv(ORE_FILE)

                if storico.empty:
                    storico = uploaded_df.copy()

                else:
                    storico = pd.concat(
                        [storico, uploaded_df],
                        ignore_index=True
                    )

                # Deduplica se presente ID
                if "ID" in storico.columns:
                    storico = storico.drop_duplicates(
                        subset=["ID"],
                        keep="last"
                    )

                storico.to_csv(
                    ORE_FILE,
                    index=False
                )

                st.success("Storico aggiornato.")
                st.rerun()

        except Exception as exc:

            st.error(
                f"Errore durante la lettura del file: {exc}"
            )


# ============================================================
# PAGE: ORE
# ============================================================

elif st.session_state.pagina == "Ore":

    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">Cruscotto ore</div>
                <div class="section-description">
                    Analisi delle ore e delle principali anomalie
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    ore_df = load_csv(ORE_FILE)

    if ore_df.empty:

        st.info("Lo storico ore è ancora vuoto.")

    else:

        st.markdown(
            f"""
            <div class="panel">
                <div class="section-title">
                    {number(len(ore_df))} registrazioni
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Individua automaticamente una colonna ore
        possible_hours = [
            "Ore",
            "ore",
            "Ore Lavorate",
            "Ore Totali",
            "Durata",
            "Extra Ore"
        ]

        hour_col = None

        for col in possible_hours:
            if col in ore_df.columns:
                hour_col = col
                break

        if hour_col:

            ore_df[hour_col] = pd.to_numeric(
                ore_df[hour_col]
                .astype(str)
                .str.replace(",", ".", regex=False),
                errors="coerce"
            ).fillna(0)

            h1, h2, h3 = st.columns(3)

            with h1:
                st.metric(
                    "Ore totali",
                    hours(ore_df[hour_col].sum())
                )

            with h2:
                st.metric(
                    "Media / registrazione",
                    hours(ore_df[hour_col].mean())
                )

            with h3:
                st.metric(
                    "Registrazioni",
                    number(len(ore_df))
                )

            if "Data" in ore_df.columns:

                ore_df["Data"] = pd.to_datetime(
                    ore_df["Data"],
                    errors="coerce"
                )

                trend = (
                    ore_df.dropna(subset=["Data"])
                    .groupby(ore_df["Data"].dt.date)[hour_col]
                    .sum()
                )

                if not trend.empty:

                    st.markdown("### Andamento ore")

                    st.line_chart(
                        trend,
                        use_container_width=True
                    )

        st.markdown("### Storico")

        st.dataframe(
            ore_df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# PAGE: CENTRO DI COSTO
# ============================================================

elif st.session_state.pagina == "Centro di Costo":

    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">Centro di Costo</div>
                <div class="section-description">
                    Registrazione e controllo economico dei servizi
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    tariffe = read_tariffe()

    def tariffa(categoria, voce, default=0):
        try:
            row = tariffe[
                (tariffe["categoria"] == categoria) &
                (tariffe["voce"] == voce)
            ]

            if not row.empty:
                return float(row.iloc[0]["costo"])

        except Exception:
            pass

        return default

    # --------------------------------------------------------
    # TARIFFE ADMIN
    # --------------------------------------------------------

    if st.session_state.ruolo == "admin":

        with st.expander("⚙️ Configurazione tariffario"):

            edited_tariffe = st.data_editor(
                tariffe,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed"
            )

            if st.button(
                "Salva tariffario",
                type="primary"
            ):

                edited_tariffe.to_csv(
                    TARIFFE_FILE,
                    index=False
                )

                st.success("Tariffario salvato.")
                st.rerun()

    # --------------------------------------------------------
    # STRUTTURA SERVIZI
    # --------------------------------------------------------

    struttura_servizi = {
        "Spazzamento Stradale": [
            "Manuale",
            "Meccanizzato",
            "Misto"
        ],
        "Raccolta Porta a Porta": [
            "RACCOLTA PAP PRATO",
            "RACCOLTA PAP CAMPI",
            "RACCOLTA PAP VAIANO",
            "RACCOLTA PAP MANTOVA",
            "RACCOLTA PAP NOVENTA",
            "RACCOLTA PAP COSTABISSARA",
            "RACCOLTA PAP CREMONA"
        ],
        "Ritiro Ingombranti": [
            "A Domicilio",
            "Abbandoni Stradali"
        ],
        "Movimentazione Scarrabili": [
            "Centro di Raccolta (Ecocentro)",
            "Aziende Private / Terzi"
        ],
        "Raccolta Cartone Selettivo": [
            "Utenze Commerciali (Negozi)",
            "Grandi Produttori / Aziende"
        ]
    }

    with st.form("nuovo_servizio"):

        st.markdown("### Nuova registrazione")

        c1, c2, c3 = st.columns(3)

        with c1:

            servizio_data = st.date_input(
                "Data servizio",
                value=date.today()
            )

            if available_commesse:

                cantiere = st.selectbox(
                    "Commessa",
                    available_commesse
                )

            else:

                cantiere = st.text_input(
                    "Commessa"
                )

        with c2:

            categoria = st.selectbox(
                "Categoria",
                list(struttura_servizi.keys())
            )

            dettaglio = st.selectbox(
                "Dettaglio",
                struttura_servizi[categoria]
            )

        with c3:

            tonnellate = st.number_input(
                "Tonnellate",
                min_value=0.0,
                step=0.1
            )

            ricavo_tipo = st.radio(
                "Modalità ricavo",
                [
                    "Tariffa per tonnellata",
                    "Ricavo fisso"
                ],
                horizontal=True
            )

            if ricavo_tipo == "Tariffa per tonnellata":

                tariffa_ton = tariffa(
                    "Generale",
                    "Tariffa tonnellata",
                    130
                )

                ricavo = tonnellate * tariffa_ton

                st.caption(
                    f"Tariffa: {euro_decimal(tariffa_ton)} / ton"
                )

            else:

                ricavo = st.number_input(
                    "Ricavo servizio",
                    min_value=0.0,
                    step=100.0
                )

        st.markdown("### Risorse impiegate")

        r1, r2, r3, r4 = st.columns(4)

        with r1:

            livello_personale = st.selectbox(
                "Livello personale",
                ["L1", "L2", "L3", "L4"]
            )

            ore_personale = st.number_input(
                "Ore personale",
                min_value=0.0,
                step=0.5
            )

        with r2:

            tipo_mezzo = st.selectbox(
                "Tipo mezzo",
                [
                    "Leggero",
                    "Compattatore",
                    "Pesante",
                    "Speciale"
                ]
            )

            ore_mezzi = st.number_input(
                "Ore mezzi",
                min_value=0.0,
                step=0.5
            )

        with r3:

            costo_personale = (
                ore_personale *
                tariffa(
                    "Personale",
                    livello_personale,
                    22
                )
            )

            costo_mezzi = (
                ore_mezzi *
                tariffa(
                    "Mezzi",
                    tipo_mezzo,
                    15
                )
            )

            st.metric(
                "Costo diretto",
                euro(costo_personale + costo_mezzi)
            )

        with r4:

            overhead_pct = tariffa(
                "Generale",
                "Overhead",
                15
            )

            overhead = (
                costo_personale +
                costo_mezzi
            ) * overhead_pct / 100

            costo_totale = (
                costo_personale +
                costo_mezzi +
                overhead
            )

            margine = ricavo - costo_totale

            st.metric(
                "Margine stimato",
                euro(margine)
            )

        st.markdown("")

        salva = st.form_submit_button(
            "＋ Registra servizio",
            type="primary",
            use_container_width=True
        )

        if salva:

            if not cantiere:
                st.error("Inserisci una commessa.")
                st.stop()

            nuovo = pd.DataFrame([{
                "ID": make_id(),
                "Data": servizio_data,
                "Cantiere": cantiere,
                "Categoria": categoria,
                "Dettaglio": dettaglio,
                "Tonnellate": tonnellate,
                "Ore Personale": ore_personale,
                "Ore Mezzi": ore_mezzi,
                "Ricavi": ricavo,
                "Costo Personale": costo_personale,
                "Costo Mezzi": costo_mezzi,
                "Overhead": overhead,
                "Costo Totale": costo_totale,
                "Margine Netto": margine,
                "Utente": st.session_state.utente
            }])

            storico = read_services()

            storico = pd.concat(
                [storico, nuovo],
                ignore_index=True
            )

            storico.to_csv(
                SERVIZI_FILE,
                index=False
            )

            st.success(
                "Servizio registrato correttamente."
            )

            st.rerun()

    # --------------------------------------------------------
    # STORICO CENTRO COSTO
    # --------------------------------------------------------

    st.markdown("### Analisi storica")

    if df.empty:

        st.info("Nessuna registrazione presente.")

    else:

        group_cols = [
            "Categoria",
            "Dettaglio"
        ]

        existing = [
            x for x in group_cols
            if x in df.columns
        ]

        if existing:

            summary = (
                df.groupby(existing)
                .agg(
                    Costi=("Costo Totale", "sum"),
                    Ricavi=("Ricavi", "sum"),
                    Margine=("Margine Netto", "sum"),
                    Tonnellate=("Tonnellate", "sum")
                )
                .reset_index()
            )

            summary["Costo / ton"] = np.where(
                summary["Tonnellate"] > 0,
                summary["Costi"] / summary["Tonnellate"],
                0
            )

            summary["Margine / ton"] = np.where(
                summary["Tonnellate"] > 0,
                summary["Margine"] / summary["Tonnellate"],
                0
            )

            st.dataframe(
                summary,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Costi": st.column_config.NumberColumn(
                        "Costi",
                        format="€ %.2f"
                    ),
                    "Ricavi": st.column_config.NumberColumn(
                        "Ricavi",
                        format="€ %.2f"
                    ),
                    "Margine": st.column_config.NumberColumn(
                        "Margine",
                        format="€ %.2f"
                    ),
                    "Costo / ton": st.column_config.NumberColumn(
                        "Costo / ton",
                        format="€ %.2f"
                    ),
                    "Margine / ton": st.column_config.NumberColumn(
                        "Margine / ton",
                        format="€ %.2f"
                    )
                }
            )


# ============================================================
# PAGE: ANAGRAFICHE
# ============================================================

elif st.session_state.pagina == "Anagrafiche":

    if st.session_state.ruolo != "admin":

        st.warning("Sezione riservata alla Direzione.")

    else:

        st.markdown(
            """
            <div class="section-header">
                <div>
                    <div class="section-title">Anagrafiche</div>
                    <div class="section-description">
                        Operatori e risorse aziendali
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        tab1, tab2 = st.tabs([
            "Operatori",
            "Mezzi"
        ])

        with tab1:

            operatori = load_csv(OPERATORI_FILE)

            if operatori.empty:

                operatori = pd.DataFrame(
                    columns=[
                        "Matricola",
                        "Nome",
                        "Cognome",
                        "Livello",
                        "Commessa"
                    ]
                )

            edited = st.data_editor(
                operatori,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True
            )

            if st.button(
                "Salva operatori",
                type="primary"
            ):

                edited.to_csv(
                    OPERATORI_FILE,
                    index=False
                )

                st.success("Anagrafica operatori salvata.")
                st.rerun()

        with tab2:

            mezzi = load_csv(MEZZI_FILE)

            if mezzi.empty:

                mezzi = pd.DataFrame(
                    columns=[
                        "Targa",
                        "Descrizione",
                        "Tipo",
                        "Commessa"
                    ]
                )

            edited_mezzi = st.data_editor(
                mezzi,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True
            )

            if st.button(
                "Salva mezzi",
                type="primary"
            ):

                edited_mezzi.to_csv(
                    MEZZI_FILE,
                    index=False
                )

                st.success("Anagrafica mezzi salvata.")
                st.rerun()


# ============================================================
# PAGE: MEZZI
# ============================================================

elif st.session_state.pagina == "Mezzi":

    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">Mezzi</div>
                <div class="section-description">
                    Utilizzo e incidenza economica dei mezzi
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    mezzi = load_csv(MEZZI_FILE)

    if mezzi.empty:

        st.info("Non sono presenti dati nell'anagrafica mezzi.")

    else:

        st.dataframe(
            mezzi,
            use_container_width=True,
            hide_index=True
        )

    if not df.empty:

        c_mezzi = (
            df["Costo Mezzi"].sum()
            if "Costo Mezzi" in df.columns
            else 0
        )

        ore_mezzi_tot = (
            df["Ore Mezzi"].sum()
            if "Ore Mezzi" in df.columns
            else 0
        )

        a, b = st.columns(2)

        with a:

            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">Costo mezzi</div>
                    <div class="kpi-value">{euro(c_mezzi)}</div>
                    <div class="kpi-meta">Periodo selezionato</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with b:

            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">Ore mezzi</div>
                    <div class="kpi-value">{hours(ore_mezzi_tot)}</div>
                    <div class="kpi-meta">Utilizzo registrato</div>
                </div>
                """,
                unsafe_allow_html=True
            )


# ============================================================
# PAGE: REPORT
# ============================================================

elif st.session_state.pagina == "Report":

    st.markdown(
        """
        <div class="section-header">
            <div>
                <div class="section-title">Report & Export</div>
                <div class="section-description">
                    Esporta i dati economici della vista corrente
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if df.empty:

        st.info("Non ci sono dati da esportare.")

    else:

        csv_data = df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "⬇ Scarica dati economici CSV",
            data=csv_data,
            file_name=f"report_cristoforo_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.markdown("### Anteprima")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# PAGE: GESTIONE ACCESSI
# ============================================================

elif st.session_state.pagina == "Gestione Accessi":

    if st.session_state.ruolo != "admin":

        st.warning("Sezione riservata alla Direzione.")

    else:

        st.markdown(
            """
            <div class="section-header">
                <div>
                    <div class="section-title">Gestione Accessi</div>
                    <div class="section-description">
                        Utenti, ruoli e commesse autorizzate
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        users = read_users()

        edited_users = st.data_editor(
            users,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "password": st.column_config.TextColumn(
                    "Password",
                    help="Password dell'utente"
                ),
                "ruolo": st.column_config.SelectboxColumn(
                    "Ruolo",
                    options=[
                        "admin",
                        "capocantiere"
                    ]
                )
            }
        )

        if st.button(
            "Salva gestione accessi",
            type="primary"
        ):

            edited_users.to_csv(
                UTENTI_FILE,
                index=False
            )

            st.success(
                "Gestione accessi aggiornata."
            )

            st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div style="
        margin-top:45px;
        padding-top:15px;
        border-top:1px solid #e5e7eb;
        color:#9ca3af;
        font-size:11px;
        text-align:center;
    ">
        CRISTOFORO · CONTROL ROOM · Sistema operativo ed economico
    </div>
    """,
    unsafe_allow_html=True
)
