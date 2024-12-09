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

# Login e senha do CEMADEN (previamente fornecidos)
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBr!'

# Carregar os dados do shapefile de Minas Gerais
mg_gdf = gpd.read_file(shp_mg_url)

# Estações Selecionadas do Sul de Minas Gerais
codigo_estacao = ['314790701A','310710901A','312870901A','315180001A','316930702A','314780801A','315250101A','313240401A','313360001A','311410501A','311360201A','313300601A']

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

# sigla do estado do Brasil
sigla_estado = 'MG'

# Data de hoje
agora = datetime.now()

# Dia, mês e ano de hoje
dia_atual = agora.day
mes_atual = agora.month
ano_atual = agora.year

# Calcula o mês e ano anteriores para a data inicial
if mes_atual == 1:
    mes_anterior = 12
    ano_anterior = ano_atual - 1
else:
    mes_anterior = mes_atual - 1
    ano_anterior = ano_atual

# Formata as datas
diai = '01'
data_inicial = f'{ano_atual}{mes_anterior:02d}{diai}'
data_final = f'{ano_atual}{mes_atual:02d}{dia_atual:02d}'
data_inicial = pd.to_datetime(data_inicial)
data_final = pd.to_datetime(data_final)

def baixar_dados_estacoes(codigo_estacao, data_inicial, data_final, sigla_estado):
    dados_estacoes = {}
    for codigo in codigo_estacao:
        dados_completos = []
        for ano_mes_dia in pd.date_range(data_inicial, data_final, freq='M'):
            ano_mes = ano_mes_dia.strftime('%Y%m')  # Formato '202401'
            sws_url = 'http://sws.cemaden.gov.br/PED/rest/pcds/dados_pcd'
            params = dict(
                rede=11, uf=sigla_estado, inicio=ano_mes, fim=ano_mes, codigo=codigo
            )
            r = requests.get(sws_url, params=params, headers={'token': token})
            dados = r.text
            linhas = dados.split("\n")
            dados_filtrados = "\n".join(linhas[1:])
            df = pd.read_csv(StringIO(dados_filtrados), sep=";")
            dados_completos.append(df)
        if dados_completos:
            dados_estacoes[codigo] = pd.concat(dados_completos)
    return dados_estacoes

def mostrar_graficos(codigo_estacao):
    if codigo_estacao not in somas_por_estacao:
        st.error(f"Estação {codigo_estacao} não encontrada.")
        return
    soma_dia_atual = somas_por_estacao[codigo_estacao]["dia_atual"]
    soma_24h = somas_por_estacao[codigo_estacao]["ultimas_24h"]
    soma_48h = somas_por_estacao[codigo_estacao]["ultimas_48h"]
    horas = ['Dia Atual', '24 Horas', '48 Horas']
    chuva_valores = [soma_dia_atual, soma_24h, soma_48h]
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(horas, chuva_valores, color=['blue', 'orange', 'green'])
    ax.set_ylabel('Precipitação (mm)')
    ax.set_title(f'Precipitação para a Estação {codigo_estacao}')
    st.pyplot(fig)

m = leafmap.Map(center=[-21, -45],zoom_start=8)

st.set_page_config(layout="wide")

dados1 = baixar_dados_estacoes(codigo_estacao, data_inicial, data_final, sigla_estado)

for codigo in list(dados1.keys()):
    valor = dados1[codigo]
    if isinstance(valor, pd.DataFrame) and valor.empty:
        del dados1[codigo]
dados2 = {}
for codigo in dados1.keys():
    df = dados1[codigo][dados1[codigo]['sensor'] != 'intensidade_precipitacao']
    df['datahora'] = pd.to_datetime(df['datahora'])
    df = df.set_index('datahora')
    dados2[codigo] = df

somas_por_estacao = {}
for codigo_estacao, df in dados2.items():
    df.index = pd.to_datetime(df.index)
    inicio_dia_atual = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_24h = agora - timedelta(hours=24)
    inicio_48h = agora - timedelta(hours=48)
    soma_dia_atual = df.loc[df.index >= inicio_dia_atual, 'valor'].sum()
    soma_24h = df.loc[df.index >= inicio_24h, 'valor'].sum()
    soma_48h = df.loc[df.index >= inicio_48h, 'valor'].sum()
    somas_por_estacao[codigo_estacao] = {
        "dia_atual": soma_dia_atual,
        "ultimas_24h": soma_24h,
        "ultimas_48h": soma_48h
    }

for i, row in gdf_mg.iterrows():
    folium.RegularPolygonMarker(
        location=[row['latitude'], row['longitude']],
        color='black',
        fillColor='green',
        numberOfSides=4,
        radius=8,
        popup=f"{row['municipio']} (Código: {row['codEstacao']})"
    ).add_to(m)

m.add_gdf(mg_gdf, layer_name="Minas Gerais")

st.sidebar.header("Filtros de Seleção")
modo_selecao = st.sidebar.radio("Selecionar Estação por:", ('Código'))
if modo_selecao == 'Código':
    estacao_selecionada = st.sidebar.selectbox("Selecione a Estação", gdf_mg['codEstacao'].unique())

mostrar = st.sidebar.checkbox("Gráfico de Precipitação")
if mostrar:
    mostrar_graficos(estacao_selecionada)

m.to_streamlit(width=1300, height=775)
st.write(somas_por_estacao)
st.write(dados2)
