# ============================================================
# CRISTOFORO | CONTROL ROOM V9.0
# Cooperativa Cristoforo — Gestione Servizi Urbani
# ============================================================
import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import io, os, re, unicodedata, hashlib, hmac, json
from datetime import datetime, date
from pathlib import Path
from contextlib import contextmanager

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
APP_TITLE  = "Cristoforo Control Room"
APP_VER    = "V9.0"
DB_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cristoforo_v9.db")
SALT_BYTES = 32

st.set_page_config(page_title=APP_TITLE, page_icon="♻️", layout="wide")

# ─────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────
@contextmanager
def db_conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def init_db():
    with db_conn() as con:
        con.executescript("""
        -- Utenti
        CREATE TABLE IF NOT EXISTS users (
            username     TEXT PRIMARY KEY,
            pw_hash      TEXT NOT NULL,
            pw_salt      TEXT NOT NULL,
            role         TEXT NOT NULL DEFAULT 'operatore',
            display_name TEXT
        );

        -- Albero servizi (configurable)
        CREATE TABLE IF NOT EXISTS service_tree (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            servizio        TEXT NOT NULL,
            sottoservizio   TEXT NOT NULL DEFAULT '',
            tipo_fatturazione TEXT NOT NULL DEFAULT 'flat',
            tariffa         REAL DEFAULT 0,
            UNIQUE(servizio, sottoservizio)
        );

        -- CCNL tariffe orarie
        CREATE TABLE IF NOT EXISTS ccnl_rates (
            contratto   TEXT NOT NULL,
            livello     TEXT NOT NULL,
            costo_h     REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (contratto, livello)
        );

        -- Mapping commesse Cantieri Digitali
        CREATE TABLE IF NOT EXISTS mapping_commesse (
            cod_commessa  TEXT PRIMARY KEY,
            servizio      TEXT DEFAULT '',
            sottoservizio TEXT DEFAULT ''
        );

        -- Mapping tipi veicolo
        CREATE TABLE IF NOT EXISTS mapping_veicoli (
            tipo_cantieri TEXT PRIMARY KEY,
            tipo_interno  TEXT DEFAULT ''
        );

        -- Import batch (tracciamento)
        CREATE TABLE IF NOT EXISTS import_batch (
            id          TEXT PRIMARY KEY,
            source      TEXT,
            importato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note        TEXT
        );

        -- Servizi (consuntivo)
        CREATE TABLE IF NOT EXISTS services (
            id              TEXT PRIMARY KEY,
            batch_id        TEXT REFERENCES import_batch(id),
            data_da         DATE,
            data_a          DATE,
            servizio        TEXT,
            sottoservizio   TEXT,
            ore_personale   REAL DEFAULT 0,
            costo_personale REAL DEFAULT 0,
            ore_veicoli     REAL DEFAULT 0,
            costo_veicoli   REAL DEFAULT 0,
            note            TEXT
        );

        -- Dettaglio personale
        CREATE TABLE IF NOT EXISTS personale (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id  TEXT REFERENCES services(id) ON DELETE CASCADE,
            batch_id    TEXT,
            matricola   TEXT,
            operatore   TEXT,
            contratto   TEXT,
            livello     TEXT,
            ore         REAL DEFAULT 0,
            costo_h     REAL DEFAULT 0,
            costo_tot   REAL DEFAULT 0,
            data        DATE,
            stato_match TEXT
        );

        -- Dettaglio veicoli
        CREATE TABLE IF NOT EXISTS veicoli (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id  TEXT REFERENCES services(id) ON DELETE CASCADE,
            batch_id    TEXT,
            targa       TEXT,
            tipo        TEXT,
            tipo_interno TEXT,
            ore         REAL DEFAULT 0,
            data        DATE
        );

        -- Ingombranti
        CREATE TABLE IF NOT EXISTS ingombranti (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            data        DATE NOT NULL,
            comune      TEXT NOT NULL,
            peso_kg     REAL DEFAULT 0,
            num_ritiri  INTEGER DEFAULT 0,
            note        TEXT,
            creato_il   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

def seed_db():
    """Popola defaults se le tabelle sono vuote."""
    with db_conn() as con:
        # Admin default
        if not con.execute("SELECT 1 FROM users").fetchone():
            _salt = os.urandom(SALT_BYTES).hex()
            _hash = hashlib.pbkdf2_hmac("sha256", b"admin", bytes.fromhex(_salt), 200_000).hex()
            con.execute("INSERT INTO users VALUES (?,?,?,'admin','Amministratore')",
                        ("admin", _hash, _salt))

        # Tariffe CCNL Servizi Ambientali (Utilitalia) — aggiornabili da admin
        if not con.execute("SELECT 1 FROM ccnl_rates").fetchone():
            rates_sa = [
                ("Servizi Ambientali","1",  16.50),
                ("Servizi Ambientali","2",  17.20),
                ("Servizi Ambientali","2B", 18.10),
                ("Servizi Ambientali","3",  18.90),
                ("Servizi Ambientali","3B", 19.80),
                ("Servizi Ambientali","4",  20.70),
                ("Servizi Ambientali","4B", 21.90),
                ("Servizi Ambientali","5",  23.20),
                ("Servizi Ambientali","6",  25.40),
                ("Servizi Ambientali","7",  28.10),
                ("Cooperative Sociali","A", 14.80),
                ("Cooperative Sociali","B", 16.10),
                ("Cooperative Sociali","B1",16.90),
                ("Cooperative Sociali","C", 17.80),
                ("Cooperative Sociali","C1",18.70),
                ("Cooperative Sociali","D", 19.90),
                ("Cooperative Sociali","D1",21.20),
                ("Cooperative Sociali","E", 23.00),
            ]
            con.executemany(
                "INSERT OR IGNORE INTO ccnl_rates VALUES (?,?,?)", rates_sa)

        # Service tree default
        if not con.execute("SELECT 1 FROM service_tree").fetchone():
            tree = [
                ("Porta a Porta","Prato","flat",0),
                ("Porta a Porta","Firenze","flat",0),
                ("Porta a Porta","Scandicci","flat",0),
                ("Porta a Porta","Signa","flat",0),
                ("Raccolta Cartone Selettivo","Firenze","flat",0),
                ("Spazzamento","Prato","flat",0),
                ("Spazzamento","Calenzano","flat",0),
                ("Ingombranti","Prato","ton",0),
                ("Ingombranti","Firenze","ton",0),
                ("Scarrabili","Prato","km",0),
            ]
            con.executemany(
                "INSERT OR IGNORE INTO service_tree(servizio,sottoservizio,tipo_fatturazione,tariffa) VALUES(?,?,?,?)",
                tree)

        # Mapping commesse default
        if not con.execute("SELECT 1 FROM mapping_commesse").fetchone():
            commesse = [
                ("CRS_PRATO",        "Porta a Porta",              "Prato"),
                ("CRS_FIRENZE",      "Raccolta Cartone Selettivo",  "Firenze"),
                ("CRS_SCANDICCI",    "Porta a Porta",              "Scandicci"),
                ("CRS_SIGNA",        "Porta a Porta",              "Signa"),
                ("CRS_CALENZANO",    "Porta a Porta",              "Calenzano"),
                ("CRS_CAMPI",        "Porta a Porta",              "Campi Bisenzio"),
                ("CRS_SESTO",        "Porta a Porta",              "Sesto Fiorentino"),
                ("CRS_LASTRA",       "Porta a Porta",              "Lastra a Signa"),
                ("CRS_SPAZZ_PRATO",  "Spazzamento",                "Prato"),
                ("CRS_SPAZZ_CAL",    "Spazzamento",                "Calenzano"),
                ("CRS_ING_PRATO",    "Ingombranti",                "Prato"),
                ("CRS_ING_FI",       "Ingombranti",                "Firenze"),
                ("CRS_SCARR_PRATO",  "Scarrabili",                 "Prato"),
                ("CRS_VALDARNO",     "",                           ""),
                ("CRS_EX_ELICA",     "",                           ""),
            ]
            con.executemany(
                "INSERT OR IGNORE INTO mapping_commesse VALUES (?,?,?)", commesse)

        # Mapping veicoli default
        if not con.execute("SELECT 1 FROM mapping_veicoli").fetchone():
            veicoli = [
                ("Costipatore 35 q.li",      "35 qt"),
                ("Compattatore 3 Assi",       "8. 3 Assi 21/27mc"),
                ("Compattatore 2 Assi",       "7. 2 Assi 16/21mc"),
                ("Vasca laterale",            "Vasca laterale"),
                ("Scarrabile",                "Scarrabile"),
                ("Furgone",                   "Furgone"),
                ("Spazzatrice",               "Spazzatrice"),
            ]
            con.executemany(
                "INSERT OR IGNORE INTO mapping_veicoli VALUES (?,?)", veicoli)

# ─────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────
def _hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()

def verify_user(username: str, password: str):
    with db_conn() as con:
        row = con.execute(
            "SELECT pw_hash, pw_salt, role, display_name FROM users WHERE username=?",
            (username,)).fetchone()
    if not row:
        return None
    if hmac.compare_digest(_hash_pw(password, row["pw_salt"]), row["pw_hash"]):
        return {"username": username, "role": row["role"], "display_name": row["display_name"]}
    return None

def is_admin():
    return st.session_state.get("user", {}).get("role") in ("admin", "direzione")

def require_login():
    if "user" not in st.session_state:
        _show_login()
        st.stop()

def _show_login():
    st.markdown(f"<h1 style='text-align:center;margin-top:3rem'>♻️ {APP_TITLE}</h1>", unsafe_allow_html=True)
    col = st.columns([1, 1, 1])[1]
    with col:
        with st.form("login_form"):
            u = st.text_input("Utente")
            p = st.text_input("Password", type="password")
            ok = st.form_submit_button("Accedi", use_container_width=True)
        if ok:
            user = verify_user(u, p)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Credenziali non valide.")

# ─────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────
def normalize_level(raw) -> str:
    """'LIVELLO 2B' → '2B', 'livello .B1' → 'B1', None → ''"""
    if not isinstance(raw, str) or not raw.strip():
        return str(raw).strip() if raw else ""
    s = unicodedata.normalize("NFC", raw).strip()
    s = re.sub(r"(?i)^livello\s*\.?\s*", "", s)
    s = re.sub(r"[.\s]+", "", s)
    return s.upper()

def get_costo_h(contratto: str, livello: str) -> float:
    liv = normalize_level(livello)
    with db_conn() as con:
        row = con.execute(
            "SELECT costo_h FROM ccnl_rates WHERE contratto=? AND livello=?",
            (contratto, liv)).fetchone()
    return float(row["costo_h"]) if row else 0.0

def excel_bytes(file_obj) -> io.BytesIO:
    """Converte UploadedFile in BytesIO rileggibile più volte."""
    return io.BytesIO(file_obj.getvalue())

def load_excel_sheet(file_obj, prefer_sheet="FOGLIO UNO") -> pd.DataFrame:
    buf = excel_bytes(file_obj)
    sheets = pd.ExcelFile(buf).sheet_names
    sheet = prefer_sheet if prefer_sheet in sheets else sheets[0]
    buf.seek(0)
    df = pd.read_excel(buf, sheet_name=sheet, dtype=str)
    df = df[[c for c in df.columns if not str(c).startswith("Unnamed")]]
    return df

def fmt_eur(v) -> str:
    try:
        return f"€ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

def fmt_h(v) -> str:
    try:
        return f"{float(v):,.1f} h".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

def batch_id_now(prefix="CD") -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    /* Font & base */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 1.5rem; }

    /* KPI tiles */
    .kpi-row { display:flex; gap:1rem; margin-bottom:1.5rem; flex-wrap:wrap; }
    .kpi { background:var(--secondary-background-color);
           border-radius:10px; padding:1rem 1.5rem;
           flex:1; min-width:140px; }
    .kpi .label { font-size:.75rem; color:#888; text-transform:uppercase;
                  letter-spacing:.05em; margin-bottom:.25rem; }
    .kpi .value { font-size:1.6rem; font-weight:700; color:var(--text-color); }
    .kpi .sub   { font-size:.8rem; color:#aaa; margin-top:.15rem; }

    /* Section header */
    .sec-head { font-size:1.1rem; font-weight:600; margin:1.5rem 0 .75rem;
                padding-bottom:.35rem; border-bottom:2px solid #22c55e; }

    /* Pill badge */
    .pill { display:inline-block; padding:.15rem .6rem; border-radius:20px;
            font-size:.75rem; font-weight:600; }
    .pill-green { background:#dcfce7; color:#15803d; }
    .pill-red   { background:#fee2e2; color:#b91c1c; }
    .pill-gray  { background:#f1f5f9; color:#475569; }

    /* Footer */
    .foot { position:fixed; bottom:0; left:0; width:100%;
            background:var(--background-color); border-top:1px solid #e2e8f0;
            text-align:center; font-size:.7rem; color:#94a3b8; padding:.35rem; }
    </style>
    """, unsafe_allow_html=True)

