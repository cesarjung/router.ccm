
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, Draw
from shapely.geometry import Point, Polygon
from datetime import datetime, timedelta
import openrouteservice
import webbrowser
import os

st.set_page_config(layout="wide")
col1, col2 = st.columns([0.15, 0.85])
with col1:
    st.image("logo_sirtec.png", width=120)
with col2:
    st.title("CCM - Roteirizador de Vistorias")

ORS_API_KEY = "INSIRA_SUA_CHAVE_AQUI"
client = openrouteservice.Client(key=ORS_API_KEY)

def format_timedelta(td):
    try:
        total_seconds = int(td.total_seconds())
        h, r = divmod(total_seconds, 3600)
        m, _ = divmod(r, 60)
        return f"{h:02}:{m:02}"
    except:
        return "00:00"

def parse_tempo(valor):
    try:
        if pd.isna(valor):
            return timedelta(0)
        valor = str(valor).strip()
        if ":" in valor:
            return pd.to_timedelta(valor)
        if valor.replace(',', '').replace('.', '').isdigit():
            return pd.to_timedelta(float(valor), unit="m")
    except:
        pass
    return timedelta(0)

cor_por_tipo = {
    "OBRA": "green",
    "PLANO MANUT.": "blue",
    "ASSIN. LPT": "orange",
    "ASSIN. VIP's": "purple",
    "PARECER 023": "red",
    "AS BUILT": "darkred"
}

col_in, col_out = st.columns([0.5, 0.5])
with col_in:
    ponto_partida_input = st.text_input("Ponto de partida (lat,lon):")
with col_out:
    ponto_chegada_input = st.text_input("Ponto de chegada (lat,lon) (opcional):")

arquivo = st.file_uploader("Selecione o arquivo Excel:", type=["xlsx"])

col_bt1, col_bt2, col_bt3 = st.columns([1, 1, 1])
with col_bt1:
    botao_roteirizar = st.button("Atualizar Rota")
with col_bt2:
    botao_visualizar = st.button("Visualizar Rota")
with col_bt3:
    botao_exportar = st.button("Exportar Rota")

if arquivo:
    df = pd.read_excel(arquivo, header=5)
    if 'Latitude' not in df or 'Longitude' not in df:
        st.error("Colunas Latitude e Longitude não encontradas.")
        st.stop()

    df = df.dropna(subset=['Latitude', 'Longitude'])
    df['Latitude'] = df['Latitude'].astype(str).str.replace(",", ".", regex=False).astype(float)
    df['Longitude'] = df['Longitude'].astype(str).str.replace(",", ".", regex=False).astype(float)

    municipios = sorted(df['Município'].dropna().unique())
    unidades = sorted(df['Unidade'].dropna().unique())
    sel_municipios = st.multiselect("Filtrar por Município:", municipios, default=municipios)
    sel_unidades = st.multiselect("Filtrar por Unidade:", unidades, default=unidades)
    df = df[df['Município'].isin(sel_municipios) & df['Unidade'].isin(sel_unidades)]

    centro = [df['Latitude'].mean(), df['Longitude'].mean()]
    mapa = folium.Map(location=centro, zoom_start=12)
    Fullscreen().add_to(mapa)
    draw = Draw(export=True, draw_options={"circle": False})
    draw.add_to(mapa)
    cluster = MarkerCluster().add_to(mapa)

    for _, row in df.iterrows():
        cor = cor_por_tipo.get(str(row.get("TIPO", "")).strip(), "gray")
        tooltip_text = f"{row.get('TIPO', '')} - {row.get('Projeto', '')}"
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            tooltip=tooltip_text,
            icon=folium.Icon(color=cor)
        ).add_to(cluster)

    saida = st_folium(mapa, width=1400, height=600, returned_objects=["all_drawings"])
