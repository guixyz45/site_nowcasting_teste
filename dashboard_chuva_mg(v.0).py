import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import numpy as np
from datetime import datetime, timedelta
import leafmap.foliumap as leafmap
import folium
from folium.plugins import MarkerCluster
from io import StringIO
import matplotlib.pyplot as plt

# URLs e caminhos de arquivos
shp_mg_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'input;/filtered_data.csv'

# Login e senha do CEMADEN
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBr!'

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(shp_mg_url)

# Estações Selecionadas do Sul de Minas Gerais
codigo_estacao = ['314790701A', '310710901A', '312870901A', '315180001A', 
                  '316930702A', '314780801A', '315250101A', '313240401A', 
                  '313360001A', '311410501A', '311360201A', '313300601A']

# Carregar os dados das estações
df1 = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(df1['longitude'], df1['latitude']))

# Realizar o filtro espacial: apenas estações dentro de Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Recuperação do token
token_url = 'http://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens'
login_payload = {'email': login, 'password': senha}
response = requests.post(token_url, json=login_payload)
content = response.json()
token = content['token']

# Defina o layout da página como largo
st.set_page_config(layout="wide")

# Data de hoje
agora = datetime.now()

# Função para baixar dados das estações
def baixar_dados_estacoes(codigo_estacao, data_especifica, sigla_estado):
    dados_estacoes = {}
    for codigo in codigo_estacao:
        sws_url = 'http://sws.cemaden.gov.br/PED/rest/pcds/dados_pcd'
        params = dict(rede=11, uf=sigla_estado, inicio=data_especifica, fim=data_especifica, codigo=codigo)
        r = requests.get(sws_url, params=params, headers={'token': token})
        dados = r.text
        linhas = dados.split("\n")
        dados_filtrados = "\n".join(linhas[1:])
        df = pd.read_csv(StringIO(dados_filtrados), sep=";")
        if not df.empty:
            df['datahora'] = pd.to_datetime(df['datahora'])
            df = df.set_index('datahora')
            dados_estacoes[codigo] = df
    return dados_estacoes

# Configuração do mapa
m = leafmap.Map(center=[-21, -45], zoom_start=8, draw_control=False, measure_control=False)

# Barra lateral
st.sidebar.header("Filtros de Seleção")
data_especifica = st.sidebar.date_input("Selecione a Data", value=datetime.now()).strftime('%Y%m%d')

if st.sidebar.button("Baixar Dados"):
    dados_baixados = baixar_dados_estacoes(codigo_estacao, data_especifica, 'MG')
    st.session_state['dados_baixados'] = dados_baixados
else:
    dados_baixados = st.session_state.get('dados_baixados', {})

# Adicionar marcadores no mapa para as estações
for _, row in gdf_mg.iterrows():
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=f"Município: {row['municipio']}<br>Código: {row['codEstacao']}",
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(m)

# Adicionar marcadores de precipitação no mapa
if dados_baixados:
    for codigo, df in dados_baixados.items():
        latitude = gdf_mg[gdf_mg['codEstacao'] == codigo]['latitude'].values[0]
        longitude = gdf_mg[gdf_mg['codEstacao'] == codigo]['longitude'].values[0]
        chuva_total = df['valor'].sum()

        # Determinar a cor do marcador com base na chuva total
        if chuva_total <= 10:
            color = 'green'
        elif chuva_total <= 50:
            color = 'orange'
        else:
            color = 'red'

        folium.CircleMarker(
            location=[latitude, longitude],
            radius=10,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=f"Estação: {codigo}<br>Chuva Total: {chuva_total:.2f} mm"
        ).add_to(m)

# Exibir o mapa
m.to_streamlit(width=1300, height=775)

# Mostrar os dados da estação
if dados_baixados:
    for codigo, df in dados_baixados.items():
        st.subheader(f"Dados da Estação: {codigo}")
        st.dataframe(df)
else:
    st.warning("Nenhum dado encontrado para a data selecionada.")
