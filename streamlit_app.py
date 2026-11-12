import streamlit as st

from ui.dashboard import run

st.set_page_config(page_title="Market Pulse", page_icon="◒", layout="wide")
run()