def kpi(label, value, sub=""):
    return f"""<div class="kpi">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      {"<div class='sub'>" + sub + "</div>" if sub else ""}
    </div>"""

def sec(title):
    st.markdown(f'<div class="sec-head">{title}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────
def page_dashboard():
    sec("📊 Riepilogo generale")
    with db_conn() as con:
        n_batch   = con.execute("SELECT COUNT(*) FROM import_batch").fetchone()[0]
        tot_h_p   = con.execute("SELECT COALESCE(SUM(ore),0) FROM personale").fetchone()[0]
        tot_costo = con.execute("SELECT COALESCE(SUM(costo_tot),0) FROM personale").fetchone()[0]
        tot_h_v   = con.execute("SELECT COALESCE(SUM(ore),0) FROM veicoli").fetchone()[0]
        n_ing     = con.execute("SELECT COUNT(*) FROM ingombranti").fetchone()[0]
        kg_ing    = con.execute("SELECT COALESCE(SUM(peso_kg),0) FROM ingombranti").fetchone()[0]

    st.markdown(f"""<div class="kpi-row">
      {kpi("Import eseguiti", n_batch)}
      {kpi("Ore personale", fmt_h(tot_h_p))}
      {kpi("Costo personale", fmt_eur(tot_costo))}
      {kpi("Ore veicoli", fmt_h(tot_h_v))}
      {kpi("Ritiri ingombranti", n_ing, f"{kg_ing/1000:,.1f} t totali")}
    </div>""", unsafe_allow_html=True)

    # Grafico costi per servizio
    sec("💶 Costi per servizio")
    with db_conn() as con:
        df = pd.read_sql("""
            SELECT s.servizio, ROUND(SUM(p.costo_tot),2) AS costo
            FROM services s
            JOIN personale p ON p.service_id = s.id
            GROUP BY s.servizio ORDER BY costo DESC
        """, con)
    if not df.empty:
        st.bar_chart(df.set_index("servizio")["costo"])
    else:
        st.info("Nessun dato ancora. Esegui un import da Cantieri Digitali.")

    # Ultimi import
    sec("🕑 Ultimi import")
    with db_conn() as con:
        df_b = pd.read_sql(
            "SELECT id, source, importato_il, note FROM import_batch ORDER BY importato_il DESC LIMIT 10",
            con)
    if not df_b.empty:
        st.dataframe(df_b, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun import ancora.")

# ─────────────────────────────────────────────────────────────
# PAGE: INGOMBRANTI
# ─────────────────────────────────────────────────────────────
def page_ingombranti():
    sec("🗑️ Gestione Ingombranti")
    tab_ins, tab_lista = st.tabs(["➕ Inserisci", "📋 Storico"])

    with tab_ins:
        with st.form("form_ing"):
            c1, c2 = st.columns(2)
            data_r   = c1.date_input("Data ritiro", value=date.today())
            comune   = c2.text_input("Comune")
            peso_kg  = c1.number_input("Peso (kg)", min_value=0.0, step=10.0)
            n_ritiri = c2.number_input("N° ritiri", min_value=0, step=1)
            note     = st.text_input("Note")
            salva    = st.form_submit_button("💾 Salva", use_container_width=True)

        if salva:
            if not comune.strip():
                st.error("Inserisci il comune.")
            else:
                with db_conn() as con:
                    con.execute(
                        "INSERT INTO ingombranti(data,comune,peso_kg,num_ritiri,note) VALUES(?,?,?,?,?)",
                        (data_r.isoformat(), comune.strip(), peso_kg, int(n_ritiri), note.strip()))
                st.success("Salvato.")
                st.rerun()

    with tab_lista:
        with db_conn() as con:
            df = pd.read_sql(
                "SELECT data, comune, peso_kg, num_ritiri, note FROM ingombranti ORDER BY data DESC",
                con)
        if df.empty:
            st.info("Nessun record.")
        else:
            # KPI
            tot_kg = df["peso_kg"].sum()
            st.markdown(f"""<div class="kpi-row">
              {kpi("Totale kg", f"{tot_kg:,.0f}")}
              {kpi("Totale tonnellate", f"{tot_kg/1000:,.2f}")}
              {kpi("N° ritiri", f"{df['num_ritiri'].sum():,.0f}")}
            </div>""", unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────
# CANTIERI DIGITALI — PARSER
# ─────────────────────────────────────────────────────────────
def _parse_personale(file_obj) -> pd.DataFrame:
    df = load_excel_sheet(file_obj)
    df["Durata (h)"]  = pd.to_numeric(
        df.get("Durata (h)", pd.Series(dtype=str)).str.replace(",", "."), errors="coerce").fillna(0.0)
    df["Data Inizio"] = pd.to_datetime(
        df.get("Data Inizio", pd.Series(dtype=str)), dayfirst=True, errors="coerce")
    return df

def _parse_veicoli(file_obj) -> pd.DataFrame:
    df = load_excel_sheet(file_obj)
    df["Durata (h)"]  = pd.to_numeric(
        df.get("Durata (h)", pd.Series(dtype=str)).str.replace(",", "."), errors="coerce").fillna(0.0)
    df["Data Inizio"] = pd.to_datetime(
        df.get("Data Inizio", pd.Series(dtype=str)), dayfirst=True, errors="coerce")
    return df

def _get_mapping_commesse() -> dict:
    with db_conn() as con:
        rows = con.execute("SELECT cod_commessa, servizio, sottoservizio FROM mapping_commesse").fetchall()
    return {r["cod_commessa"]: (r["servizio"], r["sottoservizio"]) for r in rows}

def _get_mapping_veicoli() -> dict:
    with db_conn() as con:
        rows = con.execute("SELECT tipo_cantieri, tipo_interno FROM mapping_veicoli").fetchall()
    return {r["tipo_cantieri"]: r["tipo_interno"] for r in rows}

def _elabora_import(df_p: pd.DataFrame, df_v: pd.DataFrame) -> dict:
    """
    Aggrega per commessa. Ritorna dict:
      cod → {servizio, sottoservizio, data_da, data_a, pers_rows, veic_rows}
    """
    map_c = _get_mapping_commesse()
    map_v = _get_mapping_veicoli()
    result = {}

    # ---- Personale ----
    for _, row in df_p.iterrows():
        if str(row.get("Stato Servizio", "")).strip().upper() not in ("ESEGUITO", "CONFERMATO", ""):
            pass  # accetta tutti gli stati per ora
        cod      = str(row.get("Cod Commessa", "")).strip()
        if not cod:
            continue
        svc, sub = map_c.get(cod, ("", ""))
        livello  = normalize_level(str(row.get("Livello", "")))
        ore      = float(row.get("Durata (h)", 0) or 0)
        contratto = "Servizi Ambientali"  # default; TODO: ricavare da UOT/matricola
        costo_h  = get_costo_h(contratto, livello)
        data_ts  = row.get("Data Inizio")

        slot = result.setdefault(cod, {
            "servizio": svc, "sottoservizio": sub,
            "data_da": None, "data_a": None,
            "pers_rows": [], "veic_rows": [],
        })
        if pd.notna(data_ts):
            slot["data_da"] = min(slot["data_da"], data_ts) if slot["data_da"] else data_ts
            slot["data_a"]  = max(slot["data_a"],  data_ts) if slot["data_a"]  else data_ts

        slot["pers_rows"].append({
            "matricola":   str(row.get("Matricola", "")).strip(),
            "operatore":   str(row.get("Dipendente", "")).strip(),
            "contratto":   contratto,
            "livello":     livello,
            "ore":         ore,
            "costo_h":     costo_h,
            "costo_tot":   round(ore * costo_h, 4),
            "data":        data_ts.date().isoformat() if pd.notna(data_ts) else None,
            "stato_match": "Trovato" if costo_h > 0 else "Livello non trovato",
        })

    # ---- Veicoli ----
    for _, row in df_v.iterrows():
        cod = str(row.get("Cod Commessa", "")).strip()
        if not cod:
            continue
        svc, sub = map_c.get(cod, ("", ""))
        tipo_cd  = str(row.get("Tipo Veicolo", "")).strip()
        tipo_int = map_v.get(tipo_cd, tipo_cd)
        ore      = float(row.get("Durata (h)", 0) or 0)
        data_ts  = row.get("Data Inizio")

        slot = result.setdefault(cod, {
            "servizio": svc, "sottoservizio": sub,
            "data_da": None, "data_a": None,
            "pers_rows": [], "veic_rows": [],
        })
        if pd.notna(data_ts):
            slot["data_da"] = min(slot["data_da"], data_ts) if slot["data_da"] else data_ts
            slot["data_a"]  = max(slot["data_a"],  data_ts) if slot["data_a"]  else data_ts

        slot["veic_rows"].append({
            "targa":       str(row.get("Targa", "")).strip(),
            "tipo":        tipo_cd,
            "tipo_interno":tipo_int,
            "ore":         ore,
            "data":        data_ts.date().isoformat() if pd.notna(data_ts) else None,
        })

    return result

# ─────────────────────────────────────────────────────────────
# PAGE: CANTIERI DIGITALI
# ─────────────────────────────────────────────────────────────
def page_cantieri_digitali():
    sec("📥 Importa da Cantieri Digitali")

    tab_map_c, tab_map_v, tab_import = st.tabs([
        "🗂️ Mapping Commesse",
        "🚛 Mapping Veicoli",
        "⬆️ Importa Dati",
    ])

    # ── Tab 1: Mapping commesse ──────────────────────────────
    with tab_map_c:
        st.caption("Associa ogni codice commessa di Cantieri Digitali a Servizio e Sottoservizio interno.")
        with db_conn() as con:
            df_mc = pd.read_sql(
                "SELECT cod_commessa, servizio, sottoservizio FROM mapping_commesse ORDER BY cod_commessa",
                con)
        edited = st.data_editor(df_mc, use_container_width=True, num_rows="dynamic",
                                 key="de_commesse")
        if st.button("💾 Salva mapping commesse", key="save_mc"):
            with db_conn() as con:
                con.execute("DELETE FROM mapping_commesse")
                con.executemany(
                    "INSERT INTO mapping_commesse VALUES(?,?,?)",
                    [(r["cod_commessa"], r["servizio"], r["sottoservizio"])
                     for _, r in edited.iterrows() if str(r["cod_commessa"]).strip()])
            st.success("Mapping commesse salvato.")

    # ── Tab 2: Mapping veicoli ───────────────────────────────
    with tab_map_v:
        st.caption("Associa il nome tipo veicolo di Cantieri Digitali al tipo interno.")
        with db_conn() as con:
            df_mv = pd.read_sql(
                "SELECT tipo_cantieri, tipo_interno FROM mapping_veicoli ORDER BY tipo_cantieri",
                con)
        edited_v = st.data_editor(df_mv, use_container_width=True, num_rows="dynamic",
                                   key="de_veicoli")
        if st.button("💾 Salva mapping veicoli", key="save_mv"):
            with db_conn() as con:
                con.execute("DELETE FROM mapping_veicoli")
                con.executemany(
                    "INSERT INTO mapping_veicoli VALUES(?,?)",
                    [(r["tipo_cantieri"], r["tipo_interno"])
                     for _, r in edited_v.iterrows() if str(r["tipo_cantieri"]).strip()])
            st.success("Mapping veicoli salvato.")

    # ── Tab 3: Import ────────────────────────────────────────
    with tab_import:
        st.caption("Carica i due file Excel esportati da Cantieri Digitali (Personale + Veicoli).")

        c1, c2 = st.columns(2)
        file_p = c1.file_uploader("📄 File Personale (ore dipendenti)", type=["xlsx","xls"], key="up_pers")
        file_v = c2.file_uploader("📄 File Veicoli (ore veicoli)",       type=["xlsx","xls"], key="up_veic")

        if not file_p and not file_v:
            st.info("Carica almeno uno dei due file per procedere.")
            return

        with st.spinner("Lettura file in corso..."):
            df_p = _parse_personale(file_p) if file_p else pd.DataFrame()
            df_v = _parse_veicoli(file_v)   if file_v else pd.DataFrame()

        # Anteprima file caricati
        with st.expander("🔍 Anteprima file caricati"):
            if not df_p.empty:
                st.markdown("**Personale** — prime 5 righe")
                st.dataframe(df_p.head(), use_container_width=True)
            if not df_v.empty:
                st.markdown("**Veicoli** — prime 5 righe")
                st.dataframe(df_v.head(), use_container_width=True)

        # Elaborazione
        with st.spinner("Elaborazione..."):
            result = _elabora_import(df_p, df_v)

        if not result:
            st.error("Nessuna commessa trovata nei file. Verifica che la colonna 'Cod Commessa' sia presente.")
            return

        # Riepilogo per commessa
        sec("📋 Riepilogo per commessa")
        rows_prev = []
        for cod, s in sorted(result.items()):
            ore_p  = sum(r["ore"] for r in s["pers_rows"])
            costo  = sum(r["costo_tot"] for r in s["pers_rows"])
            ore_v  = sum(r["ore"] for r in s["veic_rows"])
            rows_prev.append({
                "Commessa":     cod,
                "Servizio":     s["servizio"] or "⚠️ non mappato",
                "Sottoservizio":s["sottoservizio"],
                "Da":           str(s["data_da"].date()) if s["data_da"] else "—",
                "A":            str(s["data_a"].date())  if s["data_a"]  else "—",
                "Ore pers.":    round(ore_p, 1),
                "Costo pers.":  round(costo, 2),
                "Ore veic.":    round(ore_v, 1),
            })
        df_prev = pd.DataFrame(rows_prev)
        st.dataframe(df_prev, use_container_width=True, hide_index=True)

        # Avvisi commesse non mappate
        non_mappate = [cod for cod, s in result.items() if not s["servizio"]]
        if non_mappate:
            st.warning(f"⚠️ {len(non_mappate)} commessa/e senza Servizio assegnato: "
                       f"{', '.join(non_mappate)}. Configurale nel tab 'Mapping Commesse'.")

        salvabili = [cod for cod, s in result.items() if s["servizio"]]
        if not salvabili:
            st.error("Nessuna commessa mappata. Configura il Mapping Commesse prima di salvare.")
            return

        # Controllo duplicati
        batch_ids_esistenti = set()
        with db_conn() as con:
            rows_dup = con.execute("SELECT id FROM import_batch").fetchall()
        # (deduplication per batch_id è sufficiente — ogni import ha timestamp unico)

        col_note, col_btn = st.columns([3, 1])
        note_import = col_note.text_input("Note import (opzionale)", key="note_import")
        if col_btn.button("💾 Salva import", use_container_width=True, type="primary"):
            bid = batch_id_now("CD")
            with db_conn() as con:
                con.execute("INSERT INTO import_batch(id,source,note) VALUES(?,?,?)",
                            (bid, "Cantieri Digitali", note_import.strip()))
                for cod in salvabili:
                    s    = result[cod]
                    svc  = s["servizio"]
                    sub  = s["sottoservizio"]
                    da   = s["data_da"].date().isoformat() if s["data_da"] else None
                    a    = s["data_a"].date().isoformat()  if s["data_a"]  else None
                    ore_p  = sum(r["ore"] for r in s["pers_rows"])
                    costo_p= sum(r["costo_tot"] for r in s["pers_rows"])
                    ore_v  = sum(r["ore"] for r in s["veic_rows"])
                    sid  = f"{bid}-{cod.replace(' ', '_')}"

                    con.execute("""
                        INSERT OR REPLACE INTO services
                          (id,batch_id,data_da,data_a,servizio,sottoservizio,
                           ore_personale,costo_personale,ore_veicoli)
                        VALUES (?,?,?,?,?,?,?,?,?)
                    """, (sid, bid, da, a, svc, sub, ore_p, costo_p, ore_v))

                    con.executemany("""
                        INSERT INTO personale
                          (service_id,batch_id,matricola,operatore,contratto,
                           livello,ore,costo_h,costo_tot,data,stato_match)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """, [(sid, bid, r["matricola"], r["operatore"], r["contratto"],
                           r["livello"], r["ore"], r["costo_h"], r["costo_tot"],
                           r["data"], r["stato_match"]) for r in s["pers_rows"]])

                    con.executemany("""
                        INSERT INTO veicoli
                          (service_id,batch_id,targa,tipo,tipo_interno,ore,data)
                        VALUES (?,?,?,?,?,?,?)
                    """, [(sid, bid, r["targa"], r["tipo"], r["tipo_interno"],
                           r["ore"], r["data"]) for r in s["veic_rows"]])

            st.success(f"✅ Import salvato: {len(salvabili)} commesse, batch {bid}")
            st.rerun()

# ─────────────────────────────────────────────────────────────
# PAGE: CONSUNTIVAZIONE
# ─────────────────────────────────────────────────────────────
def page_consuntivazione():
    sec("📊 Consuntivazione")

    with db_conn() as con:
        df_svc = pd.read_sql("""
            SELECT s.id, s.data_da, s.data_a, s.servizio, s.sottoservizio,
                   s.ore_personale, s.costo_personale, s.ore_veicoli,
                   b.importato_il, b.note as batch_note
            FROM services s
            LEFT JOIN import_batch b ON b.id = s.batch_id
            ORDER BY s.data_da DESC
        """, con)

    if df_svc.empty:
        st.info("Nessun dato. Esegui prima un import da Cantieri Digitali.")
        return

    # Filtri
    col1, col2, col3 = st.columns(3)
    servizi = ["Tutti"] + sorted(df_svc["servizio"].dropna().unique().tolist())
    filtro_svc = col1.selectbox("Servizio", servizi)
    filtro_da  = col2.date_input("Dal", value=None)
    filtro_a   = col3.date_input("Al",  value=None)

    df_f = df_svc.copy()
    if filtro_svc != "Tutti":
        df_f = df_f[df_f["servizio"] == filtro_svc]
    if filtro_da:
        df_f = df_f[pd.to_datetime(df_f["data_da"]) >= pd.Timestamp(filtro_da)]
    if filtro_a:
        df_f = df_f[pd.to_datetime(df_f["data_a"])  <= pd.Timestamp(filtro_a)]

    # KPI
    st.markdown(f"""<div class="kpi-row">
      {kpi("Ore personale", fmt_h(df_f["ore_personale"].sum()))}
      {kpi("Costo personale", fmt_eur(df_f["costo_personale"].sum()))}
      {kpi("Ore veicoli", fmt_h(df_f["ore_veicoli"].sum()))}
      {kpi("Servizi", len(df_f))}
    </div>""", unsafe_allow_html=True)

    st.dataframe(df_f.drop(columns=["id"]), use_container_width=True, hide_index=True)

    # Dettaglio personale
    if not df_f.empty:
        with st.expander("👷 Dettaglio personale"):
            ids = tuple(df_f["id"].tolist())
            with db_conn() as con:
                df_det = pd.read_sql(f"""
                    SELECT operatore, matricola, contratto, livello,
                           SUM(ore) as ore_tot, SUM(costo_tot) as costo_tot
                    FROM personale
                    WHERE service_id IN ({','.join('?'*len(ids))})
                    GROUP BY operatore, matricola, contratto, livello
                    ORDER BY ore_tot DESC
                """, con, params=ids)
            st.dataframe(df_det, use_container_width=True, hide_index=True)

        with st.expander("🚛 Dettaglio veicoli"):
            with db_conn() as con:
                df_veic = pd.read_sql(f"""
                    SELECT targa, tipo_interno, SUM(ore) as ore_tot
                    FROM veicoli
                    WHERE service_id IN ({','.join('?'*len(ids))})
                    GROUP BY targa, tipo_interno
                    ORDER BY ore_tot DESC
                """, con, params=ids)
            st.dataframe(df_veic, use_container_width=True, hide_index=True)

    # Export Excel
    if st.button("⬇️ Esporta Excel"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_f.drop(columns=["id"]).to_excel(writer, sheet_name="Servizi", index=False)
            if not df_f.empty:
                ids = tuple(df_f["id"].tolist())
                with db_conn() as con:
                    df_det_exp = pd.read_sql(f"""
                        SELECT * FROM personale
                        WHERE service_id IN ({','.join('?'*len(ids))})
                    """, con, params=ids)
                    df_veic_exp = pd.read_sql(f"""
                        SELECT * FROM veicoli
                        WHERE service_id IN ({','.join('?'*len(ids))})
                    """, con, params=ids)
                df_det_exp.to_excel(writer, sheet_name="Personale", index=False)
                df_veic_exp.to_excel(writer, sheet_name="Veicoli", index=False)
        st.download_button(
            "📥 Scarica .xlsx",
            data=buf.getvalue(),
            file_name=f"consuntivo_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ─────────────────────────────────────────────────────────────
# PAGE: ADMIN
# ─────────────────────────────────────────────────────────────
def page_admin():
    sec("⚙️ Amministrazione")
    tab_tree, tab_ccnl, tab_users, tab_import_batch = st.tabs([
        "🌳 Albero Servizi",
        "💶 Tariffe CCNL",
        "👤 Utenti",
        "📦 Import Batch",
    ])

    # ── Albero servizi ──────────────────────────────────────
    with tab_tree:
        st.caption("Definisci i servizi e sottoservizi attivi. Tipo fatturazione: flat / ton / km / h.")
        with db_conn() as con:
            df_t = pd.read_sql(
                "SELECT id, servizio, sottoservizio, tipo_fatturazione, tariffa FROM service_tree ORDER BY servizio, sottoservizio",
                con)
        edited_t = st.data_editor(
            df_t.drop(columns=["id"]),
            use_container_width=True, num_rows="dynamic", key="de_tree")
        if st.button("💾 Salva albero servizi"):
            with db_conn() as con:
                con.execute("DELETE FROM service_tree")
                con.executemany(
                    "INSERT INTO service_tree(servizio,sottoservizio,tipo_fatturazione,tariffa) VALUES(?,?,?,?)",
                    [(r["servizio"], r["sottoservizio"], r["tipo_fatturazione"], r["tariffa"])
                     for _, r in edited_t.iterrows() if str(r["servizio"]).strip()])
            st.success("Albero servizi salvato.")

    # ── Tariffe CCNL ────────────────────────────────────────
    with tab_ccnl:
        st.caption("Costo orario lordo per contratto e livello (€/h).")
        with db_conn() as con:
            df_ccnl = pd.read_sql(
                "SELECT contratto, livello, costo_h FROM ccnl_rates ORDER BY contratto, livello",
                con)
        edited_ccnl = st.data_editor(df_ccnl, use_container_width=True, num_rows="dynamic", key="de_ccnl")
        if st.button("💾 Salva tariffe CCNL"):
            with db_conn() as con:
                con.execute("DELETE FROM ccnl_rates")
                con.executemany(
                    "INSERT INTO ccnl_rates VALUES(?,?,?)",
                    [(r["contratto"], r["livello"], r["costo_h"])
                     for _, r in edited_ccnl.iterrows() if str(r["contratto"]).strip()])
            st.success("Tariffe CCNL salvate.")

    # ── Utenti ──────────────────────────────────────────────
    with tab_users:
        with db_conn() as con:
            df_u = pd.read_sql(
                "SELECT username, role, display_name FROM users ORDER BY username", con)
        st.dataframe(df_u, use_container_width=True, hide_index=True)

        st.markdown("---")
        with st.form("form_new_user"):
            st.markdown("**Aggiungi / Resetta password utente**")
            c1, c2 = st.columns(2)
            nu = c1.text_input("Username")
            nr = c2.selectbox("Ruolo", ["operatore", "capocantiere", "direzione", "admin"])
            nd = c1.text_input("Nome visualizzato")
            np_ = c2.text_input("Password", type="password")
            save_u = st.form_submit_button("💾 Salva utente")
        if save_u:
            if not nu.strip() or not np_.strip():
                st.error("Username e password obbligatori.")
            else:
                salt = os.urandom(SALT_BYTES).hex()
                hsh  = _hash_pw(np_, salt)
                with db_conn() as con:
                    con.execute("""
                        INSERT INTO users(username,pw_hash,pw_salt,role,display_name)
                        VALUES(?,?,?,?,?)
                        ON CONFLICT(username) DO UPDATE SET
                          pw_hash=excluded.pw_hash, pw_salt=excluded.pw_salt,
                          role=excluded.role, display_name=excluded.display_name
                    """, (nu.strip(), hsh, salt, nr, nd.strip()))
                st.success(f"Utente '{nu}' salvato.")
                st.rerun()

    # ── Import batch ────────────────────────────────────────
    with tab_import_batch:
        with db_conn() as con:
            df_batch = pd.read_sql(
                "SELECT id, source, importato_il, note FROM import_batch ORDER BY importato_il DESC",
                con)
        if df_batch.empty:
            st.info("Nessun import ancora.")
        else:
            st.dataframe(df_batch, use_container_width=True, hide_index=True)
            selected = st.selectbox("Seleziona batch da eliminare", ["—"] + df_batch["id"].tolist())
            if selected != "—" and st.button("🗑️ Elimina batch (e tutti i suoi dati)", type="secondary"):
                with db_conn() as con:
                    con.execute("DELETE FROM personale WHERE batch_id=?", (selected,))
                    con.execute("DELETE FROM veicoli   WHERE batch_id=?", (selected,))
                    con.execute("DELETE FROM services  WHERE batch_id=?", (selected,))
                    con.execute("DELETE FROM import_batch WHERE id=?",    (selected,))
                st.success(f"Batch {selected} eliminato.")
                st.rerun()

# ─────────────────────────────────────────────────────────────
# NAVIGAZIONE & MAIN
# ─────────────────────────────────────────────────────────────
PAGES = {
    "📊 Dashboard":            page_dashboard,
    "🗑️ Ingombranti":          page_ingombranti,
    "📥 Cantieri Digitali":    page_cantieri_digitali,
    "📋 Consuntivazione":      page_consuntivazione,
}
ADMIN_PAGES = {
    "⚙️ Admin":               page_admin,
}

def main():
    init_db()
    seed_db()
    require_login()
    inject_css()

    user = st.session_state["user"]
    all_pages = {**PAGES, **(ADMIN_PAGES if is_admin() else {})}

    with st.sidebar:
        st.markdown(f"### ♻️ {APP_TITLE}")
        st.caption(f"{APP_VER}  ·  {user.get('display_name') or user['username']}")
        st.markdown("---")
        page = st.radio("Navigazione", list(all_pages.keys()), label_visibility="collapsed")
        st.markdown("---")
        if st.button("🚪 Esci", use_container_width=True):
            del st.session_state["user"]
            st.rerun()

    all_pages[page]()
    st.markdown(f'<div class="foot">{APP_TITLE} {APP_VER} — Cooperativa Cristoforo</div>',
                unsafe_allow_html=True)

if __name__ == "__main__":
    main()
