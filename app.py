import streamlit as st
import pandas as pd
import io
import os
import tempfile
from parser_anm import parse_turni_pdf, parse_matricole_pdf

st.set_page_config(
    page_title="ANM Turni",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚌 ANM — Gestione Turni Quindicinale")

# --- Session state ---
if 'records' not in st.session_state:
    st.session_state.records = []
if 'loaded' not in st.session_state:
    st.session_state.loaded = {}  # filename -> info
if 'master' not in st.session_state:
    st.session_state.master = {}  # matricola -> nome

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Carica Files")

    st.subheader("1. Lista autisti (opzionale)")
    master_file = st.file_uploader(
        "matrAUTISTI.pdf",
        type=['pdf'],
        key='upload_master',
        help="Carica la lista matricole per vedere chi manca"
    )
    if master_file:
        fname = master_file.name
        if fname not in st.session_state.loaded:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(master_file.read())
                tmp_path = tmp.name
            st.session_state.master = parse_matricole_pdf(tmp_path)
            os.unlink(tmp_path)
            st.session_state.loaded[fname] = {'tipo': 'master'}
            if st.session_state.master:
                st.success(f"✅ {len(st.session_state.master)} autisti caricati")
            else:
                st.warning("Lista non riconosciuta")

    st.divider()
    st.subheader("2. PDF Turni")
    uploaded = st.file_uploader(
        "Seleziona PDF (anche più file)",
        type=['pdf'],
        accept_multiple_files=True,
        key='upload_turni'
    )

    if uploaded:
        new_count = 0
        skip_count = 0
        err_names = []
        bar = st.progress(0)
        for i, f in enumerate(uploaded):
            if f.name not in st.session_state.loaded:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(f.read())
                    tmp_path = tmp.name
                info, recs = parse_turni_pdf(tmp_path)
                os.unlink(tmp_path)
                if recs:
                    st.session_state.records.extend(recs)
                    st.session_state.loaded[f.name] = info
                    new_count += 1
                else:
                    err_names.append(f.name)
            else:
                skip_count += 1
            bar.progress((i + 1) / len(uploaded))
        bar.empty()
        if new_count:
            st.success(f"✅ {new_count} PDF caricati")
        if skip_count:
            st.info(f"ℹ️ {skip_count} già presenti")
        if err_names:
            st.warning(f"⚠️ Non ANM: {', '.join(err_names)}")

    st.divider()
    if st.session_state.records:
        n_aut = len([v for k, v in st.session_state.loaded.items() if v and v.get('tipo') != 'master'])
        n_tot = len(st.session_state.master) if st.session_state.master else None
        label = f"{n_aut}" + (f" / {n_tot}" if n_tot else "")
        st.metric("Autisti caricati", label)

        if st.button("🗑️ Ricomincia da capo", type="secondary"):
            st.session_state.records = []
            st.session_state.loaded = {}
            st.session_state.master = {}
            st.rerun()

# --- MAIN ---
if not st.session_state.records:
    st.info("👈 Carica i PDF dei turni dal menu a sinistra.")
    with st.expander("Come funziona"):
        st.markdown("""
1. *(Facoltativo)* Carica `matrAUTISTI.pdf` per vedere chi non ha ancora inviato il PDF
2. Carica tutti i PDF quindicinali ricevuti dai colleghi
3. Seleziona il giorno per vedere la scheda turni
4. Esporta in Excel con un clic
        """)
    st.stop()

df = pd.DataFrame(st.session_state.records)

tab1, tab2, tab3 = st.tabs(["📅 Scheda del Giorno", "👤 Singolo Autista", "📋 Riepilogo"])

# ===== TAB 1: SCHEDA GIORNALIERA =====
with tab1:
    dates = sorted(df['data'].unique())

    col_d, col_f = st.columns([2, 2])
    with col_d:
        today_str = pd.Timestamp.today().strftime('%d/%m/%Y')
        default_idx = dates.index(today_str) if today_str in dates else 0
        sel_date = st.selectbox("📆 Seleziona data", dates, index=default_idx)
    with col_f:
        mostra = st.selectbox("Mostra", ["Solo in servizio", "Tutti (inclusi riposo/disp.)"])

    day = df[df['data'] == sel_date].copy()
    if mostra == "Solo in servizio":
        day_show = day[day['tipo'] == 'TURNO'].copy()
    else:
        day_show = day.copy()

    day_show = day_show.sort_values(['monto', 'nome'])

    # Metriche
    n_serv = len(day[day['tipo'] == 'TURNO'])
    n_rip = len(day[day['tipo'] == 'RIPOSO'])
    n_disp = len(day[day['tipo'].str.startswith('DISP', na=False)])
    n_altro = len(day) - n_serv - n_rip - n_disp
    giorno_label = day['giorno'].iloc[0] if not day.empty else ''

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🟢 In servizio", n_serv)
    c2.metric("⬜ Riposo", n_rip)
    c3.metric("🔵 Disponibilità", n_disp)
    c4.metric("🟡 Altro", n_altro)

    # Tabella
    cols_map = {
        'matricola': 'Matricola',
        'nome': 'Nome',
        'monto': 'Monto',
        'cadenza': 'Fine (stimata)',
        'turno_macchina': 'Turno',
        'localita': 'Deposito',
        'fine_servizio': 'Dep/Linea',
        'durata': 'Durata',
        'tipo': 'Tipo',
    }
    disp = day_show.rename(columns=cols_map)[list(cols_map.values())]

    def _color(row):
        t = row.get('Tipo', '')
        if t == 'TURNO':
            return ['background-color: #e8f5e9'] * len(row)
        if t == 'RIPOSO':
            return ['color: #999999'] * len(row)
        if 'DISP' in str(t):
            return ['background-color: #e3f2fd'] * len(row)
        if t in ('NON PRESTAZIONE', 'CONGEDO ORDINARIO', 'FERIE'):
            return ['background-color: #fff8e1'] * len(row)
        return [''] * len(row)

    st.dataframe(
        disp.style.apply(_color, axis=1),
        use_container_width=True,
        height=min(650, 60 + 38 * max(len(disp), 1))
    )

    # Export Excel
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        disp.to_excel(writer, index=False, sheet_name='Turni')
        ws = writer.sheets['Turni']
        ws.column_dimensions['B'].width = 22
        ws.column_dimensions['A'].width = 12
    buf.seek(0)

    st.download_button(
        label=f"⬇️ Esporta Excel — {giorno_label} {sel_date}",
        data=buf.getvalue(),
        file_name=f"turni_{sel_date.replace('/', '-')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

# ===== TAB 2: SINGOLO AUTISTA =====
with tab2:
    autisti = df[['matricola', 'nome']].drop_duplicates().sort_values('nome')

    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        cerca = st.text_input("🔍 Cerca (nome o matricola)")
    with col_s2:
        if cerca:
            mask = df['nome'].str.contains(cerca.upper(), na=False) | df['matricola'].str.contains(cerca, na=False)
            nomi_match = df[mask]['nome'].unique()
            nome_sel = st.selectbox("Risultati", nomi_match) if len(nomi_match) > 0 else None
        else:
            nome_sel = st.selectbox("Seleziona autista", autisti['nome'].tolist())

    if nome_sel:
        aut_df = df[df['nome'] == nome_sel].copy().sort_values('data')
        info_r = aut_df.iloc[0]
        st.subheader(f"{nome_sel}  —  Matr. {info_r['matricola']}")

        aut_disp = aut_df.rename(columns={
            'giorno': 'Giorno', 'data': 'Data', 'tipo': 'Tipo',
            'monto': 'Monto', 'cadenza': 'Fine (stimata)',
            'turno_macchina': 'Turno', 'localita': 'Deposito',
            'fine_servizio': 'Dep/Linea', 'durata': 'Durata'
        })[['Giorno', 'Data', 'Tipo', 'Monto', 'Fine (stimata)', 'Turno', 'Deposito', 'Dep/Linea', 'Durata']]

        st.dataframe(aut_disp, use_container_width=True)

        n_turni = len(aut_df[aut_df['tipo'] == 'TURNO'])
        n_rip = len(aut_df[aut_df['tipo'] == 'RIPOSO'])
        st.caption(f"Turni: {n_turni}  |  Riposo: {n_rip}  |  Altro: {len(aut_df) - n_turni - n_rip}")

# ===== TAB 3: RIEPILOGO =====
with tab3:
    n_aut_car = len([v for v in st.session_state.loaded.values() if v and v.get('tipo') != 'master'])
    n_giorni = df['data'].nunique()
    n_turni_tot = len(df[df['tipo'] == 'TURNO'])

    c1, c2, c3 = st.columns(3)
    c1.metric("Autisti nel sistema", n_aut_car)
    c2.metric("Giorni coperti", n_giorni)
    c3.metric("Turni totali", n_turni_tot)

    # Chi manca
    if st.session_state.master:
        loaded_matr = set(df['matricola'].unique())
        all_matr = set(st.session_state.master.keys())
        missing = all_matr - loaded_matr

        if missing:
            st.warning(f"⚠️ {len(missing)} autisti senza PDF")
            miss_df = pd.DataFrame(
                [{'Matricola': m, 'Nome': st.session_state.master[m]} for m in sorted(missing)]
            )
            st.dataframe(miss_df, use_container_width=True, height=300)
        else:
            st.success("✅ Tutti gli autisti hanno il PDF caricato!")

    st.subheader("Autisti caricati")
    loaded_df = pd.DataFrame([
        {
            'Matricola': v.get('matricola', ''),
            'Nome': v.get('nome', ''),
            'Dal': v.get('dal', ''),
            'Al': v.get('al', '')
        }
        for k, v in st.session_state.loaded.items()
        if v and v.get('tipo') != 'master'
    ])
    if not loaded_df.empty:
        st.dataframe(loaded_df.sort_values('Nome'), use_container_width=True)
