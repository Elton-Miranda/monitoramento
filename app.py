import os
import time

# ==============================================================================
# 🌍 1. CONFIGURAÇÃO DE AMBIENTE
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
# 🔒 SISTEMA DE LOGIN (DESATIVADO TEMPORARIAMENTE)
# ==============================================================================
# O código abaixo está comentado com '#' para não aparecer na tela.
# Para reativar: remova os '#' e apague a linha USER_ROLE = "admin"

# def check_password():
#     def password_entered():
#         user_input = st.session_state["username"].strip().lower()
#         password_input = st.session_state["password"].strip()
#         if user_input in st.secrets["passwords"]:
#             if password_input == st.secrets["passwords"][user_input]:
#                 st.session_state["password_correct"] = True
#                 st.session_state["role"] = st.secrets["roles"].get(user_input, "user") if "roles" in st.secrets else "user"
#                 del st.session_state["password"]; del st.session_state["username"]
#             else: st.session_state["password_correct"] = False
#         else: st.session_state["password_correct"] = False

#     if "password_correct" not in st.session_state:
#         st.markdown("""<style>.block-container { padding-top: 3rem; display: flex; align-items: center; justify-content: center; } div[data-testid="stForm"] { border: none; padding: 50px; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.08); background: white; width: 100%; max-width: 450px; } div[data-testid="stTextInput"] > div > div { border: 2px solid #a78bfa !important; border-radius: 10px !important; background-color: #f8fafc; padding: 0px !important; } div[data-testid="stTextInput"] input { padding: 10px 15px !important; color: #333 !important; } div[data-testid="stMarkdownContainer"] p { font-weight: 600; color: #475569; font-size: 14px; } div[data-testid="stFormSubmitButton"] > button { width: 100%; background-color: #1e1b4b !important; color: white !important; border-radius: 10px; padding: 10px; border: none; font-weight: bold; margin-top: 15px; } div[data-testid="stFormSubmitButton"] > button:hover { background-color: #7c3aed !important; } .login-title { text-align: center; font-size: 42px; font-weight: 900; color: #7c3aed; margin-bottom: 5px; margin-top: 0px; letter-spacing: -1px; } .login-subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; font-weight: 500; font-size: 0.95rem; } </style>""", unsafe_allow_html=True)
#         c1, c2, c3 = st.columns([1, 2, 1])
#         with c2:
#             st.markdown("<h1 class='login-title'>SigmaOPS</h1>", unsafe_allow_html=True)
#             st.markdown("<p class='login-subtitle'>Acesso Restrito</p>", unsafe_allow_html=True)
#             with st.form("credentials"):
#                 st.text_input("Usuário", key="username")
#                 st.text_input("Senha", type="password", key="password")
#                 st.form_submit_button("Entrar", on_click=password_entered)
#         return False
#     elif not st.session_state["password_correct"]:
#         st.error("😕 Usuário ou senha incorretos.")
#         if st.button("Tentar Novamente"): st.session_state["password_correct"] = None; st.rerun()
#         return False
#     else: return True

# if not check_password(): st.stop()
# USER_ROLE = st.session_state.get("role", "user")

# --- BYPASS DE LOGIN (ATIVO) ---
USER_ROLE = "admin" # Libera acesso total

