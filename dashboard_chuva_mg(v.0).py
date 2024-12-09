import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import numpy as np
from datetime import datetime, timedelta
import leafmap.foliumap as leafmap
import folium
import glob
import calendar
from io import StringIO
import matplotlib.pyplot as plt
from folium.plugins import MarkerCluster

# URLs e caminhos de arquivos
shp_mg_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'input;/filtered_data.csv'

# Login e senha do CEMADEN
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBr!'

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(shp_mg_url)

# Estações Selecionadas
codigo_estacao = ['314790701A', '310710901A', '312870901A', '315180001A', '316930702A', '314780801A', 
                  '315250101A', '313240401A', '313360001A', '311410501A', '311360201A', '313300601A']

# Carregar os dados das estações
df1 = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(df1['longitude'], df1['latitude']))

# Filtrar para Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Configuração de página
st.set_page_config(layout="wide")

# Map
m = leafmap.Map(center=[-21, -45], zoom_start=8)

for i, row in gdf_mg.iterrows():
    folium.Marker(
        [row['latitude'], row['longitude']],
        popup=f"Estação: {row['municipio']} (Código: {row['codEstacao']})"
    ).add_to(m)

# Recuperação do token
token_url = 'http://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens'
login_payload = {'email': login, 'password': senha}
response = requests.post(token_url, json=login_payload)
content = response.json()
token = content['token']

# Função para baixar os dados
def baixar_dados_estacoes(codigo_estacao, data_inicial, data_final, sigla_estado='MG'):
    dados_estacoes = {}
    for codigo in codigo_estacao:
        dados_completos = []
        for ano_mes_dia in pd.date_range(data_inicial, data_final, freq='M'):
            ano_mes = ano_mes_dia.strftime('%Y%m')
            sws_url = 'http://sws.cemaden.gov.br/PED/rest/pcds/dados_pcd'
            params = {'rede': 11, 'uf': sigla_estado, 'inicio': ano_mes, 'fim': ano_mes, 'codigo': codigo}
            r = requests.get(sws_url, params=params, headers={'token': token})
            dados = r.text
            linhas = dados.split("\n")
            dados_filtrados = "\n".join(linhas[1:])
            df = pd.read_csv(StringIO(dados_filtrados), sep=";")
            dados_completos.append(df)
        if dados_completos:
            dados_estacoes[codigo] = pd.concat(dados_completos)
    return dados_estacoes

# Baixar dados
data_inicial = datetime.now() - timedelta(days=30)
data_final = datetime.now()
dados_estacoes = baixar_dados_estacoes(codigo_estacao, data_inicial, data_final)

# Sidebar
st.sidebar.header("Filtros")
estacao_selecionada = st.sidebar.selectbox(
    "Selecione uma estação", 
    options=gdf_mg['codEstacao'].unique()
)
exibir_grafico = st.sidebar.checkbox("Exibir gráfico de precipitação")

# Mostrar dados da estação selecionada
if estacao_selecionada:
    st.subheader(f"Estação Selecionada: {estacao_selecionada}")
    if estacao_selecionada in dados_estacoes:
        df_estacao = dados_estacoes[estacao_selecionada]
        st.write(df_estacao.head())
    else:
        st.warning("Nenhum dado encontrado para a estação selecionada.")

# Mostrar gráfico
if exibir_grafico and estacao_selecionada in dados_estacoes:
    df_estacao = dados_estacoes[estacao_selecionada]
    df_estacao['datahora'] = pd.to_datetime(df_estacao['datahora'])
    df_estacao.set_index('datahora', inplace=True)
    df_precipitacao = df_estacao[df_estacao['sensor'] == 'precipitacao']
    
    # Agregação dos dados
    df_precipitacao_resample = df_precipitacao['valor'].resample('D').sum()
    
    # Criar gráfico
    fig, ax = plt.subplots(figsize=(10, 5))
    df_precipitacao_resample.plot(ax=ax, color='blue', label='Precipitação Diária')
    ax.set_title(f"Precipitação Diária - {estacao_selecionada}")
    ax.set_ylabel("Precipitação (mm)")
    ax.set_xlabel("Data")
    ax.legend()
    st.pyplot(fig)

# Mostrar mapa
m.to_streamlit(width=700, height=500)
