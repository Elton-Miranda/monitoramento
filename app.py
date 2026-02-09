import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import os
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- Configuração da Página ---
st.set_page_config(page_title="Monitoramento Operacional", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

# --- CSS VISUAL ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }

    /* ABAS */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #fff; border-radius: 4px 4px 0 0; border: 1px solid #ddd; color: #666; }
    .stTabs [aria-selected="true"] { background-color: #f3e5f5; color: #660099; border-color: #660099; border-bottom: none; font-weight: bold; }

    /* BOTÕES DE CONTRATO */
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] { display: flex; flex-direction: row; flex-wrap: nowrap; overflow-x: auto; width: 100%; gap: 15px; padding-bottom: 10px; }
    div[role="radiogroup"] label {
        background-color: white !important; border: 3px solid #660099 !important; border-radius: 12px !important;
        padding: 15px 10px !important; min-width: 140px !important;
        display: flex !important; justify-content: center !important; align-items: center !important; text-align: center !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; transition: 0.3s !important; cursor: pointer !important;
    }
    div[role="radiogroup"] label p { font-size: 18px !important; font-weight: 900 !important; margin: 0 !important; color: #660099 !important; width: 100%; }
    div[role="radiogroup"] label:has(input:checked) { background-color: #660099 !important; transform: translateY(-2px); }
    div[role="radiogroup"] label:has(input:checked) p { color: #ffffff !important; }

    /* GERAL */
    div.stButton > button { background-color: white; color: #660099; border: 2px solid #660099; border-radius: 8px; font-weight: 700; width: 100%; transition: 0.3s; }
    div.stButton > button:hover { background-color: #660099; color: white; border-color: #660099; }
    [data-testid="stDownloadButton"] > button { background-color: #660099 !important; color: white !important; border: none !important; font-size: 18px !important; padding: 15px !important; }
    [data-testid="stDownloadButton"] > button:hover { background-color: #4b007d !important; }

    /* METRICAS */
    div[data-testid="stMetric"] { background-color: white; border: 2px solid #e0e0e0; padding: 10px; border-radius: 12px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.08); min-height: 160px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    div[data-testid="stMetricLabel"] { width: 100%; display: flex; justify-content: center; font-size: 1.1rem !important; font-weight: 800 !important; color: #444; }
    div[data-testid="stMetricValue"] { width: 100%; display: flex; justify-content: center; font-size: 2.5rem !important; font-weight: 900 !important; color: #000; }
    [data-testid="stMetricDelta"] { justify-content: center; font-weight: 700; }

    .status-box { padding: 15px; border-radius: 8px; margin-bottom: 20px; font-weight: bold; text-align: center; border: 1px solid #ccc; }
    .status-ok { background-color: #e8f5e9; color: #2e7d32; border-color: #c8e6c9; }
    .status-error { background-color: #ffebee; color: #c62828; border-color: #ffcdd2; font-size: 0.9em;}
    .contrato-label { font-size: 20px; font-weight: 800; color: #333; margin-bottom: 8px; margin-left: 2px; }
</style>
""", unsafe_allow_html=True)

# --- ARQUIVOS DE APOIO ---
ARQUIVO_CNL_CSV = "CNL_BASE_MONITORAMENTO.csv"
ARQUIVO_CNL_XLSX = "CNL_BASE_MONITORAMENTO.xlsx"

# --- CARREGAMENTO DE SEGREDOS ---
try:
    # Carrega a URL e os HEADERS direto do secrets.toml
    API_URL = st.secrets["api"]["url"]
    API_HEADERS = dict(st.secrets["api"]["headers"])
except Exception:
    # Se não configurado, deixa vazio para tratar na função de carga
    API_URL = ""
    API_HEADERS = {}

# --- FUNÇÕES ---

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
    if not API_URL:
        return None, "Configuração de API não encontrada no secrets.toml."

    try:
        # AQUI O CÓDIGO USA O NOVO HEADER (X-API-Key) AUTOMATICAMENTE
        response = requests.get(API_URL, headers=API_HEADERS, timeout=25)

        if response.status_code == 200:
            try:
                json_data = response.json()
            except ValueError:
                return None, f"Erro: A API não retornou um JSON válido. Resposta: {response.text[:200]}"

            if 'ocorrencias' in json_data:
                df = pd.DataFrame(json_data['ocorrencias'])

                # Mapeamento
                rename_map = {
                    'ocorrencia': 'Ocorrência', 'data_abertura': 'Data Abertura', 'contrato': 'Contrato',
                    'escritorio': 'Escritório', 'cnl': 'CNL', 'at': 'AT', 'cabo': 'Cabo',
                    'afetacao': 'Afetação', 'origem': 'Origem', 'primarias': 'Primárias', 'bd': 'BD',
                    'propenso_anatel': 'Propensos - Anatel', 'reclamado_anatel': 'Reclamados - Anatel',
                    'vip': 'VIP', 'b2b_avancado': 'B2B', 'cond_alto_valor': 'Cond. Alto Valor'
                }
                df.rename(columns=rename_map, inplace=True)

                # Técnicos e Datas
                if 'tecnicos' in json_data['ocorrencias'][0]:
                    df['Técnicos'] = df['tecnicos'].apply(lambda x: len(x) if isinstance(x, list) else 0)
                else:
                    df['Técnicos'] = 0

                df['Data Abertura'] = pd.to_datetime(df['Data Abertura'], errors='coerce')
                return df, None
            else:
                return None, "JSON inválido: Chave 'ocorrencias' não encontrada."

        elif response.status_code == 403:
            return None, "Erro 403: Acesso Negado. Verifique se a X-API-Key no secrets.toml está correta."
        elif response.status_code == 401:
            return None, "Erro 401: Não Autorizado. API Key inválida."
        else:
            return None, f"Erro na API: Status {response.status_code}"

    except Exception as e:
        return None, f"Falha na conexão: {str(e)}"

def processar_regras_generico(df_full, contratos_validos=None, filtrar_contrato=None):
    agora = datetime.now()
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
        if filtrar_contrato:
            df = df_full[df_full['Contrato_Padrao'] == filtrar_contrato].copy()
        elif contratos_validos:
            df = df_full[df_full['Contrato_Padrao'].isin(contratos_validos)].copy()
        else: return pd.DataFrame()
    else: return pd.DataFrame()

    col_abertura = cols_map.get('abertura') or cols_map.get('data abertura')
    if not col_abertura: return pd.DataFrame()

    if not pd.api.types.is_datetime64_any_dtype(df[col_abertura]):
        try: df['Abertura_dt'] = pd.to_datetime(df[col_abertura], format='%d/%m/%Y, %H:%M:%S', errors='coerce')
        except: df['Abertura_dt'] = pd.to_datetime(df[col_abertura], dayfirst=True, errors='coerce')
    else:
        df['Abertura_dt'] = df[col_abertura]

    df = df.dropna(subset=['Abertura_dt'])
    df['Abertura_dt'] = df['Abertura_dt'].dt.tz_localize(None)

    df['diff_segundos'] = (agora - df['Abertura_dt']).dt.total_seconds()
    df['horas_float'] = df['diff_segundos'] / 3600

    def formatar_hhmmss(s):
        if s < 0: return "00:00:00"
        m, s = divmod(int(s), 60); h, m = divmod(m, 60); return f"{h:02d}:{m:02d}:{s:02d}"
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
    sla_color = '#d32f2f' if h and h>24 else ('#d48806' if h and h>8 else ('#389e0d' if h else '#000'))
    val_af = None
    for k in ['Afetação', 'afetação', 'Afetacao']:
        if k in row.index:
            try: val_af = float(row[k])
            except: pass
            break
    return '#1e88e5' if val_af and val_af >= 100 else sla_color

def row_style_apply(row):
    c = estilo_tabela(row)
    return [f'color: {c}; font-weight: 800'] * len(row)

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
CLIENTE B2B:  {get_val(['B2B Avançado', 'B2B'], '00')}
COND. ALTO VALOR: {get_val(['Cond. Alto Valor'], '00')}
DEFEITO:
PRAZO:"""
    return texto

def gerar_cards_mpl(kpis, contrato):
    C_BG, C_BORDER = "#ffffff", "#dddddd"
    C_TEXT, C_LABEL, C_RED, C_YELLOW, C_GREEN = "#222222", "#555555", "#d32f2f", "#f57c00", "#2e7d32"
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

    ax.text(50, 96, "MONITORAMENTO", ha='center', fontsize=32, weight='black', color='#333')
    hora = (datetime.now() - timedelta(hours=3)).strftime("%H:%M")
    ax.text(50, 92, f"{contrato} • {hora}", ha='center', fontsize=22, weight='bold', color='#660099')

    y1 = 68; draw_card_mobile(2, y1, 46, 18, "Total", kpis['total'])
    draw_card_mobile(52, y1, 46, 18, "S/ Técnico", kpis['sem_tec'], C_TEXT, alert=(kpis['sem_tec']>0))
    y2 = 42; w = 30; g = 3
    draw_card_mobile(2, y2, w, 18, "Crítico (>24h)", kpis['sla_red'], C_RED)
    draw_card_mobile(2+w+g, y2, w, 18, "Atenção (8-24h)", kpis['sla_yellow'], C_YELLOW)
    draw_card_mobile(2+2*(w+g), y2, w, 18, "No Prazo (<8h)", kpis['sla_green'], C_GREEN)
    if tem_regiao:
        y3 = 16
        draw_card_mobile(2, y3, 46, 18, "Litoral", kpis.get('lit', 0))
        draw_card_mobile(52, y3, 46, 18, "Vale", kpis.get('vale', 0))

    ax.text(50, 2, "Gerado via Painel de Controle", ha='center', fontsize=14, color="#999")
    buf = io.BytesIO(); plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG); plt.close(fig); return buf.getvalue()

def gerar_dashboard_gerencial(df_geral, contratos_list):
    C_BG, C_BAR, C_RED, C_GREEN = "#ffffff", "#660099", "#d32f2f", "#2e7d32"
    df_filtrado = df_geral[df_geral['Contrato_Padrao'].isin(contratos_list)].copy()

    total_geral = len(df_filtrado)
    total_gv = len(df_filtrado[df_filtrado['Afetação'] >= 100])
    total_fora = len(df_filtrado[df_filtrado['horas_float'] >= 8])
    total_dentro = total_geral - total_fora

    resumo = df_filtrado.groupby('Contrato_Padrao').agg(
        Total=('Ocorrência', 'count'), Grandes_Vultos=('Afetação', lambda x: (x >= 100).sum()),
        Fora_Prazo=('horas_float', lambda x: (x >= 8).sum()), Criticos=('horas_float', lambda x: (x > 24).sum())
    ).reset_index().sort_values('Total', ascending=False)

    fig, ax = plt.subplots(figsize=(14, 12), dpi=200)
    fig.patch.set_facecolor(C_BG); ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 100)

    hora = (datetime.now() - timedelta(hours=3)).strftime("%d/%m %H:%M")
    ax.text(50, 96, "VISÃO CLUSTER", ha='center', fontsize=32, weight='black', color='#333')
    ax.text(50, 92, f"Consolidado Geral • {hora}", ha='center', fontsize=20, weight='bold', color='#660099')

    def draw_box(x, y, w, h, title, val, color, alert=False):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=2", fc="white", ec="#ccc", lw=2, zorder=2)
        ax.add_patch(rect)
        shadow = patches.FancyBboxPatch((x+0.5, y-0.5), w, h, boxstyle="round,pad=0,rounding_size=2", fc="#eee", ec="none", zorder=1)
        ax.add_patch(shadow)
        ax.text(x+w/2, y+h*0.8, title.upper(), ha='center', fontsize=14, color='#555', weight='bold', zorder=3)
        ax.text(x+w/2, y+h*0.35, str(val), ha='center', fontsize=40, color=color, weight='black', zorder=3)
        if alert:
             ax.add_patch(patches.Circle((x + w - 3, y + h - 3), 2, color=C_RED, zorder=4))
             ax.text(x + w - 3, y + h - 3, "!", color="white", fontsize=16, weight='bold', ha='center', va='center', zorder=5)

    draw_box(5, 75, 42, 12, "Total de Casos", total_geral, "#333")
    draw_box(53, 75, 42, 12, "Grandes Vultos", total_gv, C_BAR, alert=(total_gv>0))
    draw_box(5, 60, 42, 12, "Dentro do Prazo (<8h)", total_dentro, C_GREEN)
    draw_box(53, 60, 42, 12, "Fora do Prazo (>=8h)", total_fora, C_RED, alert=(total_fora>0))

    y_start = 55
    ax.text(50, y_start, "DETALHAMENTO POR CONTRATO", ha='center', fontsize=18, weight='bold', color='#333')
    colunas = ["CONTRATO", "TOTAL", "G. VULTO", "FORA PRAZO", "CRÍTICO >24H"]
    dados_tabela = [[row['Contrato_Padrao'], str(row['Total']), str(row['Grandes_Vultos']), str(row['Fora_Prazo']), str(row['Criticos'])] for _, row in resumo.iterrows()]

    tbl = ax.table(cellText=dados_tabela, colLabels=colunas, loc='center', bbox=[0.05, 0.05, 0.9, 0.45])
    tbl.auto_set_font_size(False); tbl.set_fontsize(13); tbl.scale(1, 2)
    for (i, j), cell in tbl.get_celld().items():
        if i == 0:
            cell.set_text_props(weight='bold', color='white'); cell.set_facecolor('#660099'); cell.set_edgecolor('white')
        else:
            cell.set_edgecolor('#dddddd'); cell.set_text_props(weight='bold');
            if i % 2 == 0: cell.set_facecolor('#f9f9f9')

    ax.text(50, 2, "Gerado via Painel de Controle", ha='center', fontsize=12, color="#999")
    buf = io.BytesIO(); plt.savefig(buf, format="jpg", dpi=200, bbox_inches="tight", facecolor=C_BG); plt.close(fig); return buf.getvalue()

def gerar_lista_mpl_from_view(df_view, col_order, contrato):
    ITENS_POR_PAGINA = 20; export_cols = [c for c in col_order if c != 'horas_float']
    df_p = df_view[export_cols].copy(); df_p.rename(columns={'Ocorrência':'ID', 'Horas Corridas':'Tempo'}, inplace=True)
    total_linhas = len(df_p); num_paginas = (total_linhas + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA
    lista_imagens = []

    def desenhar_pagina(df_chunk, num_pag, total_pags):
        fig_height = max(4, 3 + len(df_chunk)*0.8)
        fig, ax = plt.subplots(figsize=(14, fig_height), dpi=180)
        ax.axis('off'); fig.patch.set_facecolor('white')
        hora = (datetime.now() - timedelta(hours=3)).strftime('%d/%m • %H:%M')
        titulo = f"LISTA DE PENDÊNCIAS: {contrato}\n{hora}"
        if total_pags > 1: titulo += f"\n(Parte {num_pag}/{total_pags})"
        plt.title(titulo, loc='center', pad=40, fontsize=28, weight='black', color='#333')
        tbl = ax.table(cellText=df_chunk.values.tolist(), colLabels=df_chunk.columns, cellLoc='center', loc='center')
        tbl.auto_set_font_size(False); tbl.set_fontsize(20); tbl.scale(1.2, 3.5)
        for j in range(len(df_chunk.columns)):
            cell = tbl[(0, j)]; cell.set_facecolor('#660099'); cell.set_text_props(color='white', weight='bold'); cell.set_height(0.15)
        for i in range(len(df_chunk)):
            idx_real = df_chunk.index[i]; row_original = df_view.loc[idx_real]; c = estilo_tabela(row_original)
            for j in range(len(df_chunk.columns)):
                cell = tbl[(i+1, j)]; cell.set_text_props(color=c, weight='bold'); cell.set_edgecolor("#dddddd"); cell.set_linewidth(1.5)
        buf = io.BytesIO(); plt.savefig(buf, format='jpg', dpi=180, bbox_inches='tight', facecolor='white'); plt.close(fig); return buf.getvalue()

    for i in range(num_paginas):
        inicio = i * ITENS_POR_PAGINA; fim = inicio + ITENS_POR_PAGINA; df_chunk = df_p.iloc[inicio:fim]
        img_data = desenhar_pagina(df_chunk, i+1, num_paginas); lista_imagens.append(img_data)
    return lista_imagens

# ==============================================================================
# LÓGICA PRINCIPAL (INTERFACE)
# ==============================================================================

st.title("Monitoramento Operacional")

# 1. TENTA API (Principal)
with st.spinner("Conectando ao banco de dados..."):
    df_raw, erro_api = carregar_dados_api()

# 2. SE FALHAR API -> AVISA ERRO
if df_raw is None:
    st.sidebar.markdown(f"<div class='status-box status-error'>⚠️ API Indisponível<br><small>{erro_api}</small></div>", unsafe_allow_html=True)
    st.error(f"❌ Não foi possível carregar os dados. Erro: {erro_api}")
    if st.button("🔄 Tentar Novamente"):
        carregar_dados_api.clear()
        st.rerun()
else:
    st.sidebar.markdown(f"<div class='status-box status-ok'>🟢 Conectado via API<br><small>{datetime.now().strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Forçar Atualização"):
        carregar_dados_api.clear()
        st.rerun()

    # 3. EXIBIÇÃO
    col_contrato_raw = [c for c in df_raw.columns if str(c).lower().strip() in ['contrato', 'escritório']]
    if col_contrato_raw:
        todos_contratos = df_raw[col_contrato_raw[0]].astype(str).str.strip().str.upper().unique()
        contratos_principais = ["ABILITY_SJ", "TEL_JI", "ABILITY_OS", "TEL_INTERIOR", "TEL_PC_SC", "TELEMONT"]
        opcoes_validas = [c for c in contratos_principais if c in todos_contratos]

        if not opcoes_validas:
            st.warning("Nenhum contrato conhecido encontrado.")
        else:
            tab_op, tab_ger = st.tabs(["👷 Visão Operacional", "📊 Visão Cluster"])

            # --- ABA 1 ---
            with tab_op:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<p class='contrato-label'>Selecione o Contrato:</p>", unsafe_allow_html=True)
                contrato_selecionado = st.radio("Selecione:", opcoes_validas, horizontal=True, label_visibility="collapsed")

                df = processar_regras_generico(df_raw, filtrar_contrato=contrato_selecionado)

                if df.empty:
                    st.warning(f"Nenhum dado encontrado para {contrato_selecionado}.")
                else:
                    kpis = { 'total': len(df), 'sem_tec': len(df[df['Técnicos']==0]), 'sla_red': len(df[df['horas_float']>24]),
                             'sla_yellow': len(df[(df['horas_float']>8)&(df['horas_float']<=24)]), 'sla_green': len(df[df['horas_float']<=8]),
                             'lit': len(df[df['Area']=="Litoral"]), 'vale': len(df[df['Area']=="Vale"]) }

                    c1, c2 = st.columns(2)
                    nome_arq = (datetime.now() - timedelta(hours=3)).strftime('%H%M')
                    try:
                        img_cards = gerar_cards_mpl(kpis, contrato_selecionado)
                        c1.download_button("📸 Baixar Resumo (Cards)", img_cards, f"Resumo_{nome_arq}.jpg", "image/jpeg", use_container_width=True)
                    except Exception as e: st.error(f"Erro imagem: {e}")

                    df_gv = df[df['Afetação'] >= 100].copy()
                    if not df_gv.empty:
                        st.markdown("---")
                        st.error(f"🚨 **GRANDE VULTO IDENTIFICADO ({len(df_gv)})**")
                        with st.expander("Ver Carimbos Grande Vulto", expanded=True):
                            for idx, row in df_gv.iterrows():
                                texto_pronto = gerar_texto_gv(row, contrato_selecionado)
                                st.markdown(f"**Ocorrência: {row['Ocorrência']}**")
                                st.code(texto_pronto, language="text")
                                st.caption("👆 Use o ícone no canto superior direito para copiar.")
                                st.divider()
                    st.divider()

                    st.subheader("Visão Geral")
                    m1, m2 = st.columns(2, gap="medium")
                    m1.metric("Total Aberto", kpis['total'])
                    delta_txt = "⚠️ Alerta" if kpis['sem_tec'] > 0 else "Ok"
                    m2.metric("Sem Técnico", kpis['sem_tec'], delta=delta_txt, delta_color="inverse")

                    st.subheader("SLA")
                    s1, s2, s3 = st.columns(3, gap="medium")
                    s1.metric("Crítico (>24h)", kpis['sla_red'])
                    s2.metric("Fora do Prazo (8-24h)", kpis['sla_yellow'])
                    s3.metric("No Prazo (<8h)", kpis['sla_green'])

                    if contrato_selecionado == 'ABILITY_SJ':
                        st.subheader("Região")
                        r1, r2 = st.columns(2, gap="medium"); r1.metric("Litoral", kpis['lit']); r2.metric("Vale", kpis['vale'])

                    st.divider()
                    col_f1, col_f2 = st.columns(2)
                    if contrato_selecionado == 'ABILITY_SJ':
                        f_area = col_f1.multiselect("Filtrar Área", df['Area'].unique(), placeholder="Selecione...")
                    else: col_f1.info("Filtro de região indisponível."); f_area = []
                    f_sla = col_f2.multiselect("Filtrar SLA", ["Crítico", "Atenção", "No Prazo"], placeholder="Selecione...")

                    df_show = df.copy()
                    if f_area: df_show = df_show[df_show['Area'].isin(f_area)]
                    if f_sla: df_show = df_show[df_show['Status SLA'].isin(f_sla)]
                    if 'AT' in df_show.columns: df_show['AT'] = df_show['AT'].astype(str).str[:2]

                    cols_exist = [c for c in ['Ocorrência', 'Area', 'AT', 'Afetação', 'Status SLA', 'Horas Corridas', 'Técnicos', 'horas_float'] if c in df_show.columns]
                    styler = df_show[cols_exist].style.apply(row_style_apply, axis=1).set_properties(**{'font-size': '16px', 'font-weight': '600'})
                    st.dataframe(styler, height=600, use_container_width=True, column_config={"Ocorrência": st.column_config.TextColumn("ID", width="medium"), "Afetação": st.column_config.NumberColumn("Afet.", format="%.0f"), "horas_float": None})

                    try:
                        cols_exp = [c for c in cols_exist if c != 'horas_float']
                        lista_imagens = gerar_lista_mpl_from_view(df_show, cols_exp, contrato_selecionado)
                        if len(lista_imagens) == 1:
                            c2.download_button("📄 Baixar Lista", lista_imagens[0], f"Lista_{nome_arq}.jpg", "image/jpeg", use_container_width=True)
                        else:
                            st.caption("Lista extensa dividida em partes:")
                            for idx_img, img_data in enumerate(lista_imagens):
                                c2.download_button(f"📄 Baixar Lista (Parte {idx_img + 1})", img_data, f"Lista_{nome_arq}_Parte_{idx_img + 1}.jpg", "image/jpeg", use_container_width=True)
                    except Exception as e: st.error(f"Erro lista: {e}")

            # --- ABA 2 ---
            with tab_ger:
                st.markdown("<br>", unsafe_allow_html=True)
                st.header("📊 Painel Executivo Consolidado")
                df_geral = processar_regras_generico(df_raw, contratos_validos=opcoes_validas)
                if not df_geral.empty:
                    total_geral = len(df_geral); total_gv = len(df_geral[df_geral['Afetação'] >= 100])
                    total_fora = len(df_geral[df_geral['horas_float'] >= 8]); total_dentro = total_geral - total_fora

                    g1, g2 = st.columns(2); g1.metric("Total de Casos", total_geral); g2.metric("Grandes Vultos (>100)", total_gv, delta="Atenção" if total_gv > 0 else "Normal", delta_color="inverse")
                    g3, g4 = st.columns(2); g3.metric("Dentro do Prazo (<8h)", total_dentro); g4.metric("Fora do Prazo (>=8h)", total_fora, delta="Crítico" if total_fora > 0 else "Ok", delta_color="inverse")

                    st.divider()
                    try:
                        img_dashboard = gerar_dashboard_gerencial(df_geral, opcoes_validas)
                        st.download_button(label="📸 BAIXAR DASHBOARD CLUSTER (IMAGEM)", data=img_dashboard, file_name=f"Dashboard_Cluster_{nome_arq}.jpg", mime="image/jpeg", use_container_width=True, type="primary")
                    except Exception as e: st.error(f"Erro ao gerar dashboard: {e}")

                    st.divider(); st.subheader("Detalhamento por Contrato")
                    resumo = df_geral.groupby('Contrato_Padrao').agg(
                        Total=('Ocorrência', 'count'), Grandes_Vultos=('Afetação', lambda x: (x >= 100).sum()),
                        Fora_do_Prazo=('horas_float', lambda x: (x >= 8).sum()), Criticos=('horas_float', lambda x: (x > 24).sum())
                    ).reset_index().sort_values('Total', ascending=False)
                    styler_resumo = resumo.style.set_properties(**{'font-size': '18px', 'height': '40px'})
                    st.dataframe(styler_resumo, use_container_width=True, hide_index=True, column_config={
                        "Contrato_Padrao": st.column_config.TextColumn("Contrato"), "Grandes_Vultos": st.column_config.NumberColumn("GV (>100)", format="%d 🚨"),
                        "Fora_do_Prazo": st.column_config.NumberColumn("Fora do Prazo (>=8h)", format="%d ⚠️"), "Criticos": st.column_config.NumberColumn("Críticos (>24h)", format="%d 🛑")
                    })
                else: st.info("Nenhum dado encontrado nos contratos monitorados.")
    else: st.error("Colunas de Contrato não encontradas na API.")
