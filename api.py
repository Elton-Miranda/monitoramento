import streamlit as st

from os import getenv
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

@st.cache_resource
def open_connection():
    url = getenv('DBURL', "")
    engine = create_engine(url, echo=False)
    return engine