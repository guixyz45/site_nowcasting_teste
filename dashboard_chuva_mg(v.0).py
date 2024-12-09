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

# Função para baixar dados da estação
def baixar_dados_estacoes(codigo, data_especifica, sigla_estado):
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
        return df
    return pd.DataFrame()

# Configuração do mapa
m = leafmap.Map(center=[-21, -45], zoom_start=8, draw_control=False, measure_control=False)

# Barra lateral
st.sidebar.header("Filtros de Seleção")

# Opção de seleção da estação
estacao_selecionada = st.sidebar.selectbox("Selecione a Estação (Código)", codigo_estacao)

# Seleção da data
data_especifica = st.sidebar.date_input("Selecione a Data", value=datetime.now()).strftime('%Y%m%d')

# Botão para baixar dados
if st.sidebar.button("Baixar Dados"):
    dados_baixados = baixar_dados_estacoes(estacao_selecionada, data_especifica, 'MG')
    st.session_state['dados_baixados'] = dados_baixados
else:
    dados_baixados = st.session_state.get('dados_baixados', pd.DataFrame())

# Adicionar marcadores das estações meteorológicas
for i, row in gdf_mg.iterrows():    
    # Adicionar marcador com valor
    folium.RegularPolygonMarker(
        location=[row['latitude'], row['longitude']],
        color='black',
        opacity=1,
        weight=1,
        fillColor='green',
        fillOpacity=1,
        numberOfSides=4,
        rotation=45,
        radius=8,
        popup=f"{row['municipio']} (Código: {row['codEstacao']})"
    ).add_to(m)

m.add_gdf(
    mg_gdf, 
    layer_name="Minas Gerais", 
    style={"color": "black", "weight": 1, "fillOpacity": 0, "interactive": False},
    info_mode=None
)

# Adicionar marcador específico para a estação selecionada
if not dados_baixados.empty:
    latitude = gdf_mg[gdf_mg['codEstacao'] == estacao_selecionada]['latitude'].values[0]
    longitude = gdf_mg[gdf_mg['codEstacao'] == estacao_selecionada]['longitude'].values[0]
    chuva_total = dados_baixados['valor'].sum()

    folium.Marker(
        location=[latitude, longitude],
        popup=f"Estação: {estacao_selecionada}<br>Chuva Total: {chuva_total:.2f} mm",
        icon=folium.Icon(color='green', icon='cloud')
    ).add_to(m)

# Adicionar legenda na barra lateral
st.sidebar.subheader("Legenda:")
st.sidebar.markdown("""
- **Azul**: Estações cadastradas  
- **Verde**: Estação selecionada e dados disponíveis
""")

# Exibir o mapa
m.to_streamlit(width=1300, height=775)

# Mostrar os dados da estação selecionada
if not dados_baixados.empty:
    st.subheader(f"Dados da Estação: {estacao_selecionada}")
    st.dataframe(dados_baixados)
else:
    st.warning("Nenhum dado encontrado para a data selecionada.")
