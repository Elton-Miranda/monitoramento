import os
import time

# ==============================================================================
# 🌍 1. CONFIGURAÇÃO DE AMBIENTE (GARANTE O FUSO DO SERVIDOR)
# ==============================================================================
os.environ['TZ'] = 'America/Sao_Paulo'
try:
    time.tzset()
except AttributeError:
    pass

# ==============================================================================
# 📦 IMPORTS
# ==============================================================================
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io

# --- Configuração da Página ---
st.set_page_config(
    page_title="SigmaOPS • Monitoramento", 
    page_icon="⚡", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 🎨 SIGMA UI (CSS)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .stApp { background-color: #f4f6f9; }

    /* HEADER */
    .sigma-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        padding: 20px 30px; border-radius: 12px; color: white;
        margin-bottom: 25px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 4px solid #7c3aed;
    }
    .sigma-title { 
        font-size: 28px; font-weight: 900; margin: 0; 
        background: -webkit-linear-gradient(0deg, #fff, #a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .sigma-clock {
        background: rgba(255,255,255,0.1); padding: 6px 16px; 
        border-radius: 20px; font-weight: 600; font-size: 14px;
        border: 1px solid rgba(255,255,255,0.1);
    }

    /* CARDS */
    div[data-testid="stMetric"] {
        background-color: white; border: 1px solid #e2e8f0; padding: 20px; 
        border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); 
        border-left: 6px solid #7c3aed; height: 160px;
        display: flex; flex-direction: column; justify-content: center;
    }
    div[data-testid="stMetricValue"] { font-size: 32px !important; font-weight: 900 !important; color: #0f172a !important; }
    div[data-testid="stMetricDelta"] { font-size: 15px !important; font-weight: 700 !important; }

    /* BOTÕES RADIO (VISÃO OPERACIONAL) */
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 5px; }
    div[role="radiogroup"] label {
        background-color: white !important; border: 1px solid #cbd5e1 !important;
        color: #475569 !important; padding: 10px 24px !important; border-radius: 8px !important;
        font-weight: 600 !important; transition: all 0.2s; min-width: 120px; display: flex; justify-content: center;
    }
    div[role="radiogroup"] label:has(input:checked) {
        background-color: #7c3aed !important; border-color: #7c3aed !important; color: white !important;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3) !important;
    }
    div[role="radiogroup"] label:has(input:checked) p { color: white !important; }

    /* DOWNLOAD BUTTON */
    [data-testid="stDownloadButton"] > button {
        background-color: #7c3aed !important; color: white !important; border: none !important;
        width: 100%; font-weight: bold;
    }
    [data-testid="stDownloadButton"] > button:hover { background-color: #6d28d9 !important; }

    /* --- ESTILO NOVO PARA O MULTISELECT (TAGS ROXAS) --- */
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #7c3aed !important; /* Roxo igual ao menu */
        color: white !important;
        border: 1px solid #6d28d9 !important;
    }
    .stMultiSelect [data-baseweb="tag"] span {
        color: white !important;
    }
    /* Botão de Submit do Form */
    [data-testid="stFormSubmitButton"] > button {
        background-color: #7c3aed !important;
        color: white !important;
        border: none !important;
        width: 100%;
        font-weight: bold;
    }

    .status-box { padding: 12px; border-radius: 8px; margin-bottom: 15px; font-weight: 600; text-align: center; font-size: 0.9rem; }
    .status-ok { background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .status-error { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO ---
ARQUIVO_CNL_CSV = "CNL_BASE_MONITORAMENTO.csv"
ARQUIVO_CNL_XLSX = "CNL_BASE_MONITORAMENTO.xlsx"

try:
    API_URL = st.secrets["api"]["url"]
    API_HEADERS = dict(st.secrets["api"]["headers"])
except:
    API_URL = ""
    API_HEADERS = {}

# ==============================================================================
# 🧠 LÓGICA DE CARREGAMENTO
# ==============================================================================

@st.cache_data(ttl=3600)
def carregar_base_cnl():
    df = None
    if os.path.exists(ARQUIVO_CNL_CSV):
        try: df = pd.read_csv(ARQUIVO_CNL_CSV, sep=None, engine='python')
        except: pass
    if df is None and os.path.exists(ARQUIVO_CNL_XLSX):
        try: df = pd.read_excel(ARQUIVO_CNL_XLSX)
        except: pass
    if df is not None:
        if 'CNL' in df.columns and 'MUNICÍPIO' in df.columns:
            df = df.dropna(subset=['CNL'])
            df['CNL'] = df['CNL'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df['MUNICÍPIO'] = df['MUNICÍPIO'].astype(str).str.strip().str.upper()
            return df[['CNL', 'MUNICÍPIO']].drop_duplicates(subset='CNL')
    return None

@st.cache_data(ttl=600, show_spinner=False)
def carregar_dados_api():
    if not API_URL: return None, "Sem URL configurada."
    try:
        response = requests.get(API_URL, headers=API_HEADERS, timeout=25)
        if response.status_code == 200:
            try: json_data = response.json()
            except: return None, "Erro JSON."
            if 'ocorrencias' in json_data:
                df = pd.DataFrame(json_data['ocorrencias'])
                rename_map = {
                    'ocorrencia': 'Ocorrência', 'data_abertura': 'Data Abertura', 'contrato': 'Contrato',
                    'escritorio': 'Escritório', 'cnl': 'CNL', 'at': 'AT', 'cabo': 'Cabo',
                    'afetacao': 'Afetação', 'origem': 'Origem', 'primarias': 'Primárias', 'bd': 'BD',
                    'propenso_anatel': 'Propensos - Anatel', 'reclamado_anatel': 'Reclamados - Anatel',
                    'vip': 'VIP', 'b2b_avancado': 'B2B_Value', 'cond_alto_valor': 'Cond. Alto Valor'
                }
                df.rename(columns=rename_map, inplace=True)
                
                if 'tecnicos' in json_data['ocorrencias'][0]:
                    df['Técnicos'] = df['tecnicos'].apply(lambda x: len(x) if isinstance(x, list) else 0)
                else: df['Técnicos'] = 0
                
                for col in ['VIP']:
                    if col in df.columns:
                        df[col] = df[col].apply(lambda x: 'SIM' if str(x).upper().strip() in ['TRUE', 'SIM', '1', 'S', 'YES'] else 'NÃO')
                    else: df[col] = 'NÃO'

                if 'Cond. Alto Valor' in df.columns:
                     df['Cond. Alto Valor'] = pd.to_numeric(df['Cond. Alto Valor'], errors='coerce').fillna(0)
                     df['Cond. Alto Valor'] = df['Cond. Alto Valor'].apply(lambda x: 'SIM' if x != 0 else 'NÃO')
                else:
                    df['Cond. Alto Valor'] = 'NÃO'

                if 'B2B_Value' in df.columns:
                    df['B2B'] = pd.to_numeric(df['B2B_Value'], errors='coerce').fillna(0).apply(lambda x: 'SIM' if x > 0 else 'NÃO')
                else: df['B2B'] = 'NÃO'

                df['Data Abertura'] = pd.to_datetime(df['Data Abertura'], errors='coerce')
                
                return df, None
            else: return None, "JSON incompleto."
        return None, f"Erro HTTP {response.status_code}"
    except Exception as e: return None, f"Conexão: {str(e)}"

# ==============================================================================
# 🧠 LÓGICA DE PROCESSAMENTO
# ==============================================================================
def processar_regras_generico(df_full, contratos_validos=None, filtrar_contrato=None):
    agora = datetime.utcnow() - timedelta(hours=3)
    cols_map = {str(c).lower().strip(): c for c in df_full.columns}

    df_cnl = carregar_base_cnl()
    col_cnl_main = cols_map.get('cnl')
    if df_cnl is not None and col_cnl_main:
        df_full[col_cnl_main] = df_full[col_cnl_main].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_full = pd.merge(df_full, df_cnl, left_on=col_cnl_main, right_on='CNL', how='left')
        df_full.rename(columns={'MUNICÍPIO': 'Cidade_Real'}, inplace=True)

    col_contrato = cols_map.get('contrato') or cols_map.get('escritório')
    if col_contrato:
        df_full['Contrato_Padrao'] = df_full[col_contrato].astype(str).str.strip().str.upper()
        if filtrar_contrato: df = df_full[df_full['Contrato_Padrao'] == filtrar_contrato].copy()
        elif contratos_validos: df = df_full[df_full['Contrato_Padrao'].isin(contratos_validos)].copy()
        else: return pd.DataFrame()
    else: return pd.DataFrame()

    col_abertura = cols_map.get('abertura') or cols_map.get('data abertura')
    if not col_abertura: return pd.DataFrame()

    df['Abertura_dt'] = df[col_abertura]
    df = df.dropna(subset=['Abertura_dt'])
    
    if pd.api.types.is_datetime64tz_dtype(df['Abertura_dt']):
        df['Abertura_dt'] = df['Abertura_dt'].dt.tz_localize(None)

    df['diff_segundos'] = (agora - df['Abertura_dt']).dt.total_seconds()

    if not df.empty and df['diff_segundos'].median() < -100:
        df['diff_segundos'] = df['diff_segundos'] + 10800

    df['horas_float'] = df['diff_segundos'] / 3600

    def formatar_hhmmss(s):
        if pd.isna(s): return "00:00:00"
        val = int(s)
        if val < 0: val = 0 
        m, s = divmod(val, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    
    df['Horas Corridas'] = df['diff_segundos'].apply(formatar_hhmmss)

    def classificar_sla(h):
        if h > 24: return "Crítico"
        if h > 8: return "Atenção"
        return "No Prazo"
    df['Status SLA'] = df['horas_float'].apply(classificar_sla)

    col_tec = cols_map.get('técnicos') or cols_map.get('tecnicos')
    df['Técnicos'] = pd.to_numeric(df[col_tec], errors='coerce').fillna(0)
    col_afe = cols_map.get('afetação') or cols_map.get('afetacao')
    df['Afetação'] = pd.to_numeric(df[col_afe], errors='coerce').fillna(0)

    if 'Area' not in df.columns:
        col_at = cols_map.get('at') or cols_map.get('area')
        def definir_area_safe(row):
            if row['Contrato_Padrao'] == 'ABILITY_SJ':
                val = row.get(col_at) if col_at else None
                if pd.isna(val): return "Vale"
                sigla = str(val).split('-')[0].strip().upper()
                litoral = ['TG', 'PG', 'LZ', 'MK', 'MG', 'PN', 'AA', 'BV', 'FM', 'RP', 'AC', 'FP', 'BA', 'TQ', 'BO', 'BU', 'BC', 'PJ', 'PB', 'MR']
                return "Litoral" if sigla in litoral else "Vale"
            return "Geral"
        if col_at: df['Area'] = df.apply(definir_area_safe, axis=1)
        else: df['Area'] = "Geral"

    return df.sort_values(by='horas_float', ascending=False)

def estilo_tabela(row):
    h = row.get('horas_float', None)
    sla_color = '#dc2626' if h and h>24 else ('#d97706' if h and h>8 else ('#16a34a' if h else '#000'))
    val_af = None
    for k in ['Afetação', 'afetação', 'Afetacao']:
        if k in row.index:
            try: val_af = float(row[k])
            except: pass
            break
    if val_af and val_af >= 100: sla_color = '#2563eb'
    return sla_color

def row_style_apply(row):
    base_color = estilo_tabela(row)
    styles = [f'color: {base_color}; font-weight: 700'] * len(row)
    
    for i, col_name in enumerate(row.index):
        val_str = str(row[col_name]).upper().strip()
        if col_name == 'VIP' and val_str == 'SIM':
            styles[i] = 'background-color: #f0abfc; color: #86198f; font-weight: 900; text-align: center; border-radius: 6px; padding: 4px;'
        elif col_name == 'Cond. Alto Valor' and val_str == 'SIM':
            styles[i] = 'background-color: #bef264; color: #365314; font-weight: 900; text-align: center; border-radius: 6px; padding: 4px;'
        elif col_name == 'B2B' and val_str == 'SIM':
            styles[i] = 'background-color: #a78bfa; color: #4c1d95; font-weight: 900; text-align: center; border-radius: 6px; padding: 4px;'
    return styles

# --- VISUALIZADORES ---

def gerar_texto_gv(row, contrato):
    cols_map = {c.lower().strip(): c for c in row.index}
    def get_val(keys_list, default="00"):
        if isinstance(keys_list, str): keys_list = [keys_list]
        for k in keys_list:
            if k in row.index: return str(row[k]).replace('.0', '') if pd.notna(row[k]) else default
            k_lower = k.lower().strip()
            if k_lower in cols_map: return str(row[cols_map[k_lower]]).replace('.0', '') if pd.notna(row[cols_map[k_lower]]) else default
        return default

    cidade = "N/I"
    if 'Cidade_Real' in row.index and pd.notna(row['Cidade_Real']): cidade = str(row['Cidade_Real']).upper()
    else:
        at_full = str(row.get('AT', row.get('Area', 'N/I'))).strip().upper()
        sigla_at = at_full.split('-')[0].strip() if '-' in at_full else at_full[:3]
        mapa = { 'SJC': 'SÃO JOSÉ DOS CAMPOS', 'JAC': 'JACAREÍ', 'TAU': 'TAUBATÉ', 'GUA': 'GUARATINGUETÁ', 'PNO': 'PINDAMONHANGABA', 'CAR': 'CARAGUATATUBA', 'UBA': 'UBATUBA', 'SBO': 'SÃO SEBASTIÃO', 'ILH': 'ILHABELA' }
        cidade = mapa.get(sigla_at, "VERIFICAR CIDADE")

    try: dt_criacao = row['Abertura_dt'].strftime("%d/%m/%Y")
    except: dt_criacao = str(row['Abertura_dt'])
    try: hr_criacao = row['Abertura_dt'].strftime("%H:%M")
    except: hr_criacao = ""

    texto = f"""✅ *INFORMATIVO GRANDE VULTO*

*{contrato.replace('_', ' ')}*

{row['Ocorrência']} - FTTx
ORIGEM: {get_val(['Origem'], 'OLTM')}
AT: {str(row.get('AT', row.get('Area', 'N/I')))}
CIDADE: {cidade}
QUANT. PRIMÁRIAS AFETADAS: {get_val(['Primárias', 'primarias'], 'N/I')}
CABO: {get_val(['Cabo'], 'N/I')}
AFETAÇÃO: {int(row['Afetação'])}
BDs: {get_val(['BD', 'BDs'], 'N/I')}
CRIAÇÃO: {dt_criacao}
HORA: {hr_criacao}
PROPENSOS-ANATEL: {get_val(['Propensos - Anatel'], '00')}
RECLAMADOS-ANATEL: {get_val(['Reclamados - Anatel'], '00')}
CLIENTE VIP:  {get_val(['VIP'], '00')}
CLIENTE B2B:  {get_val(['B2B'], '00')}
COND. ALTO VALOR: {get_val(['Cond. Alto Valor'], '00')}
DEFEITO:
PRAZO:"""
    return texto

def gerar_cards_mpl(kpis, contrato):
    C_BG, C_BORDER = "#ffffff", "#e2e8f0"
    C_TEXT, C_LABEL, C_RED, C_YELLOW, C_GREEN = "#1e293b", "#64748b", "#dc2626", "#d97706", "#16a34a"
    tem_regiao = (contrato == 'ABILITY_SJ')
    h_total = 14 if tem_regiao else 11
    fig, ax = plt.subplots(figsize=(12, h_total), dpi=200)
    fig.patch.set_facecolor(C_BG); ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)

    def draw_card_mobile(x, y, w, h, title, value, val_color=C_TEXT, alert=False):
        card = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=3", fc="white", ec=C_BORDER, lw=2, zorder=2)
        ax.add_patch(card)
        ax.text(x + w/2, y + h*0.82, title.upper(), ha='center', va='center', fontsize=18, color=C_LABEL, weight='bold', zorder=3)
        ax.text(x + w/2, y + h*0.4, str(value), ha='center', va='center', fontsize=55, color=val_color, weight='black', zorder=3)
        if alert:
            ax.add_patch(patches.Circle((x + w - 4, y + h - 4), 2.5, color=C_RED, zorder=4))
            ax.text(x + w - 4, y + h - 4, "!", color="white", fontsize=20, weight='bold', ha='center', va='center', zorder=5)

    ax.text(50, 96, "SIGMA OPS", ha='center', fontsize=32, weight='black', color='#7c3aed')
    hora = datetime.now().strftime("%H:%M")
    ax.text(50, 92, f"{contrato} • {hora}", ha='center', fontsize=22, weight='bold', color='#475569')

    y1 = 68; draw_card_mobile(2, y1, 46, 18, "Total", kpis['total'])
    draw_card_mobile(52, y1, 46, 18, "S/ Técnico", kpis['sem_tec'], C_TEXT, alert=(kpis['sem_tec']>0))
    y2 = 42; w = 30; g = 3
    draw_card_mobile(2, y2, w, 18, "Crítico (>24h)", kpis['sla_red'], C_RED)
    draw_card_mobile(2+w+g, y2, w, 18, "Fora Prazo", kpis['sla_yellow'], C_YELLOW)
    draw_card_mobile(2+2*(w+g), y2, w, 18, "No Prazo", kpis['sla_green'], C_GREEN)
    if tem_regiao:
        y3 = 16
        draw_card_mobile(2, y3, 46, 18, "Litoral", kpis.get('lit', 0))
        draw_card_mobile(52, y3, 46, 18, "Vale", kpis.get('vale', 0))

    ax.text(50, 2, "Gerado via SigmaOPS", ha='center', fontsize=14, color="#94a3b8")
    buf = io.BytesIO(); plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG); plt.close(fig); return buf.getvalue()

def gerar_dashboard_gerencial(df_geral, contratos_list):
    C_BG, C_BAR, C_RED, C_GREEN = "#ffffff", "#7c3aed", "#dc2626", "#16a34a"
    df_filtrado = df_geral.copy()

    total_geral = len(df_filtrado)
    total_gv = len(df_filtrado[df_filtrado['Afetação'] >= 100])
    total_fora = len(df_filtrado[df_filtrado['horas_float'] >= 8])
    total_dentro = total_geral - total_fora

    resumo = df_filtrado.groupby('Contrato_Padrao').agg(
        Total=('Ocorrência', 'count'), 
        No_Prazo=('horas_float', lambda x: (x < 8).sum()), 
        Fora_Prazo=('horas_float', lambda x: (x >= 8).sum()), 
        Grandes_Vultos=('Afetação', lambda x: (x >= 100).sum()),
        VIPs=('VIP', lambda x: (x == 'SIM').sum()),
        Alto_Valor=('Cond. Alto Valor', lambda x: (x == 'SIM').sum()),
        B2B=('B2B', lambda x: (x == 'SIM').sum()),
        Criticos=('horas_float', lambda x: (x > 24).sum())
    ).reset_index().sort_values('Total', ascending=False)

    fig, ax = plt.subplots(figsize=(14, 12), dpi=200)
    fig.patch.set_facecolor(C_BG); ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)

    hora = datetime.now().strftime("%d/%m %H:%M")
    ax.text(50, 96, "VISÃO CLUSTER", ha='center', fontsize=32, weight='black', color='#1e293b')
    ax.text(50, 92, f"Consolidado SigmaOPS • {hora}", ha='center', fontsize=20, weight='bold', color='#7c3aed')

    def draw_box(x, y, w, h, title, val, color, alert=False):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=2", fc="white", ec="#cbd5e1", lw=2, zorder=2)
        ax.add_patch(rect)
        shadow = patches.FancyBboxPatch((x+0.5, y-0.5), w, h, boxstyle="round,pad=0,rounding_size=2", fc="#f1f5f9", ec="none", zorder=1)
        ax.add_patch(shadow)
        ax.text(x+w/2, y+h*0.8, title.upper(), ha='center', fontsize=14, color='#64748b', weight='bold', zorder=3)
        ax.text(x+w/2, y+h*0.35, str(val), ha='center', fontsize=40, color=color, weight='black', zorder=3)
        if alert:
             ax.add_patch(patches.Circle((x + w - 3, y + h - 3), 2, color=C_RED, zorder=4))
             ax.text(x + w - 3, y + h - 3, "!", color="white", fontsize=16, weight='bold', ha='center', va='center', zorder=5)

    draw_box(5, 75, 42, 12, "Total de Casos", total_geral, "#1e293b")
    draw_box(53, 75, 42, 12, "Grandes Vultos", total_gv, C_BAR, alert=(total_gv>0))
    draw_box(5, 60, 42, 12, "Dentro do Prazo (<8h)", total_dentro, C_GREEN)
    draw_box(53, 60, 42, 12, "Fora do Prazo (>=8h)", total_fora, C_RED, alert=(total_fora>0))

    y_start = 55
    ax.text(50, y_start, "DETALHAMENTO POR CONTRATO", ha='center', fontsize=18, weight='bold', color='#333')
    
    colunas = ["CONTRATO", "Total", "No Prazo", "Fora Prazo", "G.V", "Vips", "Alto Valor", "B2B", ">24H"]
    dados_tabela = [[
        row['Contrato_Padrao'], 
        str(row['Total']), 
        str(row['No_Prazo']), 
        str(row['Fora_Prazo']), 
        str(row['Grandes_Vultos']),
        str(row['VIPs']),
        str(row['Alto_Valor']),
        str(row['B2B']),
        str(row['Criticos'])
    ] for _, row in resumo.iterrows()]

    tbl = ax.table(cellText=dados_tabela, colLabels=colunas, loc='center', bbox=[0.05, 0.05, 0.9, 0.45])
    tbl.auto_set_font_size(False); tbl.set_fontsize(11); tbl.scale(1, 2)
    for (i, j), cell in tbl.get_celld().items():
        if i == 0:
            cell.set_text_props(weight='bold', color='white'); cell.set_facecolor('#7c3aed'); cell.set_edgecolor('white')
        else:
            cell.set_edgecolor('#e2e8f0'); cell.set_text_props(weight='bold');
            if i % 2 == 0: cell.set_facecolor('#f8fafc')

    ax.text(50, 2, "Gerado via SigmaOPS", ha='center', fontsize=12, color="#94a3b8")
    buf = io.BytesIO(); plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG); plt.close(fig); return buf.getvalue()

def gerar_lista_mpl_from_view(df_view, col_order, contrato):
    ITENS_POR_PAGINA = 20
    
    cols_to_use = [c for c in col_order if c not in ['horas_float', 'Status SLA']]
    df_p = df_view[cols_to_use].copy()
    
    rename_dict = {
        'Ocorrência': 'ID', 
        'Horas Corridas': 'Tempo',
        'Cond. Alto Valor': 'A.V'
    }
    df_p.rename(columns=rename_dict, inplace=True)
    
    total_linhas = len(df_p)
    num_paginas = (total_linhas + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA
    lista_imagens = []

    def desenhar_pagina(df_chunk, num_pag, total_pags):
        fig_height = max(4, 3 + len(df_chunk)*0.8)
        fig, ax = plt.subplots(figsize=(14, fig_height), dpi=180)
        ax.axis('off'); fig.patch.set_facecolor('white')
        hora = datetime.now().strftime('%d/%m • %H:%M')
        titulo = f"SIGMA OPS: {contrato}\n{hora}"
        if total_pags > 1: titulo += f"\n(Parte {num_pag}/{total_pags})"
        plt.title(titulo, loc='center', pad=40, fontsize=28, weight='black', color='#1e293b')
        
        tbl = ax.table(cellText=df_chunk.values.tolist(), colLabels=df_chunk.columns, cellLoc='center', loc='center')
        
        # FONTE 12
        tbl.auto_set_font_size(False); tbl.set_fontsize(12); tbl.scale(1.2, 3.0)
        
        for j in range(len(df_chunk.columns)):
            cell = tbl[(0, j)]; cell.set_facecolor('#7c3aed'); cell.set_text_props(color='white', weight='bold'); cell.set_height(0.15)
        for i in range(len(df_chunk)):
            idx_real = df_chunk.index[i]; row_original = df_view.loc[idx_real]; c = estilo_tabela(row_original)
            for j in range(len(df_chunk.columns)):
                cell = tbl[(i+1, j)]; cell.set_text_props(color=c, weight='bold'); cell.set_edgecolor("#e2e8f0"); cell.set_linewidth(1.5)
        buf = io.BytesIO(); plt.savefig(buf, format='jpg', dpi=180, bbox_inches='tight', facecolor='white'); plt.close(fig); return buf.getvalue()

    for i in range(num_paginas):
        inicio = i * ITENS_POR_PAGINA; fim = inicio + ITENS_POR_PAGINA; df_chunk = df_p.iloc[inicio:fim]
        img_data = desenhar_pagina(df_chunk, i+1, num_paginas); lista_imagens.append(img_data)
    return lista_imagens

# ==============================================================================
# 🖥️ FRONTEND
# ==============================================================================

st.markdown(f"""
<div class="sigma-header">
    <div><p class="sigma-title">SigmaOPS</p></div>
    <div><span class="sigma-clock">{datetime.now().strftime('%H:%M')}</span></div>
</div>
""", unsafe_allow_html=True)

with st.spinner("Sincronizando SigmaOPS..."):
    df_raw, erro_api = carregar_dados_api()

if df_raw is None:
    st.sidebar.markdown(f"<div class='status-box status-error'>⚠️ Falha na API<br><small>{erro_api}</small></div>", unsafe_allow_html=True)
    st.error(f"❌ Não foi possível carregar os dados. Erro: {erro_api}")
    if st.button("🔄 Tentar Novamente", type="primary"):
        carregar_dados_api.clear()
        st.rerun()
else:
    st.sidebar.markdown(f"<div class='status-box status-ok'>🟢 Sigma Online<br><small>{datetime.now().strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Atualizar Dados"):
        carregar_dados_api.clear()
        st.rerun()

    col_contrato_raw = [c for c in df_raw.columns if str(c).lower().strip() in ['contrato', 'escritório']]
    if col_contrato_raw:
        todos_contratos = df_raw[col_contrato_raw[0]].astype(str).str.strip().str.upper().unique()
        contratos_principais = ["ABILITY_SJ", "TEL_JI", "ABILITY_OS", "TEL_INTERIOR", "TEL_PC_SC", "TELEMONT"]
        opcoes_validas = [c for c in contratos_principais if c in todos_contratos]

        if not opcoes_validas:
            st.warning("Nenhum contrato conhecido encontrado.")
        else:
            tab_op, tab_ger = st.tabs(["Visão Operacional", "Visão Cluster"])

            with tab_op:
                st.markdown("#### Selecione o Contrato")
                contrato_selecionado = st.radio("Selecione:", opcoes_validas, horizontal=True, label_visibility="collapsed")

                df = processar_regras_generico(df_raw, filtrar_contrato=contrato_selecionado)

                if df.empty:
                    st.warning(f"Nenhum dado encontrado para {contrato_selecionado}.")
                else:
                    total = len(df)
                    kpis = { 
                        'total': total, 
                        'sem_tec': len(df[df['Técnicos']==0]), 
                        'sla_red': len(df[df['horas_float']>24]),
                        'sla_yellow': len(df[(df['horas_float']>8)&(df['horas_float']<=24)]), 
                        'sla_green': len(df[df['horas_float']<=8]),
                        'lit': len(df[df['Area']=="Litoral"]), 
                        'vale': len(df[df['Area']=="Vale"]) 
                    }

                    if total <= 15:
                        delta_tot = "Entrante Normal"
                        color_tot = "normal"
                    elif total <= 30:
                        delta_tot = "Atenção"
                        color_tot = "off"
                    elif total <= 40:
                        delta_tot = "Necessário Reforço MO"
                        color_tot = "inverse"
                    else:
                        delta_tot = "Crise"
                        color_tot = "inverse"

                    pct_sem = (kpis['sem_tec']/total*100) if total else 0
                    pct_red = (kpis['sla_red']/total*100) if total else 0
                    pct_yel = (kpis['sla_yellow']/total*100) if total else 0
                    pct_grn = (kpis['sla_green']/total*100) if total else 0

                    st.markdown("### Métricas em Tempo Real")
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Total Aberto", kpis['total'], delta=delta_tot, delta_color=color_tot)
                    m2.metric("S/ Técnico", kpis['sem_tec'], delta=f"{pct_sem:.1f}% do Total", delta_color="inverse")
                    m3.metric("Crítico (>24h)", kpis['sla_red'], delta=f"{pct_red:.1f}% do Total", delta_color="inverse")
                    m4.metric("Fora Prazo", kpis['sla_yellow'], delta=f"{pct_yel:.1f}% do Total", delta_color="off")
                    m5.metric("No Prazo", kpis['sla_green'], delta=f"{pct_grn:.1f}% do Total", delta_color="normal")

                    if contrato_selecionado == 'ABILITY_SJ':
                        st.markdown("---")
                        r1, r2 = st.columns(2)
                        r1.metric("Litoral", kpis['lit'])
                        r2.metric("Vale", kpis['vale'])

                    nome_arq = (datetime.now()).strftime('%H%M')
                    
                    st.divider()
                    
                    col_dl1, col_dl2 = st.columns(2)
                    try:
                        img_cards = gerar_cards_mpl(kpis, contrato_selecionado)
                        col_dl1.download_button("Baixar Resumo (Cards)", img_cards, f"Resumo_{nome_arq}.jpg", "image/jpeg", width="stretch")
                    except: pass

                    cols_exist = [c for c in ['Ocorrência', 'Area', 'AT', 'Afetação', 'Status SLA', 'Horas Corridas', 'VIP', 'Cond. Alto Valor', 'B2B', 'Técnicos', 'horas_float'] if c in df.columns]
                    
                    try:
                        cols_exp = [c for c in cols_exist if c != 'horas_float']
                        lista_imagens = gerar_lista_mpl_from_view(df, cols_exp, contrato_selecionado)
                        if lista_imagens:
                            col_dl2.download_button("Baixar Lista Detalhada", lista_imagens[0], f"Lista_{nome_arq}.jpg", "image/jpeg", width="stretch")
                    except: pass

                    df_gv = df[df['Afetação'] >= 100].copy()
                    if not df_gv.empty:
                        st.divider()
                        st.error(f"🚨 **GRANDE VULTO DETECTADO ({len(df_gv)})**")
                        with st.expander("Ver Detalhes e Carimbos", expanded=True):
                            for idx, row in df_gv.iterrows():
                                texto_pronto = gerar_texto_gv(row, contrato_selecionado)
                                st.markdown(f"**Ocorrência: {row['Ocorrência']}**")
                                st.code(texto_pronto, language="text")
                                st.divider()
                    
                    st.divider()
                    
                    c_filt1, c_filt2 = st.columns(2)
                    f_area = []
                    if contrato_selecionado == 'ABILITY_SJ':
                        f_area = c_filt1.multiselect("Filtrar Região", df['Area'].unique())
                    f_sla = c_filt2.multiselect("Filtrar SLA", ["Crítico", "Fora do Prazo", "No Prazo"])

                    df_show = df.copy()
                    if f_area: df_show = df_show[df_show['Area'].isin(f_area)]
                    if f_sla: df_show = df_show[df_show['Status SLA'].isin(f_sla)]
                    if 'AT' in df_show.columns: df_show['AT'] = df_show['AT'].astype(str).str[:2]

                    st.dataframe(
                        df_show[cols_exist].style.apply(row_style_apply, axis=1), 
                        height=600, 
                        width="stretch", 
                        column_config={
                            "Ocorrência": st.column_config.TextColumn("ID", width="small"), 
                            "Afetação": st.column_config.NumberColumn("Afet.", format="%.0f"), 
                            "horas_float": None
                        }
                    )

            with tab_ger:
                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- FILTRO MULTISELECT DENTRO DE FORMULÁRIO ---
                with st.form("form_cluster"):
                    filtro_contratos = st.multiselect(
                        "Selecione os Contratos:",
                        options=opcoes_validas,
                        default=opcoes_validas,
                        placeholder="Escolha um ou mais contratos..."
                    )
                    aplicar = st.form_submit_button("Atualizar Visão")

                if not filtro_contratos:
                    st.warning("Selecione ao menos um contrato.")
                else:
                    # Lógica aplicada somente após o submit (ou no load inicial)
                    df_geral = processar_regras_generico(df_raw, contratos_validos=filtro_contratos)
                    
                    if not df_geral.empty:
                        total_geral = len(df_geral)
                        total_gv = len(df_geral[df_geral['Afetação'] >= 100])
                        total_fora = len(df_geral[df_geral['horas_float'] >= 8])
                        total_dentro = total_geral - total_fora

                        g1, g2 = st.columns(2)
                        g1.metric("Total Geral", total_geral)
                        g2.metric("Grandes Vultos", total_gv, delta="Atenção" if total_gv > 0 else "OK", delta_color="inverse")
                        
                        st.markdown("<br>", unsafe_allow_html=True)

                        g3, g4 = st.columns(2)
                        g3.metric("Dentro do Prazo", total_dentro)
                        g4.metric("Fora do Prazo", total_fora, delta="Crítico" if total_fora > 0 else "OK", delta_color="inverse")

                        st.divider()
                        try:
                            img_dashboard = gerar_dashboard_gerencial(df_geral, filtro_contratos)
                            st.download_button("Baixar Dashboard Gerencial", img_dashboard, f"Dash_Cluster_{nome_arq}.jpg", "image/jpeg", width="stretch", type="primary")
                        except Exception as e: st.error(f"Erro ao gerar dashboard: {e}")

                        st.divider()
                        st.markdown("##### Detalhamento por Contrato")
                        
                        resumo = df_geral.groupby('Contrato_Padrao').agg(
                            Total=('Ocorrência', 'count'), 
                            No_Prazo=('horas_float', lambda x: (x < 8).sum()),
                            Fora_Prazo=('horas_float', lambda x: (x >= 8).sum()),
                            Grandes_Vultos=('Afetação', lambda x: (x >= 100).sum()),
                            VIPs=('VIP', lambda x: (x == 'SIM').sum()),
                            Condos=('Cond. Alto Valor', lambda x: (x == 'SIM').sum()),
                            B2B=('B2B', lambda x: (x == 'SIM').sum()),
                            Criticos=('horas_float', lambda x: (x > 24).sum())
                        ).reset_index().sort_values('Total', ascending=False)
                        
                        st.dataframe(resumo, width="stretch", hide_index=True, column_config={
                            "No_Prazo": st.column_config.NumberColumn("No Prazo", format="%d "),
                            "Fora_Prazo": st.column_config.NumberColumn("Fora do Prazo", format="%d "),
                            "VIPs": st.column_config.NumberColumn("VIPs", format="%d "),
                            "Condos": st.column_config.NumberColumn("Alto Valor", format="%d "),
                            "B2B": st.column_config.NumberColumn("B2B", format="%d "),
                            "Criticos": st.column_config.NumberColumn("Críticos (>24h)", format="%d ")
                        })
                    else:
                        st.info("Sem dados para os contratos selecionados.")
    else:
        st.error("Colunas de Contrato não identificadas na API.")