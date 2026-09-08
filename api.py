import pandas as pd
import streamlit as st

from os import getenv
from loguru import logger
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


@st.cache_resource
def open_connection():
    url = getenv("DBURL", "")
    engine = create_engine(url, echo=False)
    return engine


def primary_search(primaria: str):
    try:
        engine = open_connection()
        query = text("""
        SELECT
            p.cod_primaria,
            p.id_ocorrencia,
            o.afetacao,
            o.data_ocorrencia,
            o.data_ocorrencia_final,
            o.logradouro
        FROM ocorrencia_primaria p
        INNER JOIN ocorrencias_txt o
        ON p.id_ocorrencia = o.id_ocorrencia
        WHERE p.cod_primaria LIKE :cod AND o.status = 'FECHADO'""")
        df = pd.read_sql(
            query,
            con=engine,
            params={"cod": f"%{primaria.upper()}%"},
        )
        logger.debug(f'Retorno da consulta {len(df)} item(s)')
        return df
    
    except Exception as e:
        logger.error(e)
        raise SystemError("Erro interno do servidor")
