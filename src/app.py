#!/usr/bin/env python3
import io
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import folium

# import numpy as np
import pandas as pd
import requests
import streamlit as st

# from folium.plugins import HeatMap
from loguru import logger
from matplotlib import patches
from sqlalchemy import select
from streamlit_cookies_controller import CookieController
from streamlit_folium import st_folium

from application.use_cases import reports
from application.use_cases.user import (
    atualizar_senha,
    cadastrar_novo_usuario,
    logar_usuario,
    obter_usuario_por_email,
)
from infrastructure.api import load_dminusOne
from persistence.database import get_session
from persistence.models import User

# Versão do SigmaOPS
version = "1.4.6"


@st.cache_resource
def init_logger():
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")


init_logger()

# ==============================================================================
# 🌍 1. CONFIGURAÇÃO DE AMBIENTE
# ==============================================================================
os.environ["TZ"] = "America/Sao_Paulo"
if hasattr(time, "tzset"):
    time.tzset()

st.set_page_config(
    page_title="SigmaOPS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# ⚙️ CONSTANTES GLOBAIS
# ==============================================================================
CONTRATOS_VALIDOS = [
    "ABILITY_SJ",
    "ABILITY_OS",
    "TEL_INTERIOR",
    "TEL_JI",
    "TEL_PC_SC",
    "TELEMONT",
]

nome_arq = datetime.now(time.tzset()).strftime("%H%M")

if "contrato_ofensor" not in st.session_state:
    st.session_state.contrato_ofensor = CONTRATOS_VALIDOS[0]

# ==============================================================================
# 🔐 SEGURANÇA E BANCO DE DADOS
# ==============================================================================


def get_secret(section, key):
    try:
        return st.secrets[section][key]
    except FileNotFoundError:
        return None


API_URL = get_secret("api", "url") or ""
API_URL_OFENSORES = get_secret("api", "url_ofensores") or ""
API_URL_DMINUSONE = get_secret("api", "d_minus_one") or ""

# ==============================================================================
# 🚪 LÓGICA DE LOGIN
# ==============================================================================

cookie_controller = CookieController()


def obter_validade() -> datetime:
    """Retorna o tempo de expiração para o cookie."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(minutes=30)


def logout() -> None:
    cookie_controller.remove("session_token")
    st.session_state.clear()
    time.sleep(2)
    st.rerun()


def login(user: User) -> None:
    """Atualiza o estado de sessão para refletir o login bem-sucedido e recarrega a aplicação."""
    if user.contract == "MASTER":
        default = "ABILITY_SJ"
    else:
        default = user.contract

    st.session_state.update(
        {
            "logged_in": True,
            "username": user.name,
            "email": user.email,
            "role": user.role,
            "allowed_contract": user.contract,
            "contract": default,
        }
    )
    cookie_controller.set(
        "session_token",
        user.email,
        expires=obter_validade(),
    )
    st.rerun()


def atualizar_contrato_callback():
    st.session_state.contract = st.session_state.contrato_ofensor


cookie_session = cookie_controller.get("session_token")

if cookie_session is not None:
    if "logged_in" not in st.session_state:
        try:
            login(obter_usuario_por_email(cookie_session))
        except ValueError as e:
            st.error(e)

    nova_validade = obter_validade()
    cookie_controller.set("session_token", cookie_session, expires=nova_validade)


if "logged_in" not in st.session_state:
    st.query_params.clear()

    st.markdown(
        """
    <style>
        .stApp { background-color: #ffffff; }
        [data-testid="stSidebar"], header, footer { display: none !important; }
        .login-box { margin: 1vh auto; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); max-width: 380px; border: 1px solid #f1f5f9; text-align: center; }
        .logo { font-size: 4rem; font-weight: 900; background: -webkit-linear-gradient(#a855f7, #4c1d95); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        div[data-testid="stFormSubmitButton"] button { width: 100%; background-color: #7c3aed !important; color: white !important; font-weight: bold; border-radius: 8px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="login-box"><div class="logo">Σ</div><h2 style="color:#4c1d95;margin-top:-10px;">SigmaOPS</h2></div>',
        unsafe_allow_html=True,
    )

    c1, container_cad_login, c3 = st.columns([1, 1.2, 1])
    with container_cad_login:
        aba_login, aba_cadastro = st.tabs(["Acessar", "Registar"])

        # LOGIN DE USUÁRIOS EXISTENTES
        with aba_login, st.form("login_form"):
            email = st.text_input("E-mail", icon="📧").strip().lower()
            senha = st.text_input("Senha", type="password", icon="🔐").strip()
            if st.form_submit_button("Entrar"):
                try:
                    if email and senha:
                        user = logar_usuario(email, senha)
                        login(user)
                    else:
                        st.warning("Preencha todos os campos")
                except ValueError as e:
                    st.error(e)

        # CADASTRO DE NOVOS USUÁRIOS
        with aba_cadastro, st.form("reg_form"):
            nome = st.text_input("Nome", icon="👤").strip()
            email = st.text_input("Email", icon="📧").strip()
            contrato = st.selectbox("Área", CONTRATOS_VALIDOS)
            senha = st.text_input("Senha", type="password", icon="🔐")

            if st.form_submit_button("Solicitar Acesso"):
                try:
                    cadastrar_novo_usuario(nome, email, contrato, senha)
                    st.success("Solicitação enviada. Aguarde libertação.")
                except ValueError as e:
                    st.error(e)

    st.stop()

# APLICAÇÃO PRINCIPAL
else:
    USUARIO = st.session_state["username"]
    PERFIL = st.session_state["role"]
    CONTRATOS = st.session_state["allowed_contract"]
    hora_atual = (datetime.now(UTC) - timedelta(hours=3)).strftime("%H:%M")

    # --- ESTILOS CSS ---
    st.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""<div class="sigma-header">
                <div class="sigma-title">
                    SigmaOPS
                    <span style="font-size: 15px; display: block; text-align: right;"> 🧭 {version}</span>
                </div>
                <div style="text-align:center;">
                    <span class="sigma-label">Última Atualização</span>
                    <span class="sigma-time">{hora_atual}</span>
                </div>
            </div>""",
        unsafe_allow_html=True,
    )

    # --- SIDEBAR E PAINEL ADMIN ---
    with st.sidebar:
        st.markdown(f"### 👤 {USUARIO}")

        if "mostrar_form_senha" not in st.session_state:
            st.session_state.mostrar_form_senha = False

        if st.button("Alterar Senha", width="stretch"):
            st.session_state.mostrar_form_senha = True

        placeholder = st.empty()

        if st.session_state.mostrar_form_senha:
            with placeholder.container(), st.form("change_pass_form"):
                senha_atual = st.text_input("Senha Atual", type="password")
                nova_senha_1 = st.text_input("Nova Senha", type="password")
                nova_senha_2 = st.text_input("Confirmar Nova Senha", type="password")

                col1, col2 = st.columns(2)

                with col1:
                    btn_atualizar = st.form_submit_button("Atualizar")

                with col2:
                    btn_cancelar = st.form_submit_button("Cancelar")

                if btn_atualizar:
                    if not senha_atual or not nova_senha_1 or not nova_senha_2:
                        st.error("Preencha todos os campos.")

                    elif nova_senha_1 != nova_senha_2:
                        st.error("As novas senhas não coincidem.")

                    else:
                        try:
                            email = st.session_state.get("email")
                            atualizar_senha(email, senha_atual, nova_senha_1)
                            st.success("Senha atualizada com sucesso!", icon="✅")
                            time.sleep(2)
                            st.session_state.mostrar_form_senha = False
                            placeholder.empty()

                        except ValueError as e:
                            st.error(e)

                if btn_cancelar:
                    st.session_state.mostrar_form_senha = False
                    placeholder.empty()

        if CONTRATOS:
            st.markdown(f"📍 **{CONTRATOS}**")

        if PERFIL in ["master", "admin"]:
            st.divider()
            st.markdown("#### 🛡️ Aprovação de Acessos")
            with get_session() as session:
                stmt = select(User).where(User.approved == False)
                users_pendent_approves = session.execute(stmt).mappings().all()
                if users_pendent_approves:
                    st.warning(f"🔔 {len(users_pendent_approves)} Pendente(s)")
                    for user in users_pendent_approves:
                        row = user.get("User", {})
                        with st.container(border=True):
                            st.markdown(f"**{row.name}** | {row.contract}")
                            r_sel = st.selectbox(
                                "Perfil:",
                                ["user", "admin"],
                                key=f"r_{row.id}",
                                label_visibility="collapsed",
                            )
                            c1, container_cad_login = st.columns(2)
                            if c1.button(
                                "✅ Aprovar", key=f"y_{row.id}", width="stretch"
                            ):
                                row.approved = True
                                session.commit()
                                st.toast(f"Utilizador {row.name} aprovado!")
                                time.sleep(1)
                                st.rerun()
                            if container_cad_login.button(
                                "❌ Recusar", key=f"n_{row.id}", width="stretch"
                            ):
                                session.delete(row)
                                session.commit()
                                st.toast(f"Utilizador {row.name} removido!")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.success("Tudo limpo! ✅")

        st.markdown("---")
        with st.container():
            if st.button("🚪 Sair do Sistema", width="stretch"):
                logout()

    # ==============================================================================
    # 🧠 DADOS E LÓGICA
    # ==============================================================================

    @st.cache_data(ttl=60, show_spinner=False)
    def carregar_dados_api():
        df_api = pd.DataFrame()
        erro_msg = None

        if API_URL:
            try:
                response = requests.get(API_URL, timeout=25)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(data["ocorrencias"][0].keys())
                    if "ocorrencias" in data:
                        df_api = pd.DataFrame(data["ocorrencias"])
                else:
                    erro_msg = f"Erro API: {response.status_code}"
            except Exception as e:
                logger.error(f"Erro ao carregar dados da API: {e!s}")
                erro_msg = str(e)

        if df_api.empty:
            return None, erro_msg or "Sem dados disponíveis."

        if "ocorrencia" in df_api.columns:
            df_api["ocorrencia"] = df_api["ocorrencia"].astype(int)
            df_api = df_api.drop_duplicates(subset=["ocorrencia"], keep="last")

        rename_map = {
            "ocorrencia": "Ocorrência",
            "data_abertura": "Abertura",
            "contrato": "Contrato",
            "cnl": "CNL",
            "at": "AT",
            "afetacao": "Afetação",
            "vip": "VIP",
            "cond_alto_valor": "Cond. Alto Valor",
            "b2b_avancado": "B2B",
            "tecnicos": "Técnicos",
            "origem": "Origem",
            "cabo": "Cabo",
            "primarias": "Primárias",
            "bd": "BD",
            "propenso_anatel": "Propensos - Anatel",
            "reclamado_anatel": "Reclamados - Anatel",
            "reincidencia": "Reincidência",
        }
        df_api.rename(columns=rename_map, inplace=True)

        if "Reincidência" in df_api.columns:

            def format_reinc(x):
                try:
                    if pd.isna(x) or str(x).strip() in ["", "nan", "None"]:
                        return ""
                    return str(int(float(x)))
                except:
                    return ""

            df_api["Reincidência"] = df_api["Reincidência"].apply(format_reinc)
        else:
            df_api["Reincidência"] = ""

        if "equipamentos" in df_api.columns:
            df_api["Cabo/Primária"] = df_api["equipamentos"].apply(
                lambda x: (
                    str(x[0]).strip() if isinstance(x, list) and len(x) > 0 else "-"
                )
            )
        else:
            df_api["Cabo/Primária"] = "-"

        df_api["Abertura_dt"] = pd.to_datetime(df_api["Abertura"], errors="coerce")

        if "Técnicos" in df_api.columns:
            logger.info("rodei")
            df_api["Técnicos"] = df_api["Técnicos"].apply(
                lambda x: len(x) if isinstance(x, list) else 0
            )

        if "Afetação" in df_api.columns:
            df_api["Afetação"] = (
                pd.to_numeric(df_api["Afetação"], errors="coerce").fillna(0).astype(int)
            )

        def formatar_flag(val):
            if pd.isna(val):
                return "NÃO"
            s = str(val).upper().strip()
            if s in ["TRUE", "SIM", "S", "YES"]:
                return "SIM"
            try:
                return "SIM" if float(val) > 0 else "NÃO"
            except:
                return "NÃO"

        for col in ["VIP", "Cond. Alto Valor", "B2B"]:
            if col in df_api.columns:
                df_api[col] = df_api[col].apply(formatar_flag)

        if "municipio" in df_api.columns:
            df_api.rename(columns={"municipio": "Cidade_Real"}, inplace=True)

        logger.info(df_api.columns)

        return df_api, None

    @st.cache_data(ttl=300, show_spinner=False)
    def carregar_dados_ofensores(contrato_ofensor, range=30):
        """Carrega a lista de ofensores da API, com cache de 5 minutos."""
        if not API_URL_OFENSORES:
            return None, "URL de Ofensores não configurada no secrets.toml."
        try:
            response = requests.get(
                API_URL_OFENSORES,
                params={"contrato": contrato_ofensor, "range": range},
                # headers=API_HEADERS,
                timeout=25,
            )

            if response.status_code == 200:
                return response.json(), None
            return None, f"Erro {response.status_code}"
        except Exception as e:
            logger.error(f"Erro ao carregar dados de ofensores: {e!s}")
            return None, str(e)

    def processar_json_ofensores(
        dados_json, at_sel: list[str] | None = None
    ) -> pd.DataFrame:
        """Processa a estrutura JSON dos ofensores e retorna um DataFrame formatado."""
        linhas = []

        for item in dados_json:
            if (
                at_sel is not None
                and isinstance(at_sel, list)
                and at_sel != [""]
                and item.get("ocorrencias")[0].get("at") not in at_sel
            ):
                continue
            cod_primaria = item.get("primaria", "")
            volume = item.get("count", 0)
            linhas.append(
                {
                    "Primária": cod_primaria,
                    "Município": item.get("ocorrencias")[0].get("municipio", ""),
                    "Volume (Falhas)": volume,
                    "Ocorrências": ", ".join(
                        [
                            str(dado.get("id_ocorrencia"))
                            for dado in item.get("ocorrencias", [])
                        ]
                    ),
                }
            )

        if linhas:
            return pd.DataFrame(linhas).sort_values(
                by="Volume (Falhas)", ascending=False
            )

        return pd.DataFrame()

    def processar_dados(df_raw, filtros_contrato):
        agora = datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)

        df = df_raw.copy()

        df["Contrato_Padrao"] = df["Contrato"].astype(str).str.strip().str.upper()
        if isinstance(filtros_contrato, str):
            df = df[df["Contrato_Padrao"] == filtros_contrato.upper()].copy()
        elif isinstance(filtros_contrato, list) and filtros_contrato:
            df = df[
                df["Contrato_Padrao"].isin([c.upper() for c in filtros_contrato])
            ].copy()

        df["Abertura_dt"] = pd.to_datetime(
            df["Abertura"], errors="coerce"
        ).dt.tz_localize(None)
        df["diff_s"] = (agora - df["Abertura_dt"]).dt.total_seconds().clip(lower=0)
        df["horas_float"] = df["diff_s"] / 3600

        def formatar_hms(s):
            val = int(s) if pd.notna(s) else 0
            m, s_res = divmod(val, 60)
            h, m_res = divmod(m, 60)
            return f"{int(h):02d}:{int(m_res):02d}:{int(s_res):02d}"

        df["Horas Corridas"] = df["diff_s"].apply(formatar_hms)

        def calc_sla_status(row):
            h = row["horas_float"]
            is_b2b = str(row.get("B2B", "NÃO")).upper() == "SIM"
            limite_fora = 4 if is_b2b else 8
            if h > 24:
                return "Crítico"
            elif h > limite_fora:
                return "Fora do Prazo"
            else:
                return "No Prazo"

        df["Status SLA"] = df.apply(calc_sla_status, axis=1)

        # --- NOVA REGRA DE ANTECIPAÇÃO E COBRANÇA DA EPS ---
        def calc_criticidade_eps(row):
            h = row["horas_float"]
            if h >= 7:
                return "🚨 E-MAIL(EPS)"
            elif h >= 6:
                return "🟠 GERÊNCIA(EPS)"
            elif h >= 4:
                return "🟡 COORDENADOR (EPS)"
            else:
                return "🟢 SUPERVISOR (EPS)"

        df["Criticidade EPS"] = df.apply(calc_criticidade_eps, axis=1)

        def def_area(row):
            if str(row["Contrato_Padrao"]) == "ABILITY_SJ" and pd.notna(row.get("AT")):
                return (
                    "Litoral"
                    if str(row["AT"]).split("-")[0].strip().upper()
                    in [
                        "TG",
                        "PG",
                        "LZ",
                        "MK",
                        "MG",
                        "PN",
                        "AA",
                        "BV",
                        "FM",
                        "RP",
                        "AC",
                        "FP",
                        "BA",
                        "TQ",
                        "BO",
                        "BU",
                        "BC",
                        "PJ",
                        "PB",
                        "MR",
                        "MA",
                    ]
                    else "Vale"
                )
            return "Geral"

        df["Area"] = df.apply(def_area, axis=1)

        return df.sort_values("horas_float", ascending=False)

    def gerar_texto_gv(row, contrato):
        try:
            dt = row["Abertura_dt"].strftime("%d/%m/%Y")
        except:
            dt = ""
        try:
            hr = row["Abertura_dt"].strftime("%H:%M")
        except:
            hr = ""

        def get_val(col, default=""):
            val = row.get(col)
            return (
                str(val).strip()
                if pd.notna(val)
                and str(val).strip() != ""
                and str(val).strip() != "nan"
                else default
            )

        return f"""✅ *INFORMATIVO GRANDE VULTO*

    *{contrato}*

    {get_val("Ocorrência")} - FTTx
    ORIGEM: {get_val("Origem")}
    AT: {get_val("AT")}
    CIDADE: {get_val("Cidade_Real")}
    QUANT. PRIMÁRIAS AFETADAS: {get_val("Primárias")}
    CABO: {get_val("Cabo")}
    AFETAÇÃO: {int(row.get("Afetação", 0))}
    BDs: {get_val("BD")}
    CRIAÇÃO: {dt}
    HORA: {hr}
    PROPENSOS-ANATEL: {get_val("Propensos - Anatel")}
    RECLAMADOS-ANATEL: {get_val("Reclamados - Anatel")}
    CLIENTE VIP:  {get_val("VIP", "NÃO")}
    CLIENTE B2B:  {get_val("B2B", "NÃO")}
    COND. ALTO VALOR: {get_val("Cond. Alto Valor", "NÃO")}
    DEFEITO:
    PRAZO:"""

    def gerar_cards_mpl(kpis, contrato):
        import matplotlib.pyplot as plt

        C_BG, C_BORDER, C_TEXT, C_LABEL = "#ffffff", "#e2e8f0", "#1e293b", "#64748b"
        C_RED, C_YELLOW, C_GREEN = "#dc2626", "#d97706", "#16a34a"
        h_tot = 14 if contrato == "ABILITY_SJ" else 11
        fig, ax = plt.subplots(figsize=(12, h_tot), dpi=200)
        fig.patch.set_facecolor(C_BG)
        ax.axis("off")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)

        def draw(x, y, w, h, t, v, col=C_TEXT):
            ax.add_patch(
                patches.FancyBboxPatch(
                    (x, y),
                    w,
                    h,
                    boxstyle="round,pad=0,rounding_size=3",
                    fc="white",
                    ec=C_BORDER,
                    lw=2,
                )
            )
            ax.text(
                x + w / 2,
                y + h * 0.8,
                t.upper(),
                ha="center",
                size=18,
                color=C_LABEL,
                weight="bold",
            )
            ax.text(
                x + w / 2,
                y + h * 0.4,
                str(v),
                ha="center",
                size=55,
                color=col,
                weight="black",
            )

        ax.text(
            50, 96, "SIGMA OPS", ha="center", size=32, weight="black", color="#7c3aed"
        )
        ax.text(
            50,
            92,
            f"{contrato} • {datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%H:%M')}",
            ha="center",
            size=22,
            weight="bold",
            color="#475569",
        )
        draw(2, 68, 46, 18, "Total", kpis["total"])
        draw(52, 68, 46, 18, "S/ Técnico", kpis["sem_tec"])
        w = 30
        g = 3
        draw(2, 42, w, 18, "Crítico", kpis["critico"], C_RED)
        draw(2 + w + g, 42, w, 18, "Fora do Prazo", kpis["fora"], C_YELLOW)
        draw(2 + 2 * (w + g), 42, w, 18, "No Prazo", kpis["no_prazo"], C_GREEN)
        if contrato == "ABILITY_SJ":
            draw(2, 16, 46, 18, "Litoral", kpis["lit"])
            draw(52, 16, 46, 18, "Vale", kpis["vale"])
        buf = io.BytesIO()
        plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG)
        plt.close(fig)
        return buf.getvalue()

    def gerar_lista_mpl_from_view(df_view, col_order, contrato):
        import matplotlib.pyplot as plt

        ITENS_POR_PAGINA = 20
        cols = [
            c
            for c in col_order
            if c in df_view.columns
            and c not in ["horas_float", "Status SLA", "Criticidade EPS"]
        ]

        df_p = (
            df_view[cols]
            .copy()
            .rename(
                columns={
                    "Ocorrência": "ID",
                    "Horas Corridas": "Tempo",
                    "Cond. Alto Valor": "A.V",
                    "Cabo/Primária": "Cabo/Prim.",
                    "Reincidência": "Reinc.",
                    "Afetação": "Afet.",
                    "Técnicos": "Téc.",
                }
            )
        )

        lista_imagens = []
        total_linhas = len(df_p)
        if total_linhas == 0:
            return lista_imagens

        num_paginas = (total_linhas + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA

        for i in range(num_paginas):
            inicio = i * ITENS_POR_PAGINA
            fim = inicio + ITENS_POR_PAGINA
            df_chunk = df_p.iloc[inicio:fim]
            idx_chunk = df_view.iloc[inicio:fim]

            fig, ax = plt.subplots(
                figsize=(17, max(4, 3 + len(df_chunk) * 0.8)), dpi=180
            )
            ax.axis("off")
            fig.patch.set_facecolor("white")

            titulo = f"SIGMA OPS: {contrato}\n{datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m • %H:%M')}"
            if num_paginas > 1:
                titulo += f" (Pág {i + 1}/{num_paginas})"

            plt.title(
                titulo,
                loc="center",
                pad=40,
                fontsize=28,
                weight="black",
                color="#1e293b",
            )
            tbl = ax.table(
                cellText=df_chunk.values.tolist(),
                colLabels=df_chunk.columns,
                cellLoc="center",
                loc="center",
            )

            tbl.auto_set_font_size(False)
            tbl.set_fontsize(11)
            tbl.scale(1.0, 3.0)

            for j in range(len(df_chunk.columns)):
                tbl[(0, j)].set_facecolor("#7c3aed")
                tbl[(0, j)].set_text_props(color="white", weight="bold")

            for r_idx in range(len(df_chunk)):
                row_orig = idx_chunk.iloc[r_idx]
                h = row_orig.get("horas_float", 0)
                is_b2b = str(row_orig.get("B2B", "NÃO")).upper() == "SIM"
                limite_fora = 4 if is_b2b else 8

                c = "#16a34a"
                if h > 24:
                    c = "#dc2626"
                elif h > limite_fora:
                    c = "#d97706"

                if row_orig.get("Afetação", 0) >= 100:
                    c = "#2563eb"

                for j in range(len(df_chunk.columns)):
                    tbl[(r_idx + 1, j)].set_text_props(color=c, weight="bold")
                    tbl[(r_idx + 1, j)].set_edgecolor("#e2e8f0")

            buf = io.BytesIO()
            plt.savefig(
                buf, format="jpg", dpi=180, bbox_inches="tight", facecolor="white"
            )
            plt.close(fig)
            lista_imagens.append(buf.getvalue())
        return lista_imagens

    def gerar_dashboard_gerencial(df_geral, contratos_list):
        import matplotlib.pyplot as plt

        df_filtrado = df_geral.copy()
        resumo = (
            df_filtrado.groupby("Contrato_Padrao")
            .agg(
                Total=("Ocorrência", "count"),
                No_Prazo=("Status SLA", lambda x: (x == "No Prazo").sum()),
                Fora_Prazo=("Status SLA", lambda x: (x == "Fora do Prazo").sum()),
                Grandes_Vultos=("Afetação", lambda x: (x >= 100).sum()),
                VIPs=("VIP", lambda x: (x == "SIM").sum()),
                Cond_Alto_Valor=("Cond. Alto Valor", lambda x: (x == "SIM").sum()),
                B2B=("B2B", lambda x: (x == "SIM").sum()),
                Criticos=("Status SLA", lambda x: (x == "Crítico").sum()),
            )
            .rename(
                columns={
                    "No_Prazo": "No Prazo",
                    "Fora_Prazo": "Fora Prazo",
                    "Grandes_Vultos": "G. Vulto",
                    "Cond_Alto_Valor": "Alto Valor",
                    "Criticos": "Críticos >24h",
                }
            )
            .reset_index()
            .sort_values("Total", ascending=False)
        )

        resumo.rename(columns={"Contrato_Padrao": "Contrato"}, inplace=True)

        fig, ax = plt.subplots(figsize=(16, max(4, 3 + len(resumo) * 0.8)), dpi=200)
        ax.axis("off")
        fig.patch.set_facecolor("white")

        hora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m • %H:%M")
        plt.title(
            f"VISÃO CLUSTER\nConsolidado SigmaOPS • {hora}",
            loc="center",
            pad=40,
            fontsize=28,
            weight="black",
            color="#1e293b",
        )

        tbl = ax.table(
            cellText=resumo.values.tolist(),
            colLabels=resumo.columns,
            cellLoc="center",
            loc="center",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(11)
        tbl.scale(1.2, 3.0)

        for (i, j), cell in tbl.get_celld().items():
            if i == 0:
                cell.set_facecolor("#7c3aed")
                cell.set_text_props(color="white", weight="bold")
            else:
                cell.set_edgecolor("#e2e8f0")
                cell.set_text_props(color="#1e293b", weight="bold")
                if i % 2 == 0:
                    cell.set_facecolor("#f8fafc")

        buf = io.BytesIO()
        plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return buf.getvalue()

    # ==============================================================================
    # 📊 CORPO DO DASHBOARD
    # ==============================================================================
    df_raw, erro = carregar_dados_api()

    if df_raw is not None:
        # --- ABAS DE PERFIS ---
        tab_cl = None
        if PERFIL in ["master", "admin"]:
            tab_op, tab_prim, tab_map, tab_cl, tab_report = st.tabs(  # tab_of
                ["Operacional", "Primaria Info", "Map", "Cluster", "Reportar Bug"]
            )
        else:
            tab_op, tab_prim, tab_map, tab_report = st.tabs(  # tab_of
                ["Operacional", "Primaria Info", "Map", "Reportar Bug"]
            )

        # --- ABA INFO DE PRIMÁRIA
        with tab_prim:
            from infrastructure.orm_api import primary_search

            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

            with col1:
                if st.text_input(
                    "Pesquisar",
                    placeholder="CNL ou AT",
                    key="primary_search",
                    label_visibility="collapsed",
                    icon="🔍",
                ):
                    pass

            with col2:
                if st.text_input(
                    "txt_cabo",
                    key="txt_cabo",
                    placeholder="CABO",
                    label_visibility="collapsed",
                ):
                    pass

            with col3:
                if st.text_input(
                    "txt_primaria",
                    key="txt_primaria",
                    placeholder="PRIMÁRIA",
                    label_visibility="collapsed",
                ):
                    pass

            with col4:
                if st.text_input(
                    "txt_municipio",
                    key="txt_municipio",
                    placeholder="MUNICÍPIO",
                    label_visibility="collapsed",
                ):
                    pass

            with col5:
                if st.button("Pesquisar", width="stretch"):
                    st.rerun()

            # dataframe das informações pesquisadas
            st.title(st.session_state["primary_search"].upper())

            if st.session_state["primary_search"]:
                try:
                    df = primary_search(
                        st.session_state["primary_search"],
                        st.session_state["txt_cabo"],
                        st.session_state["txt_primaria"],
                        st.session_state["txt_municipio"],
                    )
                    if df.height > 0:
                        st.dataframe(
                            df,
                            width="stretch",
                            hide_index=True,
                            column_config={
                                "ocorrencia": st.column_config.NumberColumn(
                                    alignment="center"
                                ),
                                "afetação": st.column_config.TextColumn(
                                    alignment="center"
                                ),
                                "data_ocorrencia": st.column_config.DateColumn(
                                    label="Data Abertura", format="DD/MM/YYYY HH:mm:ss"
                                ),
                                "data_ocorrencia_final": st.column_config.DateColumn(
                                    label="Data Fechamento",
                                    format="DD/MM/YYYY HH:mm:ss",
                                ),
                            },
                        )
                    else:
                        st.markdown("### Primária não localizada.")
                except Exception as e:
                    st.error(e)

        # --- ABA MAPS ---

        with tab_map:
            # @st.cache_data
            # def gerar_dados():
            #     base_lat, base_lon = -23.5505, -46.6333  # São Paulo
            #     num_pontos = 50

            #     lats = base_lat + np.random.uniform(-0.1, 0.1, num_pontos)
            #     lons = base_lon + np.random.uniform(-0.1, 0.1, num_pontos)
            #     intensidades = np.random.uniform(0.1, 1.0, num_pontos)  # Peso do calor

            #     df = pd.DataFrame(
            #         {"latitude": lats, "longitude": lons, "peso": intensidades}
            #     )
            #     return df

            # df_dados = gerar_dados()

            # 2. Controles na barra lateral do Streamlit
            # st.sidebar.header("Configurações do Mapa")
            # raio_calor = st.sidebar.slider(
            #     "Raio do Ponto de Calor", min_value=5, max_value=30, value=15
            # )

            # opacidade = st.sidebar.slider(
            #     "Opacidade", min_value=0.1, max_value=1.0, value=0.6
            # )

            # 3. Criar o mapa base Leaflet (centralizado em SP)
            mapa = folium.Map(
                location=[-23.5505, -46.6333], zoom_start=11, tiles="OpenStreetMap"
            )

            # 4. Preparar os dados para o plugin HeatMap do Leaflet
            # dados_calor = df_dados[["latitude", "longitude", "peso"]].values.tolist()

            # # 5. Adicionar o mapa de calor ao mapa base
            # HeatMap(
            #     data=dados_calor, radius=raio_calor, max_zoom=13, min_opacity=opacidade
            # ).add_to(mapa)

            st_folium(mapa, use_container_width=True, height=400)

        # --- ABA OPERACIONAL ---
        with tab_op:
            c_sel, c_ref = st.columns([5, 1], gap="small")
            with c_sel:
                if CONTRATOS and PERFIL not in ["master", "admin"]:
                    st.info(f"A visualizar: {CONTRATOS}")
                    contrato_atual = CONTRATOS
                else:
                    contrato_atual = st.radio(
                        "Selecione o Contrato:",
                        CONTRATOS_VALIDOS,
                        horizontal=True,
                        label_visibility="collapsed",
                    )
            with c_ref:
                if st.button("🔄 Atualizar", width="stretch"):
                    st.rerun()

            df_view = processar_dados(df_raw, contrato_atual)

            c_f1, c_f2 = st.columns(2)
            with c_f1:
                f_reg = st.multiselect("Região", df_view["Area"].unique())
            with c_f2:
                f_sla = st.multiselect("SLA", ["Crítico", "Fora do Prazo", "No Prazo"])

            if f_reg:
                df_view = df_view[df_view["Area"].isin(f_reg)]
            if f_sla:
                df_view = df_view[df_view["Status SLA"].isin(f_sla)]

            # KPIs HTML
            t = len(df_view)
            dados = load_dminusOne(contrato_atual, API_URL_DMINUSONE)
            ocorrencias, prazo, reincidencia = 0, 0, 0
            if dados:
                ocorrencias = dados.get("ocorrencias")
                prazo = dados.get("prazo")
                reincidencia = dados.get("reincidencia")

            k = {
                "total": t,
                "sem_tec": len(df_view[df_view["Técnicos"] == 0]),
                "critico": len(df_view[df_view["Status SLA"] == "Crítico"]),
                "fora": len(df_view[df_view["Status SLA"] == "Fora do Prazo"]),
                "no_prazo": len(df_view[df_view["Status SLA"] == "No Prazo"]),
                "lit": len(df_view[df_view["Area"] == "Litoral"]),
                "vale": len(df_view[df_view["Area"] == "Vale"]),
            }

            c_style = "background:white;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;padding:12px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.03);display:flex;flex-direction:column;justify-content:center;height:80px;"

            def badge(num, total, cor):
                if total == 0:
                    return ""
                return f"<span style='font-size:11px;font-weight:bold;color:{cor};background:{cor}15;padding:2px 6px;border-radius:4px;margin-left:8px;vertical-align:middle;'>{int((num / total) * 100)}%</span>"

            html = f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:15px;">
                <div style="{c_style}"><div style="font-size:11px;color:#64748b;">Total</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k["total"]}</div></div>
                <div style="{c_style}"><div style="font-size:11px;color:#64748b;">S/ Técnico</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k["sem_tec"]} {badge(k["sem_tec"], t, "#dc2626")}</div></div>
                <div style="{c_style.replace("#7c3aed", "#dc2626")}"><div style="font-size:11px;color:#64748b;">Crítico (>24h)</div><div style="font-size:18px;font-weight:800;color:#dc2626;">{k["critico"]} {badge(k["critico"], t, "#dc2626")}</div></div>
                <div style="{c_style.replace("#7c3aed", "#d97706")}"><div style="font-size:11px;color:#64748b;">Fora Prazo</div><div style="font-size:18px;font-weight:800;color:#d97706;">{k["fora"]} {badge(k["fora"], t, "#d97706")}</div></div>
                <div style="{c_style.replace("#7c3aed", "#16a34a")}"><div style="font-size:11px;color:#64748b;">No Prazo</div><div style="font-size:18px;font-weight:800;color:#16a34a;">{k["no_prazo"]} {badge(k["no_prazo"], t, "#16a34a")}</div></div>"""

            if contrato_atual == "ABILITY_SJ":
                html += f"""<div style="{c_style}"><div style="font-size:11px;color:#64748b;">Litoral</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k["lit"]} {badge(k["lit"], t, "#7c3aed")}</div></div><div style="{c_style}"><div style="font-size:11px;color:#64748b;">Vale</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{k["vale"]} {badge(k["vale"], t, "#7c3aed")}</div></div>"""
            html += f"""
            <div style="{c_style.replace("#7c3aed", "#b60098")}"><div style="font-size:11px;color:#B60098;">Ocorrências D-1</div><div style="font-size:18px;font-weight:800;color:#B60098;">{ocorrencias}</div></div>
            <div style="{c_style.replace("#7c3aed", "#b60098")}"><div style="font-size:11px;color:#B60098;">Prazo D-1</div><div style="font-size:18px;font-weight:800;color:#B60098;">{prazo} {badge(prazo, ocorrencias, "#b60098")}</div></div>
            <div style="{c_style.replace("#7c3aed", "#b60098")}"><div style="font-size:11px;color:#B60098;">Reincidência D-1</div><div style="font-size:18px;font-weight:800;color:#B60098;">{reincidencia} {badge(reincidencia, ocorrencias, "#b60098")}</div></div>
            """
            st.markdown(html + "</div>", unsafe_allow_html=True)

            gv = len(df_view[df_view["Afetação"] >= 100])
            if gv > 0:
                st.markdown(
                    f"<div class='alert-box'>🚨 {gv} GRANDE(S) VULTO(S) EM ABERTO</div>",
                    unsafe_allow_html=True,
                )
                with st.expander("Ver Detalhes GV"):
                    for _, row in df_view[df_view["Afetação"] >= 100].iterrows():
                        st.code(gerar_texto_gv(row, contrato_atual), language="text")

            with st.expander("📂 Opções de Exportação"):
                c1, container_cad_login = st.columns(2)
                try:
                    c1.download_button(
                        "Baixar Resumo",
                        gerar_cards_mpl(k, contrato_atual),
                        f"resumo_{nome_arq}.jpg",
                        "image/jpeg",
                        width="stretch",
                    )
                except:
                    pass

                cols_export = [
                    "Ocorrência",
                    "Cabo/Primária",
                    "AT",
                    "Afetação",
                    "Reincidência",
                    "Origem",
                    "Horas Corridas",
                    "Status SLA",
                    "VIP",
                    "Cond. Alto Valor",
                    "B2B",
                    "Técnicos",
                ]
                try:
                    imgs = gerar_lista_mpl_from_view(
                        df_view, cols_export, contrato_atual
                    )
                    if imgs:
                        if len(imgs) == 1:
                            container_cad_login.download_button(
                                "Baixar Lista",
                                imgs[0],
                                f"lista_{nome_arq}.jpg",
                                "image/jpeg",
                                width="stretch",
                            )
                        else:
                            for idx_img, img_bytes in enumerate(imgs):
                                container_cad_login.download_button(
                                    f"Baixar Lista (Pág {idx_img + 1})",
                                    img_bytes,
                                    f"lista_{nome_arq}_p{idx_img + 1}.jpg",
                                    "image/jpeg",
                                    width="stretch",
                                )
                except:
                    pass

            # --- EXIBIÇÃO DA TABELA HTML CENTRALIZADA COM RESPONSIVIDADE ---
            c_tab1, c_tab2 = st.columns([4, 1])
            with c_tab2:
                layout_modo = st.selectbox(
                    "📱 Visualização",
                    ["🖥️ PC (Completa)", "📱 Telemóvel (Resumida)"],
                    label_visibility="collapsed",
                )

            if "Telemóvel" in layout_modo:
                cols_visiveis = [
                    "Ocorrência",
                    "Cabo/Primária",
                    "AT",
                    "Afetação",
                    "Reincidência",
                    "Horas Corridas",
                    "Criticidade EPS",
                    "Técnicos",
                ]
                cols_ocultar_html = ["horas_float", "B2B"]
            else:
                cols_visiveis = [
                    "Ocorrência",
                    "Cabo/Primária",
                    "AT",
                    "Afetação",
                    "Horas Corridas",
                    "Reincidência",
                    "Origem",
                    "Status SLA",
                    "Criticidade EPS",
                    "VIP",
                    "Cond. Alto Valor",
                    "B2B",
                    "Técnicos",
                ]
                cols_ocultar_html = ["horas_float"]

            cols_logica = list(dict.fromkeys(cols_visiveis + cols_ocultar_html))
            c_final = [c for c in cols_logica if c in df_view.columns]

            df_tela = df_view[c_final]

            dict_renomear = {
                "Ocorrência": "ID",
                "Cabo/Primária": "Cabo/Prim.",
                "Afetação": "Afet.",
                "Reincidência": "Reinc.",
                "Horas Corridas": "Tempo",
                "Status SLA": "SLA",
                "Criticidade EPS": "Nível  Escalonamento",
                "Cond. Alto Valor": "A.V",
                "Técnicos": "Téc.",
            }
            df_tela.rename(columns=lambda x: dict_renomear.get(x, x), inplace=True)

            def highlight_rows_tela(row):
                h = row.get("horas_float", 0)  # checkpoint
                is_b2b = str(row.get("B2B", "NÃO")).upper() == "SIM"
                limite_fora = 4 if is_b2b else 8

                tc = "#16a34a"
                if h > 24:
                    tc = "#dc2626"
                elif h > limite_fora:
                    tc = "#d97706"

                if row.get("Afet.", 0) >= 100:
                    tc = "#2563eb"

                styles = []
                for col in row.index:
                    val = str(row[col]).upper().strip()
                    cell_style = (
                        f"color: {tc}; text-align: center !important; font-weight: 700;"
                    )

                    # --- ESTILIZAÇÃO DO BADGE DE CRITICIDADE ---
                    if col == "Criticidade":
                        if "E-MAIL" in val:
                            cell_style = "background-color: #fee2e2; color: #991b1b; font-weight: 900; border-radius: 4px;"
                        elif "COORDENADOR" in val:
                            cell_style = "background-color: #ffedd5; color: #c2410c; font-weight: 800; border-radius: 4px;"
                        elif "SUPERVISOR" in val:
                            cell_style = "background-color: #fef9c3; color: #a16207; font-weight: 800; border-radius: 4px;"
                        else:
                            cell_style = "background-color: #dcfce7; color: #15803d; font-weight: 700; border-radius: 4px;"

                    elif col == "VIP" and val == "SIM":
                        cell_style += "background-color: #f5d0fe; color: #86198f;"
                    elif col == "A.V" and val == "SIM":
                        cell_style += "background-color: #d9f99d; color: #365314;"
                    elif col == "B2B" and val == "SIM":
                        cell_style += "background-color: #ddd6fe; color: #5b21b6;"
                    styles.append(cell_style)
                return styles

            ocultar_final = [
                dict_renomear.get(c, c)
                for c in cols_ocultar_html
                if c in df_view.columns
            ]

            tabela_html = (
                df_tela.style.apply(highlight_rows_tela, axis=1)
                .set_table_attributes(
                    'style="width:100%; border-collapse: collapse; font-family: Inter, sans-serif;"'
                )
                .set_table_styles(
                    [
                        {
                            "selector": "th",
                            "props": [
                                ("text-align", "center"),
                                ("background-color", "#f1f5f9"),
                                ("color", "#475569"),
                                ("padding", "10px"),
                                ("border-bottom", "2px solid #e2e8f0"),
                                ("font-size", "13px"),
                            ],
                        },
                        {
                            "selector": "td",
                            "props": [
                                ("text-align", "center"),
                                ("padding", "8px"),
                                ("border-bottom", "1px solid #f8fafc"),
                                ("font-size", "12px"),
                            ],
                        },
                    ]
                )
                .hide(axis="index")
                .hide(subset=list(ocultar_final), axis="columns")
                .to_html()
            )

            with st.container(height=600, border=False):
                st.markdown(tabela_html, unsafe_allow_html=True)

        # --- ABA CLUSTER ---
        if tab_cl:
            with tab_cl:
                with st.form("form_cluster"):
                    c1, container_cad_login = st.columns([5, 1])
                    with c1:
                        sels = st.multiselect(
                            "Contratos:", CONTRATOS_VALIDOS, default=CONTRATOS_VALIDOS
                        )
                    with container_cad_login:
                        st.write("")
                        st.write("")
                        st.form_submit_button("Atualizar Visão", width="stretch")

                if sels:
                    df_cl = processar_dados(df_raw, sels)

                    t_g = len(df_cl)
                    t_gv = len(df_cl[df_cl["Afetação"] >= 100])
                    c_ok = len(df_cl[df_cl["Status SLA"] == "No Prazo"])
                    c_fora = len(df_cl[df_cl["Status SLA"] == "Fora do Prazo"])
                    c_crit = len(df_cl[df_cl["Status SLA"] == "Crítico"])

                    def badge_cl(num, total, cor):
                        if total == 0:
                            return ""
                        return f"<span style='font-size:10px;font-weight:bold;color:{cor};background:{cor}15;padding:2px 6px;border-radius:4px;margin-left:5px;vertical-align:middle;'>{(num / total * 100):.0f}%</span>"

                    h_cl = f"""<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:15px;">
                        <div style="{c_style}"><div style="font-size:11px;color:#64748b;">Total Geral</div><div style="font-size:18px;font-weight:800;color:#0f172a;">{t_g}</div></div>
                        <div style="{c_style.replace("#7c3aed", "#d97706")}"><div style="font-size:11px;color:#64748b;">GV</div><div style="font-size:18px;font-weight:800;color:#d97706;">{t_gv} {badge_cl(t_gv, t_g, "#d97706")}</div></div>
                        <div style="{c_style.replace("#7c3aed", "#16a34a")}"><div style="font-size:11px;color:#64748b;">No Prazo</div><div style="font-size:18px;font-weight:800;color:#16a34a;">{c_ok} {badge_cl(c_ok, t_g, "#16a34a")}</div></div>
                        <div style="{c_style.replace("#7c3aed", "#d97706")}"><div style="font-size:11px;color:#64748b;">Fora Prazo</div><div style="font-size:18px;font-weight:800;color:#d97706;">{c_fora} {badge_cl(c_fora, t_g, "#d97706")}</div></div>
                        <div style="{c_style.replace("#7c3aed", "#dc2626")}"><div style="font-size:11px;color:#64748b;">Críticos (>24h)</div><div style="font-size:18px;font-weight:800;color:#dc2626;">{c_crit} {badge_cl(c_crit, t_g, "#dc2626")}</div></div>
                    </div>"""
                    st.markdown(h_cl, unsafe_allow_html=True)

                    with st.expander("Descarregar Imagem"):
                        if st.button("Gerar Dashboard"):
                            try:
                                st.download_button(
                                    "Download",
                                    gerar_dashboard_gerencial(df_cl, sels),
                                    f"cluster_{nome_arq}.jpg",
                                    "image/jpeg",
                                )
                            except:
                                pass

                    resumo = (
                        df_cl.groupby("Contrato_Padrao")
                        .agg(
                            Total=("Ocorrência", "count"),
                            No_Prazo=("Status SLA", lambda x: (x == "No Prazo").sum()),
                            Fora_Prazo=(
                                "Status SLA",
                                lambda x: (x == "Fora do Prazo").sum(),
                            ),
                            Grandes_Vultos=("Afetação", lambda x: (x >= 100).sum()),
                            VIPs=("VIP", lambda x: (x == "SIM").sum()),
                            Cond_Alto_Valor=(
                                "Cond. Alto Valor",
                                lambda x: (x == "SIM").sum(),
                            ),
                            B2B=("B2B", lambda x: (x == "SIM").sum()),
                            Criticos=("Status SLA", lambda x: (x == "Crítico").sum()),
                        )
                        .rename(
                            columns={
                                "No_Prazo": "No Prazo",
                                "Fora_Prazo": "Fora Prazo",
                                "Grandes_Vultos": "Grandes Vultos",
                                "Criticos": "Críticos (>24h)",
                            }
                        )
                        .reset_index()
                        .sort_values("Total", ascending=False)
                    )

                    st.dataframe(resumo, width="stretch", hide_index=True)
                else:
                    st.warning("Selecione pelo menos um contrato.")

        with tab_report:
            st.markdown(
                "<h3 style='color:#1e293b;'>Reportar Bugs e Sugestões</h3>",
                unsafe_allow_html=True,
            )

            if "feedback_enviado" in st.session_state:
                st.success("Obrigado pelo seu feedback!")
                st.session_state.pop("feedback_enviado", None)
                c1, container_cad_login, c3 = st.columns([2, 1, 2])
                with container_cad_login:
                    if st.button("Enviar outro feedback", width="stretch"):
                        st.rerun()
            else:
                st.markdown(
                    "Reporte um problema ou sugestão através do formulário abaixo."
                )
                with st.form("form_report"):
                    tipo = st.selectbox(
                        "Tipo de Feedback",
                        ["Bug", "Sugestão de Melhoria"],
                        label_visibility="collapsed",
                    )
                    descricao = st.text_area(
                        "Descreva o problema ou sugestão com detalhes:",
                        placeholder="Descrição do problema \\ Sugestão.",
                        height=150,
                    )
                    contato = st.text_input(
                        "Seu email (opcional, para retorno):",
                        placeholder="Exemplo: seu.email@exemplo.com",
                        value=st.session_state.get("email", ""),
                    )
                    submit = st.form_submit_button("Enviar Feedback")
                    if submit:
                        try:
                            if descricao.strip():
                                reports.save_feedback(tipo, descricao, contato)
                                st.session_state["feedback_enviado"] = True
                                st.rerun()
                            else:
                                st.error(
                                    "Por favor, descreva o problema ou sugestão antes de enviar."
                                )
                        except Exception as e:
                            st.error(
                                "Ocorreu um erro ao enviar seu feedback. Por favor, tente novamente mais tarde."
                            )
                            logger.error(f"Erro ao salvar feedback: {e}")
    else:
        st.error("Erro ao carregar dados.")
