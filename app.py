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

# --- CSS VISUAL (BOTÕES EM LINHA ÚNICA - CORRIGIDO) ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }

    /* ============================================================
       1. BOTÕES DE CONTRATO (RADIO) - LINHA ÚNICA COM SCROLL
       ============================================================ */
    
    [data-testid="stRadio"] { background: transparent !important; }
    [data-testid="stRadio"] > label { display: none !important; }

    div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        flex-wrap: nowrap !important; /* FORÇA LINHA ÚNICA */
        overflow-x: auto; /* ROLAGEM LATERAL */
        width: 100%;
        gap: 15px;
        padding-bottom: 10px; /* Espaço para o scroll */
    }

    div[role="radiogroup"] label {
        background-color: white !important;
        border: 3px solid #660099 !important; /* Borda grossa original */
        border-radius: 12px !important;
        padding: 15px 10px !important;
        flex: 0 0 auto !important; /* Tamanho fixo, não estica nem encolhe */
        min-width: 140px !important; /* Largura mínima para ler o texto */
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        cursor: pointer !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        transition: 0.3s !important;
        margin: 0 !important;
    }

    div[role="radiogroup"] label > div:first-child { display: none !important; }

    div[role="radiogroup"] label p {
        font-size: 18px !important; /* Fonte ajustada */
        font-weight: 900 !important;
        margin: 0 !important;
        color: #660099 !important;
        white-space: nowrap !important;
        text-transform: uppercase !important;
    }

    div[role="radiogroup"] label:has(input:checked) {
        background-color: #660099 !important;
        box-shadow: 0 6px 12px rgba(102, 0, 153, 0.4) !important;
        transform: translateY(-2px);
    }
    div[role="radiogroup"] label:has(input:checked) p {
        color: #ffffff !important;
    }

    div[role="radiogroup"] label:hover {
        background-color: #f3e5f5 !important;
    }

    /* Scrollbar discreta para os botões */
    div[role="radiogroup"]::-webkit-scrollbar { height: 6px; }
    div[role="radiogroup"]::-webkit-scrollbar-thumb { background: #ccc; border-radius: 10px; }

    /* ============================================================
       2. UPLOAD - LEGÍVEL E TRADUZIDO
       ============================================================ */

    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    
    [data-testid="stFileUploaderDropzone"]::before {
        content: "📂 Arraste e solte o arquivo aqui";
        display: block; text-align: center;
        font-weight: 800; font-size: 1.3rem; 
        color: #333; margin-top: 15px;
    }

    [data-testid="stFileUploader"] button[kind="secondary"] {
        float: right !important;
        color: transparent !important;
        border: 2px solid #ccc !important;
        background: white !important;
        width: 180px !important; 
        height: 45px !important;
        margin-top: 10px !important;
        position: relative !important;
    }
    
    [data-testid="stFileUploader"] button[kind="secondary"]::after {
        content: "Inserir arquivo";
        color: #333 !important;
        position: absolute;
        top: 50%; left: 50%; transform: translate(-50%, -50%);
        font-weight: 800 !important; 
        font-size: 16px !important;
    }
    
    [data-testid="stFileUploader"] button[kind="secondary"]:hover {
        border-color: #660099 !important;
    }
    [data-testid="stFileUploader"] button[kind="secondary"]:hover::after {
        color: #660099 !important;
    }

    /* BOTÃO X (DELETAR) */
    [data-testid="stFileUploadedItem"] > div:first-child { display: none !important; }
    
    [data-testid="stFileUploadedItem"] {
        background-color: transparent !important;
        padding: 5px !important;
        justify-content: flex-end !important;
    }

    /* ============================================================
       3. METRICAS (CARDS)
       ============================================================ */
    
    div[data-testid="stMetric"] {
        background-color: white; 
        border: 2px solid #e0e0e0; 
        padding: 15px; 
        border-radius: 12px;
        text-align: center; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.08); 
        height: 140px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    
    div[data-testid="stMetricLabel"] { 
        width: 100%; justify-content: center; 
        font-size: 18px !important; 
        font-weight: 700 !important; 
        color: #444; 
    }
    
    div[data-testid="stMetricValue"] { 
        font-size: 36px !important; 
        font-weight: 900 !important; 
        color: #000; 
    }
    
    div[data-testid="stMetricDelta"] {
        font-size: 16px !important;
        font-weight: 800 !important;
    }

    div.stDownloadButton > button { 
        width: 100%; border: none; padding: 1rem; 
        border-radius: 10px; 
        font-weight: 800 !important; 
        font-size: 16px !important;
        transition: 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    div.stDownloadButton > button:hover {
        color: #660099 !important;
        border: 2px solid #660099 !important;
        background-color: #f3e5f5 !important;
    }
    
    .contrato-label {
        font-size: 20px; font-weight: 800; color: #333; margin-bottom: 8px; margin-left: 2px;
    }
    .stCodeBlock { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- Funções de Leitura e Processamento ---
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

def processar_regras(df_full, contrato_sel):
    agora = datetime.now(timezone.utc) - timedelta(hours=3)
    agora = agora.replace(tzinfo=None)

    cols_map = {c.lower().strip(): c for c in df_full.columns}

    col_contrato = cols_map.get('contrato') or cols_map.get('escritório')
    if col_contrato:
        df = df_full[df_full[col_contrato].astype(str).str.strip().str.upper() == contrato_sel].copy()
    else:
        return pd.DataFrame()

    col_abertura = cols_map.get('abertura') or cols_map.get('data abertura')
    if not col_abertura: return pd.DataFrame()

    try:
        df['Abertura_dt'] = pd.to_datetime(df[col_abertura], format='%d/%m/%Y, %H:%M:%S', errors='coerce')
    except:
        df['Abertura_dt'] = pd.to_datetime(df[col_abertura], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Abertura_dt'])

    df['diff_segundos'] = (agora - df['Abertura_dt']).dt.total_seconds()
    df['horas_float'] = df['diff_segundos'] / 3600

    def formatar_hhmmss(s):
        if s < 0: return "00:00:00"
        m, s = divmod(int(s), 60); h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    df['Horas Corridas'] = df['diff_segundos'].apply(formatar_hhmmss)

    def classificar_sla(h):
        if h > 24: return "Crítico"
        if h > 8: return "Atenção"
        return "No Prazo"
    df['Status SLA'] = df['horas_float'].apply(classificar_sla)

    col_tec = cols_map.get('técnicos') or cols_map.get('tecnicos')
    df['Técnicos'] = pd.to_numeric(df[col_tec], errors='coerce').fillna(0) if col_tec else 0

    col_afe = cols_map.get('afetação') or cols_map.get('afetacao')
    df['Afetação'] = pd.to_numeric(df[col_afe], errors='coerce') if col_afe else pd.NA

    # Lógica de Região
    if contrato_sel == 'ABILITY_SJ':
        col_at = cols_map.get('at') or cols_map.get('area')
        lista_litoral = ['TG', 'PG', 'LZ', 'MK', 'MG', 'PN', 'AA', 'BV', 'FM', 'RP', 'AC', 'FP', 'BA', 'TQ', 'BO', 'BU', 'BC', 'PJ', 'PB', 'MR']
        def definir_area(val):
            if pd.isna(val): return "Vale"
            sigla = str(val).split('-')[0].strip().upper()
            return "Litoral" if sigla in lista_litoral else "Vale"
        
        if col_at: df['Area'] = df[col_at].apply(definir_area)
        else: df['Area'] = "N/A"
    else:
        df['Area'] = "Geral"

    return df.sort_values(by='horas_float', ascending=False)

def estilo_tabela(row):
    h = row.get('horas_float', None)
    sla_color = '#d32f2f' if h and h>24 else ('#d48806' if h and h>8 else ('#389e0d' if h else '#000'))
    val_af = None
    for k in ['Afetação', 'afetação', 'Afetacao']:
        if k in row.index:
            try: val_af = float(row[k])
            except: pass; break
    return '#1e88e5' if val_af and val_af >= 100 else sla_color

def row_style_apply(row):
    c = estilo_tabela(row)
    return [f'color: {c}; font-weight: 800'] * len(row)

# --- Geradores de Imagem (Cards) ---
def gerar_cards_mpl(kpis, contrato):
    C_BG, C_SHADOW, C_BORDER = "#ffffff", "#eeeeee", "#dddddd"
    C_TEXT, C_LABEL, C_RED, C_YELLOW, C_GREEN = "#222222", "#555555", "#d32f2f", "#f57c00", "#2e7d32"
    
    # SÓ MOSTRA REGIÃO SE FOR ABILITY_SJ
    tem_regiao = (contrato == 'ABILITY_SJ')
    h_total = 14 if tem_regiao else 11
    
    fig, ax = plt.subplots(figsize=(12, h_total), dpi=200) 
    fig.patch.set_facecolor(C_BG)
    ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)

    def draw_card_mobile(x, y, w, h, title, value, val_color=C_TEXT, alert=False):
        card = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=3", fc="white", ec=C_BORDER, lw=2, zorder=2)
        ax.add_patch(card)
        shadow = patches.FancyBboxPatch((x+0.8, y-0.8), w, h, boxstyle="round,pad=0,rounding_size=3", fc="#e0e0e0", ec="none", zorder=1)
        ax.add_patch(shadow)
        ax.text(x + w/2, y + h*0.82, title.upper(), ha='center', va='center', fontsize=18, color=C_LABEL, weight='bold', zorder=3)
        ax.text(x + w/2, y + h*0.4, str(value), ha='center', va='center', fontsize=55, color=val_color, weight='black', zorder=3)
        if alert:
            ax.add_patch(patches.Circle((x + w - 4, y + h - 4), 2.5, color=C_RED, zorder=4))
            ax.text(x + w - 4, y + h - 4, "!", color="white", fontsize=20, weight='bold', ha='center', va='center', zorder=5)

    ax.text(50, 96, "MONITORAMENTO", ha='center', fontsize=32, weight='black', color='#333')
    hora = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%H:%M")
    ax.text(50, 92, f"{contrato} • {hora}", ha='center', fontsize=22, weight='bold', color='#660099')

    y1, h_card = 68, 18
    draw_card_mobile(2, y1, 46, h_card, "Total", kpis['total'])
    draw_card_mobile(52, y1, 46, h_card, "S/ Técnico", kpis['sem_tec'], C_TEXT, alert=(kpis['sem_tec']>0))

    y2, w_sla, gap = 42, 30, 3
    draw_card_mobile(2, y2, w_sla, h_card, "Crítico", kpis['sla_red'], C_RED)
    draw_card_mobile(2 + w_sla + gap, y2, w_sla, h_card, "Atenção", kpis['sla_yellow'], C_YELLOW)
    draw_card_mobile(2 + 2*(w_sla + gap), y2, w_sla, h_card, "Ok", kpis['sla_green'], C_GREEN)

    if tem_regiao:
        y3 = 16
        draw_card_mobile(2, y3, 46, h_card, "Litoral", kpis.get('lit', 0))
        draw_card_mobile(52, y3, 46, h_card, "Vale", kpis.get('vale', 0))

    ax.text(50, 2, "Gerado via Painel de Controle", ha='center', fontsize=14, color="#999")
    buf = io.BytesIO()
    plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG)
    plt.close(fig); return buf.getvalue()

def gerar_lista_mpl_from_view(df_view, col_order, contrato):
    export_cols = [c for c in col_order if c != 'horas_float']
    df_p = df_view[export_cols].copy()
    rename = {'Ocorrência':'ID', 'Horas Corridas':'Tempo'}
    df_p.rename(columns=rename, inplace=True)
    fig_height = max(4, 3 + len(df_p)*0.8) 
    fig, ax = plt.subplots(figsize=(14, fig_height), dpi=180)
    ax.axis('off'); fig.patch.set_facecolor('white')
    hora = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime('%d/%m • %H:%M')
    plt.title(f"LISTA DE PENDÊNCIAS: {contrato}\n{hora}", loc='center', pad=40, fontsize=28, weight='black', color='#333')
    tbl = ax.table(cellText=df_p.values.tolist(), colLabels=df_p.columns, cellLoc='center', loc='center')
    tbl.auto_set_font_size(False); tbl.set_fontsize(20); tbl.scale(1.2, 3.5)
    for j in range(len(df_p.columns)):
        cell = tbl[(0, j)]; cell.set_facecolor('#660099'); cell.set_text_props(color='white', weight='bold'); cell.set_height(0.15)
    for i in range(len(df_p)):
        c = estilo_tabela(df_view.iloc[i])
        for j in range(len(df_p.columns)):
            cell = tbl[(i+1, j)]; cell.set_text_props(color=c, weight='bold'); cell.set_edgecolor("#dddddd"); cell.set_linewidth(1.5)
    buf = io.BytesIO()
    plt.savefig(buf, format='jpg', dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig); return buf.getvalue()

def gerar_texto_gv(row, contrato):
    cols_map = {c.lower().strip(): c for c in row.index}
    def get_val(keys_list, default="00"):
        if isinstance(keys_list, str): keys_list = [keys_list]
        for k in keys_list:
            if k in row.index: return str(row[k]).replace('.0', '') if pd.notna(row[k]) else default
            k_lower = k.lower().strip()
            if k_lower in cols_map: return str(row[cols_map[k_lower]]).replace('.0', '') if pd.notna(row[cols_map[k_lower]]) else default
        return default

    id_occ = row['Ocorrência']
    origem = get_val(['Origem'], 'OLTM')
    at = str(row.get('AT', row.get('Area', 'N/I')))
    
    cidade = "JACAREÍ"
    if "-" in at:
        try: cidade = at.split('-')[1].strip()
        except: pass
        
    afetacao = int(row['Afetação'])
    dt_obj = row['Abertura_dt']
    data_criacao = dt_obj.strftime("%d/%m/%Y")
    hora_criacao = dt_obj.strftime("%H:%M")

    primarias = get_val(['Primárias', 'primarias'], 'N/I')
    cabo = get_val(['Cabo'], 'N/I')
    bds = get_val(['BD', 'BDs'], 'N/I')
    prop_anatel = get_val(['Propensos - Anatel'], '00')
    rec_anatel = get_val(['Reclamados - Anatel'], '00')
    vip = get_val(['VIP'], '00')
    b2b = get_val(['B2B Avançado', 'B2B'], '00')
    alto_valor = get_val(['Cond. Alto Valor'], '00')
    defeito = get_val(['Falha', 'Causa'], 'FIBRA SEM SINAL')

    texto = f"""✅ *INFORMATIVO GRANDE VULTO*

*{contrato.replace('_', ' ')}*

{id_occ} - FTTx
ORIGEM: {origem}
AT: {at}
CIDADE: {cidade} 
QUANT. PRIMÁRIAS AFETADAS: {primarias}
CABO: {cabo}
AFETAÇÃO: {afetacao}
BDs: {bds}
CRIAÇÃO: {data_criacao}
HORA: {hora_criacao}
PROPENSOS-ANATEL: {prop_anatel}
RECLAMADOS-ANATEL: {rec_anatel}
CLIENTE VIP:  {vip}
CLIENTE B2B:  {b2b}
COND. ALTO VALOR: {alto_valor}
DEFEITO: 
PRAZO:"""
    return texto

def gerar_imagem_carimbo_mpl(texto):
    num_linhas = len(texto.split('\n'))
    h_fig = 4 + (num_linhas * 0.4)
    fig, ax = plt.subplots(figsize=(10, h_fig), dpi=200)
    fig.patch.set_facecolor('white')
    ax.axis('off')
    
    texto_limpo = texto.replace('*', '') 
    ax.text(0.05, 0.95, texto_limpo, ha='left', va='top', fontsize=18, family='monospace', color='#333333', linespacing=1.5, transform=ax.transAxes)
    rect = patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, linewidth=4, edgecolor='#660099', facecolor='none')
    ax.add_patch(rect)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='jpg', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig); return buf.getvalue()

