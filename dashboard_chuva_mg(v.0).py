# Importações e configurações existentes (não alteradas)

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

# Estações Selecionadas do Sul de Minas Gerais
codigo_estacao = ['314790701A', '310710901A', '312870901A', '315180001A', '316930702A', '314780801A', 
                  '315250101A', '313240401A', '313360001A', '311410501A', '311360201A', '313300601A']

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

# Configuração de datas iniciais
agora = datetime.now()
dia_atual = agora.day
mes_atual = agora.month
ano_atual = agora.year

if mes_atual == 1:
    mes_anterior = 12
    ano_anterior = ano_atual - 1
else:
    mes_anterior = mes_atual - 1
    ano_anterior = ano_atual

diai = '01'
data_inicial = f'{ano_atual}{mes_anterior:02d}{diai}'
data_final = f'{ano_atual}{mes_atual:02d}{dia_atual:02d}'
data_inicial = pd.to_datetime(data_inicial)
data_final = pd.to_datetime(data_final)

# Função existente para baixar dados
def baixar_dados_estacoes(codigo_estacao, data_inicial, data_final, sigla_estado):
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

# Dados baixados (conforme código original)
dados2 = baixar_dados_estacoes(codigo_estacao, data_inicial, data_final, 'MG')

# Sidebar para seleção de estação e controle do gráfico
st.sidebar.header("Filtros de Seleção")
estacao_selecionada = st.sidebar.selectbox(
    "Selecione a Estação", gdf_mg['codEstacao'].unique()
)
mostrar_grafico = st.sidebar.checkbox("Mostrar gráfico")

# Exibição dos dados da estação selecionada
st.subheader(f"Dados da Estação: {estacao_selecionada}")
if estacao_selecionada in dados2:
    df_selecionado = dados2[estacao_selecionada]
    st.write(df_selecionado.head())  # Exibe os primeiros dados da estação selecionada

# Adição da funcionalidade de gráficos (nova)
if mostrar_grafico and estacao_selecionada in dados2:
    st.subheader(f"Gráfico de Precipitação - Estação {estacao_selecionada}")
    df_selecionado['datahora'] = pd.to_datetime(df_selecionado['datahora'])
    df_selecionado = df_selecionado.set_index('datahora')
    df_precipitacao = df_selecionado[df_selecionado['sensor'] == 'precipitacao']

    # Agregar os dados por dia
    df_precipitacao_resample = df_precipitacao['valor'].resample('D').sum()

    # Gerar gráfico
    fig, ax = plt.subplots(figsize=(10, 5))
    df_precipitacao_resample.plot(ax=ax, color='blue', label='Precipitação Diária')
    ax.set_title(f"Precipitação Diária - Estação {estacao_selecionada}")
    ax.set_ylabel("Precipitação (mm)")
    ax.set_xlabel("Data")
    ax.legend()
    st.pyplot(fig)

# Mapa com folium (código original)
m = leafmap.Map(center=[-21, -45], zoom_start=8)
for i, row in gdf_mg.iterrows():
    folium.Marker(
        [row['latitude'], row['longitude']],
        popup=f"Estação: {row['municipio']} (Código: {row['codEstacao']})"
    ).add_to(m)
m.to_streamlit(width=1300, height=775)