# ==============================================================================
# 🎨 SIGMA UI - V15.17 (ESTILOS FINAIS)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f4f6f9; }

    .block-container { padding-top: 3.5rem !important; padding-bottom: 1rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; max-width: 100% !important; }
    .sigma-header { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 10px 15px; border-radius: 8px; color: white; margin-top: -10px; margin-bottom: 10px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #7c3aed; }
    .sigma-title { font-size: 18px; font-weight: 900; margin: 0; background: -webkit-linear-gradient(0deg, #fff, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sigma-clock { background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 12px; font-weight: 600; font-size: 11px; border: 1px solid rgba(255,255,255,0.1); }

    .stMultiSelect [data-baseweb="tag"] { background-color: #7c3aed !important; color: white !important; border: 1px solid #6d28d9 !important; }
    .stMultiSelect [data-baseweb="tag"] span { color: white !important; }
    .stMultiSelect [data-baseweb="tag"] svg { fill: white !important; }

    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] { display: grid !important; grid-template-columns: repeat(3, 1fr) !important; gap: 8px !important; background-color: transparent !important; width: 100% !important; margin-bottom: 5px; }
    div[role="radiogroup"] label { background-color: white !important; border: 1px solid #cbd5e1 !important; color: #475569 !important; padding: 8px 4px !important; border-radius: 6px !important; font-weight: 600 !important; font-size: 12px !important; transition: all 0.2s; margin: 0 !important; width: 100% !important; height: 100% !important; display: flex; justify-content: center; align-items: center; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); white-space: normal !important; line-height: 1.2 !important; }
    div[role="radiogroup"] label:has(input:checked) { background-color: #7c3aed !important; border-color: #7c3aed !important; color: white !important; box-shadow: 0 2px 5px rgba(124, 58, 237, 0.3) !important; }
    div[role="radiogroup"] label:has(input:checked) p { color: white !important; }
    div[role="radiogroup"] label:hover { background-color: #f1f5f9 !important; border-color: #94a3b8 !important; }

    @media only screen and (max-width: 600px) {
        div[role="radiogroup"] { grid-template-columns: repeat(2, 1fr) !important; }
        div[role="radiogroup"] label { padding: 8px 2px !important; font-size: 11px !important; }
        .sigma-title { font-size: 16px; }
    }

    .stDataFrame td { text-align: center !important; font-size: 12px !important; padding: 2px !important; } 
    .stDataFrame th { text-align: center !important; font-size: 12px !important; }
    .alert-box { padding: 6px; border-radius: 6px; background-color: #fee2e2; border: 1px solid #fecaca; color: #991b1b; font-weight: bold; font-size: 13px; text-align: center; margin-bottom: 5px; }
    [data-testid="stFormSubmitButton"] > button { background-color: #7c3aed !important; color: white !important; border: none !important; }
    .modo-leitura { font-size: 24px; line-height: 1.6; color: #1e293b; background-color: white; padding: 30px; border-radius: 15px; border-left: 10px solid #7c3aed; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO ---
try:
    API_URL = st.secrets["api"]["url"]
    API_HEADERS = dict(st.secrets["api"].get("headers", {}))
except:
    API_URL = ""
    API_HEADERS = {}

ARQUIVO_CNL_CSV = "CNL_BASE_MONITORAMENTO.csv"
ARQUIVO_CNL_XLSX = "CNL_BASE_MONITORAMENTO.xlsx"

# ==============================================================================
# 🧠 LÓGICA (MANTIDA)
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
            df = df.dropna(subset=['CNL']); df['CNL'] = df['CNL'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip(); df['MUNICÍPIO'] = df['MUNICÍPIO'].astype(str).str.strip().str.upper()
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
                rename_map = { 'ocorrencia': 'Ocorrência', 'data_abertura': 'Data Abertura', 'contrato': 'Contrato', 'escritorio': 'Escritório', 'cnl': 'CNL', 'at': 'AT', 'cabo': 'Cabo', 'afetacao': 'Afetação', 'origem': 'Origem', 'primarias': 'Primárias', 'bd': 'BD', 'propenso_anatel': 'Propensos - Anatel', 'reclamado_anatel': 'Reclamados - Anatel', 'vip': 'VIP', 'b2b_avancado': 'B2B_Value', 'cond_alto_valor': 'Cond. Alto Valor' }
                df.rename(columns=rename_map, inplace=True)
                df['Técnicos'] = df['tecnicos'].apply(lambda x: len(x) if isinstance(x, list) else 0) if 'tecnicos' in json_data['ocorrencias'][0] else 0
                for col in ['VIP']: df[col] = df[col].apply(lambda x: 'SIM' if str(x).upper().strip() in ['TRUE', 'SIM', '1', 'S', 'YES'] else 'NÃO') if col in df.columns else 'NÃO'
                df['Cond. Alto Valor'] = pd.to_numeric(df['Cond. Alto Valor'], errors='coerce').fillna(0).apply(lambda x: 'SIM' if x != 0 else 'NÃO') if 'Cond. Alto Valor' in df.columns else 'NÃO'
                df['B2B'] = pd.to_numeric(df['B2B_Value'], errors='coerce').fillna(0).apply(lambda x: 'SIM' if x > 0 else 'NÃO') if 'B2B_Value' in df.columns else 'NÃO'
                df['Data Abertura'] = pd.to_datetime(df['Data Abertura'], errors='coerce')
                return df, None
            else: return None, "JSON incompleto."
        return None, f"Erro HTTP {response.status_code}"
    except Exception as e: return None, f"Conexão: {str(e)}"

def processar_regras_generico(df_full, contratos_validos=None, filtrar_contrato=None):
    agora = datetime.utcnow() - timedelta(hours=3)
    cols_map = {str(c).lower().strip(): c for c in df_full.columns}
    df_cnl = carregar_base_cnl()
    col_cnl_main = cols_map.get('cnl')
    if df_cnl is not None and col_cnl_main:
        df_full[col_cnl_main] = df_full[col_cnl_main].astype(str).str.replace(r'\.0$', '', regex=True).str.strip(); df_full = pd.merge(df_full, df_cnl, left_on=col_cnl_main, right_on='CNL', how='left'); df_full.rename(columns={'MUNICÍPIO': 'Cidade_Real'}, inplace=True)
    
    col_contrato = cols_map.get('contrato') or cols_map.get('escritório')
    if col_contrato:
        df_full['Contrato_Padrao'] = df_full[col_contrato].astype(str).str.strip().str.upper()
        if filtrar_contrato: df = df_full[df_full['Contrato_Padrao'] == filtrar_contrato].copy()
        elif contratos_validos: df = df_full[df_full['Contrato_Padrao'].isin(contratos_validos)].copy()
        else: return pd.DataFrame()
    else: return pd.DataFrame()
    
    col_abertura = cols_map.get('abertura') or cols_map.get('data abertura')
    if not col_abertura: return pd.DataFrame()
    df['Abertura_dt'] = df[col_abertura]; df = df.dropna(subset=['Abertura_dt'])
    if pd.api.types.is_datetime64tz_dtype(df['Abertura_dt']): df['Abertura_dt'] = df['Abertura_dt'].dt.tz_localize(None)
    df['diff_segundos'] = (agora - df['Abertura_dt']).dt.total_seconds()
    if not df.empty and df['diff_segundos'].median() < -100: df['diff_segundos'] = df['diff_segundos'] + 10800
    df['horas_float'] = df['diff_segundos'] / 3600
    def formatar_hhmmss(s):
        if pd.isna(s): return "00:00:00"
        val = int(s); val = 0 if val < 0 else val; m, s = divmod(val, 60); h, m = divmod(m, 60); return f"{h:02d}:{m:02d}:{s:02d}"
    df['Horas Corridas'] = df['diff_segundos'].apply(formatar_hhmmss)
    def classificar_sla(h): return "Crítico" if h > 24 else ("Fora do Prazo" if h > 8 else "No Prazo")
    df['Status SLA'] = df['horas_float'].apply(classificar_sla)
    col_tec = cols_map.get('técnicos') or cols_map.get('tecnicos'); df['Técnicos'] = pd.to_numeric(df[col_tec], errors='coerce').fillna(0)
    col_afe = cols_map.get('afetação') or cols_map.get('afetacao'); df['Afetação'] = pd.to_numeric(df[col_afe], errors='coerce').fillna(0)
    
    col_at = cols_map.get('at') or cols_map.get('area')
    def definir_area_safe(row):
        if str(row.get('Contrato_Padrao', '')).upper() == 'ABILITY_SJ':
            val = row.get(col_at) if col_at else None
            if pd.isna(val): return "Vale"
            sigla = str(val).split('-')[0].strip().upper()
            litoral = ['TG', 'PG', 'LZ', 'MK', 'MG', 'PN', 'AA', 'BV', 'FM', 'RP', 'AC', 'FP', 'BA', 'TQ', 'BO', 'BU', 'BC', 'PJ', 'PB', 'MR']
            return "Litoral" if sigla in litoral else "Vale"
        return row.get('Area', 'Geral')
    df['Area'] = df.apply(definir_area_safe, axis=1)
    
    return df.sort_values(by='horas_float', ascending=False)

def estilo_tabela(row):
    h = row.get('horas_float', None); sla_color = '#dc2626' if h and h>24 else ('#d97706' if h and h>8 else ('#16a34a' if h else '#000'))
    val_af = None
    for k in ['Afetação', 'afetação', 'Afetacao']:
        if k in row.index:
            try: val_af = float(row[k]); break
            except: pass
    if val_af and val_af >= 100: sla_color = '#2563eb'
    return sla_color

def row_style_apply(row):
    base_color = estilo_tabela(row); styles = [f'color: {base_color}; font-weight: 700; text-align: center; vertical-align: middle'] * len(row)
    for i, col_name in enumerate(row.index):
        val_str = str(row[col_name]).upper().strip()
        if col_name == 'VIP' and val_str == 'SIM': styles[i] = 'background-color: #f0abfc; color: #86198f; font-weight: 900; text-align: center; border-radius: 6px; padding: 2px;'
        elif col_name == 'Cond. Alto Valor' and val_str == 'SIM': styles[i] = 'background-color: #bef264; color: #365314; font-weight: 900; text-align: center; border-radius: 6px; padding: 2px;'
        elif col_name == 'B2B' and val_str == 'SIM': styles[i] = 'background-color: #a78bfa; color: #4c1d95; font-weight: 900; text-align: center; border-radius: 6px; padding: 2px;'
    return styles

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
        at_full = str(row.get('AT', row.get('Area', 'N/I'))).strip().upper(); sigla_at = at_full.split('-')[0].strip() if '-' in at_full else at_full[:3]
        mapa = { 'SJC': 'SÃO JOSÉ DOS CAMPOS', 'JAC': 'JACAREÍ', 'TAU': 'TAUBATÉ', 'GUA': 'GUARATINGUETÁ', 'PNO': 'PINDAMONHANGABA', 'CAR': 'CARAGUATATUBA', 'UBA': 'UBATUBA', 'SBO': 'SÃO SEBASTIÃO', 'ILH': 'ILHABELA' }
        cidade = mapa.get(sigla_at, "VERIFICAR CIDADE")
    try: dt_criacao = row['Abertura_dt'].strftime("%d/%m/%Y")
    except: dt_criacao = str(row['Abertura_dt'])
    try: hr_criacao = row['Abertura_dt'].strftime("%H:%M")
    except: hr_criacao = ""
    return f"""✅ *INFORMATIVO GRANDE VULTO*\n\n*{contrato.replace('_', ' ')}*\n\n{row['Ocorrência']} - FTTx\nORIGEM: {get_val(['Origem'], 'OLTM')}\nAT: {str(row.get('AT', row.get('Area', 'N/I')))}\nCIDADE: {cidade}\nQUANT. PRIMÁRIAS AFETADAS: {get_val(['Primárias', 'primarias'], 'N/I')}\nCABO: {get_val(['Cabo'], 'N/I')}\nAFETAÇÃO: {int(row['Afetação'])}\nBDs: {get_val(['BD', 'BDs'], 'N/I')}\nCRIAÇÃO: {dt_criacao}\nHORA: {hr_criacao}\nPROPENSOS-ANATEL: {get_val(['Propensos - Anatel'], '00')}\nRECLAMADOS-ANATEL: {get_val(['Reclamados - Anatel'], '00')}\nCLIENTE VIP:  {get_val(['VIP'], '00')}\nCLIENTE B2B:  {get_val(['B2B'], '00')}\nCOND. ALTO VALOR: {get_val(['Cond. Alto Valor'], '00')}\nDEFEITO:\nPRAZO:"""

def gerar_cards_mpl(kpis, contrato):
    C_BG, C_BORDER = "#ffffff", "#e2e8f0"; C_TEXT, C_LABEL = "#1e293b", "#64748b"; C_RED, C_YELLOW, C_GREEN = "#dc2626", "#d97706", "#16a34a"
    tem_regiao = (contrato == 'ABILITY_SJ'); h_total = 14 if tem_regiao else 11
    fig, ax = plt.subplots(figsize=(12, h_total), dpi=200); fig.patch.set_facecolor(C_BG); ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    def draw_card_mobile(x, y, w, h, title, value, val_color=C_TEXT, alert=False):
        card = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=3", fc="white", ec=C_BORDER, lw=2, zorder=2); ax.add_patch(card); ax.text(x + w/2, y + h*0.82, title.upper(), ha='center', va='center', fontsize=18, color=C_LABEL, weight='bold', zorder=3); ax.text(x + w/2, y + h*0.4, str(value), ha='center', va='center', fontsize=55, color=val_color, weight='black', zorder=3)
        if alert: ax.add_patch(patches.Circle((x + w - 4, y + h - 4), 2.5, color=C_RED, zorder=4)); ax.text(x + w - 4, y + h - 4, "!", color="white", fontsize=20, weight='bold', ha='center', va='center', zorder=5)
    ax.text(50, 96, "SIGMA OPS", ha='center', fontsize=32, weight='black', color='#7c3aed'); hora = datetime.now().strftime("%H:%M"); ax.text(50, 92, f"{contrato} • {hora}", ha='center', fontsize=22, weight='bold', color='#475569')
    y1 = 68; draw_card_mobile(2, y1, 46, 18, "Total", kpis['total']); draw_card_mobile(52, y1, 46, 18, "S/ Técnico", kpis['sem_tec'], C_TEXT, alert=(kpis['sem_tec']>0))
    y2 = 42; w = 30; g = 3; draw_card_mobile(2, y2, w, 18, "Crítico (>24h)", kpis['sla_red'], C_RED); draw_card_mobile(2+w+g, y2, w, 18, "Fora Prazo", kpis['sla_yellow'], C_YELLOW); draw_card_mobile(2+2*(w+g), y2, w, 18, "No Prazo", kpis['sla_green'], C_GREEN)
    if tem_regiao: y3 = 16; draw_card_mobile(2, y3, 46, 18, "Litoral", kpis.get('lit', 0)); draw_card_mobile(52, y3, 46, 18, "Vale", kpis.get('vale', 0))
    buf = io.BytesIO(); plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG); plt.close(fig); return buf.getvalue()

def gerar_dashboard_gerencial(df_geral, contratos_list):
    C_BG, C_BAR, C_RED, C_GREEN = "#ffffff", "#7c3aed", "#dc2626", "#16a34a"; df_filtrado = df_geral.copy()
    total_geral = len(df_filtrado); total_gv = len(df_filtrado[df_filtrado['Afetação'] >= 100]); total_fora = len(df_filtrado[df_filtrado['horas_float'] >= 8]); total_dentro = total_geral - total_fora
    resumo = df_filtrado.groupby('Contrato_Padrao').agg(Total=('Ocorrência', 'count'), No_Prazo=('horas_float', lambda x: (x < 8).sum()), Fora_Prazo=('horas_float', lambda x: (x >= 8).sum()), Grandes_Vultos=('Afetação', lambda x: (x >= 100).sum()), VIPs=('VIP', lambda x: (x == 'SIM').sum()), Alto_Valor=('Cond. Alto Valor', lambda x: (x == 'SIM').sum()), B2B=('B2B', lambda x: (x == 'SIM').sum()), Criticos=('horas_float', lambda x: (x > 24).sum())).reset_index().sort_values('Total', ascending=False)
    fig, ax = plt.subplots(figsize=(14, 12), dpi=200); fig.patch.set_facecolor(C_BG); ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    hora = datetime.now().strftime("%d/%m %H:%M"); ax.text(50, 96, "VISÃO CLUSTER", ha='center', fontsize=32, weight='black', color='#1e293b'); ax.text(50, 92, f"Consolidado SigmaOPS • {hora}", ha='center', fontsize=20, weight='bold', color='#7c3aed')
    def draw_box(x, y, w, h, title, val, color, alert=False):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=2", fc="white", ec="#cbd5e1", lw=2, zorder=2); ax.add_patch(rect); shadow = patches.FancyBboxPatch((x+0.5, y-0.5), w, h, boxstyle="round,pad=0,rounding_size=2", fc="#f1f5f9", ec="none", zorder=1); ax.add_patch(shadow); ax.text(x+w/2, y+h*0.8, title.upper(), ha='center', fontsize=14, color='#64748b', weight='bold', zorder=3); ax.text(x+w/2, y+h*0.35, str(val), ha='center', fontsize=40, color=color, weight='black', zorder=3)
        if alert: ax.add_patch(patches.Circle((x + w - 3, y + h - 3), 2, color=C_RED, zorder=4)); ax.text(x + w - 3, y + h - 3, "!", color="white", fontsize=16, weight='bold', ha='center', va='center', zorder=5)
    draw_box(5, 75, 42, 12, "Total de Casos", total_geral, "#1e293b"); draw_box(53, 75, 42, 12, "Grandes Vultos", total_gv, C_BAR, alert=(total_gv>0)); draw_box(5, 60, 42, 12, "Dentro do Prazo (<8h)", total_dentro, C_GREEN); draw_box(53, 60, 42, 12, "Fora do Prazo (>=8h)", total_fora, C_RED, alert=(total_fora>0))
    y_start = 55; ax.text(50, y_start, "DETALHAMENTO POR CONTRATO", ha='center', fontsize=18, weight='bold', color='#333')
    colunas = ["CONTRATO", "TOTAL", "NO PZ", "FORA PZ", "G. VULTO", "VIPS", "ALTO VALOR", "B2B", "CRÍTICO >24H"]
    dados_tabela = [[row['Contrato_Padrao'], str(row['Total']), str(row['No_Prazo']), str(row['Fora_Prazo']), str(row['Grandes_Vultos']), str(row['VIPs']), str(row['Alto_Valor']), str(row['B2B']), str(row['Criticos'])] for _, row in resumo.iterrows()]
    tbl = ax.table(cellText=dados_tabela, colLabels=colunas, loc='center', bbox=[0.05, 0.05, 0.9, 0.45]); tbl.auto_set_font_size(False); tbl.set_fontsize(11); tbl.scale(1, 2)
    for (i, j), cell in tbl.get_celld().items():
        if i == 0: cell.set_text_props(weight='bold', color='white'); cell.set_facecolor('#7c3aed'); cell.set_edgecolor('white')
        else: cell.set_edgecolor('#e2e8f0'); cell.set_text_props(weight='bold'); 
        if i % 2 == 0: cell.set_facecolor('#f8fafc')
    ax.text(50, 2, "Gerado via SigmaOPS", ha='center', fontsize=12, color="#94a3b8"); buf = io.BytesIO(); plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG); plt.close(fig); return buf.getvalue()

def gerar_lista_mpl_from_view(df_view, col_order, contrato):
    ITENS_POR_PAGINA = 20; cols_to_use = [c for c in col_order if c not in ['horas_float', 'Status SLA']]; df_p = df_view[cols_to_use].copy(); rename_dict = {'Ocorrência': 'ID', 'Horas Corridas': 'Tempo', 'Cond. Alto Valor': 'A.V'}; df_p.rename(columns=rename_dict, inplace=True)
    total_linhas = len(df_p); num_paginas = (total_linhas + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA; lista_imagens = []
    def desenhar_pagina(df_chunk, num_pag, total_pags):
        fig_height = max(4, 3 + len(df_chunk)*0.8); fig, ax = plt.subplots(figsize=(14, fig_height), dpi=180); ax.axis('off'); fig.patch.set_facecolor('white')
        hora = datetime.now().strftime('%d/%m • %H:%M'); titulo = f"SIGMA OPS: {contrato}\n{hora}"; 
        if total_pags > 1: titulo += f"\n(Parte {num_pag}/{total_pags})"
        plt.title(titulo, loc='center', pad=40, fontsize=28, weight='black', color='#1e293b')
        tbl = ax.table(cellText=df_chunk.values.tolist(), colLabels=df_chunk.columns, cellLoc='center', loc='center'); tbl.auto_set_font_size(False); tbl.set_fontsize(12); tbl.scale(1.2, 3.0)
        for j in range(len(df_chunk.columns)): cell = tbl[(0, j)]; cell.set_facecolor('#7c3aed'); cell.set_text_props(color='white', weight='bold'); cell.set_height(0.15)
        for i in range(len(df_chunk)):
            idx_real = df_chunk.index[i]; row_original = df_view.loc[idx_real]; c = estilo_tabela(row_original)
            for j in range(len(df_chunk.columns)): cell = tbl[(i+1, j)]; cell.set_text_props(color=c, weight='bold'); cell.set_edgecolor("#e2e8f0"); cell.set_linewidth(1.5)
        buf = io.BytesIO(); plt.savefig(buf, format='jpg', dpi=180, bbox_inches='tight', facecolor='white'); plt.close(fig); return buf.getvalue()
    for i in range(num_paginas): inicio = i * ITENS_POR_PAGINA; fim = inicio + ITENS_POR_PAGINA; df_chunk = df_p.iloc[inicio:fim]; img_data = desenhar_pagina(df_chunk, i+1, num_paginas); lista_imagens.append(img_data)
    return lista_imagens

# ==============================================================================
# 🖥️ FRONTEND - DASHBOARD COMPACTO
# ==============================================================================

# --- MODO VOZ ---
if st.query_params.get("mode") == "voz":
    with st.spinner("Gerando..."):
        df_raw, erro = carregar_dados_api()
        if df_raw is not None:
            df_geral = processar_regras_generico(df_raw, contratos_validos=df_raw['Contrato'].unique())
            total = len(df_geral); criticos = len(df_geral[df_geral['horas_float'] > 24])
            st.markdown(f"<div class='modo-leitura'>Resumo: {total} casos. {criticos} críticos.</div>", unsafe_allow_html=True); st.stop()

# --- HEADER SLIM ---
st.markdown(f"""<div class="sigma-header"><div><p class="sigma-title">SigmaOPS</p></div><div><span class="sigma-clock">{datetime.now().strftime('%H:%M')}</span></div></div>""", unsafe_allow_html=True)

with st.spinner("Sincronizando..."):
    df_raw, erro_api = carregar_dados_api()

if df_raw is None:
    st.error(f"Falha na API: {erro_api}")
    if st.button("🔄 Tentar Novamente"): carregar_dados_api.clear(); st.rerun()
else:
    col_contrato_raw = [c for c in df_raw.columns if str(c).lower().strip() in ['contrato', 'escritório']]
    if col_contrato_raw:
        todos_contratos = df_raw[col_contrato_raw[0]].astype(str).str.strip().str.upper().unique()
        contratos_principais = ["ABILITY_SJ", "TEL_JI", "ABILITY_OS", "TEL_INTERIOR", "TEL_PC_SC", "TELEMONT"]
        opcoes_validas = [c for c in contratos_principais if c in todos_contratos]

        if not opcoes_validas: st.warning("Nenhum contrato encontrado.")
        else:
            container_op = None; container_cluster = None
            if USER_ROLE == "admin": tab_op, tab_ger = st.tabs(["Operacional", "Cluster"]); container_op = tab_op; container_cluster = tab_ger
            else: container_op = st.container()

            with container_op:
                # LINHA 1: MENU E FILTROS COMPACTOS
                c_sel, c_filt1, c_filt2, c_refresh = st.columns([1.5, 1, 1, 0.5])
                with c_sel: 
                    # --- RESTAURAÇÃO: BOTÕES (RADIO GRID) ---
                    contrato_selecionado = st.radio("Selecione:", opcoes_validas, horizontal=True, label_visibility="collapsed")
                with c_refresh: 
                    if st.button("🔄", help="Atualizar"): carregar_dados_api.clear(); st.rerun()

                df = processar_regras_generico(df_raw, filtrar_contrato=contrato_selecionado)
                
                if df.empty: st.warning("Sem dados.")
                else:
                    # FILTROS DINÂMICOS
                    f_area = []; f_sla = []
                    with c_filt1: 
                        if contrato_selecionado == 'ABILITY_SJ': f_area = st.multiselect("Região", df['Area'].unique(), placeholder="Região", label_visibility="collapsed")
                    with c_filt2: f_sla = st.multiselect("SLA", ["Crítico", "Fora do Prazo", "No Prazo"], placeholder="SLA", label_visibility="collapsed")

                    # KPIs COMPACTOS (GRID HTML)
                    total = len(df); kpis = { 'total': total, 'sem_tec': len(df[df['Técnicos']==0]), 'sla_red': len(df[df['horas_float']>24]), 'sla_yellow': len(df[(df['horas_float']>8)&(df['horas_float']<=24)]), 'sla_green': len(df[df['horas_float']<=8]), 'lit': len(df[df['Area']=="Litoral"]), 'vale': len(df[df['Area']=="Vale"]) }
                    
                    # --- HTML INJECTION FOR METRICS ---
                    card_style = "background:white;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;padding:8px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.03);display:flex;flex-direction:column;justify-content:center;height:70px;"
                    val_style = "font-size:18px;font-weight:800;color:#0f172a;line-height:1.2;"
                    lbl_style = "font-size:11px;color:#64748b;margin-bottom:2px;"
                    
                    def get_delta_html(val, color): return f"<span style='font-size:10px;font-weight:bold;color:{color};background:{color}15;padding:1px 4px;border-radius:4px;'>{val}</span>"
                    
                    cards_html_list = []
                    
                    cards_html_list.append(f'<div style="{card_style}"><div style="{lbl_style}">Total</div><div style="{val_style}">{kpis["total"]}</div></div>')
                    
                    cards_html_list.append(f'<div style="{card_style}"><div style="{lbl_style}">S/ Técnico</div><div style="{val_style}">{kpis["sem_tec"]} {get_delta_html(f"{(kpis["sem_tec"]/total*100):.0f}%", "#dc2626")}</div></div>')
                    
                    cards_html_list.append(f'<div style="{card_style.replace("#7c3aed", "#dc2626")}"><div style="{lbl_style}">Crítico (>24h)</div><div style="{val_style}">{kpis["sla_red"]} {get_delta_html(f"{(kpis["sla_red"]/total*100):.0f}%", "#dc2626")}</div></div>')
                    
                    cards_html_list.append(f'<div style="{card_style.replace("#7c3aed", "#d97706")}"><div style="{lbl_style}">Fora do Prazo (>8h)</div><div style="{val_style}">{kpis["sla_yellow"]} {get_delta_html(f"{(kpis["sla_yellow"]/total*100):.0f}%", "#d97706")}</div></div>')
                    
                    cards_html_list.append(f'<div style="{card_style.replace("#7c3aed", "#16a34a")}"><div style="{lbl_style}">No Prazo</div><div style="{val_style}">{kpis["sla_green"]} {get_delta_html(f"{(kpis["sla_green"]/total*100):.0f}%", "#16a34a")}</div></div>')

                    if contrato_selecionado == 'ABILITY_SJ':
                        cards_html_list.append(f'<div style="{card_style}"><div style="{lbl_style}">Litoral</div><div style="{val_style}">{kpis["lit"]}</div></div>')
                        cards_html_list.append(f'<div style="{card_style}"><div style="{lbl_style}">Vale</div><div style="{val_style}">{kpis["vale"]}</div></div>')

                    html_kpis = f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:15px;">{''.join(cards_html_list)}</div>"""
                    st.markdown(html_kpis, unsafe_allow_html=True)

                    # ALERTA COMPACTO (GRANDE VULTO)
                    df_gv = df[df['Afetação'] >= 100].copy()
                    if not df_gv.empty:
                        st.markdown(f"<div class='alert-box'>🚨 {len(df_gv)} GRANDE(S) VULTO(S) EM ABERTO</div>", unsafe_allow_html=True)
                        with st.expander("Ver Detalhes GV"):
                            for idx, row in df_gv.iterrows(): st.code(gerar_texto_gv(row, contrato_selecionado), language="text")

                    # MENU DE EXPORTAÇÃO
                    with st.expander("📂 Opções de Exportação (Imagens e Relatórios)"):
                        col_dl1, col_dl2 = st.columns(2)
                        nome_arq = (datetime.now()).strftime('%H%M')
                        try: img_cards = gerar_cards_mpl(kpis, contrato_selecionado); col_dl1.download_button("Baixar Resumo (Cards)", img_cards, f"Resumo_{nome_arq}.jpg", "image/jpeg", width="stretch")
                        except: pass
                        cols_exist = [c for c in ['Ocorrência', 'Area', 'AT', 'Afetação', 'Status SLA', 'Horas Corridas', 'VIP', 'Cond. Alto Valor', 'B2B', 'Técnicos', 'horas_float'] if c in df.columns]
                        try:
                            cols_exp = [c for c in cols_exist if c != 'horas_float']; lista_imagens = gerar_lista_mpl_from_view(df, cols_exp, contrato_selecionado)
                            if lista_imagens:
                                if len(lista_imagens) == 1: col_dl2.download_button("Baixar Lista", lista_imagens[0], f"Lista_{nome_arq}.jpg", "image/jpeg", width="stretch")
                                else:
                                    for i, img_data in enumerate(lista_imagens): col_dl2.download_button(f"Baixar Parte {i+1}", img_data, f"Lista_{nome_arq}_P{i+1}.jpg", "image/jpeg", width="stretch")
                        except Exception as e: st.error(f"Erro lista: {e}")

                    # A TABELA
                    df_show = df.copy()
                    if f_area: df_show = df_show[df_show['Area'].isin(f_area)]
                    if f_sla: df_show = df_show[df_show['Status SLA'].isin(f_sla)]
                    if 'AT' in df_show.columns: df_show['AT'] = df_show['AT'].astype(str).str[:2]

                    st.dataframe(
                        df_show[cols_exist].style.apply(row_style_apply, axis=1), 
                        height=500, width=None, use_container_width=True,
                        column_config={"Ocorrência": st.column_config.TextColumn("ID", width="small"), "Afetação": st.column_config.NumberColumn("Afet.", format="%.0f"), "horas_float": None}
                    )

            if container_cluster:
                with container_cluster:
                    with st.form("form_cluster"): 
                        filtro_contratos = st.multiselect("Contratos:", options=opcoes_validas, default=opcoes_validas, placeholder="Selecione...")
                        aplicar = st.form_submit_button("Atualizar Visão", use_container_width=True) # Botão largo
                    
                    if filtro_contratos:
                        df_geral = processar_regras_generico(df_raw, contratos_validos=filtro_contratos)
                        if not df_geral.empty:
                            total_geral = len(df_geral); total_gv = len(df_geral[df_geral['Afetação'] >= 100])
                            
                            # --- HTML GRID FOR CLUSTER (UNIFIED DESIGN) ---
                            # Same style as Operational
                            card_style = "background:white;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;padding:8px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.03);display:flex;flex-direction:column;justify-content:center;height:70px;"
                            val_style = "font-size:18px;font-weight:800;color:#0f172a;line-height:1.2;"
                            lbl_style = "font-size:11px;color:#64748b;margin-bottom:2px;"
                            def get_delta_html(val, color): return f"<span style='font-size:10px;font-weight:bold;color:{color};background:{color}15;padding:1px 4px;border-radius:4px;'>{val}</span>"

                            no_prazo_count = len(df_geral[df_geral['horas_float'] < 8])
                            fora_prazo_count = len(df_geral[df_geral['horas_float'] >= 8])

                            # No indentation in HTML strings to avoid bugs
                            html_kpis_cluster = f"""
                            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:15px;">
                                <div style="{card_style}">
                                    <div style="{lbl_style}">Total Geral</div>
                                    <div style="{val_style}">{total_geral}</div>
                                </div>
                                <div style="{card_style.replace('#7c3aed', '#d97706')}">
                                    <div style="{lbl_style}">GV</div>
                                    <div style="{val_style}">{total_gv} {get_delta_html('Fora do Prazo' if total_gv > 0 else 'OK', '#d97706')}</div>
                                </div>
                                <div style="{card_style.replace('#7c3aed', '#16a34a')}">
                                    <div style="{lbl_style}">No Prazo</div>
                                    <div style="{val_style}">{no_prazo_count}</div>
                                </div>
                                <div style="{card_style.replace('#7c3aed', '#dc2626')}">
                                    <div style="{lbl_style}">Fora Prazo</div>
                                    <div style="{val_style}">{fora_prazo_count} {get_delta_html('Crítico', '#dc2626')}</div>
                                </div>
                            </div>
                            """
                            st.markdown(html_kpis_cluster, unsafe_allow_html=True)
                            
                            with st.expander("Baixar Imagem do Cluster"):
                                try: img_dashboard = gerar_dashboard_gerencial(df_geral, filtro_contratos); st.download_button("Baixar Dashboard", img_dashboard, f"Dash_{nome_arq}.jpg", "image/jpeg")
                                except: pass

                            st.markdown("##### Detalhamento")
                            resumo = df_geral.groupby('Contrato_Padrao').agg(Total=('Ocorrência', 'count'), No_Prazo=('horas_float', lambda x: (x < 8).sum()), Fora_Prazo=('horas_float', lambda x: (x >= 8).sum()), Grandes_Vultos=('Afetação', lambda x: (x >= 100).sum()), VIPs=('VIP', lambda x: (x == 'SIM').sum()), Condos=('Cond. Alto Valor', lambda x: (x == 'SIM').sum()), B2B=('B2B', lambda x: (x == 'SIM').sum()), Criticos=('horas_float', lambda x: (x > 24).sum())).reset_index().sort_values('Total', ascending=False)
                            st.dataframe(resumo.style.set_properties(**{'text-align': 'center'}), use_container_width=True, hide_index=True)
                        else: st.info("Sem dados.")
    else: st.error("Erro dados.")