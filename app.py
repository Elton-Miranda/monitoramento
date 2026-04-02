import os
import time
import json
import re
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests
import matplotlib.patches as patches
import io
import bcrypt
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import DocumentSnapshot

# Versão do SigmaOPS
version = "1.3.0"

# Validador
def validar_document(document):
    if isinstance(document, DocumentSnapshot) and document.exists:
        return True
    return False

# ==============================================================================
# 🌍 1. CONFIGURAÇÃO DE AMBIENTE
# ==============================================================================
os.environ['TZ'] = 'America/Sao_Paulo'
if hasattr(time, 'tzset'):
    time.tzset()

st.set_page_config(
    page_title="SigmaOPS", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inicialização do Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==============================================================================
# ⚙️ CONSTANTES GLOBAIS
# ==============================================================================
CONTRATOS_VALIDOS = ["ABILITY_SJ", "TEL_JI", "ABILITY_OS", "TEL_INTERIOR", "TEL_PC_SC", "TELEMONT"]
nome_arq = datetime.now().strftime('%H%M')

# ==============================================================================
# 🔐 SEGURANÇA E BANCO DE DADOS
# ==============================================================================
def get_secret(section, key):
    try: return st.secrets[section][key]
    except: return None

API_URL = get_secret("api", "url") or ""
API_URL_OFENSORES = get_secret("api", "url_ofensores") or ""
API_HEADERS = dict(st.secrets["api"].get("headers", {})) if get_secret("api", "headers") else {}
SESSION_SALT = get_secret("security", "session_salt") or "sigma_master_key_2026"

# ==============================================================================
# 📡 HISTÓRICO DE CAMPO (FIREBASE)
# ==============================================================================
def salvar_status_campo(ocorrencia, status, obs, usuario):
    ref = db.collection("status_campo").document(str(ocorrencia))
    novo_registro = {
        "status": status,
        "obs": obs,
        "usuario": usuario,
        "data_str": (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%d/%m %H:%M"),
        "timestamp": datetime.now(timezone.utc)
    }
    
    doc = ref.get()
    if validar_document(doc):
        ref.update({"historico": firestore.ArrayUnion([novo_registro])})
    else:
        ref.set({"historico": [novo_registro]})

def carregar_status_campo():
    try:
        docs = db.collection("status_campo").get()
        status_dict = {}
        for doc in docs:
            dados = doc.to_dict()
            historico = dados.get("historico", [])
            if historico:
                ultimo = historico[-1]
                texto = f"{ultimo['status']}"
                if ultimo.get('obs'): texto += f" ({ultimo['obs']})"
                if ultimo.get('usuario'): texto += f" 👤 {ultimo['usuario']}"
                status_dict[doc.id] = texto
        return status_dict
    except:
        return {}

# ==============================================================================
# 🚪 LÓGICA DE LOGIN
# ==============================================================================
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False,
        "username": None,
        "email": None,
        "role": None,
        "allowed_contract": None
        })