# --- Interface Principal ---
st.title("Monitoramento Operacional")
hora_br = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime('%d/%m %H:%M:%S')
st.markdown(f"<div style='margin-bottom: 20px; color: grey; font-weight: bold;'>Atualizado: {hora_br}</div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Inserir arquivo", type=["xlsx", "csv"], key="uploader", label_visibility="collapsed")

if uploaded_file:
    df_raw = carregar_dados(uploaded_file)
    if df_raw is not None and not df_raw.empty:
        col_contrato_raw = [c for c in df_raw.columns if c.lower().strip() in ['contrato', 'escritório']]
        
        if col_contrato_raw:
            todos_contratos = df_raw[col_contrato_raw[0]].astype(str).str.strip().str.upper().unique()
            
            # LISTA DE CONTRATOS ATUALIZADA
            contratos_principais = [
                "ABILITY_SJ", 
                "TEL_JI", 
                "ABILITY_OS", 
                "TEL_INTERIOR", 
                "TEL_PC_SC", 
                "TELEMONT"
            ]
            
            opcoes_validas = [c for c in contratos_principais if c in todos_contratos]
            
            if not opcoes_validas:
                st.warning("Nenhum contrato conhecido encontrado no arquivo.")
            else:
                st.markdown("<p class='contrato-label'>Selecione o Contrato:</p>", unsafe_allow_html=True)
                
                contrato_selecionado = st.radio("Selecione:", opcoes_validas, horizontal=True, label_visibility="collapsed")
                
                df = processar_regras(df_raw, contrato_selecionado)
                
                if df.empty:
                    st.warning("Nenhum dado válido encontrado.")
                else:
                    kpis = {
                        'total': len(df), 'sem_tec': len(df[df['Técnicos']==0]),
                        'sla_red': len(df[df['horas_float']>24]), 
                        'sla_yellow': len(df[(df['horas_float']>8)&(df['horas_float']<=24)]),
                        'sla_green': len(df[df['horas_float']<=8]),
                        'lit': len(df[df['Area']=="Litoral"]), 'vale': len(df[df['Area']=="Vale"])
                    }

                    st.success("✅ **Dados Processados!**")
                    c1, c2 = st.columns(2)
                    nome = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime('%H%M')
                    try:
                        img_cards = gerar_cards_mpl(kpis, contrato_selecionado)
                        c1.download_button("📸 Baixar Resumo (Cards)", img_cards, f"Resumo_{nome}.jpg", "image/jpeg", use_container_width=True)
                    except Exception as e: st.error(e)

                    # --- GRANDE VULTO ---
                    df_gv = df[df['Afetação'] >= 100].copy()
                    
                    if not df_gv.empty:
                        st.markdown("---")
                        st.error(f"🚨 **GRANDE VULTO IDENTIFICADO ({len(df_gv)})**")
                        
                        with st.expander("Ver Carimbos Grande Vulto", expanded=True):
                            for idx, row in df_gv.iterrows():
                                st.markdown(f"**Ocorrência: {row['Ocorrência']} | Afetação: {int(row['Afetação'])}**")
                                
                                texto_pronto = gerar_texto_gv(row, contrato_selecionado)
                                st.code(texto_pronto, language="text")
                                st.caption("👆 Copie o texto acima OU baixe a imagem abaixo 👇")
                                
                                try:
                                    img_carimbo = gerar_imagem_carimbo_mpl(texto_pronto)
                                    nome_arquivo_gv = f"Carimbo_{row['Ocorrência']}_{nome}.jpg"
                                    st.download_button(
                                        label=f"📸 Baixar Carimbo - {row['Ocorrência']}",
                                        data=img_carimbo,
                                        file_name=nome_arquivo_gv,
                                        mime="image/jpeg",
                                        key=f"btn_gv_{row['Ocorrência']}"
                                    )
                                except Exception as e: st.warning(f"Erro imagem: {e}")
                                st.divider()
                    st.divider()

                    # DASHBOARD
                    st.subheader("Visão Geral")
                    m1, m2 = st.columns(2, gap="medium")
                    m1.metric("Total Aberto", kpis['total'])
                    delta_txt = "⚠️ Alerta" if kpis['sem_tec'] > 0 else "Ok"
                    m2.metric("Sem Técnico", kpis['sem_tec'], delta=delta_txt, delta_color="inverse")

                    st.subheader("SLA")
                    s1, s2, s3 = st.columns(3, gap="medium")
                    s1.metric("Crítico (>24h)", kpis['sla_red'])
                    s2.metric("Atenção (8-24h)", kpis['sla_yellow'])
                    s3.metric("No Prazo (<8h)", kpis['sla_green'])

                    if contrato_selecionado == 'ABILITY_SJ':
                        st.subheader("Região")
                        r1, r2 = st.columns(2, gap="medium")
                        r1.metric("Litoral", kpis['lit'])
                        r2.metric("Vale", kpis['vale'])

                    st.divider()

                    # FILTROS E TABELA
                    col_f1, col_f2 = st.columns(2)
                    if contrato_selecionado == 'ABILITY_SJ':
                        f_area = col_f1.multiselect("Filtrar Área", df['Area'].unique(), placeholder="Selecione...")
                    else:
                        col_f1.info("Filtro de região indisponível.")
                        f_area = []
                    
                    f_sla = col_f2.multiselect("Filtrar SLA", ["Crítico", "Atenção", "No Prazo"], placeholder="Selecione...")

                    df_show = df.copy()
                    if f_area: df_show = df_show[df_show['Area'].isin(f_area)]
                    if f_sla: df_show = df_show[df_show['Status SLA'].isin(f_sla)]
                    if 'AT' in df_show.columns: df_show['AT'] = df_show['AT'].astype(str).str[:2]

                    cols_final = ['Ocorrência', 'Area', 'AT', 'Afetação', 'Status SLA', 'Horas Corridas', 'Técnicos', 'horas_float']
                    cols_exist = [c for c in cols_final if c in df_show.columns]

                    styler = df_show[cols_exist].style.apply(row_style_apply, axis=1) \
                        .set_properties(**{'font-size': '16px', 'font-weight': '600'}) \
                        .set_table_styles([
                            {'selector': 'th', 'props': [('font-size', '18px'), ('font-weight', 'bold'), ('background-color', '#f0f2f6')]}
                        ])
                    
                    st.dataframe(styler, height=600, use_container_width=True,
                                 column_config={"Ocorrência": st.column_config.TextColumn("ID", width="medium"), 
                                                "Afetação": st.column_config.NumberColumn("Afet.", format="%.0f"),
                                                "horas_float": None})

                    try:
                        cols_exp = [c for c in cols_exist if c != 'horas_float']
                        img_lista = gerar_lista_mpl_from_view(df_show, cols_exp, contrato_selecionado)
                        c2.download_button("📄 Baixar Lista Detalhada", img_lista, f"Lista_{nome}.jpg", "image/jpeg", use_container_width=True)
                    except: pass
        else:
            st.error("Coluna 'Contrato' não encontrada.")
    else: st.info("Ficheiro vazio.")
else: st.info("Carregue a base geral para iniciar.")