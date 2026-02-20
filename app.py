import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import sqlite3
import bcrypt
import firebase_admin
from firebase_admin import credentials, firestore

# ==============================================================================
# 🌍 1. CONFIGURAÇÃO DE AMBIENTE
# ==============================================================================
os.environ['TZ'] = 'America/Sao_Paulo'
try:
    time.tzset()
except AttributeError:
    pass

st.set_page_config(
    page_title="SigmaOPS", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inicialização do Firebase
if not firebase_admin._apps:
	cred = credentials.Certificate('serviceAccountKey.json')
	firebase_admin.initialize_app(cred)
db = firestore.client()

# ==============================================================================
# ⚙️ CONSTANTES GLOBAIS
# ==============================================================================
ARQUIVO_CNL_CSV = "CNL_BASE_MONITORAMENTO.csv"
ARQUIVO_CNL_XLSX = "CNL_BASE_MONITORAMENTO.xlsx"
DB_FILE = "users_sigma.db"
CONTRATOS_VALIDOS = ["ABILITY_SJ", "TEL_JI", "ABILITY_OS", "TEL_INTERIOR", "TEL_PC_SC", "TELEMONT"]
nome_arq = datetime.now().strftime('%H%M')

# ==============================================================================
# 🔐 SEGURANÇA E BANCO DE DADOS
# ==============================================================================
def get_secret(section, key):
    try: return st.secrets[section][key]
    except: return None

API_URL = get_secret("api", "url") or ""
API_HEADERS = dict(st.secrets["api"].get("headers", {})) if get_secret("api", "headers") else {}
SESSION_SALT = get_secret("security", "session_salt") or "sigma_master_key_2026"

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    try:
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                     (username TEXT PRIMARY KEY, password_hash TEXT, role TEXT, contract TEXT, approved INTEGER, created_at TEXT)''')
        conn.commit(); conn.close()
    except: pass

def db_actions(action, u=None, p=None, c=None, r=None):
    conn = get_db_connection()
    try:
        if action == "add":
            ph = bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (u.upper(), ph, 'user', c, 0, datetime.now().strftime("%Y-%m-%d")))
            conn.commit(); return True, "Solicitação enviada. Aguarde liberação."
        elif action == "verify":
            res = conn.execute("SELECT role, contract, approved, password_hash FROM users WHERE username=?", (u.upper(),)).fetchone()
            if res:
                stored_hash = res[3]
                if bcrypt.checkpw(p.encode('utf-8'), stored_hash.encode('utf-8')):
                    return res 
            return None
        elif action == "pending":
            return pd.read_sql_query("SELECT username, contract FROM users WHERE approved = 0", conn)
        elif action == "approve":
            conn.execute("UPDATE users SET approved = 1, role = ? WHERE username = ?", (r, u))
            conn.commit()
        elif action == "delete":
            conn.execute("DELETE FROM users WHERE username = ?", (u,))
            conn.commit()
    except Exception as e: return False, str(e)
    finally: conn.close()

init_db()

# ==============================================================================
# 🚪 LÓGICA DE LOGIN
# ==============================================================================
if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "username": None, "role": None, "allowed_contract": None})

def confirm_login(u, r, c):
    st.session_state.update({"logged_in": True, "username": u, "role": r, "allowed_contract": c})
    st.rerun()

if not st.session_state["logged_in"]:
    st.query_params.clear()
    
    st.markdown("""
    <style>
        .stApp { background-color: #ffffff; }
        [data-testid="stSidebar"], header, footer { display: none !important; }
        .login-box { margin: 10vh auto; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); max-width: 380px; border: 1px solid #f1f5f9; text-align: center; }
        .logo { font-size: 4rem; font-weight: 900; background: -webkit-linear-gradient(#a855f7, #4c1d95); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        div[data-testid="stFormSubmitButton"] button { width: 100%; background-color: #7c3aed !important; color: white !important; font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-box"><div class="logo">Σ</div><h2 style="color:#4c1d95;margin-top:-10px;">SigmaOPS</h2></div>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        t1, t2 = st.tabs(["Acessar", "Cadastrar"])
        with t1:
            with st.form("login_form"):
                email = st.text_input("E-mail").strip()
                passwd = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    if email and passwd:
                        user_ref = db.collection("users").document(email)
                        user_doc = user_ref.get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            senha_hash = user_data["hash"].encode()
                            if bcrypt.checkpw(passwd.encode(), senha_hash):
                                confirm_login(user_data['name'], user_data['role'], user_data['contract'])
                            else:
                                st.error("Senha incorreta!")
                        else:
                            st.error("Usuário não encontrado!")
                    else:
                        st.warning("Preencha todos os campos.")
        with t2:
            with st.form("reg_form"):
                name = st.text_input("Nome").strip()
                email = st.text_input("Email").strip()
                contract = st.selectbox("Área", CONTRATOS_VALIDOS)
                passwd = st.text_input("Senha", type="password")
                hashed = bcrypt.hashpw(passwd.encode(), bcrypt.gensalt())
                if st.form_submit_button("Solicitar Acesso"):
                    if name and email and passwd:
                        user_ref = db.collection("users").document(email)
                        if user_ref.get().exists:
                            st.error("Usuário já existe!")
                        else:
                            user_ref.set({
                                "name": name,
                                "email": email,
                                "hash": hashed.decode(),
                                "role": "user",
                                "contract": contract,
                                "created_at": firestore.SERVER_TIMESTAMP,
                                "approved": False
                            })
                            st.success("Solicitação enviada. Aguarde liberação.")
                    else: st.error("Preencha todos os campos.")
    st.stop()

# ==============================================================================
# 🚀 APLICAÇÃO PRINCIPAL
# ==============================================================================
USUARIO = st.session_state["username"]
PERFIL = st.session_state["role"]
CONTRATO = st.session_state["allowed_contract"]

# --- ESTILOS CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    .block-container { padding-top: 2rem !important; padding-bottom: 5rem !important; }
    
    .sigma-header { 
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); 
        padding: 20px 30px; border-radius: 0 0 12px 12px; 
        display: flex; justify-content: space-between; align-items: flex-start; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-bottom: 4px solid #7c3aed; margin-bottom: 20px; 
    }
    .sigma-title { font-size: 24px; font-weight: 900; color: white; margin: 0; }
    .sigma-time { font-size: 20px; font-weight: 800; color: white; background: rgba(255,255,255,0.1); padding: 4px 12px; border-radius: 6px; }
    .sigma-label { font-size: 10px; color: #94a3b8; font-weight: 700; text-transform: uppercase; text-align: right; display: block; }

    div[data-testid="stButton"] button { background-color: #7c3aed !important; color: white !important; font-weight: 700 !important; border: none !important; }
    .sidebar-footer button { background-color: #fee2e2 !important; color: #991b1b !important; border: 1px solid #fecaca !important; width: 100%; }
    
    div[role="radiogroup"] label { background-color: white !important; border: 1px solid #e2e8f0; font-weight: 600; color: #64748b; padding: 8px 16px; border-radius: 6px; transition: all 0.2s; }
    div[role="radiogroup"] label:has(input:checked) { background-color: #7c3aed !important; color: white !important; border-color: #7c3aed; }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    
    .stMultiSelect [data-baseweb="tag"] { background-color: #7c3aed !important; color: white !important; }
    .stDataFrame td { text-align: center !important; font-size: 12px !important; vertical-align: middle; padding: 6px !important; }
    .stDataFrame th { background-color: #f1f5f9 !important; font-size: 13px !important; color: #475569 !important; }
    .alert-box { background-color: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; border: 1px solid #fecaca; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

hora_atual = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%H:%M")
st.markdown(f'<div class="sigma-header"><div class="sigma-title">SigmaOPS</div><div><span class="sigma-label">Última Atualização</span><span class="sigma-time">{hora_atual}</span></div></div>', unsafe_allow_html=True)

# --- SIDEBAR E PAINEL ADMIN ---
with st.sidebar:
    st.markdown(f"### 👤 {USUARIO}")
    if CONTRATO: st.markdown(f"📍 **{CONTRATO}**")
    
    if PERFIL == "master":
        st.divider()
        st.markdown("#### 🛡️ Aprovação de Acessos")
        user_ref = db.collection("users").where("approved", "==", False ).get()
        os.system('clear')
        if user_ref:
            st.warning(f"🔔 {len(user_ref)} Pendente(s)")
            for user in user_ref:
                row = user.to_dict() or {}
                with st.container(border=True):
                    st.markdown(f"**{row.get('name', '')}** | {row.get('contract', '')}")
                    r_sel = st.selectbox("Perfil:", ["user", "admin"], key=f"r_{user.id}", label_visibility="collapsed")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Aprovar", key=f"y_{user.id}", width="stretch"): 
                        user.reference.update({"approved": True, "role": r_sel})
                        st.toast(f"Usuário {row.get('name')} aprovado!")
                        st.rerun()
                    if c2.button("❌ Recusar", key=f"n_{user.id}", width="stretch"): 
                        user.reference.delete()
                        st.toast(f"Usuário {row.get('name')} removido!")
                        st.rerun()
        else:
            st.success("Tudo limpo! ✅")

    st.markdown("---")
    st.markdown("<div style='height: 20vh'></div>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
        if st.button("🚪 Sair do Sistema"):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 🧠 DADOS (CACHE OTIMIZADO) E EXPORTAÇÃO
# ==============================================================================
@st.cache_data(ttl=3600)
def carregar_base_cnl():
    if os.path.exists(ARQUIVO_CNL_CSV):
        try: df = pd.read_csv(ARQUIVO_CNL_CSV, sep=None, engine='python'); df['CNL'] = df['CNL'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip(); return df[['CNL', 'MUNICÍPIO']].drop_duplicates(subset='CNL')
        except: pass
    if os.path.exists(ARQUIVO_CNL_XLSX):
        try: df = pd.read_excel(ARQUIVO_CNL_XLSX); df['CNL'] = df['CNL'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip(); return df[['CNL', 'MUNICÍPIO']].drop_duplicates(subset='CNL')
        except: pass
    return None

@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados_api():
    if not API_URL: return None, "Sem URL configurada."
    try:
        response = requests.get(API_URL, headers=API_HEADERS, timeout=25)
        if response.status_code == 200:
            data = response.json()
            if 'ocorrencias' in data:
                df = pd.DataFrame(data['ocorrencias'])
                rename_map = { 
                    'ocorrencia': 'Ocorrência', 'data_abertura': 'Abertura', 'contrato': 'Contrato', 
                    'cnl': 'CNL', 'at': 'AT', 'afetacao': 'Afetação', 'vip': 'VIP', 
                    'cond_alto_valor': 'Cond. Alto Valor', 'b2b_avancado': 'B2B', 
                    'tecnicos': 'Técnicos', 'origem': 'Origem',
                    'cabo': 'Cabo', 'primarias': 'Primárias', 'bd': 'BD',
                    'propenso_anatel': 'Propensos - Anatel', 'reclamado_anatel': 'Reclamados - Anatel'
                }
                df.rename(columns=rename_map, inplace=True)
                df['Abertura_dt'] = pd.to_datetime(df['Abertura'], errors='coerce')
                if 'Técnicos' in df.columns: df['Técnicos'] = df['Técnicos'].apply(lambda x: len(x) if isinstance(x, list) else 0)
                
                def formatar_flag(val):
                    if pd.isna(val): return 'NÃO'
                    s = str(val).upper().strip()
                    if s in ['TRUE', 'SIM', 'S', 'YES']: return 'SIM'
                    try:
                        return 'SIM' if float(val) > 0 else 'NÃO'
                    except:
                        return 'NÃO'

                for col in ['VIP', 'Cond. Alto Valor', 'B2B']:
                    if col in df.columns: 
                        df[col] = df[col].apply(formatar_flag)
                        
                return df, None
        return None, f"Erro {response.status_code}"
    except Exception as e: return None, str(e)

def processar_dados(df_raw, filtros_contrato):
    agora = datetime.now() - timedelta(hours=3)
    df = df_raw.copy()
    df_cnl = carregar_base_cnl()
    if df_cnl is not None:
        df['CNL'] = df['CNL'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df = pd.merge(df, df_cnl, on='CNL', how='left')
        df.rename(columns={'MUNICÍPIO': 'Cidade_Real'}, inplace=True)
    
    df['Contrato_Padrao'] = df['Contrato'].astype(str).str.strip().str.upper()
    if isinstance(filtros_contrato, str): df = df[df['Contrato_Padrao'] == filtros_contrato.upper()].copy()
    elif isinstance(filtros_contrato, list) and filtros_contrato: df = df[df['Contrato_Padrao'].isin([c.upper() for c in filtros_contrato])].copy()
    
    df['diff_s'] = (agora - df['Abertura_dt']).dt.total_seconds()
    df['horas_float'] = df['diff_s'] / 3600
    
    def formatar_hms(s):
        val = int(s) if pd.notna(s) else 0
        m, s_res = divmod(val, 60); h, m_res = divmod(m, 60)
        return f"{int(h):02d}:{int(m_res):02d}:{int(s_res):02d}"
    df['Horas Corridas'] = df['diff_s'].apply(formatar_hms)
    
    def calc_sla_status(row):
        h = row['horas_float']
        is_b2b = str(row.get('B2B', 'NÃO')).upper() == 'SIM'
        limite_fora = 4 if is_b2b else 8
        if h > 24: return "Crítico"
        elif h > limite_fora: return "Fora do Prazo"
        else: return "No Prazo"
        
    df['Status SLA'] = df.apply(calc_sla_status, axis=1)
    
    def def_area(row):
        if str(row['Contrato_Padrao']) == 'ABILITY_SJ' and pd.notna(row.get('AT')):
            return "Litoral" if str(row['AT']).split('-')[0].strip().upper() in ['TG','PG','LZ','MK','MG','PN','AA','BV','FM','RP','AC','FP','BA','TQ','BO','BU','BC','PJ','PB','MR','MA'] else "Vale"
        return "Geral"
    df['Area'] = df.apply(def_area, axis=1)
    return df.sort_values('horas_float', ascending=False)

def highlight_rows(row):
    h = row.get('horas_float', 0)
    is_b2b = str(row.get('B2B', 'NÃO')).upper() == 'SIM'
    limite_fora = 4 if is_b2b else 8
    
    tc = '#16a34a' 
    if h > 24: tc = '#dc2626' 
    elif h > limite_fora: tc = '#d97706' 
    
    if row.get('Afetação', 0) >= 100: tc = '#2563eb'
    
    styles = []
    for col in row.index:
        val = str(row[col]).upper().strip()
        cell_style = f'color: {tc}; text-align: center; font-weight: 700;'
        
        if col == 'VIP' and val == 'SIM': cell_style += 'background-color: #f5d0fe; color: #86198f; border-radius: 4px;'
        elif col == 'Cond. Alto Valor' and val == 'SIM': cell_style += 'background-color: #d9f99d; color: #365314; border-radius: 4px;'
        elif col == 'B2B' and val == 'SIM': cell_style += 'background-color: #ddd6fe; color: #5b21b6; border-radius: 4px;'
            
        styles.append(cell_style)
    return styles

def gerar_texto_gv(row, contrato):
    try: dt = row['Abertura_dt'].strftime("%d/%m/%Y")
    except: dt = ""
    try: hr = row['Abertura_dt'].strftime("%H:%M")
    except: hr = ""
    
    def get_val(col, default=""):
        val = row.get(col)
        return str(val).strip() if pd.notna(val) and str(val).strip() != "" and str(val).strip() != "nan" else default

    return f"""✅ *INFORMATIVO GRANDE VULTO*

*{contrato}*

{get_val('Ocorrência')} - FTTx
ORIGEM: {get_val('Origem')}
AT: {get_val('AT')}
CIDADE: {get_val('Cidade_Real')}
QUANT. PRIMÁRIAS AFETADAS: {get_val('Primárias')}
CABO: {get_val('Cabo')}
AFETAÇÃO: {int(row.get('Afetação', 0))}
BDs: {get_val('BD')}
CRIAÇÃO: {dt}
HORA: {hr}
PROPENSOS-ANATEL: {get_val('Propensos - Anatel')}
RECLAMADOS-ANATEL: {get_val('Reclamados - Anatel')}
CLIENTE VIP:  {get_val('VIP', 'NÃO')}
CLIENTE B2B:  {get_val('B2B', 'NÃO')}
COND. ALTO VALOR: {get_val('Cond. Alto Valor', 'NÃO')}
DEFEITO:
PRAZO:"""

def gerar_cards_mpl(kpis, contrato):
    C_BG, C_BORDER, C_TEXT, C_LABEL = "#ffffff", "#e2e8f0", "#1e293b", "#64748b"
    C_RED, C_YELLOW, C_GREEN = "#dc2626", "#d97706", "#16a34a"
    h_tot = 14 if contrato == 'ABILITY_SJ' else 11
    fig, ax = plt.subplots(figsize=(12, h_tot), dpi=200); fig.patch.set_facecolor(C_BG); ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    def draw(x,y,w,h,t,v,col=C_TEXT):
        ax.add_patch(patches.FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0,rounding_size=3",fc="white",ec=C_BORDER,lw=2))
        ax.text(x+w/2,y+h*0.8,t.upper(),ha='center',size=18,color=C_LABEL,weight='bold')
        ax.text(x+w/2,y+h*0.4,str(v),ha='center',size=55,color=col,weight='black')
    ax.text(50,96,"SIGMA OPS",ha='center',size=32,weight='black',color='#7c3aed'); ax.text(50,92,f"{contrato} • {datetime.now().strftime('%H:%M')}",ha='center',size=22,weight='bold',color='#475569')
    draw(2,68,46,18,"Total",kpis['total']); draw(52,68,46,18,"S/ Técnico",kpis['sem_tec'])
    w=30; g=3; draw(2,42,w,18,"Crítico",kpis['critico'],C_RED); draw(2+w+g,42,w,18,"Fora do Prazo",kpis['fora'],C_YELLOW); draw(2+2*(w+g),42,w,18,"No Prazo",kpis['no_prazo'],C_GREEN)
    if contrato == 'ABILITY_SJ': draw(2,16,46,18,"Litoral",kpis['lit']); draw(52,16,46,18,"Vale",kpis['vale'])
    buf = io.BytesIO(); plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG); plt.close(fig); return buf.getvalue()

def gerar_lista_mpl_from_view(df_view, col_order, contrato):
    ITENS_POR_PAGINA = 20
    cols = [c for c in col_order if c in df_view.columns and c not in ['horas_float', 'Status SLA']]
    df_p = df_view[cols].copy().rename(columns={'Ocorrência': 'ID', 'Horas Corridas': 'Tempo', 'Cond. Alto Valor': 'A.V'})
    
    lista_imagens = []
    total_linhas = len(df_p)
    if total_linhas == 0: return lista_imagens
        
    num_paginas = (total_linhas + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA
    
    for i in range(num_paginas):
        inicio = i * ITENS_POR_PAGINA; fim = inicio + ITENS_POR_PAGINA
        df_chunk = df_p.iloc[inicio:fim]; idx_chunk = df_view.iloc[inicio:fim]
        
        fig, ax = plt.subplots(figsize=(14, max(4, 3 + len(df_chunk)*0.8)), dpi=180)
        ax.axis('off'); fig.patch.set_facecolor('white')
        
        titulo = f"SIGMA OPS: {contrato}\n{datetime.now().strftime('%d/%m • %H:%M')}"
        if num_paginas > 1: titulo += f" (Pág {i+1}/{num_paginas})"
            
        plt.title(titulo, loc='center', pad=40, fontsize=28, weight='black', color='#1e293b')
        tbl = ax.table(cellText=df_chunk.values.tolist(), colLabels=df_chunk.columns, cellLoc='center', loc='center')
        tbl.auto_set_font_size(False); tbl.set_fontsize(12); tbl.scale(1.2, 3.0)
        
        for j in range(len(df_chunk.columns)): 
            tbl[(0, j)].set_facecolor('#7c3aed'); tbl[(0, j)].set_text_props(color='white', weight='bold')
            
        for r_idx in range(len(df_chunk)):
            row_orig = idx_chunk.iloc[r_idx]
            h = row_orig.get('horas_float', 0)
            is_b2b = str(row_orig.get('B2B', 'NÃO')).upper() == 'SIM'
            limite_fora = 4 if is_b2b else 8
            
            c = '#16a34a'
            if h > 24: c = '#dc2626'
            elif h > limite_fora: c = '#d97706'
            
            if row_orig.get('Afetação', 0) >= 100: c = '#2563eb'
                
            for j in range(len(df_chunk.columns)): 
                tbl[(r_idx+1, j)].set_text_props(color=c, weight='bold')
                tbl[(r_idx+1, j)].set_edgecolor("#e2e8f0")
                
        buf = io.BytesIO(); plt.savefig(buf, format='jpg', dpi=180, bbox_inches='tight', facecolor='white'); plt.close(fig)
        lista_imagens.append(buf.getvalue())
    return lista_imagens

def gerar_dashboard_gerencial(df_geral, contratos_list):
    C_BG, C_BAR, C_RED, C_GREEN = "#ffffff", "#7c3aed", "#dc2626", "#16a34a"; df_filtrado = df_geral.copy()
    resumo = df_filtrado.groupby('Contrato_Padrao').agg(
        Total=('Ocorrência', 'count'), 
        No_Prazo=('Status SLA', lambda x: (x == 'No Prazo').sum()), 
        Fora_Prazo=('Status SLA', lambda x: (x == 'Fora do Prazo').sum()), 
        Grandes_Vultos=('Afetação', lambda x: (x >= 100).sum()), 
        Criticos=('Status SLA', lambda x: (x == 'Crítico').sum())
    ).reset_index().sort_values('Total', ascending=False)
    
    fig, ax = plt.subplots(figsize=(14, 12), dpi=200); fig.patch.set_facecolor(C_BG); ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    hora = datetime.now().strftime("%d/%m %H:%M"); ax.text(50, 96, "VISÃO CLUSTER", ha='center', fontsize=32, weight='black', color='#1e293b'); ax.text(50, 92, f"Consolidado SigmaOPS • {hora}", ha='center', fontsize=20, weight='bold', color='#7c3aed')
    colunas = ["CONTRATO", "TOTAL", "No Prazo", "Fora do Prazo", "G. VULTO", "CRÍTICO >24H"]
    dados = [[row['Contrato_Padrao'], str(row['Total']), str(row['No_Prazo']), str(row['Fora_Prazo']), str(row['Grandes_Vultos']), str(row['Criticos'])] for _, row in resumo.iterrows()]
    tbl = ax.table(cellText=dados, colLabels=colunas, loc='center', bbox=[0.05, 0.05, 0.9, 0.45]); tbl.auto_set_font_size(False); tbl.set_fontsize(11); tbl.scale(1, 2)
    for (i, j), cell in tbl.get_celld().items():
        if i == 0: cell.set_text_props(weight='bold', color='white'); cell.set_facecolor('#7c3aed')
        else: cell.set_edgecolor('#e2e8f0'); cell.set_text_props(weight='bold'); 
        if i % 2 == 0: cell.set_facecolor('#f8fafc')
    buf = io.BytesIO(); plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG); plt.close(fig); return buf.getvalue()

# ==============================================================================
# 📊 CORPO DO DASHBOARD
# ==============================================================================
df_raw, erro = carregar_dados_api()

if df_raw is not None:
    if PERFIL in ["master", "admin"]: 
        tab_op, tab_cl = st.tabs(["Operacional", "Cluster"])
    else: 
        tab_op = st.container(); tab_cl = None

    # --- ABA OPERACIONAL ---
    with tab_op:
        c_sel, c_ref = st.columns([5, 1], gap="small")
        with c_sel:
            if CONTRATO and PERFIL not in ["master", "admin"]:
                st.info(f"Visualizando: {CONTRATO}")
                contrato_atual = CONTRATO
            else:
                contrato_atual = st.radio("Selecione o Contrato:", CONTRATOS_VALIDOS, horizontal=True, label_visibility="collapsed")
        with c_ref:
            if st.button("🔄 Atualizar", width="stretch"): carregar_dados_api.clear(); st.rerun()

        df_view = processar_dados(df_raw, contrato_atual)
        
        c_f1, c_f2 = st.columns(2)
        with c_f1: f_reg = st.multiselect("Região", df_view['Area'].unique())
        with c_f2: f_sla = st.multiselect("SLA", ["Crítico", "Fora do Prazo", "No Prazo"])
        
        if f_reg: df_view = df_view[df_view['Area'].isin(f_reg)]
        if f_sla: df_view = df_view[df_view['Status SLA'].isin(f_sla)]

        # KPIs HTML
        t = len(df_view)
        k = {'total': t, 'sem_tec': len(df_view[df_view['Técnicos']==0]), 'critico': len(df_view[df_view['Status SLA']=='Crítico']), 'fora': len(df_view[df_view['Status SLA']=='Fora do Prazo']), 'no_prazo': len(df_view[df_view['Status SLA']=='No Prazo']), 'lit': len(df_view[df_view['Area']=='Litoral']), 'vale': len(df_view[df_view['Area']=='Vale'])}
        
        c_style = "background:white;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;padding:8px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.03);display:flex;flex-direction:column;justify-content:center;height:70px;"
        def password(v, c): return f"<span style='font-size:10px;font-weight:bold;color:{c};background:{c}15;padding:1px 4px;border-radius:4px;'>{v}</span>" if t>0 else ""
        
        html = f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:15px;">
            <div style="{c_style}"><div style="font-size:11px;color:#64748b;">Total</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k['total']}</div></div>
            <div style="{c_style}"><div style="font-size:11px;color:#64748b;">S/ Técnico</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k['sem_tec']} {password(f"{(k['sem_tec']/t*100):.0f}%", "#dc2626")}</div></div>
            <div style="{c_style.replace('#7c3aed','#dc2626')}"><div style="font-size:11px;color:#64748b;">Crítico (>24h)</div><div style="font-size:18px;font-weight:800;color:#dc2626;">{k['critico']}</div></div>
            <div style="{c_style.replace('#7c3aed','#d97706')}"><div style="font-size:11px;color:#64748b;">Fora Prazo</div><div style="font-size:18px;font-weight:800;color:#d97706;">{k['fora']}</div></div>
            <div style="{c_style.replace('#7c3aed','#16a34a')}"><div style="font-size:11px;color:#64748b;">No Prazo</div><div style="font-size:18px;font-weight:800;color:#16a34a;">{k['no_prazo']}</div></div>"""
        
        if contrato_atual == 'ABILITY_SJ': html += f"""<div style="{c_style}"><div style="font-size:11px;color:#64748b;">Litoral</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k['lit']}</div></div><div style="{c_style}"><div style="font-size:11px;color:#64748b;">Vale</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k['vale']}</div></div>"""
        st.markdown(html + "</div>", unsafe_allow_html=True)

        gv = len(df_view[df_view['Afetação']>=100])
        if gv > 0:
            st.markdown(f"<div class='alert-box'>🚨 {gv} GRANDE(S) VULTO(S) EM ABERTO</div>", unsafe_allow_html=True)
            with st.expander("Ver Detalhes GV"):
                for _, row in df_view[df_view['Afetação'] >= 100].iterrows(): st.code(gerar_texto_gv(row, contrato_atual), language="text")

        with st.expander("📂 Opções de Exportação"):
            c1, c2 = st.columns(2)
            try: 
                # AQUI FOI CORRIGIDO: Botão agora usa 100% do tamanho
                c1.download_button("Baixar Resumo", gerar_cards_mpl(k, contrato_atual), f"resumo_{nome_arq}.jpg", "image/jpeg", width="stretch")
            except: pass
            
            cols_export = ['Ocorrência', 'Area', 'AT', 'Afetação', 'Status SLA', 'Horas Corridas', 'VIP', 'Cond. Alto Valor', 'B2B', 'Técnicos']
            try: 
                imgs = gerar_lista_mpl_from_view(df_view, cols_export, contrato_atual)
                if imgs: 
                    if len(imgs) == 1:
                        c2.download_button("Baixar Lista", imgs[0], f"lista_{nome_arq}.jpg", "image/jpeg", width="stretch")
                    else:
                        for idx_img, img_bytes in enumerate(imgs):
                            c2.download_button(f"Baixar Lista (Pág {idx_img+1})", img_bytes, f"lista_{nome_arq}_p{idx_img+1}.jpg", "image/jpeg", width="stretch")
            except: pass

        cols_visiveis = ['Ocorrência', 'Area', 'AT', 'Afetação', 'Status SLA', 'Horas Corridas', 'VIP', 'Cond. Alto Valor', 'B2B', 'Técnicos']
        cols_para_logica = cols_visiveis + ['horas_float']
        c_final = [c for c in cols_para_logica if c in df_view.columns]

        st.dataframe(
            df_view[c_final].style.apply(highlight_rows, axis=1), 
            width="stretch", 
            hide_index=True, 
            height=600, 
            column_config={
                "Ocorrência": st.column_config.TextColumn("ID", width="small"),
                "Afetação": st.column_config.NumberColumn("Afet.", format="%.0f"),
                "horas_float": None 
            }
        )

    # --- ABA CLUSTER ---
    if tab_cl:
        with tab_cl:
            with st.form("form_cluster"):
                c1, c2 = st.columns([5, 1])
                with c1: sels = st.multiselect("Contratos:", CONTRATOS_VALIDOS, default=CONTRATOS_VALIDOS)
                with c2: 
                    st.write("")
                    st.write("")
                    st.form_submit_button("Atualizar Visão", width="stretch")
            
            if sels:
                df_cl = processar_dados(df_raw, sels)
                
                t_g = len(df_cl)
                t_gv = len(df_cl[df_cl['Afetação']>=100])
                c_ok = len(df_cl[df_cl['Status SLA']=='No Prazo'])
                c_fora = len(df_cl[df_cl['Status SLA']=='Fora do Prazo'])
                c_crit = len(df_cl[df_cl['Status SLA']=='Crítico'])
                
                h_cl = f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:15px;">
                    <div style="{c_style}"><div style="font-size:11px;color:#64748b;">Total Geral</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{t_g}</div></div>
                    <div style="{c_style.replace('#7c3aed','#d97706')}"><div style="font-size:11px;color:#64748b;">GV</div><div style="font-size:18px;font-weight:800;color:#d97706;">{t_gv}</div></div>
                    <div style="{c_style.replace('#7c3aed','#16a34a')}"><div style="font-size:11px;color:#64748b;">No Prazo</div><div style="font-size:18px;font-weight:800;color:#16a34a;">{c_ok}</div></div>
                    <div style="{c_style.replace('#7c3aed','#d97706')}"><div style="font-size:11px;color:#64748b;">Fora Prazo</div><div style="font-size:18px;font-weight:800;color:#d97706;">{c_fora}</div></div>
                    <div style="{c_style.replace('#7c3aed','#dc2626')}"><div style="font-size:11px;color:#64748b;">Críticos (>24h)</div><div style="font-size:18px;font-weight:800;color:#dc2626;">{c_crit}</div></div>
                </div>"""
                st.markdown(h_cl, unsafe_allow_html=True)
                
                with st.expander("Baixar Imagem"):
                    if st.button("Gerar Dashboard"):
                        try: st.download_button("Download", gerar_dashboard_gerencial(df_cl, sels), f"cluster_{nome_arq}.jpg", "image/jpeg")
                        except: pass
                
                resumo = df_cl.groupby('Contrato_Padrao').agg(
                    Total=('Ocorrência', 'count'), 
                    No_Prazo=('Status SLA', lambda x: (x == 'No Prazo').sum()), 
                    Fora_Prazo=('Status SLA', lambda x: (x == 'Fora do Prazo').sum()), 
                    Grandes_Vultos=('Afetação', lambda x: (x >= 100).sum()), 
                    VIPs=('VIP', lambda x: (x == 'SIM').sum()), 
                    Cond_Alto_Valor=('Cond. Alto Valor', lambda x: (x == 'SIM').sum()), 
                    B2B=('B2B', lambda x: (x == 'SIM').sum()), 
                    Criticos=('Status SLA', lambda x: (x == 'Crítico').sum())
                ).rename(columns={
                    'No_Prazo': 'No Prazo',
                    'Fora_Prazo': 'Fora Prazo',
                    'Grandes_Vultos': 'Grandes Vultos',
                    'Criticos': 'Críticos (>24h)'
                }).reset_index().sort_values('Total', ascending=False)
                
                st.dataframe(resumo, width="stretch", hide_index=True)
            else:
                st.warning("Selecione pelo menos um contrato.")
else:
    st.error("Erro ao carregar dados da API.")