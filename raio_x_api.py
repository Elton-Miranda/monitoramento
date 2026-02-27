import sys

# guard before importing Streamlit to avoid warnings when running the file
# directly with `python` instead of `streamlit run`.
from streamlit.runtime.scriptrunner import get_script_run_ctx
if get_script_run_ctx() is None:
    print("This app must be launched with `streamlit run raio_x_api.py`")
    sys.exit(0)

import streamlit as st
import pandas as pd
import requests

# ==============================================================================
# ⚙️ CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Raio-X da API (Busca Avançada)", page_icon="🔍", layout="wide")

st.title("📡 Raio-X: Busca por Equipamentos, Arquivos e Primárias")

try:
    URL = st.secrets["api"]["url"]
    HEADERS = dict(st.secrets["api"].get("headers", {}))
except Exception as e:
    st.error("❌ Erro ao carregar secrets.toml. Verifique suas configurações.")
    st.stop()

st.info(f"Conectando a: `{URL}`")

# ==============================================================================
# 📡 FUNÇÃO DE DOWNLOAD
# ==============================================================================
@st.cache_data(ttl=60)
def fetch_data():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Erro {response.status_code}: {response.text}"
    except Exception as e:
        return None, str(e)

with st.spinner("Baixando dados..."):
    data, erro = fetch_data()

# ==============================================================================
# 📊 RENDERIZAÇÃO NA TELA
# ==============================================================================
if erro:
    st.error(f"❌ Falha de conexão: {erro}")
elif data:
    st.success("✅ Sucesso! Dados recebidos.")
    
    if 'ocorrencias' in data:
        df = pd.DataFrame(data['ocorrencias'])
        
        c1, c2 = st.columns([1, 2.5])
        
        with c1:
            st.subheader("🔍 Colunas Reais")
            colunas_ordenadas = sorted(df.columns)
            st.code("\n".join([f"-> {col}" for col in colunas_ordenadas]))
            
        with c2:
            st.subheader("🧪 Detetive de Dados")
            st.markdown("Procurando colunas que possam conter o `ocorrencia_eq.txt` ou a `primária`...")
            
            # --- REDE DE CAPTURA AMPLIADA ---
            # Aqui colocamos tudo que pode ser uma pista de onde está o arquivo ou texto
            palavras_chave = [
                'cabo', 'cab', 'primari', 'pri', 
                'eq', 'equip', 'equipamento', 
                'txt', 'arq', 'arquivo', 'file', 
                'desc', 'obs', 'log', 'historico', 'texto'
            ]
            
            colunas_encontradas = [
                c for c in df.columns 
                if any(chave in str(c).lower().replace('á', 'a').replace('ã', 'a') for chave in palavras_chave)
            ]
            
            if colunas_encontradas:
                st.success(f"Encontradas {len(colunas_encontradas)} colunas suspeitas!")
                # Mostra o conteúdo para você ler e ver se é o texto do TXT
                st.dataframe(df[colunas_encontradas].head(15), width='stretch')
                
                st.markdown("**Valores únicos / Exemplos de preenchimento:**")
                for col in colunas_encontradas:
                    # Pega os primeiros 100 caracteres para não quebrar a tela se o texto do txt for gigante
                    valores_unicos = df[col].dropna().astype(str).str[:100].unique()
                    st.caption(f"**{col}**: `{', '.join(valores_unicos[:5])}...`")
            else:
                st.warning("⚠️ Nenhuma coluna suspeita encontrada.")
                
        st.divider()
        
        st.subheader("🗂️ Amostra Completa (Olhe todas as colunas para ter certeza)")
        st.dataframe(df.head(20), width='stretch')
        
    else:
        st.error("❌ O JSON não tem a chave 'ocorrencias'.")