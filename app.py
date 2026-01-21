import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- Configuração da Página ---
st.set_page_config(
    page_title="Monitoramento Operacional",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS VISUAL ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    
    /* Estilo dos Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        height: 130px; 
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    div[data-testid="stMetricLabel"] { width: 100%; justify-content: center; font-size: 14px; color: #666; }
    div[data-testid="stMetricValue"] { font-size: 26px; font-weight: bold; color: #000; }
    
    div.stDownloadButton > button { width: 100%; border: none; padding: 0.6rem; border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- Funções ---
@st.cache_data(ttl=60)
def carregar_dados(uploaded_file):
    try:
        if uploaded_file.name.endswith('.xlsx'):
            return pd.read_excel(uploaded_file)
        else:
            return pd.read_csv(uploaded_file, sep=None, engine='python')
    except Exception as e:
        st.error(f"Erro ao ler: {e}")
        return None

def processar_regras(df):
    agora = datetime.now(timezone.utc) - timedelta(hours=3)
    agora = agora.replace(tzinfo=None)

    # 1. Identificar Coluna
    cols_map = {c.lower().strip(): c for c in df.columns}
    col_abertura = cols_map.get('abertura') or cols_map.get('data abertura')

    if not col_abertura: return pd.DataFrame()

    # 2. Conversão de Data
    try:
        df['Abertura_dt'] = pd.to_datetime(df[col_abertura], format='%d/%m/%Y, %H:%M:%S', errors='coerce')
    except:
        df['Abertura_dt'] = pd.to_datetime(df[col_abertura], dayfirst=True, errors='coerce')
    
    df = df.dropna(subset=['Abertura_dt'])

    # 3. Cálculo de Tempo
    df['diff_segundos'] = (agora - df['Abertura_dt']).dt.total_seconds()
    df['horas_float'] = df['diff_segundos'] / 3600
    
    def formatar_hhmmss(s):
        if s < 0: return "00:00:00"
        m, s = divmod(int(s), 60); h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    
    df['Horas Corridas'] = df['diff_segundos'].apply(formatar_hhmmss)

    # 4. SLA
    def classificar_sla(h):
        if h > 24: return "Crítico"
        if h > 8: return "Atenção"
        return "No Prazo"
    df['Status SLA'] = df['horas_float'].apply(classificar_sla)

    # 5. Outros
    col_tec = cols_map.get('técnicos') or cols_map.get('tecnicos')
    df['Técnicos'] = pd.to_numeric(df[col_tec], errors='coerce').fillna(0) if col_tec else 0

    col_at = cols_map.get('at') or cols_map.get('area')
    lista_lit = ['TG', 'PG', 'LZ', 'MK', 'MG', 'PN', 'AA', 'BV', 'FM', 'RP', 'AC', 'FP', 'BA', 'TQ', 'BO', 'BU', 'BC', 'PJ', 'PB', 'MR']
    
    def definir_area(val):
        if pd.isna(val): return "Vale"
        sigla = str(val).split('-')[0].strip().upper()
        return "Litoral" if sigla in lista_lit else "Vale"

    if col_at: df['Area'] = df[col_at].apply(definir_area)
    else: df['Area'] = "N/A"

    return df.sort_values(by='horas_float', ascending=False)

def cor_fundo_sla_tabela(row):
    # Função para colorir a tabela interativa na tela
    h = row['horas_float']
    c = '#fff1f0' if h > 24 else ('#fffbe6' if h > 8 else '#f6ffed')
    # Cor do texto também muda levemente para combinar
    text_c = '#cf1322' if h > 24 else ('#d48806' if h > 8 else '#389e0d')
    return [f'background-color: {c}; color: {text_c}; font-weight: bold'] * len(row)

# ==========================================
# GERAÇÃO IMAGEM (JPEG) - ESTILO MODERNO
# ==========================================
def gerar_cards_mpl(kpis):
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor('white')
    ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    
    hora = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime('%H:%M')
    
    ax.text(5, 95, "Monitoramento Operacional", fontsize=18, weight='bold', color='#333')
    ax.text(95, 95, hora, fontsize=14, color='#888', ha='right')
    
    def box(x, y, w, h, lbl, val, clr='black'):
        s = patches.FancyBboxPatch((x+.5,y-.5), w, h, boxstyle="round,pad=0.5", linewidth=0, color='#eee')
        b = patches.FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.5", linewidth=1, edgecolor='#ddd', facecolor='white')
        ax.add_patch(s); ax.add_patch(b)
        ax.text(x+w/2, y+h*.65, lbl, ha='center', fontsize=10, color='#666')
        ax.text(x+w/2, y+h*.25, str(val), ha='center', fontsize=20, weight='bold', color=clr)

    ax.text(5, 85, "Geral", fontsize=12, color='#333', weight='bold')
    box(5, 70, 40, 10, "Total Aberto", kpis['total'])
    box(50, 70, 40, 10, "Sem Técnico", kpis['sem_tec'], '#d32f2f' if kpis['sem_tec']>0 else '#388e3c')
    
    ax.text(5, 60, "SLA", fontsize=12, color='#333', weight='bold')
    box(5, 45, 25, 10, "Crítico", kpis['sla_red'], '#d32f2f')
    box(35, 45, 25, 10, "Atenção", kpis['sla_yellow'], '#d48806')
    box(65, 45, 25, 10, "No Prazo", kpis['sla_green'], '#389e0d')

    ax.text(5, 35, "Região", fontsize=12, color='#333', weight='bold')
    box(5, 20, 40, 10, "Litoral", kpis['lit'])
    box(50, 20, 40, 10, "Vale", kpis['vale'])
    
    b = io.BytesIO()
    plt.savefig(b, format='jpg', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return b.getvalue()

def gerar_lista_mpl(df):
    # Seleção de Colunas para o Print
    cols = {'Ocorrência':'ID', 'AT':'AT', 'Status SLA':'Status', 'Horas Corridas':'Tempo'}
    use = [c for c in cols.keys() if c in df.columns]
    
    df_view = df[use].head(40).copy()
    df_view.rename(columns=cols, inplace=True)
    
    # Altura dinâmica
    h_fig = len(df_view) * 0.35 + 2
    fig, ax = plt.subplots(figsize=(10, h_fig))
    ax.axis('off'); fig.patch.set_facecolor('white')
    
    hora = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime('%H:%M')
    plt.title(f"Lista Detalhada - {hora}", pad=20, fontsize=14, weight='bold', color='#333')

    # Tabela Base
    # colColours define o fundo do cabeçalho (cinza claro)
    tbl = ax.table(
        cellText=df_view.values, 
        colLabels=df_view.columns, 
        cellLoc='center', 
        loc='center', 
        colColours=['#f8f9fa']*len(df_view.columns) 
    )
    
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.2, 1.8)

    # ESTILIZAÇÃO MODERNA (Letras Coloridas)
    if 'Status' in df_view.columns:
        idx_status = list(df_view.columns).index('Status')
        
        # Percorre todas as células da tabela
        # Células começam em (1,0) pois (0,X) é cabeçalho
        for row_idx in range(len(df_view)):
            val = df_view.iloc[row_idx]['Status']
            
            # Pega a célula da coluna Status
            cell = tbl[(row_idx + 1, idx_status)]
            
            # Aplica cor na FONTE, não no fundo
            if val == 'Crítico':
                cell.get_text().set_color('#d32f2f') # Vermelho Escuro
                cell.get_text().set_weight('bold')
            elif val == 'Atenção':
                cell.get_text().set_color('#d48806') # Laranja Escuro
                cell.get_text().set_weight('bold')
            elif val == 'No Prazo':
                cell.get_text().set_color('#389e0d') # Verde Escuro
                cell.get_text().set_weight('bold')

            # Opcional: Deixar as linhas com fundo alternado suave (Zebra)
            # if row_idx % 2 == 0:
            #    for c_idx in range(len(df_view.columns)):
            #        tbl[(row_idx+1, c_idx)].set_facecolor('#fafafa')

    b = io.BytesIO()
    plt.savefig(b, format='jpg', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return b.getvalue()

# --- Interface ---
st.title("Monitoramento Operacional")
hora_br = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime('%d/%m %H:%M:%S')
st.markdown(f"<div style='margin-bottom: 20px; color: grey;'>Atualizado: {hora_br}</div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Carregar ficheiro", type=["xlsx", "csv"], label_visibility="collapsed")

if uploaded_file:
    df_raw = carregar_dados(uploaded_file)
    if df_raw is not None and not df_raw.empty:
        df = processar_regras(df_raw)
        
        if df.empty:
             st.warning("Verifique a coluna 'Abertura'.")
        else:
            kpis = {
                'total': len(df), 'sem_tec': len(df[df['Técnicos']==0]),
                'sla_red': len(df[df['horas_float']>24]), 
                'sla_yellow': len(df[(df['horas_float']>8)&(df['horas_float']<=24)]),
                'sla_green': len(df[df['horas_float']<=8]), 
                'lit': len(df[df['Area']=="Litoral"]), 'vale': len(df[df['Area']=="Vale"])
            }

            st.write("### 📤 Exportar Relatórios")
            c1, c2 = st.columns(2)
            nome = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime('%H%M')
            try:
                c1.download_button("📸 Baixar Cards", gerar_cards_mpl(kpis), f"Cards_{nome}.jpg", "image/jpeg", use_container_width=True)
                c2.download_button("📄 Baixar Lista", gerar_lista_mpl(df), f"Lista_{nome}.jpg", "image/jpeg", use_container_width=True)
            except: pass

            st.divider()

            st.subheader("Geral")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Total Aberto", kpis['total'])
            c2.metric("Sem Técnico", kpis['sem_tec'], delta="Alert" if kpis['sem_tec']>0 else "Ok", delta_color="inverse")

            st.subheader("SLA")
            s1, s2, s3 = st.columns(3, gap="medium")
            s1.metric("Crítico (>24h)", kpis['sla_red'])
            s2.metric("Atenção (8-24h)", kpis['sla_yellow'])
            s3.metric("No Prazo (<8h)", kpis['sla_green'])

            st.subheader("Região")
            a1, a2 = st.columns(2, gap="medium")
            a1.metric("Litoral", kpis['lit'])
            a2.metric("Vale", kpis['vale'])

            st.divider()

            col_f1, col_f2 = st.columns(2)
            f_area = col_f1.multiselect("Filtrar Área", df['Area'].unique())
            f_sla = col_f2.multiselect("Filtrar SLA", ["Crítico", "Atenção", "No Prazo"])

            df_show = df.copy()
            if f_area: df_show = df_show[df_show['Area'].isin(f_area)]
            if f_sla: df_show = df_show[df_show['Status SLA'].isin(f_sla)]

            # AQUI: Colunas para Tabela Interativa
            cols_final = ['Ocorrência', 'Area', 'AT', 'Status SLA', 'Horas Corridas', 'Técnicos', 'horas_float']
            cols_exist = [c for c in cols_final if c in df_show.columns]
            
            # Aplica a cor também na tabela da tela
            st.dataframe(
                df_show[cols_exist].style.apply(cor_fundo_sla_tabela, axis=1),
                width="stretch", 
                height=600,
                column_config={
                    "Ocorrência": st.column_config.TextColumn("ID", width="small"),
                    "AT": st.column_config.TextColumn("AT", width="medium"),
                    "Horas Corridas": st.column_config.TextColumn(width="medium"), 
                    "horas_float": None,
                }
            )
    else: st.info("Ficheiro vazio.")
else: st.info("Aguardando ficheiro...")