def confirm_login(u, e, r, c):
    st.session_state.update({"logged_in": True, "username": u, "email": e, "role": r, "allowed_contract": c})
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
        t1, t2 = st.tabs(["Acessar", "Registar"])
        with t1:
            with st.form("login_form"):
                email = st.text_input("E-mail").strip()
                passwd = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    if email and passwd:
                        master_email = get_secret("master", "email")
                        master_pass = get_secret("master", "password")
                        
                        if master_email and email == master_email and passwd == master_pass:
                            confirm_login("Master Admin", "master", "Geral", "master")
                        else:
                            user_ref = db.collection("users").document(email)
                            user_doc = user_ref.get()
                            if validar_document(user_doc):
                                user_data = user_doc.to_dict()
                                senha_hash = user_data["hash"].encode()
                                if not user_data.get("approved", False):
                                    st.warning("O seu acesso ainda está pendente de aprovação.")
                                elif bcrypt.checkpw(passwd.encode(), senha_hash):
                                    confirm_login(user_data['name'], user_data['email'], user_data['role'], user_data['contract'])
                                else:
                                    st.error("Senha incorreta!")
                            else:
                                st.error("Utilizador não encontrado!")
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
                        if validar_document(user_ref.get()):
                            st.error("O utilizador já existe!")
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
                            st.success("Solicitação enviada. Aguarde libertação.")
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
    
    div[role="radiogroup"] label { background-color: white !important; border: 1px solid #e2e8f0; font-weight: 600; padding: 8px 16px; border-radius: 6px; transition: all 0.2s; }
    div[role="radiogroup"] label p { color: #64748b !important; }
    div[role="radiogroup"] label:has(input:checked) { background-color: #7c3aed !important; border-color: #7c3aed !important; }
    div[role="radiogroup"] label:has(input:checked) p { color: white !important; font-weight: 800 !important; }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    
    .stMultiSelect [data-baseweb="tag"] { background-color: #7c3aed !important; color: white !important; }
    .alert-box { background-color: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; border: 1px solid #fecaca; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

hora_atual = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%H:%M")
st.markdown(
    f'''<div class="sigma-header">
            <div class="sigma-title">
                SigmaOPS
                <span style="font-size: 15px; display: block; text-align: right;">&#x16B6; {version}</span>
            </div>
            <div style="text-align:center;">
                <span class="sigma-label">Última Atualização</span>
                <span class="sigma-time">{hora_atual}</span>
            </div>
        </div>''',
    unsafe_allow_html=True)

# --- SIDEBAR E PAINEL ADMIN ---
with st.sidebar:
    st.markdown(f"### 👤 {USUARIO}")
    
    if "mostrar_form_senha" not in st.session_state:
        st.session_state.mostrar_form_senha = False
    
    if st.button("Alterar Senha", use_container_width=True):
        st.session_state.mostrar_form_senha = True

    placeholder = st.empty()

    if st.session_state.mostrar_form_senha:
        with placeholder.container():
            with st.form("change_pass_form"):
                current_pass = st.text_input("Senha Atual", type="password")
                new_pass = st.text_input("Nova Senha", type="password")
                confirm_pass = st.text_input("Confirmar Nova Senha", type="password")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    btn_atualizar = st.form_submit_button("Atualizar")
                with col2:
                    btn_cancelar = st.form_submit_button("Cancelar")

                if btn_atualizar:
                    if not current_pass or not new_pass or not confirm_pass:
                        st.error("Preencha todos os campos.")
                    elif new_pass != confirm_pass:
                        st.error("As novas senhas não coincidem.")
                    else:
                        user_ref = db.collection("users").document(st.session_state["email"])
                        user_doc = user_ref.get()
                        if isinstance(user_doc, DocumentSnapshot) and user_doc.exists:
                            user_data = user_doc.to_dict()
                            senha_hash = user_data["hash"].encode()
                            if bcrypt.checkpw(current_pass.encode(), senha_hash):
                                new_hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt())
                                user_ref.update({"hash": new_hashed.decode()})
                                st.success("Senha atualizada com sucesso!", icon="✅")
                                time.sleep(2)
                                st.session_state.mostrar_form_senha = False
                                placeholder.empty()
                            else:
                                st.error("Senha atual incorreta.")
                if btn_cancelar:
                    st.session_state.mostrar_form_senha = False
                    placeholder.empty()

    
    if CONTRATO: st.markdown(f"📍 **{CONTRATO}**")
    
    if PERFIL in ["master", "admin"]:
        st.divider()
        st.markdown("#### 🛡️ Aprovação de Acessos")
        user_ref = db.collection("users").where(filter=FieldFilter("approved", "==", False)).get()
        if user_ref:
            st.warning(f"🔔 {len(user_ref)} Pendente(s)")
            for user in user_ref:
                row = user.to_dict() or {}
                with st.container(border=True):
                    st.markdown(f"**{row.get('name', '')}** | {row.get('contract', '')}")
                    r_sel = st.selectbox("Perfil:", ["user", "admin"], key=f"r_{user.id}", label_visibility="collapsed")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Aprovar", key=f"y_{user.id}", use_container_width=True): 
                        user.reference.update({"approved": True, "role": r_sel})
                        st.toast(f"Utilizador {row.get('name')} aprovado!")
                        time.sleep(1)
                        st.rerun()
                    if c2.button("❌ Recusar", key=f"n_{user.id}", use_container_width=True): 
                        user.reference.delete()
                        st.toast(f"Utilizador {row.get('name')} removido!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.success("Tudo limpo! ✅")

    st.markdown("---")
    with st.container():
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ==============================================================================
# 🧠 DADOS E LÓGICA
# ==============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados_api():
    df_api = pd.DataFrame()
    erro_msg = None
    
    if API_URL:
        try:
            response = requests.get(API_URL, headers=API_HEADERS, timeout=25)
            if response.status_code == 200:
                data = response.json()
                if 'ocorrencias' in data:
                    df_api = pd.DataFrame(data['ocorrencias'])
            else:
                erro_msg = f"Erro API: {response.status_code}"
        except Exception as e: 
            erro_msg = str(e)

    df_hist = pd.DataFrame()
    if os.path.exists("historico_sigma.json"):
        try: 
            with open("historico_sigma.json", "r", encoding="utf-8") as f:
                data_hist = json.load(f)
                if 'ocorrencias' in data_hist:
                    df_hist = pd.DataFrame(data_hist['ocorrencias'])
                else:
                    df_hist = pd.DataFrame(data_hist)
        except: 
            pass

    if df_api.empty and df_hist.empty:
        return None, erro_msg or "Sem dados disponíveis."
        
    df = pd.concat([df_hist, df_api], ignore_index=True)
    
    if 'ocorrencia' in df.columns:
        df = df.drop_duplicates(subset=['ocorrencia'], keep='last')

    rename_map = { 
        'ocorrencia': 'Ocorrência', 'data_abertura': 'Abertura', 'contrato': 'Contrato', 
        'cnl': 'CNL', 'at': 'AT', 'afetacao': 'Afetação', 'vip': 'VIP', 
        'cond_alto_valor': 'Cond. Alto Valor', 'b2b_avancado': 'B2B', 
        'tecnicos': 'Técnicos', 'origem': 'Origem',
        'cabo': 'Cabo', 'primarias': 'Primárias', 'bd': 'BD',
        'propenso_anatel': 'Propensos - Anatel', 'reclamado_anatel': 'Reclamados - Anatel',
        'reincidencia': 'Reincidência'
    }
    df.rename(columns=rename_map, inplace=True)
    
    if 'Reincidência' in df.columns:
        def format_reinc(x):
            try:
                if pd.isna(x) or str(x).strip() in ["", "nan", "None"]: return ""
                return str(int(float(x)))
            except:
                return ""
        df['Reincidência'] = df['Reincidência'].apply(format_reinc)
    else:
        df['Reincidência'] = ""
    
    if 'equipamentos' in df.columns:
        df['Cabo/Primária'] = df['equipamentos'].apply(
            lambda x: str(x[0]).strip() if isinstance(x, list) and len(x) > 0 else "-"
        )
    else:
        df['Cabo/Primária'] = "-"
    
    df['Abertura_dt'] = pd.to_datetime(df['Abertura'], errors='coerce')
    
    if 'Técnicos' in df.columns: 
        df['Técnicos'] = df['Técnicos'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    
    if 'Afetação' in df.columns:
        df['Afetação'] = pd.to_numeric(df['Afetação'], errors='coerce').fillna(0).astype(int)
    
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

    if 'municipio' in df.columns:
        df.rename(columns={'municipio': 'Cidade_Real'}, inplace=True)
            
    return df, None

@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados_ofensores():
    if not API_URL_OFENSORES: return None, "URL de Ofensores não configurada no secrets.toml."
    try:
        response = requests.get(API_URL_OFENSORES, headers=API_HEADERS, timeout=25)
        if response.status_code == 200:
            return response.json(), None
        return None, f"Erro {response.status_code}"
    except Exception as e: 
        return None, str(e)

def processar_json_ofensores(dados_json):
    linhas = []
    
    if isinstance(dados_json, dict):
        for key, value in dados_json.items():
            if isinstance(value, list):
                dados_json = value
                break

    if not isinstance(dados_json, list): return pd.DataFrame()

    for item in dados_json:
        nome_completo = item.get("primaria", "")
        detalhes = item.get("detalhes", [])
        
        volume = len(detalhes)
        lista_ocs = [str(d.get("ocorrencia", "")) for d in detalhes]
        ocorrencias_str = ", ".join(lista_ocs)
        
        busca = re.search(r'([A-Za-z]{2})(\d+)-(.*)', str(nome_completo))
        
        if busca:
            at = busca.group(1).upper()
            cb = busca.group(2)
            prim = busca.group(3)
        else:
            at = "-"
            cb = "-"
            prim = nome_completo 
            
        linhas.append({
            "AT": at,
            "Cabo": cb,
            "Primária": prim,
            "Volume (Falhas)": volume,
            "Ocorrências (IDs)": ocorrencias_str
        })
        
    df = pd.DataFrame(linhas)
    if not df.empty:
        df = df.sort_values(by="Volume (Falhas)", ascending=False)
    return df

def carregar_base_share():
    print("\n--- INÍCIO DA LEITURA DO SHARE ---")
    file_options = [
        "share_at_sj.csv",
        "SHARE_AT_SJ.csv", 
        "SHARE_AT_SJC_JAI.xlsx",
        "SHARE_AT_SJC_JAI.xlsx - SHARE_AT_SJ.csv", 
        "SHARE_AT_SJC_JAI.xlsx - SHARE_AT _JAI.csv"
    ]
    
    for file in file_options:
        if os.path.exists(file):
            print(f"⏳ Ficheiro encontrado: {file}. A tentar ler...")
            try:
                if file.endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:
                    # Tenta vírgula normal (ERRO DE DIGITAÇÃO CORRIGIDO AQUI)
                    df = pd.read_csv(file) 
                    
                    # Se detetar que só criou 1 coluna, o Excel exportou com ponto e vírgula
                    if len(df.columns) < 3:  
                        print("Aviso: Formato incorreto detetado, a tentar com separador ';'")
                        df = pd.read_csv(file, sep=';')
                
                print(f"✅ Ficheiro {file} lido com sucesso. Linhas totais: {len(df)}")
                df.columns = df.columns.str.strip()
                
                if 'nom_AreaTelefonica' in df.columns and 'qtd_Acessos' in df.columns:
                    print("⚙️ Colunas corretas encontradas. A processar matemática...")
                    df = df.dropna(subset=['num_MesAno', 'nom_AreaTelefonica', 'qtd_Acessos'])
                    
                    df['num_MesAno'] = df['num_MesAno'].astype(float).astype(int).astype(str)
                    df['year'] = df['num_MesAno'].str[-4:].astype(int)
                    df['month'] = df['num_MesAno'].str[:-4].astype(int)
                    df['date'] = pd.to_datetime({'year': df['year'], 'month': df['month'], 'day': 1})
                    
                    latest_date = df['date'].max()
                    df_latest = df[df['date'] == latest_date]
                    
                    dict_share = df_latest.groupby('nom_AreaTelefonica')['qtd_Acessos'].sum().to_dict()
                    print(f"🚀 Sucesso! Dicionário criado com {len(dict_share)} ATs.")
                    return dict_share
                else:
                    print(f"❌ Aviso: O ficheiro {file} não tem as colunas corretas.")
            except Exception as e:
                print(f"❌ Erro ao ler {file}: {str(e)}")
                continue
                
    print("--- FIM: NENHUM FICHEIRO VÁLIDO ENCONTRADO ---")
    return {}

def processar_dados(df_raw, filtros_contrato):
    agora = datetime.now().replace(tzinfo=None)
    
    df = df_raw.copy()
    
    df['Contrato_Padrao'] = df['Contrato'].astype(str).str.strip().str.upper()
    if isinstance(filtros_contrato, str): df = df[df['Contrato_Padrao'] == filtros_contrato.upper()].copy()
    elif isinstance(filtros_contrato, list) and filtros_contrato: df = df[df['Contrato_Padrao'].isin([c.upper() for c in filtros_contrato])].copy()
    
    df['Abertura_dt'] = pd.to_datetime(df['Abertura'], errors='coerce').dt.tz_localize(None)
    df['diff_s'] = (agora - df['Abertura_dt']).dt.total_seconds().clip(lower=0)
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
    
    dict_status = carregar_status_campo()
    df['Último Status'] = df['Ocorrência'].astype(str).map(dict_status).fillna("A aguardar atualização")
    
    return df.sort_values('horas_float', ascending=False)

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
    import matplotlib.pyplot as plt
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
    import matplotlib.pyplot as plt
    ITENS_POR_PAGINA = 20
    cols = [c for c in col_order if c in df_view.columns and c not in ['horas_float', 'Status SLA']]
    
    df_p = df_view[cols].copy().rename(columns={
        'Ocorrência': 'ID', 
        'Horas Corridas': 'Tempo', 
        'Cond. Alto Valor': 'A.V',
        'Cabo/Primária': 'Cabo/Prim.',
        'Reincidência': 'Reinc.',
        'Afetação': 'Afet.',
        'Técnicos': 'Téc.'
    })
    
    lista_imagens = []
    total_linhas = len(df_p)
    if total_linhas == 0: return lista_imagens
        
    num_paginas = (total_linhas + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA
    
    for i in range(num_paginas):
        inicio = i * ITENS_POR_PAGINA; fim = inicio + ITENS_POR_PAGINA
        df_chunk = df_p.iloc[inicio:fim]; idx_chunk = df_view.iloc[inicio:fim]
        
        fig, ax = plt.subplots(figsize=(17, max(4, 3 + len(df_chunk)*0.8)), dpi=180)
        ax.axis('off'); fig.patch.set_facecolor('white')
        
        titulo = f"SIGMA OPS: {contrato}\n{datetime.now().strftime('%d/%m • %H:%M')}"
        if num_paginas > 1: titulo += f" (Pág {i+1}/{num_paginas})"
            
        plt.title(titulo, loc='center', pad=40, fontsize=28, weight='black', color='#1e293b')
        tbl = ax.table(cellText=df_chunk.values.tolist(), colLabels=df_chunk.columns, cellLoc='center', loc='center')
        
        tbl.auto_set_font_size(False); tbl.set_fontsize(11); tbl.scale(1.0, 3.0)
        
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
    import matplotlib.pyplot as plt
    df_filtrado = df_geral.copy()
    resumo = df_filtrado.groupby('Contrato_Padrao').agg(
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
        'Grandes_Vultos': 'G. Vulto',
        'Cond_Alto_Valor': 'Alto Valor',
        'Criticos': 'Críticos >24h'
    }).reset_index().sort_values('Total', ascending=False)
    
    resumo.rename(columns={'Contrato_Padrao': 'Contrato'}, inplace=True)

    fig, ax = plt.subplots(figsize=(16, max(4, 3 + len(resumo)*0.8)), dpi=200)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    
    hora = datetime.now().strftime("%d/%m • %H:%M")
    plt.title(f"VISÃO CLUSTER\nConsolidado SigmaOPS • {hora}", loc='center', pad=40, fontsize=28, weight='black', color='#1e293b')
    
    tbl = ax.table(cellText=resumo.values.tolist(), colLabels=resumo.columns, cellLoc='center', loc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1.2, 3.0)
    
    for (i, j), cell in tbl.get_celld().items():
        if i == 0: 
            cell.set_facecolor('#7c3aed')
            cell.get_text().set_color('white')
            cell.get_text().set_weight('bold')
        else: 
            cell.set_edgecolor('#e2e8f0')
            cell.get_text().set_weight('bold')
            cell.get_text().set_color('#1e293b')
            if i % 2 == 0: 
                cell.set_facecolor('#f8fafc')
                
    buf = io.BytesIO()
    plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor='white')
    plt.close(fig)
    return buf.getvalue()

# ==============================================================================
# 📊 CORPO DO DASHBOARD
# ==============================================================================
df_raw, erro = carregar_dados_api()

if df_raw is not None:
    # --- ABAS DE PERFIS ---
    if PERFIL in ["master", "admin"]: 
        tab_op, tab_cl, tab_of, tab_share = st.tabs(["Operacional", "Cluster", "Ofensores", "Criticidade Share"])
    else: 
        tab_op, tab_of, tab_share = st.tabs(["Operacional", "Ofensores", "Criticidade Share"])
        tab_cl = None

    # --- ABA OPERACIONAL ---
    with tab_op:
        c_sel, c_ref = st.columns([5, 1], gap="small")
        with c_sel:
            if CONTRATO and PERFIL not in ["master", "admin"]:
                st.info(f"A visualizar: {CONTRATO}")
                contrato_atual = CONTRATO
            else:
                contrato_atual = st.radio("Selecione o Contrato:", CONTRATOS_VALIDOS, horizontal=True, label_visibility="collapsed")
        with c_ref:
            if st.button("🔄 Atualizar", use_container_width=True): carregar_dados_api.clear(); st.rerun()

        df_view = processar_dados(df_raw, contrato_atual)
        
        c_f1, c_f2 = st.columns(2)
        with c_f1: f_reg = st.multiselect("Região", df_view['Area'].unique())
        with c_f2: f_sla = st.multiselect("SLA", ["Crítico", "Fora do Prazo", "No Prazo"])
        
        if f_reg: df_view = df_view[df_view['Area'].isin(f_reg)]
        if f_sla: df_view = df_view[df_view['Status SLA'].isin(f_sla)]

        # KPIs HTML
        t = len(df_view)
        k = {'total': t, 'sem_tec': len(df_view[df_view['Técnicos']==0]), 'critico': len(df_view[df_view['Status SLA']=='Crítico']), 'fora': len(df_view[df_view['Status SLA']=='Fora do Prazo']), 'no_prazo': len(df_view[df_view['Status SLA']=='No Prazo']), 'lit': len(df_view[df_view['Area']=='Litoral']), 'vale': len(df_view[df_view['Area']=='Vale'])}
        
        c_style = "background:white;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;padding:12px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.03);display:flex;flex-direction:column;justify-content:center;height:80px;"
        
        def badge(num, total, cor): 
            if total == 0: return ""
            return f"<span style='font-size:11px;font-weight:bold;color:{cor};background:{cor}15;padding:2px 6px;border-radius:4px;margin-left:8px;vertical-align:middle;'>{int((num/total)*100)}%</span>"
        
        html = f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:15px;">
            <div style="{c_style}"><div style="font-size:11px;color:#64748b;">Total</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k['total']}</div></div>
            <div style="{c_style}"><div style="font-size:11px;color:#64748b;">S/ Técnico</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k['sem_tec']} {badge(k['sem_tec'], t, '#dc2626')}</div></div>
            <div style="{c_style.replace('#7c3aed','#dc2626')}"><div style="font-size:11px;color:#64748b;">Crítico (>24h)</div><div style="font-size:18px;font-weight:800;color:#dc2626;">{k['critico']} {badge(k['critico'], t, '#dc2626')}</div></div>
            <div style="{c_style.replace('#7c3aed','#d97706')}"><div style="font-size:11px;color:#64748b;">Fora Prazo</div><div style="font-size:18px;font-weight:800;color:#d97706;">{k['fora']} {badge(k['fora'], t, '#d97706')}</div></div>
            <div style="{c_style.replace('#7c3aed','#16a34a')}"><div style="font-size:11px;color:#64748b;">No Prazo</div><div style="font-size:18px;font-weight:800;color:#16a34a;">{k['no_prazo']} {badge(k['no_prazo'], t, '#16a34a')}</div></div>"""
        
        if contrato_atual == 'ABILITY_SJ': html += f"""<div style="{c_style}"><div style="font-size:11px;color:#64748b;">Litoral</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k['lit']} {badge(k['lit'], t, '#7c3aed')}</div></div><div style="{c_style}"><div style="font-size:11px;color:#64748b;">Vale</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k['vale']} {badge(k['vale'], t, '#7c3aed')}</div></div>"""
        st.markdown(html + "</div>", unsafe_allow_html=True)

        gv = len(df_view[df_view['Afetação']>=100])
        if gv > 0:
            st.markdown(f"<div class='alert-box'>🚨 {gv} GRANDE(S) VULTO(S) EM ABERTO</div>", unsafe_allow_html=True)
            with st.expander("Ver Detalhes GV"):
                for _, row in df_view[df_view['Afetação'] >= 100].iterrows(): st.code(gerar_texto_gv(row, contrato_atual), language="text")

        with st.expander("📂 Opções de Exportação"):
            c1, c2 = st.columns(2)
            try: 
                c1.download_button("Baixar Resumo", gerar_cards_mpl(k, contrato_atual), f"resumo_{nome_arq}.jpg", "image/jpeg", use_container_width=True)
            except: pass
            
            cols_export = ['Ocorrência', 'Cabo/Primária', 'AT', 'Afetação', 'Reincidência', 'Origem', 'Horas Corridas', 'Status SLA', 'VIP', 'Cond. Alto Valor', 'B2B', 'Técnicos']
            try: 
                imgs = gerar_lista_mpl_from_view(df_view, cols_export, contrato_atual)
                if imgs: 
                    if len(imgs) == 1:
                        c2.download_button("Baixar Lista", imgs[0], f"lista_{nome_arq}.jpg", "image/jpeg", use_container_width=True)
                    else:
                        for idx_img, img_bytes in enumerate(imgs):
                            c2.download_button(f"Baixar Lista (Pág {idx_img+1})", img_bytes, f"lista_{nome_arq}_p{idx_img+1}.jpg", "image/jpeg", use_container_width=True)
            except: pass

        # --- PAINEL DE INSERÇÃO DE STATUS ---
        with st.expander("📝 Atualizar Status da Equipa de Campo", expanded=False):
            with st.form("form_status_campo", clear_on_submit=True):
                
                lista_ocs = df_view['Ocorrência'].astype(str).tolist()
                
                if lista_ocs:
                    dict_format = {}
                    for _, row in df_view.iterrows():
                        oc = str(row['Ocorrência'])
                        cabo = str(row.get('Cabo/Primária', '-'))
                        at_local = str(row.get('AT', '-'))
                        
                        afet = row.get('Afetação', 0)
                        try: afet = int(afet)
                        except: afet = 0
                        gv_flag = " - GV" if afet >= 100 else ""
                        
                        dict_format[oc] = f"{oc} | {at_local} | {cabo}{gv_flag}"
                        
                    c_st1, c_st2, c_st3 = st.columns([1.5, 1, 2])
                    sel_oc = c_st1.selectbox("Ocorrência", lista_ocs, format_func=lambda x: dict_format.get(x, x))
                    sel_st = c_st2.selectbox("Ação", ["Em deslocamento", "A percorrer Rota", "A lançar Cabo", "A preparar Fusão", "A aguardar Material", "Caixa de Emenda", "A aguardar Teste", "Outro"])
                    txt_obs = c_st3.text_input("Observação (Opcional)", placeholder="Ex. a lançar x metros de cabo, a aguardar chegada da equipa, etc.")
                    
                    if PERFIL in ["master", "admin"]:
                        c_btn1, c_btn2 = st.columns(2)
                        btn_salvar = c_btn1.form_submit_button("💾 Guardar Histórico", use_container_width=True)
                        btn_apagar = c_btn2.form_submit_button("🗑️ Apagar Histórico", use_container_width=True)
                    else:
                        btn_salvar = st.form_submit_button("💾 Guardar Histórico", use_container_width=True)
                        btn_apagar = False
                        
                    if btn_salvar:
                        salvar_status_campo(sel_oc, sel_st, txt_obs, USUARIO)
                        st.success(f"Status da ocorrência {sel_oc} atualizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                        
                    if btn_apagar:
                        db.collection("status_campo").document(str(sel_oc)).delete()
                        st.success(f"Histórico apagado! Status retornado para 'A aguardar atualização'.")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info("Nenhuma ocorrência disponível na tela para atualizar.")
                    st.form_submit_button("💾 Guardar", disabled=True)

        # --- EXIBIÇÃO DA TABELA HTML CENTRALIZADA COM RESPONSIVIDADE ---
        c_tab1, c_tab2 = st.columns([4, 1])
        with c_tab2:
            layout_modo = st.selectbox("📱 Visualização", ["🖥️ PC (Completa)", "📱 Telemóvel (Resumida)"], label_visibility="collapsed")

        if "Telemóvel" in layout_modo:
            cols_visiveis = [
                'Ocorrência', 'Cabo/Primária', 'AT', 'Afetação', 
                'Reincidência', 'Horas Corridas', 'Último Status', 'Técnicos'
            ]
            cols_ocultar_html = ['horas_float', 'B2B']
        else:
            cols_visiveis = [
                'Ocorrência', 'Cabo/Primária', 'AT', 'Afetação', 'Reincidência', 
                'Origem', 'Horas Corridas', 'Status SLA', 'Último Status', 
                'VIP', 'Cond. Alto Valor', 'B2B', 'Técnicos'
            ]
            cols_ocultar_html = ['horas_float']
        
        cols_logica = list(dict.fromkeys(cols_visiveis + cols_ocultar_html))
        c_final = [c for c in cols_logica if c in df_view.columns]

        df_tela = df_view[c_final].copy()
        dict_renomear = {
            'Ocorrência': 'ID', 'Cabo/Primária': 'Cabo/Prim.', 
            'Afetação': 'Afet.', 'Reincidência': 'Reinc.',
            'Horas Corridas': 'Tempo', 'Status SLA': 'SLA',
            'Último Status': 'Status', 'Cond. Alto Valor': 'A.V', 
            'Técnicos': 'Téc.'
        }
        df_tela.rename(columns=lambda x: dict_renomear.get(x, x), inplace=True)

        def highlight_rows_tela(row):
            h = row.get('horas_float', 0)
            is_b2b = str(row.get('B2B', 'NÃO')).upper() == 'SIM'
            limite_fora = 4 if is_b2b else 8
            
            tc = '#16a34a' 
            if h > 24: tc = '#dc2626' 
            elif h > limite_fora: tc = '#d97706' 
            
            if row.get('Afet.', 0) >= 100: tc = '#2563eb'
            
            styles = []
            for col in row.index:
                val = str(row[col]).upper().strip()
                cell_style = f'color: {tc}; text-align: center !important; font-weight: 700;'
                
                if col == 'VIP' and val == 'SIM': cell_style += 'background-color: #f5d0fe; color: #86198f;'
                elif col == 'A.V' and val == 'SIM': cell_style += 'background-color: #d9f99d; color: #365314;'
                elif col == 'B2B' and val == 'SIM': cell_style += 'background-color: #ddd6fe; color: #5b21b6;'
                styles.append(cell_style)
            return styles

        ocultar_final = [dict_renomear.get(c, c) for c in cols_ocultar_html if c in df_view.columns]

        tabela_html = df_tela.style.apply(highlight_rows_tela, axis=1).set_table_attributes(
            'style="width:100%; text-align:center; border-collapse: collapse; font-family: Inter, sans-serif;"'
        ).set_table_styles([
            dict(selector='th', props=[('text-align', 'center'), ('background-color', '#f1f5f9'), ('color', '#475569'), ('padding', '10px'), ('border-bottom', '2px solid #e2e8f0'), ('font-size', '13px')]),
            dict(selector='td', props=[('padding', '8px'), ('border-bottom', '1px solid #f8fafc'), ('font-size', '12px')])
        ]).hide(axis='index').hide(subset=ocultar_final, axis='columns').to_html()

        with st.container(height=600, border=False):
            st.markdown(tabela_html, unsafe_allow_html=True)

    # --- ABA CLUSTER ---
    if tab_cl:
        with tab_cl:
            with st.form("form_cluster"):
                c1, c2 = st.columns([5, 1])
                with c1: sels = st.multiselect("Contratos:", CONTRATOS_VALIDOS, default=CONTRATOS_VALIDOS)
                with c2: 
                    st.write("")
                    st.write("")
                    st.form_submit_button("Atualizar Visão", use_container_width=True)
            
            if sels:
                df_cl = processar_dados(df_raw, sels)
                
                t_g = len(df_cl)
                t_gv = len(df_cl[df_cl['Afetação']>=100])
                c_ok = len(df_cl[df_cl['Status SLA']=='No Prazo'])
                c_fora = len(df_cl[df_cl['Status SLA']=='Fora do Prazo'])
                c_crit = len(df_cl[df_cl['Status SLA']=='Crítico'])
                
                def badge_cl(num, total, cor): 
                    if total == 0: return ""
                    return f"<span style='font-size:10px;font-weight:bold;color:{cor};background:{cor}15;padding:2px 6px;border-radius:4px;margin-left:5px;vertical-align:middle;'>{(num/total*100):.0f}%</span>"
                
                h_cl = f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:15px;">
                    <div style="{c_style}"><div style="font-size:11px;color:#64748b;">Total Geral</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{t_g}</div></div>
                    <div style="{c_style.replace('#7c3aed','#d97706')}"><div style="font-size:11px;color:#64748b;">GV</div><div style="font-size:18px;font-weight:800;color:#d97706;">{t_gv} {badge_cl(t_gv, t_g, '#d97706')}</div></div>
                    <div style="{c_style.replace('#7c3aed','#16a34a')}"><div style="font-size:11px;color:#64748b;">No Prazo</div><div style="font-size:18px;font-weight:800;color:#16a34a;">{c_ok} {badge_cl(c_ok, t_g, '#16a34a')}</div></div>
                    <div style="{c_style.replace('#7c3aed','#d97706')}"><div style="font-size:11px;color:#64748b;">Fora Prazo</div><div style="font-size:18px;font-weight:800;color:#d97706;">{c_fora} {badge_cl(c_fora, t_g, '#d97706')}</div></div>
                    <div style="{c_style.replace('#7c3aed','#dc2626')}"><div style="font-size:11px;color:#64748b;">Críticos (>24h)</div><div style="font-size:18px;font-weight:800;color:#dc2626;">{c_crit} {badge_cl(c_crit, t_g, '#dc2626')}</div></div>
                </div>"""
                st.markdown(h_cl, unsafe_allow_html=True)
                
                with st.expander("Descarregar Imagem"):
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
                
                st.dataframe(resumo, use_container_width=True, hide_index=True)
            else:
                st.warning("Selecione pelo menos um contrato.")

    # --- ABA OFENSORES (NOVA API DIRETA) ---
    with tab_of:
        st.markdown("<h3 style='color:#1e293b;'>🏆 Ranking de Primárias Ofensoras</h3>", unsafe_allow_html=True)
        st.markdown("Monitorização de equipamentos em crise com base na API em tempo real.")
        
        c_f1, c_f2 = st.columns([5, 1], gap="small")
        with c_f1:
            at_sel = st.text_input("Filtrar por AT (Digite a sigla, ex: PE, TT):", placeholder="Deixe em branco para ver todas as ATs...").strip().upper()
        with c_f2:
            st.write("")
            st.write("")
            if st.button("🔄 Atualizar Base", use_container_width=True):
                carregar_dados_ofensores.clear()
                st.rerun()

        st.write("")
        
        dados_of, erro_of = carregar_dados_ofensores()
        
        if dados_of is not None:
            df_rank = processar_json_ofensores(dados_of)
            
            if not df_rank.empty:
                if at_sel:
                    ats_list = [x.strip() for x in at_sel.split(',')]
                    df_rank = df_rank[df_rank['AT'].isin(ats_list)]
                    
                if not df_rank.empty:
                    top_1 = df_rank.iloc[0]
                    if top_1['Volume (Falhas)'] > 1:
                        st.markdown(f"""
                        <div style='background-color: #fee2e2; border-left: 5px solid #dc2626; padding: 15px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                            <h4 style='color: #991b1b; margin: 0; font-weight: 800;'>🚨 ALERTA DE OFENSOR CRÍTICO</h4>
                            <p style='color: #7f1d1d; margin: 5px 0 0 0; font-size: 15px;'>
                                A primária <b>{top_1['Primária']}</b> (AT: {top_1['AT']} | Cabo: {top_1['Cabo']}) possui <b>{top_1['Volume (Falhas)']} chamados ativos</b> simultâneos.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    st.markdown("##### 📋 Detalhamento dos Casos em Crise")
                    st.dataframe(
                        df_rank.style.set_properties(**{'text-align': 'center', 'font-weight': '600'}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhuma primária ofensora encontrada para a AT selecionada.")
            else:
                st.info("🎉 Excelente! Nenhuma primária ofensora detetada no momento.")
        else:
            st.error(f"Falha ao comunicar com a API de Ofensores: {erro_of}")

    # --- ABA CRITICIDADE SHARE ---
    with tab_share:
        st.markdown("<h3 style='color:#1e293b;'>📉 Análise de Criticidade (Share da AT)</h3>", unsafe_allow_html=True)
        st.markdown("Calcula a percentagem de clientes offline em relação ao tamanho total da central (AT). Permite descobrir quando uma ocorrência pequena em números absolutos é, na verdade, uma falha gravíssima e de grande impacto relativo para aquela localidade.")
        
        dict_share = carregar_base_share()
        
        if not dict_share:
            st.warning("⚠️ Ficheiro de Share não encontrado. Coloque o ficheiro CSV extraído de Share na mesma pasta do sistema para ativar esta função.")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                limite_critico = st.slider("🚨 Alerta de Crise a partir de (%)", min_value=1.0, max_value=20.0, value=3.0, step=0.5, help="Pela regra de ouro: Perder mais de 3% de toda a central num único evento já configura um cenário crítico ou de Grande Vulto.")
                
            df_share = df_view.copy()
            df_share['AT_Clean'] = df_share['AT'].astype(str).str.split('-').str[0].str.strip().str.upper()
            
            df_share = df_share[(df_share['AT_Clean'] != '-') & (df_share['Afetação'] > 0)].copy()
            
            if not df_share.empty:
                df_share['Total_Clientes_AT'] = df_share['AT_Clean'].map(dict_share)
                df_share = df_share.dropna(subset=['Total_Clientes_AT'])
                
                if not df_share.empty:
                    df_share['Total_Clientes_AT'] = df_share['Total_Clientes_AT'].astype(int)
                    df_share['Risco_Pct'] = (df_share['Afetação'] / df_share['Total_Clientes_AT']) * 100
                    
                    df_share = df_share.sort_values(by='Risco_Pct', ascending=False)
                    
                    qtd_criticos = len(df_share[df_share['Risco_Pct'] >= limite_critico])
                    pior_oc = df_share.iloc[0]
                    
                    c_k1, c_k2, c_k3 = st.columns(3)
                    c_k1.markdown(f"<div class='alert-box' style='background:#fef2f2; border-color:#fecaca;'><div style='color:#991b1b; font-size:12px;'>Ocorrências em Crise (>{limite_critico}%)</div><div style='font-size:24px; font-weight:900;'>{qtd_criticos}</div></div>", unsafe_allow_html=True)
                    
                    cor_pior = '#dc2626' if pior_oc['Risco_Pct'] >= limite_critico else '#d97706'
                    c_k2.markdown(f"<div class='alert-box' style='background:#fffbeb; border-color:#fde68a;'><div style='color:#92400e; font-size:12px;'>Maior Risco Atual (AT: {pior_oc['AT_Clean']})</div><div style='font-size:24px; font-weight:900; color:{cor_pior};'>{pior_oc['Risco_Pct']:.2f}% de toda a Central</div></div>", unsafe_allow_html=True)
                    
                    st.write("")
                    st.markdown("##### 📋 Ocorrências classificadas por Risco de Impacto")
                    
                    df_share['Risco (%)'] = df_share['Risco_Pct'].apply(lambda x: f"{x:.2f}%")
                    
                    cols_exibicao = ['Ocorrência', 'AT_Clean', 'Cabo/Primária', 'Afetação', 'Total_Clientes_AT', 'Risco (%)', 'Último Status']
                    df_style = df_share[cols_exibicao + ['Risco_Pct']].rename(columns={'AT_Clean': 'AT', 'Total_Clientes_AT': 'Tamanho da Central (Share)', 'Afetação': 'Clientes Fora'})
                    
                    def highlight_risco(row):
                        risco = row.get('Risco_Pct', 0)
                        if risco >= limite_critico:
                            return ['background-color: #fee2e2; color: #991b1b; font-weight: 800;' for _ in row]
                        elif risco >= limite_critico / 2:
                            return ['background-color: #fffbeb; color: #92400e; font-weight: 600;' for _ in row]
                        return ['' for _ in row]
                    
                    st.dataframe(
                        df_style.style.apply(highlight_risco, axis=1).hide(subset=['Risco_Pct'], axis='columns').set_properties(**{'text-align': 'center'}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhuma das ATs com falha no momento foi encontrada no ficheiro de Share. Verifique as siglas das ATs.")
            else:
                st.info("Não há ocorrências com afetação nas ATs no momento (Todas zeradas).")

else:
    st.error("Erro ao carregar dados.")