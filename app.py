import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURAZIONE PAGINA E GRAFICA AVANZATA
# ==========================================
st.set_page_config(page_title="Control Room | Cristoforo", layout="wide", page_icon="♻️")

st.markdown("""
    <style>
    .main {background-color: #f8fbfc;}
    
    .main-title {
        text-align: center;
        color: #008b3a;
        font-size: 2.8rem;
        font-weight: 900;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin-bottom: 0px;
        padding-bottom: 0px;
    }
    .sub-title {
        text-align: center;
        color: #555;
        font-size: 1.2rem;
        font-weight: 400;
        margin-top: 10px;
        margin-bottom: 30px;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        background-color: white;
        padding: 12px 20px;
        border-radius: 10px;
        margin-bottom: 12px;
        border: 1px solid #e0e6ed;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: #f0fdf4;
        border-color: #008b3a;
        transform: translateX(5px);
        box-shadow: 0 4px 8px rgba(0, 139, 58, 0.15);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label p {
        font-size: 1.15rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------
# INTESTAZIONE CENTRATA
# ------------------------------------------
st.markdown('<h1 class="main-title">Hub Operativo | Controllo Ore e Gestione Economica</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Piattaforma unificata per la validazione turni, storicizzazione e Centri di Costo.</p>', unsafe_allow_html=True)

col_vuota_sinistra, col_logo_centro, col_vuota_destra = st.columns([1.5, 1, 1.5])
with col_logo_centro:
    try:
        st.image("Cristoforo_2025_no-ONLUS.png", use_container_width=True)
    except:
        pass

st.markdown("---")

# ==========================================
# 2. SISTEMA DI LOGIN E DATABASE UTENTI DINAMICO
# ==========================================
FILE_UTENTI = "utenti_cristoforo.csv"

if not os.path.exists(FILE_UTENTI):
    utenti_base = pd.DataFrame([
        {"Username": "direzione", "Password": "admin", "Ruolo": "admin", "Cantieri": "TUTTI"},
        {"Username": "resp_prato", "Password": "123", "Ruolo": "capocantiere", "Cantieri": "RACCOLTA PAP PRATO, Spazzamento Stradale"},
        {"Username": "resp_mantova", "Password": "456", "Ruolo": "capocantiere", "Cantieri": "RACCOLTA PAP MANTOVA, Movimentazione Scarrabili"}
    ])
    utenti_base.to_csv(FILE_UTENTI, index=False)

df_utenti = pd.read_csv(FILE_UTENTI)
utenti_db = {}
for _, row in df_utenti.iterrows():
    utenti_db[str(row['Username'])] = {
        "pwd": str(row['Password']),
        "ruolo": str(row['Ruolo']),
        "cantieri": [c.strip() for c in str(row['Cantieri']).split(',')]
    }

if "loggato" not in st.session_state:
    st.session_state["loggato"] = False

if not st.session_state["loggato"]:
    st.subheader("🔐 Accesso Area Operativa")
    with st.form("login_form"):
        user = st.text_input("Nome Utente")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Accedi")
        
        if submit:
            if user in utenti_db and utenti_db[user]["pwd"] == pwd:
                st.session_state["loggato"] = True
                st.session_state["utente"] = user
                st.session_state["ruolo"] = utenti_db[user]["ruolo"]
                st.session_state["cantieri"] = utenti_db[user]["cantieri"]
                st.rerun()
            else:
                st.error("❌ Credenziali errate. Riprova.")
    st.stop() 

# ==========================================
# 3. MENU LATERALE (SIDEBAR)
# ==========================================
st.sidebar.markdown(f"### 👤 Ciao, {st.session_state['utente'].upper()}")

if st.sidebar.button("Esci (Logout)", use_container_width=True):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown("#### 📌 Navigazione")

voci_menu = [
    "🏠 0. Sintesi Direzionale",
    "📥 1. Validazione Turni", 
    "📈 2. Cruscotto Ore", 
    "⚙️ 3. Anagrafiche e Export",
    "📊 4. Centro di Costo (Economico)"
]

if st.session_state["ruolo"] == "admin":
    voci_menu.append("🔐 5. Gestione Accessi")

menu_scelta = st.sidebar.radio("Navigazione", voci_menu, label_visibility="collapsed")

# ==========================================
# 4. FUNZIONI DI SUPPORTO E DATABASE ORE
# ==========================================
def converti_ore(valore):
    if pd.isna(valore): return 0.0
    if isinstance(valore, str):
        parti = str(valore).split(':')
        if len(parti) >= 2: return float(parti[0]) + float(parti[1])/60.0
    elif hasattr(valore, 'hour'):
        return getattr(valore, 'hour') + getattr(valore, 'minute')/60.0
    return float(valore)

FILE_STORICO = "storico_ore_cristoforo.csv"
FILE_ANAG_OP = "anagrafica_operatori.csv"
FILE_ANAG_MEZZI = "anagrafica_mezzi.csv"
NOME_FILE_DATI_COSTI = "storico_servizi_v9.csv"

def aggiorna_storico(nuovo_df):
    if os.path.exists(FILE_STORICO):
        storico_esistente = pd.read_csv(FILE_STORICO)
        df_completo = pd.concat([storico_esistente, nuovo_df]).drop_duplicates(subset=['ID'], keep='last')
    else:
        df_completo = nuovo_df
    df_completo.to_csv(FILE_STORICO, index=False)
    return df_completo

# ==========================================
# 5. CONTENUTO DELLE SEZIONI
# ==========================================

# ------------------------------------------
# MENU 0: SINTESI DIREZIONALE
# ------------------------------------------
if menu_scelta == "🏠 0. Sintesi Direzionale":
    st.subheader("🏠 Sintesi Direzionale e Andamento Cantieri")
    
    if os.path.isfile(NOME_FILE_DATI_COSTI) and os.path.getsize(NOME_FILE_DATI_COSTI) > 0:
        df_costi = pd.read_csv(NOME_FILE_DATI_COSTI)
        
        if st.session_state["ruolo"] != "admin":
            cantieri_permessi = st.session_state["cantieri"]
            df_costi = df_costi[df_costi["Dettaglio"].isin(cantieri_permessi) | df_costi["Macrocategoria"].isin(cantieri_permessi)]
            
        if not df_costi.empty:
            tot_fatt = df_costi['Fatturato (€)'].sum()
            tot_costi = df_costi['Costo Totale (€)'].sum()
            margine_tot = df_costi['Margine Netto (€)'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Fatturato Totale", f"€ {tot_fatt:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c2.metric("Costi Totali", f"€ {tot_costi:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c3.metric("Margine Netto Globale", f"€ {margine_tot:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 
                      delta=f"€ {margine_tot:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            st.markdown("---")
            
            # KPI TONNELLATE DIREZIONALI
            df_costi['Tonnellate_Num'] = pd.to_numeric(df_costi['Tonnellate'].replace('-', 0), errors='coerce').fillna(0)
            df_ton = df_costi[df_costi['Tonnellate_Num'] > 0]
            
            if not df_ton.empty:
                st.markdown("### ⚖️ Performance Servizi a Misura (KPI per Tonnellata)")
                report_ton = df_ton.groupby("Dettaglio")[["Costo Totale (€)", "Margine Netto (€)", "Tonnellate_Num"]].sum().reset_index()
                report_ton['Costo per Ton (€)'] = report_ton['Costo Totale (€)'] / report_ton['Tonnellate_Num']
                report_ton['Margine per Ton (€)'] = report_ton['Margine Netto (€)'] / report_ton['Tonnellate_Num']
                
                st.dataframe(
                    report_ton[['Dettaglio', 'Tonnellate_Num', 'Costo per Ton (€)', 'Margine per Ton (€)']].style.format({
                        'Tonnellate_Num': "{:.2f} t",
                        'Costo per Ton (€)': "€ {:.2f}",
                        'Margine per Ton (€)': "€ {:.2f}"
                    }).background_gradient(subset=['Margine per Ton (€)'], cmap="RdYlGn"),
                    use_container_width=True
                )
                st.markdown("---")

            # DIVISIONE UTILI E PERDITE
            df_cantieri = df_costi.groupby(["Dettaglio"])[["Fatturato (€)", "Costo Totale (€)", "Margine Netto (€)"]].sum().reset_index()
            df_positivi = df_cantieri[df_cantieri['Margine Netto (€)'] >= 0].sort_values(by='Margine Netto (€)', ascending=False)
            df_negativi = df_cantieri[df_cantieri['Margine Netto (€)'] < 0].sort_values(by='Margine Netto (€)', ascending=True)
            
            col_pos, col_neg = st.columns(2)
            with col_pos:
                st.markdown("### 🟢 Cantieri in Utile")
                if not df_positivi.empty:
                    st.dataframe(df_positivi[['Dettaglio', 'Margine Netto (€)']].style.format({'Margine Netto (€)': "€ {:.2f}"}).background_gradient(subset=['Margine Netto (€)'], cmap="Greens"), use_container_width=True)
                else:
                    st.info("Nessun cantiere in utile.")
                    
            with col_neg:
                st.markdown("### 🔴 Cantieri in Perdita")
                if not df_negativi.empty:
                    st.dataframe(df_negativi[['Dettaglio', 'Margine Netto (€)']].style.format({'Margine Netto (€)': "€ {:.2f}"}).background_gradient(subset=['Margine Netto (€)'], cmap="Reds_r"), use_container_width=True)
                else:
                    st.success("Nessun cantiere in perdita.")
        else:
            st.info("Nessun dato economico per i tuoi cantieri.")
    else:
        st.info("Nessun dato economico salvato.")

# ------------------------------------------
# MENU 1: VALIDAZIONE TURNI
# ------------------------------------------
elif menu_scelta == "📥 1. Validazione Turni":
    st.subheader("📥 Validazione Turni Operativi")
    uploaded_file = st.file_uploader("Trascina il file estratto dal gestionale (Es. Excel o CSV)", type=["xlsx", "csv"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file, header=1)
            else: df = pd.read_excel(uploaded_file, header=1)
            df['Durata_Prev_Dec'] = df['durata prevista'].apply(converti_ore)
            df['Scostamento_Ore'] = df['Durata'] - df['Durata_Prev_Dec']
            colonne_utili = ['ID', 'Data', 'Operatori', 'Targa', 'durata prevista', 'Durata_Prev_Dec', 'Durata', 'Scostamento_Ore']
            df_pulito = df[colonne_utili].copy()
            aggiorna_storico(df_pulito)
            df_anomalie = df_pulito[df_pulito['Scostamento_Ore'] != 0].copy()
            st.success("✅ File elaborato e salvato nello storico!")
            col1, col2, col3 = st.columns(3)
            col1.metric("Servizi nel File", len(df))
            col2.metric("Discrepanze Rilevate", len(df_anomalie))
            ore_extra = df_anomalie[df_anomalie['Scostamento_Ore'] > 0]['Scostamento_Ore'].sum()
            col3.metric("Monte Ore Extra Rilevato", f"+ {ore_extra:.2f} h")
            if len(df_anomalie) > 0:
                st.dataframe(df_anomalie[['ID', 'Data', 'Operatori', 'Targa', 'durata prevista', 'Durata', 'Scostamento_Ore']].style.format({"Scostamento_Ore": "{:.2f}"}).background_gradient(subset=['Scostamento_Ore'], cmap="Reds"), use_container_width=True)
        except Exception as e:
            st.error(f"Errore tecnico: {e}")

# ------------------------------------------
# MENU 2: CRUSCOTTO ORE
# ------------------------------------------
elif menu_scelta == "📈 2. Cruscotto Ore":
    st.subheader("📈 Cruscotto e Statistiche Ore")
    if os.path.exists(FILE_STORICO):
        df_storico = pd.read_csv(FILE_STORICO)
        df_storico_anomalie = df_storico[df_storico['Scostamento_Ore'] != 0]
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.markdown("**Top 5 Operatori per Ore Extra**")
            ore_extra = df_storico_anomalie[df_storico_anomalie['Scostamento_Ore'] > 0]
            if not ore_extra.empty: st.bar_chart(ore_extra.groupby('Operatori')['Scostamento_Ore'].sum().sort_values(ascending=False).head(5), color="#008b3a")
        with col_stat2:
            st.markdown("**Andamento Anomalie nel Tempo**")
            if not df_storico_anomalie.empty: st.line_chart(df_storico_anomalie.groupby('Data')['Scostamento_Ore'].sum())
        st.dataframe(df_storico, use_container_width=True)
    else:
        st.info("Nessun dato storico presente.")

# ------------------------------------------
# MENU 3: ANAGRAFICHE
# ------------------------------------------
elif menu_scelta == "⚙️ 3. Anagrafiche e Export":
    if st.session_state["ruolo"] != "admin": st.warning("⚠️ Accesso riservato alla Direzione.")
    else:
        st.subheader("⚙️ Gestione Anagrafiche")
        if os.path.exists(FILE_STORICO):
            df_storico = pd.read_csv(FILE_STORICO)
            df_costi = df_storico.copy()
            df_costi['Singolo_Operatore'] = df_costi['Operatori'].astype(str).str.split(',')
            df_costi = df_costi.explode('Singolo_Operatore')
            df_costi['Singolo_Operatore'] = df_costi['Singolo_Operatore'].str.strip()
            operatori_univoci = pd.DataFrame(df_costi['Singolo_Operatore'].dropna().unique(), columns=['Operatore'])
            if os.path.exists(FILE_ANAG_OP): operatori_univoci = pd.merge(operatori_univoci, pd.read_csv(FILE_ANAG_OP), on='Operatore', how='left')
            else: operatori_univoci['Livello Contrattuale'] = 'Da Assegnare'
            mezzi_univoci = pd.DataFrame(df_costi['Targa'].dropna().unique(), columns=['Targa'])
            if os.path.exists(FILE_ANAG_MEZZI): mezzi_univoci = pd.merge(mezzi_univoci, pd.read_csv(FILE_ANAG_MEZZI), on='Targa', how='left')
            else: mezzi_univoci['Tipologia Mezzo'] = 'Da Assegnare'

            col_edit_op, col_edit_mezzi = st.columns(2)
            with col_edit_op:
                anagrafica_op_aggiornata = st.data_editor(operatori_univoci, hide_index=True, num_rows="dynamic", key="edit_op")
                anagrafica_op_aggiornata.to_csv(FILE_ANAG_OP, index=False)
            with col_edit_mezzi:
                anagrafica_mezzi_aggiornata = st.data_editor(mezzi_univoci, hide_index=True, num_rows="dynamic", key="edit_mezzi")
                anagrafica_mezzi_aggiornata.to_csv(FILE_ANAG_MEZZI, index=False)

            df_costi = pd.merge(df_costi, anagrafica_op_aggiornata, left_on='Singolo_Operatore', right_on='Operatore', how='left')
            df_costi = pd.merge(df_costi, anagrafica_mezzi_aggiornata, on='Targa', how='left')
            pivot_costi = df_costi.groupby(['Data', 'Livello Contrattuale', 'Tipologia Mezzo'])['Durata'].sum().reset_index()
            st.download_button("📥 Esporta Flusso Ore (CSV)", data=pivot_costi.to_csv(index=False).encode('utf-8'), file_name="Export_Ore_Pulite.csv", mime="text/csv", type="primary")
        else: st.info("Nessun dato presente.")

# ------------------------------------------
# MENU 4: CENTRO DI COSTO (ECONOMICO)
# ------------------------------------------
elif menu_scelta == "📊 4. Centro di Costo (Economico)":
    st.subheader("📊 Inserimento ed Economia Centri di Costo")
    
    struttura_servizi = {
        "Spazzamento Stradale": ["Manuale", "Meccanizzato", "Misto"],
        "Raccolta Porta a Porta": [
            "RACCOLTA PAP PRATO", "RACCOLTA PAP CAMPI", "RACCOLTA PAP VAIANO", 
            "RACCOLTA PAP MANTOVA", "RACCOLTA PAP NOVENTA", "RACCOLTA PAP COSTABISSARA", 
            "RACCOLTA PAP CREMONA"
        ],
        "Ritiro Ingombranti": ["A Domicilio", "Abbandoni Stradali"],
        "Movimentazione Scarrabili": ["Centro di Raccolta (Ecocentro)", "Aziende Private / Terzi"],
        "Raccolta Cartone Selettivo": ["Utenze Commerciali (Negozi)", "Grandi Produttori / Aziende"]
    }

    cantieri_permessi = st.session_state["cantieri"]
    struttura_filtrata = {}
    if "TUTTI" in cantieri_permessi:
        struttura_filtrata = struttura_servizi
    else:
        for macro, dettagli in struttura_servizi.items():
            dettagli_ok = [d for d in dettagli if d in cantieri_permessi or macro in cantieri_permessi]
            if dettagli_ok: struttura_filtrata[macro] = dettagli_ok

    if not struttura_filtrata:
        st.warning("Non hai cantieri assegnati. Contatta la direzione.")
    else:
        if st.session_state["ruolo"] == "admin":
            with st.expander("⚙️ Configura Tariffario Aziendale", expanded=False):
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    costo_l1 = st.number_input("Livello 1 (A2 - D2)", value=22.0, step=0.5)
                    costo_l2 = st.number_input("Livello 2 (B1 - D1)", value=25.0, step=0.5)
                    costo_l3 = st.number_input("Livello 3 (C1 - C2)", value=28.0, step=0.5)
                    costo_l4 = st.number_input("Livello 4 (C3 - C1)", value=32.0, step=0.5)
                with col_t2:
                    costo_mezzo_1 = st.number_input("Mezzo Leggero (Porter)", value=15.0, step=1.0)
                    costo_mezzo_2 = st.number_input("Mezzo Costipatore", value=25.0, step=1.0)
                    costo_mezzo_3 = st.number_input("Mezzo Pesante", value=45.0, step=1.0)
                    costo_mezzo_4 = st.number_input("Mezzo Speciale", value=65.0, step=1.0)
                with col_t3:
                    perc_costi_generali = st.number_input("Quota Costi Generali (%)", value=15.0, step=1.0)
                    tariffa_tonnellata = st.number_input("Tariffa Fatturata (€/ton)", value=130.0, step=5.0)
        else:
            costo_l1, costo_l2, costo_l3, costo_l4 = 22.0, 25.0, 28.0, 32.0
            costo_mezzo_1, costo_mezzo_2, costo_mezzo_3, costo_mezzo_4 = 15.0, 25.0, 45.0, 65.0
            perc_costi_generali, tariffa_tonnellata = 15.0, 130.0

        st.markdown("#### 📝 Compilazione Turno")
        c1, c2, c3 = st.columns(3)
        with c1: data_servizio = st.date_input("Data del servizio")
        with c2:
            tipo_servizio = st.selectbox("Macrocategoria", list(struttura_filtrata.keys()))
            dettaglio_servizio = st.selectbox("Dettaglio (Cantiere)", struttura_filtrata[tipo_servizio])
        usa_tonnellate = tipo_servizio in ["Ritiro Ingombranti", "Raccolta Cartone Selettivo"]
        with c3:
            if usa_tonnellate:
                tonnellate = st.number_input("Tonnellate Raccolte (Resa)", min_value=0.0, value=5.0, step=0.1)
                fatturato_fisso = 0.0
            else:
                tonnellate = 0.0
                fatturato_fisso = st.number_input("Fatturato Fisso (€)", min_value=0.0, value=0.0, step=50.0)

        st.markdown("#### 👥 Utilizzo Personale (Ore)")
        p1, p2, p3, p4 = st.columns(4)
        with p1: ore_l1 = st.number_input("Liv. 1 (A2 - D2)", min_value=0.0, value=0.0, step=0.5)
        with p2: ore_l2 = st.number_input("Liv. 2 (B1 - D1)", min_value=0.0, value=0.0, step=0.5)
        with p3: ore_l3 = st.number_input("Liv. 3 (C1 - C2)", min_value=0.0, value=0.0, step=0.5)
        with p4: ore_l4 = st.number_input("Liv. 4 (C3 - C1)", min_value=0.0, value=0.0, step=0.5)

        st.markdown("#### 🚛 Utilizzo Mezzi (Ore)")
        m1, m2, m3, m4 = st.columns(4)
        with m1: ore_mezzo_1 = st.number_input("Ore Leggero", min_value=0.0, value=0.0, step=0.5)
        with m2: ore_mezzo_2 = st.number_input("Ore Costipatore", min_value=0.0, value=0.0, step=0.5)
        with m3: ore_mezzo_3 = st.number_input("Ore Pesante", min_value=0.0, value=0.0, step=0.5)
        with m4: ore_mezzo_4 = st.number_input("Ore Speciale", min_value=0.0, value=0.0, step=0.5)

        if st.button("💾 Calcola Margini e Salva", type="primary"):
            costo_personale = sum([ore_l1*costo_l1, ore_l2*costo_l2, ore_l3*costo_l3, ore_l4*costo_l4])
            costo_mezzi = sum([ore_mezzo_1*costo_mezzo_1, ore_mezzo_2*costo_mezzo_2, ore_mezzo_3*costo_mezzo_3, ore_mezzo_4*costo_mezzo_4])
            costo_oper_diretto = costo_personale + costo_mezzi
            valore_generali = costo_oper_diretto * (perc_costi_generali / 100)
            costo_totale = costo_oper_diretto + valore_generali
            ricavo_totale = (tonnellate * tariffa_tonnellata) if usa_tonnellate else fatturato_fisso
            margine = ricavo_totale - costo_totale

            nuovo_dato = pd.DataFrame([{
                "Data": data_servizio.strftime("%d/%m/%Y"), "Utente": st.session_state["utente"],
                "Macrocategoria": tipo_servizio, "Dettaglio": dettaglio_servizio,
                "Ore L1": ore_l1, "Ore L2": ore_l2, "Ore L3": ore_l3, "Ore L4": ore_l4,
                "Ore Porter": ore_mezzo_1, "Ore Costipatore": ore_mezzo_2, "Ore Pesante": ore_mezzo_3, "Ore Speciale": ore_mezzo_4,
                "Tonnellate": tonnellate if usa_tonnellate else "-",
                "Costo Op. (€)": costo_personale, "Costo Mezzi (€)": costo_mezzi,
                "Quota Gen. (€)": valore_generali, "Costo Totale (€)": costo_totale,
                "Fatturato (€)": ricavo_totale, "Margine Netto (€)": margine
            }])
            nuovo_dato.to_csv(NOME_FILE_DATI_COSTI, mode='a' if os.path.isfile(NOME_FILE_DATI_COSTI) else 'w', header=not os.path.isfile(NOME_FILE_DATI_COSTI), index=False)
            
            st.success("✅ Dati salvati con successo! Ecco i KPI del turno:")
            col_k1, col_k2, col_k3 = st.columns(3)
            col_k1.metric("Margine Netto Generato", f"€ {margine:,.2f}")
            if usa_tonnellate and tonnellate > 0:
                costo_ton = costo_totale / tonnellate
                margine_ton = margine / tonnellate
                col_k2.metric("Costo per Ton.", f"€ {costo_ton:,.2f} / t")
                col_k3.metric("Margine per Ton.", f"€ {margine_ton:,.2f} / t")
            else:
                col_k2.metric("Costi Totali", f"€ {costo_totale:,.2f}")
                col_k3.metric("Ricavi Totali", f"€ {ricavo_totale:,.2f}")

        if os.path.isfile(NOME_FILE_DATI_COSTI) and os.path.getsize(NOME_FILE_DATI_COSTI) > 0:
            dati_storici_costi = pd.read_csv(NOME_FILE_DATI_COSTI)
            if st.session_state["ruolo"] != "admin":
                dati_storici_costi = dati_storici_costi[dati_storici_costi["Dettaglio"].isin(cantieri_permessi) | dati_storici_costi["Macrocategoria"].isin(cantieri_permessi)]
            if not dati_storici_costi.empty:
                st.markdown("---")
                st.markdown("#### 📍 Riepilogo Cantieri Autorizzati")
                dati_storici_costi['Tonnellate_Num'] = pd.to_numeric(dati_storici_costi['Tonnellate'].replace('-', 0), errors='coerce').fillna(0)
                report_dettaglio = dati_storici_costi.groupby(["Macrocategoria", "Dettaglio"])[["Costo Totale (€)", "Fatturato (€)", "Margine Netto (€)", "Tonnellate_Num"]].sum().reset_index()
                report_dettaglio['Costo/Ton Media (€)'] = report_dettaglio.apply(lambda x: x['Costo Totale (€)'] / x['Tonnellate_Num'] if x['Tonnellate_Num'] > 0 else 0, axis=1)
                report_dettaglio['Margine/Ton Media (€)'] = report_dettaglio.apply(lambda x: x['Margine Netto (€)'] / x['Tonnellate_Num'] if x['Tonnellate_Num'] > 0 else 0, axis=1)
                
                colonne_da_mostrare = ["Macrocategoria", "Dettaglio", "Costo Totale (€)", "Fatturato (€)", "Margine Netto (€)"]
                if report_dettaglio['Tonnellate_Num'].sum() > 0:
                    colonne_da_mostrare.extend(["Costo/Ton Media (€)", "Margine/Ton Media (€)"])
                
                st.dataframe(report_dettaglio[colonne_da_mostrare].style.format({col: "€ {:.2f}" for col in ["Costo Totale (€)", "Fatturato (€)", "Margine Netto (€)", "Costo/Ton Media (€)", "Margine/Ton Media (€)"]}), use_container_width=True)

# ------------------------------------------
# MENU 5: GESTIONE ACCESSI (SOLO ADMIN)
# ------------------------------------------
elif menu_scelta == "🔐 5. Gestione Accessi":
    st.subheader("🔐 Gestione Accessi e Permessi Cantieri")
    if st.session_state["ruolo"] != "admin": st.error("Accesso negato.")
    else:
        df_utenti = pd.read_csv(FILE_UTENTI)
        df_utenti_edit = st.data_editor(df_utenti, num_rows="dynamic", use_container_width=True, column_config={"Password": st.column_config.TextColumn("Password (Visibile all'Admin)"), "Ruolo": st.column_config.SelectboxColumn("Ruolo", options=["admin", "capocantiere"]), "Cantieri": st.column_config.TextColumn("Commesse (Separa con virgola)")})
        if st.button("💾 Salva Modifiche Database Utenti", type="primary"):
            df_utenti_edit.to_csv(FILE_UTENTI, index=False)
            st.success("✅ Database aggiornato! I permessi saranno attivi al prossimo login.")