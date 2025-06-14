
import streamlit as st
import pandas as pd
import folium
import webbrowser
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import Point, Polygon
import openrouteservice
from openrouteservice import convert
import tempfile
import os

# Configurações da página
st.set_page_config(layout="wide", page_title="Roteirizador CCM")
st.markdown("<h1 style='text-align: left;'>Roteirizador CCM</h1>", unsafe_allow_html=True)

# Exibe logo
st.image("logo_sirtec.png", width=120)

# Leitura da base
@st.cache_data
def carregar_base():
    return pd.read_excel("base_servicos.xlsx")

df_original = carregar_base()

# Filtros
col1, col2 = st.columns(2)
with col1:
    municipios = st.multiselect("Filtrar por Município:", sorted(df_original["Município"].unique()), default=list(df_original["Município"].unique()))
with col2:
    unidades = st.multiselect("Filtrar por Unidade:", sorted(df_original["Unidade"].unique()), default=list(df_original["Unidade"].unique()))

df = df_original[df_original["Município"].isin(municipios) & df_original["Unidade"].isin(unidades)]

# Mapa base
m = folium.Map(location=[-29.68, -53.80], zoom_start=8)
draw = Draw(export=True)
draw.add_to(m)

# Adiciona pontos no mapa
tipo_cor = {
    "OBRA": "green",
    "PLANO MANUT.": "blue",
    "ASSIN. LPT": "orange",
    "ASSIN. VIP's": "purple",
    "PARECER 023": "red",
    "AS BUILT": "darkred"
}
for _, row in df.iterrows():
    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        tooltip=f"{row['TIPO']} - {row['Projeto']}",
        icon=folium.Icon(color=tipo_cor.get(row["TIPO"], "gray"))
    ).add_to(m)

# Exibe mapa
st_data = st_folium(m, width=1200, height=500)

# Entrada e botões
col3, col4 = st.columns([2, 3])
with col3:
    inicio = st.text_input("Endereço de início da rota (lat,lon)", "-29.68,-53.80")
    fim = st.text_input("Endereço de fim da rota (lat,lon)", "-29.68,-53.80")

with col4:
    gerar = st.button("Atualizar Rota")
    visualizar = st.button("Visualizar Rota")
    exportar = st.button("Exportar Rota")

# Processamento
if gerar:
    try:
        coords = [[float(x) for x in inicio.split(",")]]
        for _, row in df.iterrows():
            coords.append([row["Latitude"], row["Longitude"]])
        coords.append([float(x) for x in fim.split(",")])

        client = openrouteservice.Client(key="sua-chave-ors")
        routes = client.directions(coords, profile='driving-car', format='geojson')

        tempos = []
        acumulado = 0
        for i in range(len(coords)-1):
            res = client.directions([coords[i], coords[i+1]], profile='driving-car')
            tempo_seg = res['routes'][0]['summary']['duration']
            tempo_min = round(tempo_seg / 60)
            deslocamento = tempo_min
            tempo_exec = df.iloc[i]["TEMPO"] if "TEMPO" in df.columns else 0
            acumulado += deslocamento + tempo_exec
            tempos.append((tempo_exec, deslocamento, acumulado))

        df_resultado = df.copy()
        df_resultado["Tempo Execução"] = [t[0] for t in tempos]
        df_resultado["Tempo Deslocamento"] = [t[1] for t in tempos]
        df_resultado["Total Acumulado"] = [t[2] for t in tempos]

        st.dataframe(df_resultado[["TIPO", "Unidade", "Projeto", "Município", "Latitude", "Longitude", "Tempo Execução", "Tempo Deslocamento", "Total Acumulado"]])
        st.session_state["df_resultado"] = df_resultado
        st.success("Rota processada com sucesso!")

    except Exception as e:
        st.error(f"Erro ao gerar rota: {e}")

if visualizar and "df_resultado" in st.session_state:
    mapa_rota = folium.Map(location=[-29.68, -53.80], zoom_start=8)
    for _, row in st.session_state["df_resultado"].iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            tooltip=f"{row['TIPO']} - {row['Projeto']}",
            icon=folium.Icon(color=tipo_cor.get(row["TIPO"], "gray"))
        ).add_to(mapa_rota)

    coords_rota = [[float(x) for x in inicio.split(",")]] + [[row["Latitude"], row["Longitude"]] for _, row in st.session_state["df_resultado"].iterrows()] + [[float(x) for x in fim.split(",")]]
    rota = client.directions(coords_rota, profile='driving-car', format='geojson')
    folium.GeoJson(rota, name="Rota").add_to(mapa_rota)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmpfile:
        mapa_rota.save(tmpfile.name)
        webbrowser.open("file://" + tmpfile.name)

if exportar and "df_resultado" in st.session_state:
    df_resultado = st.session_state["df_resultado"]
    excel_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df_resultado.to_excel(excel_file.name, index=False)
    with open(excel_file.name, "rb") as f:
        st.download_button("Clique aqui para baixar o roteiro", data=f.read(), file_name="roteiro.xlsx")
